import os
import uuid
from src.core.exceptions import ImageValidationError, ValidationError
from src.config import settings

def validate_image(image_path: str) -> None:
    if not os.path.exists(image_path):
        raise ImageValidationError("File not found")
    
    size_mb = os.path.getsize(image_path) / (1024 * 1024)
    if size_mb > settings.max_image_size_mb:
        raise ImageValidationError("Image too large")
    
    with open(image_path, "rb") as f:
        header = f.read(8)
    
    is_jpeg = header[:3] == b'\xff\xd8\xff'
    is_png = header[:4] == b'\x89PNG'
    
    if not (is_jpeg or is_png):
        raise ImageValidationError("Invalid image type — JPEG or PNG only")
    
def validate_status(status: str) -> None:
    if status not in ("lost", "found"):
        raise ValidationError("Status must be 'lost' or 'found'")
    
def validate_item_id(item_id: str) -> None:
    try:
        uuid.UUID(item_id)
    except ValueError:
        raise ValidationError("Invalid item ID format")
