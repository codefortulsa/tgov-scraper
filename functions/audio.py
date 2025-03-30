import os
import json
import logging
from typing import Optional, Dict, List
import subprocess
import torch
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
from pathlib import Path

logger = logging.getLogger(__name__)


async def transcribe_audio(
    audio_path: str,
    output_dir: str,
    model_size: str = "tiny",
    device: str = "cpu",
    language: Optional[str] = None,
    verbose: bool = False,
    vad_filter: bool = False,
    beam_size: int = 5,
    force_download: bool = False,
    hf_token: Optional[str] = None,
    max_duration: int = 300,  # Default to 5 minutes (300 seconds)
    min_segment_duration: float = 0.5,  # Minimum segment duration for speaker assignment
    roll_call_mode: bool = False,  # Special mode for roll call scenarios
) -> str:
    """
    Transcribe a video file with speaker diarization using faster-whisper and pyannote.

    Args:
        video_path: Path to the video file
        output_dir: Directory to save the transcription
        model_size: Size of the Whisper model to use
        device: Device to use for inference
        language: Language code
        verbose: Whether to print verbose output
        vad_filter: Whether to use Voice Activity Detection
        beam_size: Beam size for the decoder
        force_download: Whether to force download the model
        hf_token: Hugging Face token for accessing diarization models
        max_duration: Maximum duration in seconds to process (default: 300 seconds / 5 minutes)
        min_segment_duration: Minimum segment duration for speaker assignment (default: 0.5 seconds)
        roll_call_mode: Special mode for roll call scenarios (default: False)

    Returns:
        Path to the saved JSON file

    Raises:
        ValueError: If speaker diarization is not available or fails
    """

    # Check for HF token in environment if not provided
    if not hf_token:
        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            raise ValueError(
                "No Hugging Face token found in HUGGINGFACE_TOKEN environment variable or --hf-token parameter. "
                "Speaker diarization requires a valid Hugging Face token with access to pyannote/speaker-diarization-3.1. "
                "Please visit https://hf.co/pyannote/speaker-diarization-3.1 to accept the user conditions and "
                "set your token in the HUGGINGFACE_TOKEN environment variable or pass it with --hf-token."
            )
        else:
            logger.info("Using Hugging Face token from environment variable.")

    # Create audio directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get the base filename without extension
    audio_filename = os.path.basename(audio_path)
    base_filename = os.path.splitext(audio_filename)[0]

    # Define output path
    json_file: Path = os.path.join(output_dir, f"{base_filename}.json")

    # First, perform regular transcription
    logger.info("Performing transcription with faster-whisper...")

    # Handle MPS device (Apple Silicon)
    compute_type = "float32"
    whisper_device = device
    if device == "mps":
        logger.info(
            "MPS device requested but faster-whisper doesn't support it. Using CPU instead."
        )
        whisper_device = "cpu"

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
            model = WhisperModel(
                model_path, device=whisper_device, compute_type=compute_type
            )
        else:
            model = WhisperModel(
                model_size,
                device=whisper_device,
                compute_type=compute_type,
                download_root="./models/whisper",
            )
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        logger.info("Falling back to tiny model")
        model = WhisperModel(
            "tiny",
            device=whisper_device,
            compute_type=compute_type,
            download_root="./models/whisper",
        )

    # Run the transcription
    segments, info = model.transcribe(
        audio_path,
        language=language,
        task="transcribe",
        beam_size=beam_size,
        vad_filter=vad_filter,
        vad_parameters=dict(min_silence_duration_ms=500) if vad_filter else None,
    )

    # Process the segments
    segments_list = []
    for segment in segments:
        # Skip segments beyond max_duration
        if segment.start > max_duration:
            break

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

    # Now perform speaker diarization
    logger.info("Performing speaker diarization with pyannote.audio...")

    # Handle device for diarization
    diarize_device = device
    if device == "mps":
        if torch.backends.mps.is_available():
            logger.info("Using MPS device for diarization")
        else:
            logger.warning(
                "MPS requested but not available. Using CPU for diarization."
            )
            diarize_device = "cpu"

    # Check for PyAnnote models in the Hugging Face cache
    from huggingface_hub import HfFolder, hf_hub_download, try_to_load_from_cache

    # Print Hugging Face cache directory
    cache_dir = os.path.expanduser("~/.cache/huggingface")
    logger.info(f"Hugging Face cache directory: {cache_dir}")

    # Check if the token is valid
    logger.info(f"Checking if Hugging Face token is valid...")
    try:
        token_is_valid = HfFolder.get_token() is not None
        logger.info(f"Token from HfFolder: {token_is_valid}")
    except Exception as e:
        logger.warning(f"Error checking token from HfFolder: {e}")

    # Set the token explicitly
    os.environ["HF_TOKEN"] = hf_token
    os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token

    # Check for PyAnnote models
    model_ids = [
        "pyannote/speaker-diarization-3.1",
        "pyannote/segmentation-3.0",
    ]

    for model_id in model_ids:
        logger.info(f"Checking for model: {model_id}")
        try:
            # Try to find the model in cache
            cache_path = try_to_load_from_cache(
                repo_id=model_id,
                filename="config.yaml",
                use_auth_token=hf_token,
            )
            if cache_path:
                logger.info(f"Found model in cache: {cache_path}")
            else:
                logger.info(f"Model not found in cache, will download: {model_id}")

                # Try to download the model
                try:
                    download_path = hf_hub_download(
                        repo_id=model_id,
                        filename="config.yaml",
                        use_auth_token=hf_token,
                        force_download=True,
                    )
                    logger.info(f"Downloaded model to: {download_path}")
                except Exception as download_error:
                    logger.error(
                        f"Error downloading model {model_id}: {download_error}"
                    )
        except Exception as e:
            logger.error(f"Error checking for model {model_id}: {e}")

    # Initialize the speaker diarization pipeline
    try:
        logger.info(
            f"Initializing speaker diarization pipeline with token: {hf_token[:5]}..."
        )
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
        )

        # Set the appropriate device
        if diarize_device == "cuda":
            logger.info("Moving pipeline to CUDA device")
            pipeline = pipeline.to(torch.device("cuda"))
        elif diarize_device == "mps" and torch.backends.mps.is_available():
            logger.info("Moving pipeline to MPS device")
            pipeline = pipeline.to(torch.device("mps"))

        # Run the pipeline on the audio file
        logger.info("Running diarization pipeline...")
        diarization = pipeline(audio_path)

        # Extract speaker segments
        speaker_segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_segments.append(
                {"start": turn.start, "end": turn.end, "speaker": speaker}
            )

        logger.info(f"Found {len(speaker_segments)} speaker segments")

        # Assign speakers to transcription segments
        logger.info("Assigning speakers to transcription segments...")
        for segment in segments_list:
            segment_start = segment["start"]
            segment_end = segment["end"]
            segment_duration = segment_end - segment_start

            # Find the speaker who speaks the most during this segment
            speaker_times = {}
            for speaker_segment in speaker_segments:
                if (
                    speaker_segment["end"] > segment_start
                    and speaker_segment["start"] < segment_end
                ):
                    # Calculate overlap
                    overlap_start = max(segment_start, speaker_segment["start"])
                    overlap_end = min(segment_end, speaker_segment["end"])
                    overlap_duration = overlap_end - overlap_start

                    if overlap_duration > 0:
                        speaker = speaker_segment["speaker"]
                        speaker_times[speaker] = (
                            speaker_times.get(speaker, 0) + overlap_duration
                        )

            # Special handling for very short segments (like "here" responses in roll calls)
            if roll_call_mode:
                # Check if this segment contains a councillor name call
                is_name_call = "councillor" in segment["text"].strip().lower()
                is_response = segment["text"].strip().lower() in [
                    "here",
                    "present",
                    "yes",
                    "no",
                ]

                if is_name_call:
                    # This is likely the clerk calling a name
                    # Mark this segment with a special tag to identify the clerk
                    segment["is_clerk"] = True

                    # Use the dominant speaker for the clerk
                    if speaker_times:
                        dominant_speaker = max(speaker_times, key=speaker_times.get)
                        segment["speaker"] = dominant_speaker
                    else:
                        segment["speaker"] = "SPEAKER_UNK"

                elif is_response and segment_duration < min_segment_duration:
                    # This is likely a councillor responding
                    # Try to find a different speaker than the clerk

                    # Look for the most recent name call (clerk)
                    clerk_speaker = None
                    for i in range(len(segments_list)):
                        if i >= segment["id"] - 1:
                            break
                        prev_segment = segments_list[i]
                        if prev_segment.get("is_clerk", False):
                            clerk_speaker = prev_segment.get("speaker", "SPEAKER_UNK")
                            break

                    if clerk_speaker and speaker_times:
                        # Try to find a different speaker than the clerk
                        for spk in speaker_times:
                            if spk != clerk_speaker:
                                segment["speaker"] = spk
                                break
                        else:
                            # If no different speaker found, use the dominant one
                            dominant_speaker = max(speaker_times, key=speaker_times.get)
                            segment["speaker"] = dominant_speaker
                    else:
                        # If can't find clerk or no speaker times, use dominant speaker
                        if speaker_times:
                            dominant_speaker = max(speaker_times, key=speaker_times.get)
                            segment["speaker"] = dominant_speaker
                        else:
                            segment["speaker"] = "SPEAKER_UNK"
                else:
                    # For other segments, use the dominant speaker
                    if speaker_times:
                        dominant_speaker = max(speaker_times, key=speaker_times.get)
                        segment["speaker"] = dominant_speaker
                    else:
                        segment["speaker"] = "SPEAKER_UNK"
            else:
                # Standard speaker assignment for normal segments
                if speaker_times:
                    dominant_speaker = max(speaker_times, key=speaker_times.get)
                    segment["speaker"] = dominant_speaker
                else:
                    segment["speaker"] = "SPEAKER_UNK"
    except Exception as e:
        logger.error(
            f"Error during diarization pipeline initialization or processing: {e}"
        )
        logger.error(f"Error type: {type(e).__name__}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        # Fail with a clear error message
        raise ValueError(
            f"Speaker diarization failed: {e}\n\n"
            "Please ensure you have:\n"
            "1. A valid Hugging Face token with access to pyannote/speaker-diarization-3.1\n"
            "2. Accepted the user conditions at https://hf.co/pyannote/speaker-diarization-3.1\n"
            "3. Set your token in the HUGGINGFACE_TOKEN environment variable or passed it with --hf-token\n"
            "4. A working internet connection to download the model"
        ) from e

    # Save the detailed JSON with timing and speaker information
    transcription_data = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "segments": segments_list,
    }

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(transcription_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Detailed JSON with speaker information saved to: {json_file}")

    if verbose:
        print("\nTranscription preview with speakers:")
        for i, segment in enumerate(segments_list[:5]):
            speaker = segment.get("speaker", "Unknown")
            print(f"{speaker}: {segment['text']}")
            if i == 4:  # Show only first 5 segments
                print("...")

    return json_file
