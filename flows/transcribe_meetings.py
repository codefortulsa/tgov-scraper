from prefect import flow
import os

from db.queries import get_meetings
from tasks.diarize import diarize_meeting, BUCKET_NAME


@flow(log_prints=True)
def transcribe_meetings():
    print(f"S3_BUCKET environment variable: {os.getenv('S3_BUCKET')}")
    print(f"BUCKET_NAME from tasks.diarize: {BUCKET_NAME}")

    meetings_to_diarize = get_meetings(video=True, s3_path=True)
    print(f"Found {len(meetings_to_diarize)} meetings to diarize")
    for meeting in meetings_to_diarize:
        print(f"Processing meeting: {meeting.meeting} with s3_path: {meeting.s3_path}")
        diarize_meeting(meeting)


if __name__ == "__main__":
    transcribe_meetings()
