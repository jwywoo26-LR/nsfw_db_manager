"""
FastAPI application for NSFW Image Asset Manager
"""

import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from .database import get_db, init_db
from .models import ImageAsset
from .schemas import (
    ImageAssetCreate,
    ImageAssetResponse,
    ImageAssetSearchParams,
    SearchResponse,
    UploadResponse,
    DeleteResponse
)
from .s3_utils import S3Manager

# Configuration
USE_LOCAL_STORAGE = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"
LOCAL_UPLOAD_DIR = os.getenv("LOCAL_UPLOAD_DIR", "uploads/images")

# Initialize FastAPI app
app = FastAPI(
    title="NSFW Image Asset Manager",
    description="API for managing NSFW image assets with local or S3 storage and metadata",
    version="1.0.0"
)

# Initialize S3 manager (only if not using local storage)
s3_manager = S3Manager() if not USE_LOCAL_STORAGE else None

# Create upload directory if using local storage
if USE_LOCAL_STORAGE:
    upload_path = Path(LOCAL_UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    # Mount static files for serving images
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("🚀 NSFW Image Asset Manager API is running!")


@app.get("/")
async def root():
    """Root endpoint - redirect to docs"""
    return RedirectResponse(url="/docs")


@app.post("/api/upload", response_model=UploadResponse, tags=["Upload"])
async def upload_image_asset(
    file: UploadFile = File(..., description="Image file to upload"),
    angle_1: Optional[str] = Query(None, description="Angle direction 1"),
    angle_2: Optional[str] = Query(None, description="Angle direction 2"),
    action_1: Optional[str] = Query(None, description="Action direction 1"),
    action_2: Optional[str] = Query(None, description="Action direction 2"),
    action_3: Optional[str] = Query(None, description="Action direction 3"),
    prompt: Optional[str] = Query(None, description="Prompt or description for the image"),
    db: Session = Depends(get_db)
):
    """
    Upload an image asset to local storage or S3 and save metadata to database

    - **file**: Image file (PNG, JPG, etc.)
    - **angle_1**: First angle tag
    - **angle_2**: Second angle tag
    - **action_1**: First action tag
    - **action_2**: Second action tag
    - **action_3**: Third action tag
    - **prompt**: Optional prompt or description
    """
    try:
        # Read file content
        file_content = await file.read()

        s3_url = None
        local_file_path = None

        if USE_LOCAL_STORAGE:
            # Save to local storage
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{file.filename}"
            file_path = Path(LOCAL_UPLOAD_DIR) / filename

            with open(file_path, "wb") as f:
                f.write(file_content)

            local_file_path = str(file_path)
            print(f"✅ Saved locally: {local_file_path}")
        else:
            # Upload to S3
            s3_url = s3_manager.upload_file_bytes(
                file_bytes=file_content,
                filename=file.filename
            )

            if not s3_url:
                raise HTTPException(status_code=500, detail="Failed to upload image to S3")

        # Create database record
        image_asset = ImageAsset(
            s3_url=s3_url,
            local_file_path=local_file_path,
            angle_1=angle_1,
            angle_2=angle_2,
            action_1=action_1,
            action_2=action_2,
            action_3=action_3,
            prompt=prompt,
            original_filename=file.filename
        )

        db.add(image_asset)
        db.commit()
        db.refresh(image_asset)

        return UploadResponse(
            success=True,
            message="Image uploaded successfully",
            asset=ImageAssetResponse.from_orm(image_asset),
            s3_url=s3_url if s3_url else local_file_path
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/search", response_model=SearchResponse, tags=["Search"])
async def search_image_assets(
    angle_1: Optional[str] = Query(None, description="Filter by angle_1"),
    angle_2: Optional[str] = Query(None, description="Filter by angle_2"),
    action_1: Optional[str] = Query(None, description="Filter by action_1"),
    action_2: Optional[str] = Query(None, description="Filter by action_2"),
    action_3: Optional[str] = Query(None, description="Filter by action_3"),
    prompt: Optional[str] = Query(None, description="Filter by prompt (partial match)"),
    include_deleted: bool = Query(False, description="Include deleted assets"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Search for image assets based on angle, action, and prompt filters

    Returns a paginated list of matching image assets.
    All filter parameters are optional - omit them to search all assets.
    Prompt search uses partial matching (LIKE query).
    """
    try:
        # Build query
        query = db.query(ImageAsset)

        # Apply filters
        if not include_deleted:
            query = query.filter(ImageAsset.deleted_at.is_(None))

        if angle_1:
            query = query.filter(ImageAsset.angle_1 == angle_1)
        if angle_2:
            query = query.filter(ImageAsset.angle_2 == angle_2)
        if action_1:
            query = query.filter(ImageAsset.action_1 == action_1)
        if action_2:
            query = query.filter(ImageAsset.action_2 == action_2)
        if action_3:
            query = query.filter(ImageAsset.action_3 == action_3)
        if prompt:
            query = query.filter(ImageAsset.prompt.like(f"%{prompt}%"))

        # Get total count
        total = query.count()

        # Apply pagination
        results = query.offset(offset).limit(limit).all()

        return SearchResponse(
            total=total,
            limit=limit,
            offset=offset,
            results=[ImageAssetResponse.from_orm(asset) for asset in results]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/download/{asset_id}", tags=["Download"])
async def download_image_asset(
    asset_id: int,
    db: Session = Depends(get_db)
):
    """
    Download an image asset by ID

    Returns the file directly (local storage) or redirects to S3 URL.
    """
    try:
        # Get asset from database
        asset = db.query(ImageAsset).filter(ImageAsset.id == asset_id).first()

        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset with ID {asset_id} not found")

        if asset.deleted_at:
            raise HTTPException(status_code=410, detail=f"Asset with ID {asset_id} has been deleted")

        # Serve file based on storage type
        if USE_LOCAL_STORAGE and asset.local_file_path:
            # Serve local file
            file_path = Path(asset.local_file_path)
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=f"File not found: {asset.local_file_path}")
            return FileResponse(file_path, filename=asset.original_filename)
        elif asset.s3_url:
            # Redirect to S3 URL
            return RedirectResponse(url=asset.s3_url)
        else:
            raise HTTPException(status_code=404, detail="No file location found for this asset")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@app.get("/api/assets/{asset_id}", response_model=ImageAssetResponse, tags=["Assets"])
async def get_image_asset(
    asset_id: int,
    db: Session = Depends(get_db)
):
    """
    Get metadata for a specific image asset by ID
    """
    try:
        asset = db.query(ImageAsset).filter(ImageAsset.id == asset_id).first()

        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset with ID {asset_id} not found")

        return ImageAssetResponse.from_orm(asset)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get asset: {str(e)}")


@app.delete("/api/assets/{asset_id}", response_model=DeleteResponse, tags=["Assets"])
async def delete_image_asset(
    asset_id: int,
    hard_delete: bool = Query(False, description="Permanently delete from database and S3"),
    db: Session = Depends(get_db)
):
    """
    Delete an image asset

    - **soft delete** (default): Sets deleted_at timestamp, keeps S3 file
    - **hard delete**: Removes from database and deletes S3 file
    """
    try:
        asset = db.query(ImageAsset).filter(ImageAsset.id == asset_id).first()

        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset with ID {asset_id} not found")

        if hard_delete:
            # Delete from S3
            s3_manager.delete_file(asset.s3_url)

            # Delete from database
            db.delete(asset)
            db.commit()

            return DeleteResponse(
                success=True,
                message=f"Asset {asset_id} permanently deleted",
                deleted_asset=None
            )
        else:
            # Soft delete - set deleted_at timestamp
            asset.deleted_at = datetime.utcnow()
            db.commit()
            db.refresh(asset)

            return DeleteResponse(
                success=True,
                message=f"Asset {asset_id} soft deleted",
                deleted_asset=ImageAssetResponse.from_orm(asset)
            )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@app.get("/api/metadata/actions", tags=["Metadata"])
async def get_unique_actions(db: Session = Depends(get_db)):
    """
    Get all unique action_1 values from the database for dropdown filters
    """
    try:
        # Query distinct action_1 values, excluding None/empty
        actions = db.query(ImageAsset.action_1).distinct().filter(
            ImageAsset.action_1.isnot(None),
            ImageAsset.action_1 != ""
        ).order_by(ImageAsset.action_1).all()

        # Extract values from tuples
        action_list = [action[0] for action in actions]

        return {
            "actions": action_list,
            "count": len(action_list)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get actions: {str(e)}")


@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "NSFW Image Asset Manager",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
