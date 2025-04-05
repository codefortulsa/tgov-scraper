"""
Pydantic models for meeting data
"""

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class MeetingQuery(BaseModel):
    """Model for meeting index"""

    name: Optional[str] = Field(description="Name of the meeting")
    date: Optional[str] = Field(description="Date and time of the meeting")
    clip_id: Optional[str] = Field(None, description="Granicus clip ID")


class Meeting(MeetingQuery):
    """
    Model representing a government meeting
    """

    duration: str = Field(description="Duration of the meeting")
    agenda: Optional[HttpUrl] = Field(None, description="URL to the meeting agenda")
    video: Optional[HttpUrl] = Field(None, description="URL to the meeting video")

    def __str__(self) -> str:
        """String representation of the meeting"""
        return f"{self.name}-{self.date}-({self.clip_id})"


class GranicusPlayerPage(BaseModel):
    """Model for Granicus video URLs"""

    url: HttpUrl = Field(description="Base URL of the Granicus player page")
    stream_url: Optional[HttpUrl] = None
    download_url: Optional[HttpUrl] = None
