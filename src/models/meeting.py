"""
Pydantic models for meeting data
"""

from typing import Optional

from dyntastic import Dyntastic
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class Meeting(Dyntastic):
    """
    Model representing a government meeting
    """

    __table_name__ = "tgov-meeting"
    __hash_key__ = "clip_id"

    clip_id: Optional[str] = Field(None, description="Granicus clip ID")
    meeting: str = Field(description="Name of the meeting")
    date: datetime = Field(description="Date and time of the meeting")
    duration: str = Field(description="Duration of the meeting")
    agenda: Optional[HttpUrl] = Field(None, description="URL to the meeting agenda")
    video: Optional[HttpUrl] = Field(None, description="URL to the meeting video")

    def __str__(self) -> str:
        """String representation of the meeting"""
        return f"{self.meeting} - {self.date} ({self.duration})"


class GranicusPlayerPage(BaseModel):
    """Model for Granicus video URLs"""

    url: HttpUrl = Field(description="Base URL of the Granicus player page")
    stream_url: Optional[HttpUrl] = None
    download_url: Optional[HttpUrl] = None
