import asyncio
import os
import json

from pathlib import Path

from src.aws import save_content_to_s3
from src.models.meeting import GranicusPlayerPage, Meeting
from src.granicus import get_video_player
from src.videos import download_file, transcribe_video_with_diarization

BUCKET_NAME = os.getenv("S3_BUCKET")
FOLDER_NAME = "transcripts"


def download_video(file_name: str, video_url: str):
    # Create output directory if it doesn't exist
    VIDEO_DIRECTORY = Path("data/video")
    VIDEO_DIRECTORY.mkdir(parents=True, exist_ok=True)
    # file_name = "regular_council_meeting___2025_03_26"

    # Define output path for the video
    output_path = VIDEO_DIRECTORY / f"{file_name}.mp4"

    # video_url = "https://tulsa-ok.granicus.com/MediaPlayer.php?view_id=4&clip_id=6501"
    # video_url = "https://tulsa-ok.granicus.com/player/clip/6578?view_id=4&redirect=true"
    # video_url = "https://tulsa-ok.granicus.com/MediaPlayer.php?view_id=4&clip_id=4274"
    print(f"Downloading video from {video_url}")
    # Get video player page info
    player_page: GranicusPlayerPage = asyncio.run(get_video_player(video_url))

    # Run the download
    video_file = download_file(str(player_page.download_url), output_path)

    # Display the result
    if video_file:
        print(f"Video saved to: {video_file}")

    return video_file


def run_diarization(video_file: Path, meeting: Meeting):
    transcription_dir = Path("data/transcripts")

    transcription = asyncio.run(
        transcribe_video_with_diarization(video_file, transcription_dir)
    )
    # Add transcript to S3
    # Convert dictionary to JSON string before saving
    transcription_json = json.dumps(transcription, indent=2, ensure_ascii=False)
    save_content_to_s3(
        transcription_json,
        BUCKET_NAME,
        f"{FOLDER_NAME}/{video_file.name}.json",
        "application/json",
    )
    meeting.transcripts = [f"{FOLDER_NAME}/{video_file.name}.json"]
    meeting.save()

    print(transcription)


if __name__ == "__main__":
    video_file = download_video(
        "test", "https://tulsa-ok.granicus.com/MediaPlayer.php?view_id=4&clip_id=6501"
    )
    if video_file:
        run_diarization(video_file)
    else:
        print("Video file not found")
