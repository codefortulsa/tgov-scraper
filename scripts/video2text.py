#!/usr/bin/env python3
"""
Script to transcribe video files using faster-whisper and save the results.
"""

import os
import sys
import argparse
import json
from pathlib import Path
import time
import logging
from typing import Dict, List, Optional, Tuple, Union
import asyncio
import requests
from requests.exceptions import ChunkedEncodingError, ConnectionError
from urllib3.exceptions import IncompleteRead, ProtocolError
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Patch huggingface_hub to add retries
try:
    from huggingface_hub import file_download

    original_http_get = file_download.http_get

    def http_get_with_retry(*args, **kwargs):
        max_retries = 5
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                return original_http_get(*args, **kwargs)
            except (
                ChunkedEncodingError,
                ConnectionError,
                IncompleteRead,
                ProtocolError,
            ) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Download failed with error: {e}. Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})"
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Download failed after {max_retries} attempts: {e}")
                    raise

    # Replace the original function with our retry version
    file_download.http_get = http_get_with_retry
    logger.info("Added retry mechanism to huggingface_hub downloads")
except ImportError:
    logger.warning("Could not patch huggingface_hub for retries")

# Now import WhisperModel
from faster_whisper import WhisperModel


async def transcribe_video(
    video_path: str,
    output_dir: str,
    model_size: str = "tiny",
    device: str = "cpu",
    language: Optional[str] = None,
    verbose: bool = False,
    vad_filter: bool = False,
    beam_size: int = 5,
    force_download: bool = False,
) -> str:
    """
    Transcribe a video file using faster-whisper and save the results.

    Args:
        video_path: Path to the video file
        output_dir: Directory to save the transcription
        model_size: Size of the Whisper model to use (tiny, base, small, medium, large-v1, large-v2, large-v3)
        device: Device to use for inference (cpu or cuda)
        language: Language code (e.g., 'en' for English)
        verbose: Whether to print verbose output
        vad_filter: Whether to use Voice Activity Detection to filter out non-speech
        beam_size: Beam size for the decoder
        force_download: Whether to force download the model even if it exists

    Returns:
        Path to the saved transcription file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get the base filename without extension
    video_filename = os.path.basename(video_path)
    base_filename = os.path.splitext(video_filename)[0]

    # Define output paths
    transcript_path = os.path.join(output_dir, f"{base_filename}.txt")
    json_path = os.path.join(output_dir, f"{base_filename}.json")

    logger.info(f"Loading Whisper model: {model_size}")
    # Load the Whisper model
    try:
        from huggingface_hub import snapshot_download

        # Force download the model if requested
        if force_download:
            logger.info(f"Force downloading model {model_size}")
            model_path = snapshot_download(
                repo_id=f"guillaumekln/faster-whisper-{model_size}",
                local_dir=f"./models/whisper/{model_size}",
                force_download=True,
            )
            model = WhisperModel(model_path, device=device, compute_type="float32")
        else:
            model = WhisperModel(
                model_size,
                device=device,
                compute_type="float32",
                download_root="./models/whisper",
            )
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        logger.info("Falling back to tiny model")
        model = WhisperModel(
            "tiny",
            device=device,
            compute_type="float32",
            download_root="./models/whisper",
        )

    logger.info(f"Transcribing video: {video_path}")
    start_time = time.time()

    # Run the transcription
    segments, info = model.transcribe(
        video_path,
        language=language,
        task="transcribe",
        beam_size=beam_size,
        vad_filter=vad_filter,
        vad_parameters=dict(min_silence_duration_ms=500) if vad_filter else None,
    )

    # Process the segments
    transcript_text = ""
    segments_list = []

    logger.info("Processing transcription segments...")
    for segment in segments:
        # Add to full transcript
        transcript_text += f"{segment.text}\n"

        # Add to segments list for JSON output
        segment_dict = {
            "id": segment.id,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "words": (
                [
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability,
                    }
                    for word in segment.words
                ]
                if segment.words
                else []
            ),
        }
        segments_list.append(segment_dict)

    # Save the full transcript
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript_text)

    # Save the detailed JSON with timing information
    transcription_data = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "segments": segments_list,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transcription_data, f, indent=2, ensure_ascii=False)

    elapsed_time = time.time() - start_time
    logger.info(f"Transcription completed in {elapsed_time:.2f} seconds")
    logger.info(f"Transcript saved to: {transcript_path}")
    logger.info(f"Detailed JSON saved to: {json_path}")

    if verbose:
        print("\nTranscription preview:")
        preview_length = min(500, len(transcript_text))
        print(f"{transcript_text[:preview_length]}...")

    return transcript_path


async def process_directory(
    input_dir: str,
    output_dir: str,
    model_size: str = "tiny",
    device: str = "cpu",
    language: Optional[str] = None,
    verbose: bool = False,
    vad_filter: bool = False,
    beam_size: int = 5,
    force_download: bool = False,
) -> List[str]:
    """
    Process all video files in a directory.

    Args:
        input_dir: Directory containing video files
        output_dir: Directory to save transcriptions
        model_size: Size of the Whisper model to use
        device: Device to use for inference
        language: Language code
        verbose: Whether to print verbose output
        vad_filter: Whether to use Voice Activity Detection
        beam_size: Beam size for the decoder
        force_download: Whether to force download the model

    Returns:
        List of paths to the saved transcription files
    """
    video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
    video_files = []

    # Find all video files in the directory
    for ext in video_extensions:
        video_files.extend(list(Path(input_dir).glob(f"*{ext}")))

    if not video_files:
        logger.warning(f"No video files found in {input_dir}")
        return []

    logger.info(f"Found {len(video_files)} video files to process")

    # Process each video file
    transcript_paths = []
    for video_file in video_files:
        transcript_path = await transcribe_video(
            str(video_file),
            output_dir,
            model_size=model_size,
            device=device,
            language=language,
            verbose=verbose,
            vad_filter=vad_filter,
            beam_size=beam_size,
            force_download=force_download,
        )
        transcript_paths.append(transcript_path)

    return transcript_paths


async def main():
    parser = argparse.ArgumentParser(
        description="Transcribe video files using faster-whisper"
    )
    parser.add_argument(
        "input", help="Path to video file or directory containing video files"
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="data/transcripts",
        help="Directory to save transcriptions (default: data/transcripts)",
    )
    parser.add_argument(
        "--model-size",
        "-m",
        choices=["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"],
        default="small",
        help="Size of the Whisper model to use (default: small)",
    )
    parser.add_argument(
        "--device",
        "-d",
        choices=["cpu", "cuda"],
        default="cpu",
        help="Device to use for inference (default: cpu)",
    )
    parser.add_argument(
        "--language",
        "-l",
        help="Language code (e.g., 'en' for English). If not specified, Whisper will auto-detect.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print verbose output"
    )
    parser.add_argument(
        "--vad-filter",
        action="store_true",
        help="Use Voice Activity Detection to filter out non-speech (default: False)",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam size for the decoder (default: 5)",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Force download the model even if it exists (default: False)",
    )

    args = parser.parse_args()

    # Create models directory if it doesn't exist
    os.makedirs("models/whisper", exist_ok=True)

    # Check if input is a file or directory
    input_path = args.input
    if os.path.isfile(input_path):
        # Process a single file
        await transcribe_video(
            input_path,
            args.output_dir,
            model_size=args.model_size,
            device=args.device,
            language=args.language,
            verbose=args.verbose,
            vad_filter=args.vad_filter,
            beam_size=args.beam_size,
            force_download=args.force_download,
        )
    elif os.path.isdir(input_path):
        # Process all video files in the directory
        await process_directory(
            input_path,
            args.output_dir,
            model_size=args.model_size,
            device=args.device,
            language=args.language,
            verbose=args.verbose,
            vad_filter=args.vad_filter,
            beam_size=args.beam_size,
            force_download=args.force_download,
        )
    else:
        logger.error(f"Error: Input path {input_path} does not exist")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
