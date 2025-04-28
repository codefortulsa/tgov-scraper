from datetime import datetime
from prefect import flow

from tasks.minutes import get_new_minutes



@flow(log_prints=True)
async def check_for_new_minutes():
    # TODO: Get the last run page from the database
    # last_run_page = get_last_run_page()
    last_run_page = 47711
    new_minutes, new_last_run_page = await get_new_minutes(last_run_page)
    # TODO: Save last run page to the database
    # set_last_run_page(new_last_run_page)
    # TODO: get meetings with no speaker ids from db
    meetings = [datetime(2025, 2, 26, 17, 0)]
    # TODO: get transcriptions from db
    for minutes in new_minutes:
        if minutes.meeting_date in meetings:
            # TODO: Get diarisation
            # diarisation = await get_diarisation(minutes)
            # TODO: Get the transcription instead of diarisation
            # transcription = get_transcriptions(meeting)
            # TODO: Get the speaker names
            # new_transcription = get_speaker_names(minutes, diarisation)
            # TODO: Replace transcription
            # replace_transcription(new_diarization)


if __name__ == "__main__":
    import asyncio

    asyncio.run(check_for_new_minutes())
