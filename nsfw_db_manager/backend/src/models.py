"""
Database models for NSFW Image Asset Manager
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ImageAsset(Base):
    """
    ImageAsset model for storing NSFW image metadata
    """
    __tablename__ = "image_assets"

    # Basic required fields
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Angle directions
    angle_1 = Column(String(255), nullable=True, index=True)
    angle_2 = Column(String(255), nullable=True, index=True)

    # Action directions
    action_1 = Column(String(255), nullable=True, index=True)
    action_2 = Column(String(255), nullable=True, index=True)
    action_3 = Column(String(255), nullable=True, index=True)

    # Prompt (optional text description for image generation context)
    prompt = Column(Text, nullable=True)

    # File storage (S3 or Local)
    s3_url = Column(String(1024), nullable=True)  # Made nullable for local storage
    local_file_path = Column(String(1024), nullable=True)  # Local file path

    # Original filename for reference
    original_filename = Column(String(512), nullable=True)

    def __repr__(self):
        return f"<ImageAsset(id={self.id}, s3_url={self.s3_url})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "angle_1": self.angle_1,
            "angle_2": self.angle_2,
            "action_1": self.action_1,
            "action_2": self.action_2,
            "action_3": self.action_3,
            "prompt": self.prompt,
            "s3_url": self.s3_url,
            "local_file_path": self.local_file_path,
            "original_filename": self.original_filename
        }
