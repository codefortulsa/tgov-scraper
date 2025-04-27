from prefect import flow

from tasks.meetings import get_new_meetings


@flow(log_prints=True)
async def check_for_new_minutes():
    # TODO: Get the last run page from the database
    # last_run_page = get_last_run_page()
    last_run_page = 47711
    new_minutes, new_last_run_page = await get_new_meetings(last_run_page)
    # TODO: Save last run page to the database
    # set_last_run_page(new_last_run_page)
    for minutes in new_minutes:
        # TODO: Get the transcriptions
        # transcription = get_transcriptions(meeting)
        # transcription =
        new_diarization = get_speaker_names(minutes, transcription)
        # TODO: Replace the transcription
        # replace_transcription(new_diarization)


if __name__ == "__main__":
    import asyncio

    asyncio.run(check_for_new_minutes())
