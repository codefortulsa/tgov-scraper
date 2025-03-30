#!/usr/bin/env python3
"""
Utility functions for working with video streams from Granicus player pages.
"""

import asyncio
import re
import tempfile
import os
import io
from typing import Optional, Tuple, BinaryIO
from urllib.request import urlopen
import time
import json
import aiohttp
from selectolax.parser import HTMLParser
import m3u8
import requests
from pydub import AudioSegment
from pathlib import Path
import whisperx
from .huggingface import get_whisper, get_whisperx
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_output_path(file: Path, dir: Path, ext: str = "json") -> Path:

    file_name = os.path.basename(file)
    base_name = os.path.splitext(file_name)[0]
    output_path = os.path.join(dir, f"{base_name}.{ext}")
    logger.info(f"Output will be saved to: {output_path}")
    return output_path


async def fetch_page(url: str, session: aiohttp.ClientSession) -> str:
    """
    Fetch the HTML content of a page.

    Args:
        url: The URL to fetch
        session: An aiohttp ClientSession

    Returns:
        The HTML content as a string
    """
    async with session.get(url) as response:
        if response.status != 200:
            raise Exception(f"Failed to fetch {url}, status code: {response.status}")
        return await response.text()


def download_file(url: str, output_path: Path):
    print(f"Downloading video from: {url}")
    print(f"Saving to: {output_path}")

    with requests.get(str(url)) as response:
        if response.status_code != 200:
            print(f"Failed to download, status code: {response.status_code}")
            return None

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                downloaded += len(chunk)

                # Report progress every 5%
                if total_size > 0:
                    percent = int(downloaded * 100 / total_size)
                    if percent % 5 == 0 and percent > 0:
                        print(
                            f"Downloaded {percent}% ({downloaded/1024/1024:.1f} MB / {total_size/1024/1024:.1f} MB)"
                        )

    print(f"Download complete: {url}")
    return output_path


async def save_audio(
    video_path: str,
    output_path: Optional[str] = None,
    max_duration: Optional[int] = None,
    sample_rate: int = 16000,
    channels: int = 1,
    temp_dir: Optional[str] = None,
) -> str:
    """
    Extract audio from a video file using ffmpeg.

    Args:
        video_path: Path to the video file
        output_path: Path to save the extracted audio (WAV format)
                    If None, a temporary file will be created
        max_duration: Maximum duration in seconds to extract (None for entire video)
        sample_rate: Sample rate for the output audio (default: 16000 Hz)
        channels: Number of audio channels (default: 1 for mono)
        temp_dir: Directory to use for temporary files (if output_path is None)

    Returns:
        Path to the extracted audio file
    """
    # If no output path is provided, create a temporary file
    if output_path is None:
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False, dir=temp_dir
        )
        output_path = temp_file.name
        temp_file.close()

    # Prepare ffmpeg command
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file if it exists
        "-i",
        video_path,
        "-vn",  # No video
        "-acodec",
        "pcm_s16le",  # 16-bit PCM
        "-ar",
        str(sample_rate),  # Sample rate
        "-ac",
        str(channels),  # Number of channels
    ]

    # Add duration limit if specified
    if max_duration is not None:
        ffmpeg_cmd.extend(["-t", str(max_duration)])

    # Add output path
    ffmpeg_cmd.append(output_path)

    # Run ffmpeg command
    try:
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode("utf-8") if stderr else "Unknown error"
            raise RuntimeError(f"Failed to extract audio: {error_message}")

        return output_path
    except Exception as e:
        # Clean up temporary file if we created one and an error occurred
        if output_path is None and os.path.exists(output_path):
            os.unlink(output_path)
        raise e


async def transcribe_video(video_path: Path, output_path: Path):
    model = await get_whisper(model_size="tiny")
    logger.info(f"Transcribing video: {video_path}")
    start_time = time.time()

    # Get the output path for the transcription
    transcription_path = get_output_path(video_path, output_path, ext="json")

    # Run the transcription
    segments, info = model.transcribe(
        video_path,
        language=None,
        task="transcribe",
        beam_size=5,
        vad_filter=False,
        vad_parameters=None,
    )

    # Process the segments
    segments_list = []

    logger.info("Processing transcription segments...")
    for segment in segments:
        # Add to segments list for JSON output
        segment_dict = {
            "id": segment.id,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "speaker": "Unknown",  # Default speaker when diarization is not available
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

    # Save the detailed JSON with timing information
    transcription_data = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "segments": segments_list,
    }

    with open(transcription_path, "w", encoding="utf-8") as f:
        json.dump(transcription_data, f, indent=2, ensure_ascii=False)

    elapsed_time = time.time() - start_time
    logger.info(f"Transcription completed in {elapsed_time:.2f} seconds")
    logger.info(f"Detailed JSON saved to: {transcription_path}")
    return transcription_data


