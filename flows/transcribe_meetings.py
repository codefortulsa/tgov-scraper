from prefect import flow

from db.queries import get_meetings
from tasks.diarize import diarize_meeting


@flow(log_prints=True)
def transcribe_meetings():
    meetings_to_diarize = get_meetings(video=True, s3_path=True)
    print(f"Found {len(meetings_to_diarize)} meetings to diarize")
    for meeting in meetings_to_diarize:
        diarize_meeting(meeting)


if __name__ == "__main__":
    transcribe_meetings()
