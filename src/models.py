from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid

class ItemCreate(BaseModel):
    status: str
    user_text: str
    image_path: str

class ItemRecord(BaseModel):
    id: uuid.UUID
    status: str
    user_text: str
    image_path: Optional[str] = None
    vlm_description: Optional[dict] = None
    embedding: Optional[bytes] = None
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None

class MatchResult(BaseModel):
    item: ItemRecord
    score: float
    reason: Optional[str] = None