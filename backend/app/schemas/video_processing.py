from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class VideoProcessResult(BaseModel):
    success: bool
    message: Optional[str] = None
    processed_frame_paths: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None

    class Config:
        from_attributes = True # orm_mode = True for Pydantic v1 