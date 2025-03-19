#!/usr/bin/env python3
"""
Summary generator for Tulsa Government Access Television meetings.

This script looks for meetings from the past week and generates placeholder summaries
for them, storing the results in a summaries.jsonl file.
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.models.meeting import Meeting, MeetingSummary

MEETINGS_FILE = Path("data/meetings.jsonl")
SUMMARY_FILE = Path("data/summaries.jsonl")


async def load_meetings() -> List[Meeting]:
    """
    Load the meetings from the meetings.jsonl file.

    Returns:
        A list of meeting data dictionaries
    """
    if not MEETINGS_FILE.exists():
        print("Meetings file not found. Please run scripts/summary.py first.")
        return []

    meetings = []
    with MEETINGS_FILE.open("r") as f:
        for line in f:
            if line.strip():
                meetings.append(Meeting(**json.loads(line)))

    print(f"Loaded {len(meetings)} meetings.")
    return meetings


async def load_summaries() -> list[MeetingSummary]:
    """
    Load existing summaries from summaries.jsonl if it exists.

    Returns:
        A dictionary mapping meeting IDs to summary data
    """
    if not SUMMARY_FILE.exists():
        return []

    summaries = []
    with SUMMARY_FILE.open("r") as f:
        for line in f:
            if line.strip():
                summary = json.loads(line)
                summaries.append(MeetingSummary(**summary))

    print(f"Loaded {len(summaries)} existing summaries.")
    return summaries


async def find_recent_meetings(meetings: List[Meeting]) -> List[Meeting]:
    """
    Find meetings from the past week that need summaries.

    Args:
        meetings: List of meeting data dictionaries

    Returns:
        List of meetings from the past week
    """
    now = datetime.now(timezone.utc)
    one_week_ago = now - timedelta(days=7)

    recent_meetings = []
    for meeting in meetings:
        # Try to parse the ISO date string
        try:
            meeting_date = datetime.fromisoformat(meeting.date)
            # Check if the meeting is within the past week
            if meeting_date > one_week_ago and meeting_date <= now:
                recent_meetings.append(meeting)
        except (ValueError, KeyError):
            # Skip meetings with invalid dates
            continue

    print(f"Found {len(recent_meetings)} meetings from the past week.")
    return recent_meetings


async def generate_placeholder_summary(meeting: Meeting) -> list[MeetingSummary]:
    """
    Generate a placeholder summary for a meeting.

    Args:
        meeting: Meeting data dictionary

    Returns:
        Summary data dictionary with placeholder text
    """
    # Create the summary object
    summary = MeetingSummary(
        meeting=meeting,
        summary="[PLACEHOLDER] This meeting summary will be generated automatically.",
        summarization_date=datetime.now(timezone.utc).isoformat(),
        needs_summarization=True,
    )

    return summary


async def save_summaries(summaries: List[MeetingSummary]) -> None:

    # Create data directory if they doesn't exist
    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)

    # save to website directory
    with SUMMARY_FILE.open("w") as f:
        for summary in summaries:
            f.write(summary.model_dump_json() + "\n")
    print(f"Saved {len(summaries)} summaries to {SUMMARY_FILE}.")


async def main() -> None:
    """Main function to generate summaries for recent meetings."""
    # Load existing data
    meetings = await load_meetings()

    summaries = await load_summaries()
    original_summary_count = len(summaries)
    summarized_meetings = [s.meeting for s in summaries]

    # Find recent meetings
    recent_meetings = await find_recent_meetings(meetings)

    for meeting in recent_meetings:
        if meeting not in summarized_meetings:
            # This is a new meeting that needs a summary
            summary = await generate_placeholder_summary(meeting)
            summaries.append(summary)

    new_summary_count = len(summaries) - original_summary_count
    print(f"Generated {new_summary_count} new summaries.")

    # Save all summaries back to the file
    await save_summaries(summaries)


if __name__ == "__main__":
    asyncio.run(main())
