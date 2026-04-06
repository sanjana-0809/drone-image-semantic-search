import cloudinary
import cloudinary.uploader
import os
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)
def upload_to_cloudinary(file_path: str, public_id: str) -> str:
    result = cloudinary.uploader.upload(
        file_path,
        public_id=public_id,
        folder="drone-search",
        overwrite=True
    )
    return result["secure_url"]
