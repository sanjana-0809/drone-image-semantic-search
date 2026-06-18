"""AI image understanding pipeline for uploaded drone imagery."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from .config import get_settings


settings = get_settings()
Image.MAX_IMAGE_PIXELS = settings.max_image_pixels
logger = logging.getLogger(__name__)

_ocr_reader = None
_blip_processor = None
_blip_model = None
_yolo_model = None
_sahi_model = None
_clip_model = None
_clip_preprocess = None
_clip_tokenizer = None


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_torch_device():
    """Return the preferred inference device without forcing GPU unexpectedly."""
    import torch

    requested = os.getenv("AI_DEVICE", "").strip().lower()
    use_gpu = _bool_env("USE_GPU")

    if requested == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    if requested in {"cuda", "gpu"} or (not requested and use_gpu):
        if torch.cuda.is_available():
            return torch.device("cuda")
        logger.warning("GPU inference requested but CUDA is unavailable; using CPU")
        return torch.device("cpu")

    if requested == "mps":
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return torch.device("mps")
        logger.warning("MPS inference requested but unavailable; using CPU")

    return torch.device("cpu")


def _model_device(model):
    try:
        return next(model.parameters()).device
    except StopIteration:
        return _get_torch_device()


def _move_to_device(inputs, device):
    if hasattr(inputs, "to"):
        return inputs.to(device)
    return {
        key: value.to(device) if hasattr(value, "to") else value
        for key, value in inputs.items()
    }


def _resize_to_max_side(image: Image.Image, max_side: int | None) -> Image.Image:
    if not max_side or max_side <= 0:
        return image

    width, height = image.size
    longest_side = max(width, height)
    if longest_side <= max_side:
        return image

    scale = max_side / longest_side
    size = (
        max(1, round(width * scale)),
        max(1, round(height * scale)),
    )
    return image.resize(size, Image.Resampling.LANCZOS)


def _get_ocr():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr

        use_gpu = _bool_env("USE_GPU")
        # EasyOCR downloads model weights on first use. The default (~/.EasyOCR)
        # is not writable for the non-root container user, so point it at a
        # directory we control and create it up front.
        storage_dir = os.getenv("EASYOCR_STORAGE_DIR", str(settings.backend_dir / ".easyocr"))
        os.makedirs(storage_dir, exist_ok=True)
        _ocr_reader = easyocr.Reader(
            ["en"],
            gpu=use_gpu,
            model_storage_directory=storage_dir,
            user_network_directory=storage_dir,
            download_enabled=True,
        )
        logger.info("EasyOCR loaded (storage=%s)", storage_dir)
    return _ocr_reader


def _get_blip():
    global _blip_processor, _blip_model
    if _blip_model is None:
        from transformers import BlipForConditionalGeneration, BlipProcessor

        model_name = os.getenv("BLIP_MODEL_NAME", "Salesforce/blip-image-captioning-base")
        _blip_processor = BlipProcessor.from_pretrained(model_name)
        _blip_model = BlipForConditionalGeneration.from_pretrained(model_name)
        _blip_model.to(_get_torch_device())
        _blip_model.eval()
        logger.info("BLIP captioning model loaded: %s", model_name)
    return _blip_processor, _blip_model


def _load_yolo_model():
    from ultralytics import YOLO

    model_name = os.getenv("YOLO_MODEL_NAME", "yolov8s.pt")
    try:
        return YOLO(model_name)
    except Exception as exc:
        allow_unsafe = os.getenv("ALLOW_UNSAFE_YOLO_LOAD", "false").lower() == "true"
        if not allow_unsafe:
            raise RuntimeError(
                "YOLO model loading failed. If you trust the model file and need legacy "
                "PyTorch checkpoint loading, set ALLOW_UNSAFE_YOLO_LOAD=true."
            ) from exc

        import torch

        logger.warning("Using unsafe YOLO checkpoint loading because ALLOW_UNSAFE_YOLO_LOAD=true")
        original_load = torch.load

        def patched_load(*args, **kwargs):
            kwargs["weights_only"] = False
            return original_load(*args, **kwargs)

        try:
            torch.load = patched_load
            return YOLO(model_name)
        finally:
            torch.load = original_load


def _get_yolo():
    global _yolo_model
    if _yolo_model is None:
        _yolo_model = _load_yolo_model()
        logger.info("YOLO model loaded")
    return _yolo_model


def _get_clip():
    global _clip_model, _clip_preprocess, _clip_tokenizer
    if _clip_model is None:
        import open_clip

        model_name = os.getenv("CLIP_MODEL_NAME", "ViT-L-14")
        pretrained = os.getenv("CLIP_PRETRAINED", "laion2b_s32b_b82k")
        _clip_model, _, _clip_preprocess = open_clip.create_model_and_transforms(
            model_name,
            pretrained=pretrained,
        )
        _clip_tokenizer = open_clip.get_tokenizer(model_name)
        _clip_model.to(_get_torch_device())
        _clip_model.eval()
        logger.info("CLIP model loaded: %s / %s", model_name, pretrained)
    return _clip_model, _clip_preprocess, _clip_tokenizer


def _open_rgb_image(image_path: str, max_side: int | None = None) -> Image.Image:
    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image)
        rgb_image = image.convert("RGB")

    return _resize_to_max_side(rgb_image, max_side)


def extract_ocr_text(image_path: str) -> str:
    """Extract visible text from an image using EasyOCR.

    Returns an empty string when no text is found. Raises on a real failure
    (e.g. model load error) so the caller can record it instead of silently
    treating a crash as "no text".
    """
    reader = _get_ocr()
    max_side = _int_env("OCR_IMAGE_MAX_SIDE", 2048)
    confidence_threshold = _float_env("OCR_CONFIDENCE_THRESHOLD", 0.3)

    with _open_rgb_image(image_path, max_side=max_side) as image:
        if _bool_env("OCR_ENHANCE_IMAGE", True):
            image = ImageEnhance.Contrast(image).enhance(1.25)
            image = ImageEnhance.Sharpness(image).enhance(1.1)
        ocr_image = np.asarray(image).copy()

    results = reader.readtext(ocr_image)
    texts = [
        str(result[1]).strip()
        for result in results
        if float(result[2]) > confidence_threshold and str(result[1]).strip()
    ]
    return " | ".join(texts)[:2000]


def generate_caption(image_path: str) -> str:
    """Generate a scene caption using BLIP. Raises on failure so the caller can record it."""
    import torch

    processor, model = _get_blip()
    device = _model_device(model)
    max_side = _int_env("BLIP_IMAGE_MAX_SIDE", 1024)
    max_new_tokens = _int_env("BLIP_MAX_NEW_TOKENS", 50)

    with _open_rgb_image(image_path, max_side=max_side) as image:
        inputs = processor(image, return_tensors="pt")

    inputs = _move_to_device(inputs, device)
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=max_new_tokens)
    caption = processor.decode(output[0], skip_special_tokens=True)
    return caption.strip()[:500]


def _get_sahi_model():
    """Wrap the configured YOLO weights in a SAHI detection model (cached)."""
    global _sahi_model
    if _sahi_model is None:
        from sahi import AutoDetectionModel

        model_name = os.getenv("YOLO_MODEL_NAME", "yolov8s.pt")
        device = _get_torch_device()
        device_str = "cuda:0" if device.type == "cuda" else device.type
        confidence = _float_env("YOLO_CONFIDENCE", 0.2)

        # SAHI renamed the Ultralytics backend from "yolov8" to "ultralytics"
        # across versions; try the current name first, then the legacy one.
        last_err: Exception | None = None
        for model_type in ("ultralytics", "yolov8"):
            try:
                _sahi_model = AutoDetectionModel.from_pretrained(
                    model_type=model_type,
                    model_path=model_name,
                    confidence_threshold=confidence,
                    device=device_str,
                )
                logger.info("SAHI detection model loaded (%s): %s", model_type, model_name)
                break
            except Exception as exc:  # noqa: BLE001 - probe the next backend name
                last_err = exc
        if _sahi_model is None:
            raise RuntimeError(f"Could not initialise SAHI detection model: {last_err}")
    return _sahi_model


def _detect_objects_sahi(image_path: str) -> list[str]:
    """Sliced (tiled) detection for small top-down aerial objects.

    Slicing a large tile into overlapping crops makes each object relatively
    larger per inference, which is what lets a general detector pick up small
    overhead vehicles/people that whole-image inference misses entirely.
    """
    from sahi.predict import get_sliced_prediction

    model = _get_sahi_model()
    slice_size = _int_env("SAHI_SLICE_SIZE", 640)
    overlap = _float_env("SAHI_OVERLAP_RATIO", 0.2)

    result = get_sliced_prediction(
        image_path,
        model,
        slice_height=slice_size,
        slice_width=slice_size,
        overlap_height_ratio=overlap,
        overlap_width_ratio=overlap,
        verbose=0,
    )

    detected: list[str] = []
    for obj in result.object_prediction_list:
        label = str(obj.category.name)
        if label and label not in detected:
            detected.append(label)
    return detected[:50]


def _detect_objects_yolo(image_path: str) -> list[str]:
    """Whole-image YOLO detection (no tiling)."""
    model = _get_yolo()
    device = _get_torch_device()
    device_arg = 0 if device.type == "cuda" else device.type
    confidence = _float_env("YOLO_CONFIDENCE", 0.2)
    image_size = _int_env("YOLO_IMAGE_SIZE", 1280)
    results = model(
        image_path,
        verbose=False,
        conf=confidence,
        imgsz=image_size,
        device=device_arg,
    )

    detected: list[str] = []
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            label = str(model.names[class_id])
            if label not in detected:
                detected.append(label)

    return detected[:50]


def detect_objects(image_path: str) -> list[str]:
    """Detect objects, defaulting to SAHI tiled inference for aerial imagery.

    Strategy (each degrades to the next, so detection never hard-fails the upload):
      1. SAHI sliced inference - best recall for small top-down objects.
      2. Whole-image YOLO - if SAHI is unavailable or errors.
    Raises only if both paths fail, so ``process_image`` can record the failure.

    The detector still uses general (COCO) classes by default; point
    ``YOLO_MODEL_NAME`` at VisDrone/DOTA weights for aerial-specific classes.
    """
    backend = os.getenv("DETECTION_BACKEND", "sahi").strip().lower()

    if backend == "sahi":
        try:
            return _detect_objects_sahi(image_path)
        except Exception:
            logger.exception(
                "SAHI detection failed for %s; falling back to whole-image YOLO",
                Path(image_path).name,
            )

    return _detect_objects_yolo(image_path)


def extract_dominant_colors(image_path: str, k: int = 3) -> list[str]:
    """Extract top-k dominant colors from a resized image sample. Raises on failure."""
    color_count = max(1, min(k, 8))
    max_side = _int_env("COLOR_SAMPLE_MAX_SIDE", 160)

    with _open_rgb_image(image_path, max_side=max_side) as image:
        quantized = image.quantize(
            colors=color_count,
            method=Image.Quantize.MEDIANCUT,
            dither=Image.Dither.NONE,
        )
        palette = quantized.getpalette() or []
        color_bins = quantized.getcolors(maxcolors=image.width * image.height) or []

    colors = []
    for _, palette_index in sorted(color_bins, reverse=True):
        offset = palette_index * 3
        red, green, blue = palette[offset : offset + 3]
        colors.append(f"#{red:02x}{green:02x}{blue:02x}")
        if len(colors) == color_count:
            break

    return colors


def process_image(image_path: str) -> tuple[dict, dict[str, str]]:
    """Run the full AI understanding pipeline on a single image.

    Each stage runs independently: one failing stage does not abort the others.
    Returns ``(results, stage_errors)`` where ``stage_errors`` maps the name of
    any stage that raised to its error message, so the caller can distinguish a
    genuinely empty result from a silent failure.
    """
    filename = Path(image_path).name
    logger.info("Processing image: %s", filename)

    stages: list[tuple[str, Any, Any]] = [
        ("caption", generate_caption, ""),
        ("detected_objects", detect_objects, []),
        ("dominant_colors", extract_dominant_colors, []),
        ("ocr_text", extract_ocr_text, ""),
    ]

    results: dict = {}
    stage_errors: dict[str, str] = {}
    for key, func, default in stages:
        try:
            results[key] = func(image_path)
        except Exception as exc:  # noqa: BLE001 - one stage must not abort the rest
            logger.exception("%s stage failed for %s", key, filename)
            results[key] = default
            stage_errors[key] = str(exc) or exc.__class__.__name__

    return results, stage_errors


def generate_clip_embedding(image_path: str) -> list[float]:
    """Generate a normalized CLIP image embedding."""
    import torch

    model, preprocess, _ = _get_clip()
    device = _model_device(model)
    max_side = _int_env("CLIP_IMAGE_MAX_SIDE", 2048)

    with _open_rgb_image(image_path, max_side=max_side) as image:
        image_tensor = preprocess(image).unsqueeze(0)

    image_tensor = image_tensor.to(device)
    with torch.inference_mode():
        embedding = model.encode_image(image_tensor)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

    return embedding.squeeze().cpu().numpy().tolist()


def text_to_embedding(text: str) -> list[float]:
    """Convert a text query to a normalized CLIP embedding."""
    import torch

    model, _, tokenizer = _get_clip()
    safe_text = " ".join(text.split())[:500]
    expanded = (
        f"{safe_text}, aerial view, drone footage, {safe_text} from above, "
        f"satellite view of {safe_text}"
    )

    device = _model_device(model)
    tokens = tokenizer([expanded]).to(device)
    with torch.inference_mode():
        embedding = model.encode_text(tokens)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

    return embedding.squeeze().cpu().numpy().tolist()
