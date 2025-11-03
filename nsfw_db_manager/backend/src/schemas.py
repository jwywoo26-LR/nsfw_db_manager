"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ImageAssetBase(BaseModel):
    """Base schema for ImageAsset"""
    angle_1: Optional[str] = None
    angle_2: Optional[str] = None
    action_1: Optional[str] = None
    action_2: Optional[str] = None
    action_3: Optional[str] = None
    prompt: Optional[str] = None
    original_filename: Optional[str] = None


class ImageAssetCreate(ImageAssetBase):
    """Schema for creating ImageAsset"""
    s3_url: str = Field(..., description="S3 URL of the uploaded image")


class ImageAssetUpdate(ImageAssetBase):
    """Schema for updating ImageAsset (all fields optional)"""
    s3_url: Optional[str] = None


class ImageAssetResponse(ImageAssetBase):
    """Schema for ImageAsset response"""
    id: int
    created_at: datetime
    deleted_at: Optional[datetime] = None
    s3_url: Optional[str] = None  # Made optional for local storage
    local_file_path: Optional[str] = None  # Added for local storage

    class Config:
        from_attributes = True  # Renamed from orm_mode in Pydantic v2


class ImageAssetSearchParams(BaseModel):
    """Schema for search query parameters"""
    angle_1: Optional[str] = Field(None, description="Filter by angle_1")
    angle_2: Optional[str] = Field(None, description="Filter by angle_2")
    action_1: Optional[str] = Field(None, description="Filter by action_1")
    action_2: Optional[str] = Field(None, description="Filter by action_2")
    action_3: Optional[str] = Field(None, description="Filter by action_3")
    prompt: Optional[str] = Field(None, description="Filter by prompt (partial match)")
    include_deleted: bool = Field(False, description="Include deleted assets")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class UploadResponse(BaseModel):
    """Schema for upload response"""
    success: bool
    message: str
    asset: Optional[ImageAssetResponse] = None
    s3_url: Optional[str] = None


class SearchResponse(BaseModel):
    """Schema for search response"""
    total: int
    limit: int
    offset: int
    results: list[ImageAssetResponse]


class DeleteResponse(BaseModel):
    """Schema for delete response"""
    success: bool
    message: str
    deleted_asset: Optional[ImageAssetResponse] = None