async def transcribe_video_with_diarization(
    video_path: Path,
    output_path: Path,
    model_size: str = "medium",
    device: str = "auto",
    compute_type: str = "auto",
    batch_size: int = 8,
):
    """
    Transcribe a video with speaker diarization using WhisperX.

    Args:
        video_path: Path to the video file
        output_path: Directory to save the output files
        model_size: Size of the model (tiny, base, small, medium, large)
        device: Device to use: 'auto' (default), 'cpu', 'cuda', or 'mps'
        compute_type: Precision: 'auto' (default), 'float32', 'float16', or 'int8'
        batch_size: Batch size for processing

    Returns:
        Transcription data with speaker information
    """
    logger.info(f"Transcribing video with speaker diarization: {video_path}")
    start_time = time.time()

    # Get the output path for the transcription
    transcription_path = get_output_path(video_path, output_path, ext="diarized.json")

    # Load WhisperX components with optimized settings
    model_components = await get_whisperx(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        batch_size=batch_size,
    )

    # Extract individual components
    model = model_components["model"]

    # Get the actual device being used after auto-detection
    actual_device = model.device

    # 1. Transcribe with WhisperX
    logger.info(f"Running initial transcription with batch size {batch_size}...")
    transcription = model.transcribe(str(video_path), batch_size=batch_size)
    detected_language = transcription["language"]
    logger.info(f"Detected language: {detected_language}")

    # 2. Load alignment model based on detected language
    logger.info(f"Loading alignment model for detected language: {detected_language}")
    align_model, align_metadata = whisperx.load_align_model(
        language_code=detected_language,
        device=actual_device,
        model_dir="../models/whisperx/alignment",
    )

    # 3. Run alignment
    logger.info("Aligning transcription with audio...")
    result_aligned = whisperx.align(
        transcription["segments"],
        align_model,
        align_metadata,
        str(video_path),
        actual_device,
        return_char_alignments=False,
    )

    # 4. Run diarization if available
    if "diarize_model" in model_components:
        logger.info("Running speaker diarization...")
        try:
            diarize_model = model_components["diarize_model"]
            diarize_segments = diarize_model(str(video_path))

            # Assign speakers to words and segments
            logger.info("Assigning speakers to transcription...")
            result = whisperx.assign_word_speakers(diarize_segments, result_aligned)
        except Exception as e:
            logger.error(f"Diarization failed: {str(e)}")
            logger.info("Proceeding with aligned transcription without speaker labels")
            result = result_aligned
    else:
        logger.warning(
            "Diarization model not available. Using aligned transcription without speaker labels."
        )
        result = result_aligned

    # Process the result into a standardized format
    segments_list = []

    logger.info("Processing transcription segments...")
    for segment in result["segments"]:
        # Extract speaker from the segment if available
        speaker = segment.get("speaker", "UNKNOWN")

        # Add to segments list for JSON output
        segment_dict = {
            "id": segment.get("id", 0),
            "start": segment.get("start", 0),
            "end": segment.get("end", 0),
            "text": segment.get("text", ""),
            "speaker": speaker,
            "words": [
                {
                    "word": word.get("word", ""),
                    "start": word.get("start", 0),
                    "end": word.get("end", 0),
                    "speaker": word.get("speaker", speaker),
                    "probability": (
                        word.get("probability", 1.0) if "probability" in word else 1.0
                    ),
                }
                for word in segment.get("words", [])
            ],
        }
        segments_list.append(segment_dict)

    # Save the detailed JSON with timing and speaker information
    transcription_data = {
        "language": result.get("language", detected_language),
        "segments": segments_list,
    }

    with open(transcription_path, "w", encoding="utf-8") as f:
        json.dump(transcription_data, f, indent=2, ensure_ascii=False)

    elapsed_time = time.time() - start_time
    logger.info(f"Diarized transcription completed in {elapsed_time:.2f} seconds")
    logger.info(f"Detailed JSON saved to: {transcription_path}")

    return transcription_data
