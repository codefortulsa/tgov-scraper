from typing import Sequence
from prefect import task

from src.meetings import (
    get_tgov_meetings,
    get_registry_meetings,
    write_registry_meetings,
)
from src.models.meeting import Meeting


@task
async def get_new_meetings():
    # TODO: accept max_limit parameter
    tgov_meetings: Sequence[Meeting] = await get_tgov_meetings()
    print(f"Got {len(tgov_meetings)} tgov meetings.")
    tgov_clip_ids = [tm.clip_id for tm in tgov_meetings]
    # print(f"tgov_clip_ids: {tgov_clip_ids}")

    registry_meetings: Sequence[Meeting] = ()
    print(f"Got {len(registry_meetings)} registry meetings.")

    registry_clip_ids = [rm.clip_id for rm in registry_meetings]

    new_meetings: Sequence[Meeting] = [
        tm for tm in tgov_meetings if tm.clip_id not in registry_clip_ids
    ]

    if new_meetings:
        registry_meetings += new_meetings
        write_registry_meetings(registry_meetings)
        return new_meetings

    print(f"No new meetings. {len(registry_meetings)} in registry.")
    return []
