from prefect import flow

from db.queries import get_meetings
from tasks.diarize import download_video_and_put_in_s3
from tasks.meetings import register_meetings


# @flow(log_prints=True)
def download_meetings():
    new_meetings = register_meetings()
    print(f"Registered {len(new_meetings)} new meetings")
    meetings_to_download = get_meetings(days=7, video=True, s3_path=False)
    print(f"Found {len(meetings_to_download)} meetings to download")
    for meeting in meetings_to_download:
        download_video_and_put_in_s3(meeting)
    # new_subtitled_video_pages = await create_subtitled_video_pages(new_transcribed_meetings)
    # new_translated_meetings = await translate_transcriptions(new_transcribed_meetings)


if __name__ == "__main__":
    download_meetings()
