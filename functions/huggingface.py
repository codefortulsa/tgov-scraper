"""
Utility functions for loading Hugging Face models.
"""

import os
import logging
import time
from typing import Optional
from pathlib import Path
import torch
from pyannote.audio import Pipeline
from faster_whisper import WhisperModel
import whisperx
import dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

dotenv.load_dotenv()
hf_token = os.getenv("HUGGINGFACE_TOKEN")


async def get_whisper(
    model_size: str,
    device: str = "cpu",
    force_download: bool = False,
    download_root: str = "../models/whisper",
):
    """
    Load a Whisper model from Hugging Face.

    Args:
        model_size: Size of the model (tiny, base, small, medium, large-v1, large-v2, large-v3)
        device: Device to use for inference (cpu, cuda, or mps)
        force_download: Whether to force download the model even if it exists
        download_root: Directory to save the downloaded model

    Returns:
        Loaded WhisperModel
    """
    # Handle MPS device (Apple Silicon)
    compute_type = "float32"
    whisper_device = device
    # Ensure the model directory exists
    os.makedirs(download_root, exist_ok=True)

    # Load the Whisper model

    model = WhisperModel(
        model_size,
        device=whisper_device,
        compute_type=compute_type,
        download_root=download_root,
    )
    logger.info(f"Successfully loaded Whisper model: {model_size}")
    return model


async def get_whisperx(
    model_size: str = "medium",
    device: str = "auto",
    compute_type: str = "auto",
    download_root: str = "../models/whisperx",
    language: Optional[str] = None,
    batch_size: int = 16,
) -> dict:
    """
    Load WhisperX model with diarization support.

    Args:
        model_size: Size of the model (tiny, base, small, medium, large-v1, large-v2, large-v3)
        device: Device to use for inference ('auto', 'cpu', 'cuda', 'mps')
                'auto' will use CUDA if available, otherwise CPU
        compute_type: Computation precision ('auto', 'float32', 'float16', 'int8')
                    'auto' will use float16 for GPU, int8 for CPU
        download_root: Directory to save the downloaded models
        language: Language code (e.g., 'en', 'fr'). If None, will be auto-detected.
        batch_size: Batch size for processing

    Returns:
        Dictionary containing WhisperX model components
    """
    # Ensure the model directory exists
    os.makedirs(download_root, exist_ok=True)

    # Auto-detect optimal device and compute type
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Auto-detected device: {device}")

    if compute_type == "auto":
        if device == "cuda":
            compute_type = "float16"  # Better performance on GPU
        else:
            compute_type = "int8"  # Better performance on CPU
        logger.info(f"Auto-selected compute_type: {compute_type}")

    start_time = time.time()
    logger.info(
        f"Loading WhisperX model: {model_size} on {device} with {compute_type} precision"
    )

    # Create result dictionary to hold model components
    result = {}

    # Load main transcription model
    transcribe_model = whisperx.load_model(
        model_size,
        device=device,
        compute_type=compute_type,
        download_root=download_root,
    )
    result["model"] = transcribe_model

    # Load alignment model if language is specified
    if language is not None:
        logger.info(f"Loading alignment model for language: {language}")
        align_model, align_metadata = whisperx.load_align_model(
            language_code=language,
            device=device,
            model_dir=os.path.join(download_root, "alignment"),
        )
        result["align_model"] = align_model
        result["align_metadata"] = align_metadata

    # Create diarization pipeline if token is available
    if hf_token:
        try:
            logger.info("Loading diarization pipeline")
            diarize_model = whisperx.DiarizationPipeline(
                use_auth_token=hf_token, device=device
            )
            result["diarize_model"] = diarize_model
        except Exception as e:
            logger.error(f"Failed to load diarization pipeline: {e}")
            logger.warning("Diarization will not be available")

    elapsed_time = time.time() - start_time
    logger.info(f"WhisperX model loaded in {elapsed_time:.2f} seconds")

    return result
