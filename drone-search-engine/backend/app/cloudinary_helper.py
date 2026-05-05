"""Cloudinary image storage helper."""

from __future__ import annotations

import os

from .config import get_settings


settings = get_settings()


def _require_cloudinary_config() -> None:
    missing = [
        name
        for name in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(f"Cloudinary is not configured; missing {', '.join(missing)}")


def upload_to_cloudinary(file_path: str, public_id: str) -> str:
    """Upload an image and return its HTTPS delivery URL."""
    _require_cloudinary_config()
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )

    result = cloudinary.uploader.upload(
        file_path,
        public_id=public_id,
        folder=settings.cloudinary_folder,
        overwrite=True,
        resource_type="image",
    )
    secure_url = result.get("secure_url")
    if not secure_url:
        raise RuntimeError("Cloudinary upload completed without a secure URL")
    return secure_url
