"""AI image understanding pipeline for uploaded drone imagery."""
# redeined
from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from .config import get_settings


settings = get_settings()
Image.MAX_IMAGE_PIXELS = settings.max_image_pixels
logger = logging.getLogger(__name__)

_ocr_reader = None
_blip_processor = None
_blip_model = None
_yolo_model = None
_clip_model = None
_clip_preprocess = None
_clip_tokenizer = None


def _get_ocr():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr

        use_gpu = os.getenv("USE_GPU", "false").lower() == "true"
        _ocr_reader = easyocr.Reader(["en"], gpu=use_gpu)
        logger.info("EasyOCR loaded")
    return _ocr_reader


def _get_blip():
    global _blip_processor, _blip_model
    if _blip_model is None:
        from transformers import BlipForConditionalGeneration, BlipProcessor

        model_name = os.getenv("BLIP_MODEL_NAME", "Salesforce/blip-image-captioning-base")
        _blip_processor = BlipProcessor.from_pretrained(model_name)
        _blip_model = BlipForConditionalGeneration.from_pretrained(model_name)
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
        _clip_model.eval()
        logger.info("CLIP model loaded: %s / %s", model_name, pretrained)
    return _clip_model, _clip_preprocess, _clip_tokenizer


def _open_rgb_image(image_path: str) -> Image.Image:
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image)
    return image.convert("RGB")


def extract_ocr_text(image_path: str) -> str:
    """Extract visible text from an image using EasyOCR."""
    try:
        reader = _get_ocr()
        results = reader.readtext(image_path)
        texts = [str(result[1]).strip() for result in results if result[2] > 0.3 and str(result[1]).strip()]
        return " | ".join(texts)[:2000]
    except Exception:
        logger.exception("OCR failed for %s", Path(image_path).name)
        return ""


def generate_caption(image_path: str) -> str:
    """Generate a scene caption using BLIP."""
    try:
        import torch

        processor, model = _get_blip()
        with _open_rgb_image(image_path) as image:
            image = image.resize((384, 384))
            inputs = processor(image, return_tensors="pt")

        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=50)
        caption = processor.decode(output[0], skip_special_tokens=True)
        return caption.strip()[:500]
    except Exception:
        logger.exception("Captioning failed for %s", Path(image_path).name)
        return ""


def detect_objects(image_path: str) -> list[str]:
    """Detect objects using YOLO."""
    try:
        model = _get_yolo()
        results = model(image_path, verbose=False, conf=0.3)

        detected: list[str] = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                label = str(model.names[class_id])
                if label not in detected:
                    detected.append(label)

        return detected[:50]
    except Exception:
        logger.exception("Object detection failed for %s", Path(image_path).name)
        return []


def extract_dominant_colors(image_path: str, k: int = 3) -> list[str]:
    """Extract top-k dominant colors using K-means clustering."""
    try:
        import cv2
        from sklearn.cluster import KMeans

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("OpenCV could not read image")

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (100, 100))
        pixels = img.reshape(-1, 3).astype(np.float32)

        kmeans = KMeans(n_clusters=max(1, min(k, 8)), n_init=10, random_state=42)
        kmeans.fit(pixels)

        colors = []
        for center in kmeans.cluster_centers_:
            red, green, blue = int(center[0]), int(center[1]), int(center[2])
            colors.append(f"#{red:02x}{green:02x}{blue:02x}")
        return colors
    except Exception:
        logger.exception("Color extraction failed for %s", Path(image_path).name)
        return []


def process_image(image_path: str) -> dict:
    """Run the full AI understanding pipeline on a single image."""
    filename = Path(image_path).name
    logger.info("Processing image: %s", filename)

    return {
        "caption": generate_caption(image_path),
        "detected_objects": detect_objects(image_path),
        "dominant_colors": extract_dominant_colors(image_path),
        "ocr_text": extract_ocr_text(image_path),
    }


def generate_clip_embedding(image_path: str) -> list[float]:
    """Generate a normalized CLIP image embedding."""
    import torch

    model, preprocess, _ = _get_clip()
    with _open_rgb_image(image_path) as image:
        image_tensor = preprocess(image).unsqueeze(0)

    with torch.no_grad():
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

    tokens = tokenizer([expanded])
    with torch.no_grad():
        embedding = model.encode_text(tokens)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

    return embedding.squeeze().cpu().numpy().tolist()
