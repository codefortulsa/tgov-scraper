"""
Pydantic models for meeting data
"""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field, HttpUrl, validator


class Meeting(BaseModel):
    """
    Model representing a government meeting
    """

    meeting: str = Field(description="Name of the meeting")
    date: str = Field(
        description="ISO-formatted date and time of the meeting with timezone"
    )
    date_display: Optional[str] = Field(
        None, description="Human-readable date and time format"
    )
    duration: str = Field(description="Duration of the meeting")
    agenda: Optional[HttpUrl] = Field(None, description="URL to the meeting agenda")
    video: Optional[HttpUrl] = Field(None, description="URL to the meeting video")

    @validator("date_display", pre=True, always=True)
    def set_date_display(cls, v, values):
        """Set date_display to a readable format if not provided"""
        if v is None and "date" in values:
            # If the date is in ISO format, try to make it more readable
            try:
                dt = datetime.fromisoformat(values["date"])
                return dt.strftime("%B %d, %Y - %I:%M %p")
            except (ValueError, TypeError):
                return values["date"]
        return v

    def __str__(self) -> str:
        """String representation of the meeting"""
        display_date = self.date_display or self.date
        return f"{self.meeting} - {display_date} ({self.duration})"


class MeetingSummary(BaseModel):
    """Model for meeting summaries"""

    meeting: Meeting = Field(description="Meeting details")
    summary: str = Field(description="Summary of the meeting")
    summarization_date: str = Field(description="Date and time of the summarization")
    needs_summarization: bool = Field(
        description="Whether the summary needs to be generated"
    )


class GranicusPlayerPage(BaseModel):
    """Model for Granicus video URLs"""

    url: HttpUrl = Field(description="Base URL of the Granicus player page")
    stream_url: Optional[HttpUrl] = None
    download_url: Optional[HttpUrl] = None
