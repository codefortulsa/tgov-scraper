#!/usr/bin/env python3
"""
Summary generator for Tulsa Government Access Television meetings.

This script retrieves the list of meetings from the TGOV website and
saves them to a JSONL file for further processing or analysis.
"""
import os
import sys


import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.meetings import get_meetings
from src.models.meeting import Meeting


async def generate_summary() -> List[Dict[str, Any]]:
    """
    Generate a summary of all meetings.

    Returns:
        List of meeting data as dictionaries
    """
    meetings: List[Meeting] = await get_meetings()

    # Convert Pydantic models to dictionaries for JSON serialization
    # Use model_dump with mode='json' to ensure all values are JSON serializable
    return [meeting.model_dump(mode="json") for meeting in meetings]


async def save_to_jsonl(meetings: List[Dict[str, Any]], file_path: Path) -> None:
    """
    Save meetings data to a JSONL file.

    Args:
        meetings: List of meeting data as dictionaries
        file_path: Path to the output JSONL file
    """
    # Create directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write each meeting as a JSON line
    with file_path.open("w") as f:
        for meeting in meetings:
            f.write(json.dumps(meeting) + "\n")

    print(f"Saved {len(meetings)} meetings to {file_path}")


async def main() -> None:
    """Main function to retrieve and save meeting data."""
    # Original output path
    output_path = Path("data/meetings.jsonl")

    print("Retrieving meetings data...")
    meetings = await generate_summary()
    print(f"Found {len(meetings)} meetings")

    # Save to original location
    await save_to_jsonl(meetings, output_path)

    print("Summary generation complete")


if __name__ == "__main__":
    asyncio.run(main())
