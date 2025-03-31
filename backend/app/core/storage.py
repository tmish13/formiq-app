"""Storage module."""
import os
import uuid
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import StorageError


def upload_video(file: UploadFile) -> str:
    """Upload video file."""
    try:
        # Create upload directory if it doesn't exist
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        # Generate unique filename
        filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
        filepath = os.path.join(settings.UPLOAD_DIR, filename)

        # Save file
        with open(filepath, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)

        # Return video URL
        return f"{settings.UPLOAD_URL}/{filename}"
    except Exception as e:
        raise StorageError(f"Failed to upload video: {str(e)}")


def delete_video(video_url: str) -> None:
    """Delete video file."""
    try:
        # Extract filename from URL
        filename = os.path.basename(video_url)
        filepath = os.path.join(settings.UPLOAD_DIR, filename)

        # Delete file if it exists
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        raise StorageError(f"Failed to delete video: {str(e)}") 