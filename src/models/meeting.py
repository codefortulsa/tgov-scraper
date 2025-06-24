"""
Pydantic models for meeting data
"""

from typing import Optional

from dyntastic import Dyntastic
from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from datetime import datetime
from typing import List


def clean_filename(meeting_name: str) -> str:
    return meeting_name.replace(" ", "_").replace("/", "_").replace(":", "_")


class Meeting(Dyntastic):
    __table_name__ = "tgov-meeting"
    __hash_key__ = "clip_id"

    model_config = ConfigDict(extra="ignore")

    clip_id: Optional[str] = Field(None, description="Granicus clip ID")
    meeting: str = Field(description="Name of the meeting")
    date: datetime = Field(description="Date and time of the meeting")
    duration: str = Field(description="Duration of the meeting")
    agenda: Optional[HttpUrl] = Field(None, description="URL to the meeting agenda")
    video: Optional[HttpUrl] = Field(None, description="URL to the meeting video")
    transcripts: Optional[List[HttpUrl]] = Field(
        None, description="URLs to the meeting transcripts"
    )
    subtitles: Optional[List[HttpUrl]] = Field(
        None, description="URLs to the meeting subtitle tracks"
    )
    s3_path: Optional[str] = Field(
        default=None, description="S3 path to the meeting video"
    )

    def __str__(self) -> str:
        """String representation of the meeting"""
        return f"{self.meeting} ({self.date})"

    def filename(self) -> str:
        return f"{self.clip_id}/{clean_filename(self.meeting)}/({self.date})"


class GranicusPlayerPage(BaseModel):
    url: HttpUrl = Field(description="Base URL of the Granicus player page")
    stream_url: Optional[HttpUrl] = None
    download_url: Optional[HttpUrl] = None
