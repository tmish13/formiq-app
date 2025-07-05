from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any

class VideoProcessResult(BaseModel):
    success: bool
    message: Optional[str] = None
    processed_frame_paths: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True) 