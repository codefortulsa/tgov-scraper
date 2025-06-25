import os
from src.aws import get_video_from_s3, upload_to_s3
from src.run_diarization import download_video, run_diarization
from prefect import task

from src.models.meeting import Meeting


BUCKET_NAME = os.getenv("S3_BUCKET")
FOLDER_NAME = "videos"


# @task
def download_video_and_put_in_s3(meeting: Meeting):
    video_file = download_video(f"{meeting.meeting}_{meeting.date}", str(meeting.video))
    if video_file:
        print(f"Uploading video to S3: {video_file}")
        s3_path = f"{FOLDER_NAME}/{video_file.name}"
        upload_to_s3(video_file, BUCKET_NAME, f"{FOLDER_NAME}/{video_file.name}")
        print(f"Uploaded video to S3: {s3_path}")
        print("Saving meeting.")
        meeting.s3_path = s3_path
        meeting.save()
    else:
        print("Video file not found")


@task
def diarize_meeting(meeting: Meeting):
    if BUCKET_NAME is None:
        raise ValueError("S3_BUCKET environment variable is not set")

    if meeting.s3_path is None:
        print(f"Meeting {meeting.meeting} has no s3_path, skipping")
        return

    video_file = get_video_from_s3(BUCKET_NAME, meeting.s3_path)
    if video_file:
        run_diarization(video_file, meeting)
    else:
        print("Video file not found")
    # TODO: Update meeting with transcript location
