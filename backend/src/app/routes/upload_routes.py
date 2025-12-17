"""
File upload routes
"""
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from src.app.dependencies import get_current_user
from src.app.models.user import UserInDB
import os
import uuid
from datetime import datetime
from pathlib import Path

router = APIRouter()

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    "image": ["jpg", "jpeg", "png", "gif", "webp"],
    "video": ["mp4", "webm", "mov", "avi"],
    "audio": ["mp3", "wav", "ogg", "m4a"],
    "document": ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "zip", "rar"]
}

ALLOWED_EXTENSIONS_FLAT = (
    ALLOWED_EXTENSIONS["image"] + 
    ALLOWED_EXTENSIONS["video"] + 
    ALLOWED_EXTENSIONS["audio"] + 
    ALLOWED_EXTENSIONS["document"]
)

# Upload directory (can be changed to cloud storage)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def get_file_type(ext: str) -> str:
    """Determine file type from extension"""
    ext_lower = ext.lower()
    if ext_lower in ALLOWED_EXTENSIONS["image"]:
        return "image"
    elif ext_lower in ALLOWED_EXTENSIONS["video"]:
        return "video"
    elif ext_lower in ALLOWED_EXTENSIONS["audio"]:
        return "audio"
    elif ext_lower in ALLOWED_EXTENSIONS["document"]:
        return "document"
    return "document"

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Upload a file (image, video, audio, or document).
    Returns URL, name, and MIME type for use in messages.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Get file extension
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if ext not in ALLOWED_EXTENSIONS_FLAT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS_FLAT)}"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_type = get_file_type(ext)
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    safe_filename = f"{timestamp}_{file_id}.{ext}"
    
    # Create type-specific directory
    type_dir = UPLOAD_DIR / file_type
    type_dir.mkdir(exist_ok=True)
    
    file_path = type_dir / safe_filename
    
    # Save file locally (in production, upload to S3/Cloudinary/etc.)
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Generate URL (in production, this would be a cloud storage URL)
    # For now, return a relative path that can be served statically
    file_url = f"/uploads/{file_type}/{safe_filename}"
    
    return {
        "url": file_url,
        "name": file.filename,
        "mime": file.content_type or "application/octet-stream",
        "type": file_type,
        "size": len(content)
    }


