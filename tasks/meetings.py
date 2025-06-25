import asyncio
from typing import List
from prefect import task

from src.meetings import (
    get_tgov_meetings,
    get_registry_meetings,
    write_registry_meetings,
)
from src.models.meeting import Meeting


# @task
def register_meetings() -> List[Meeting]:
    # TODO: accept max_limit parameter
    tgov_meetings = asyncio.run(get_tgov_meetings())
    print(f"Got {len(tgov_meetings)} tgov meetings.")
    # print(f"tgov_clip_ids: {tgov_clip_ids}")

    registry_meetings = get_registry_meetings()
    print(f"Got {len(registry_meetings)} registry meetings.")

    registry_clip_ids = [rm.clip_id for rm in registry_meetings]

    new_meetings = [tm for tm in tgov_meetings if tm.clip_id not in registry_clip_ids]

    if new_meetings:
        registry_meetings += new_meetings
        write_registry_meetings(registry_meetings)

    return registry_meetings
    # meeting_with_video = [
    #     meeting for meeting in registry_meetings if meeting.video is not None
    # ]
    # print(f"Found {len(meeting_with_video)} in registry with video.")
    # meetings_without_transcripts = [
    #     meeting for meeting in registry_meetings if meeting.transcripts is None
    # ]

    # print(f"Found {len(meetings_without_transcripts)} in registry without transcripts.")
    # return meetings_without_transcripts
