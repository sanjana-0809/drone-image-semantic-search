"""
AI Image Understanding Pipeline
Runs 4 models on every uploaded drone image:
1. EasyOCR — extract visible text
2. BLIP-2 (base) — generate scene caption
3. YOLOv8 nano — detect objects
4. OpenCV — extract dominant colors
Plus CLIP embedding generation for vector search.
"""

import os
import numpy as np
from PIL import Image

# ─── Lazy-loaded model singletons ───────────────────────────────
# Models are heavy — load once, reuse forever.

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
        _ocr_reader = easyocr.Reader(["en"], gpu=False)
        print("✅ EasyOCR loaded")
    return _ocr_reader


def _get_blip():
    global _blip_processor, _blip_model
    if _blip_model is None:
        from transformers import BlipProcessor, BlipForConditionalGeneration
        model_name = "Salesforce/blip-image-captioning-base"
        _blip_processor = BlipProcessor.from_pretrained(model_name)
        _blip_model = BlipForConditionalGeneration.from_pretrained(model_name)
        print("✅ BLIP captioning model loaded")
    return _blip_processor, _blip_model


def _get_yolo():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        _yolo_model = YOLO("yolov8n.pt")  # nano — fastest
        print("✅ YOLOv8 nano loaded")
    return _yolo_model


def _get_clip():
    global _clip_model, _clip_preprocess, _clip_tokenizer
    if _clip_model is None:
        import open_clip
        _clip_model, _, _clip_preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        _clip_tokenizer = open_clip.get_tokenizer("ViT-B-32")
        _clip_model.eval()
        print("✅ CLIP ViT-B/32 loaded")
    return _clip_model, _clip_preprocess, _clip_tokenizer


# ─── Pipeline Steps ────────────────────────────────────────────

def extract_ocr_text(image_path: str) -> str:
    """Step 1: Extract any visible text from the image using EasyOCR."""
    try:
        reader = _get_ocr()
        results = reader.readtext(image_path)
        texts = [r[1] for r in results if r[2] > 0.3]  # confidence > 0.3
        return " | ".join(texts) if texts else ""
    except Exception as e:
        print(f"  ⚠️ OCR failed: {e}")
        return ""


def generate_caption(image_path: str) -> str:
    """Step 2: Generate a scene caption using BLIP-2 base."""
    try:
        processor, model = _get_blip()
        image = Image.open(image_path).convert("RGB")
        
        # Resize for speed — BLIP doesn't need full resolution
        image.thumbnail((384, 384))
        
        inputs = processor(image, return_tensors="pt")
        output = model.generate(**inputs, max_new_tokens=50)
        caption = processor.decode(output[0], skip_special_tokens=True)
        return caption.strip()
    except Exception as e:
        print(f"  ⚠️ Caption failed: {e}")
        return ""


def detect_objects(image_path: str) -> list:
    """Step 3: Detect objects using YOLOv8 nano."""
    try:
        model = _get_yolo()
        results = model(image_path, verbose=False, conf=0.3)
        
        detected = []
        for r in results:
            for box in r.boxes:
                class_id = int(box.cls[0])
                label = model.names[class_id]
                confidence = float(box.conf[0])
                if label not in detected:  # deduplicate
                    detected.append(label)
        
        return detected
    except Exception as e:
        print(f"  ⚠️ Object detection failed: {e}")
        return []


def extract_dominant_colors(image_path: str, k: int = 3) -> list:
    """Step 4: Extract top-k dominant colors using K-means clustering."""
    try:
        import cv2
        from sklearn.cluster import KMeans
        
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (100, 100))  # small for speed
        
        pixels = img.reshape(-1, 3).astype(np.float32)
        
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
        kmeans.fit(pixels)
        
        colors = []
        for center in kmeans.cluster_centers_:
            r, g, b = int(center[0]), int(center[1]), int(center[2])
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            colors.append(hex_color)
        
        return colors
    except Exception as e:
        print(f"  ⚠️ Color extraction failed: {e}")
        return []


# ─── Main Pipeline ──────────────────────────────────────────────

def process_image(image_path: str) -> dict:
    """
    Run the full AI understanding pipeline on a single image.
    Returns dict with: caption, detected_objects, dominant_colors, ocr_text
    """
    print(f"🔍 Processing: {os.path.basename(image_path)}")
    
    ocr_text = extract_ocr_text(image_path)
    print(f"  📝 OCR: {ocr_text[:80] if ocr_text else '(none)'}")
    
    caption = generate_caption(image_path)
    print(f"  📸 Caption: {caption}")
    
    objects = detect_objects(image_path)
    print(f"  🎯 Objects: {objects}")
    
    colors = extract_dominant_colors(image_path)
    print(f"  🎨 Colors: {colors}")
    
    return {
        "caption": caption,
        "detected_objects": objects,
        "dominant_colors": colors,
        "ocr_text": ocr_text,
    }


# ─── CLIP Embedding Functions ──────────────────────────────────

def generate_clip_embedding(image_path: str) -> list:
    """Generate a CLIP image embedding (512-dim vector)."""
    import torch
    
    model, preprocess, _ = _get_clip()
    
    image = Image.open(image_path).convert("RGB")
    image_tensor = preprocess(image).unsqueeze(0)
    
    with torch.no_grad():
        embedding = model.encode_image(image_tensor)
        # L2 normalize
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
    
    return embedding.squeeze().cpu().numpy().tolist()


def text_to_embedding(text: str) -> list:
    """Convert a text query to a CLIP embedding (same space as images)."""
    import torch
    
    model, _, tokenizer = _get_clip()
    
    tokens = tokenizer([text])
    
    with torch.no_grad():
        embedding = model.encode_text(tokens)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
    
    return embedding.squeeze().cpu().numpy().tolist()
