from datetime import datetime, timedelta
from typing import List, Optional
from dyntastic import A
from src.models.meeting import Meeting


def get_meetings(
    days: int = 7, video: Optional[bool] = None, s3_path: Optional[bool] = None
) -> List[Meeting]:
    """
    Get meetings that occurred in the past number of days from now.
    """
    now = datetime.now()
    target_date = now - timedelta(days=days)
    meetings = Meeting.scan(
        A.date >= target_date,
    )
    meetings_list = [
        m
        for m in meetings
        if (video is None or bool(m.video) == video)
        and (s3_path is None or bool(m.s3_path) == s3_path)
    ]

    return list(meetings_list)
