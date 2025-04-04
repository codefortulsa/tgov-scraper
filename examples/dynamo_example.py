#!/usr/bin/env python3
"""Example script demonstrating the use of DynamoDB service with Meeting objects."""

import asyncio
import os
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from pydantic import HttpUrl

import sys
from pathlib import Path

# Add the parent directory to the Python path to allow importing from src
sys.path.append(str(Path(__file__).parent.parent))

from src.dynamo import DynamoDBService
from src.models.meeting import Meeting


async def main():
    """Demonstrate DynamoDB operations with Meeting objects."""
    # Load environment variables from .env file
    load_dotenv()

    # Initialize DynamoDB service
    dynamo_service = DynamoDBService(table_name="ExampleMeetings")

    # Create table if it doesn't exist
    table_exists = dynamo_service.create_table_if_not_exists()
    if not table_exists:
        print("Failed to create or verify DynamoDB table. Exiting.")
        return

    # Example meeting data
    meetings = [
        Meeting(
            meeting="City Council",
            date="2023-05-15T18:00:00",
            duration="2h 15m",
            agenda=HttpUrl("https://example.com/agenda1"),
            video=HttpUrl("https://example.com/video1"),
            clip_id="12345",
        ),
        Meeting(
            meeting="Planning Commission",
            date="2023-05-16T10:00:00",
            duration="1h 30m",
            agenda=HttpUrl("https://example.com/agenda2"),
            video=HttpUrl("https://example.com/video2"),
            clip_id="67890",
        ),
        Meeting(
            meeting="City Council",
            date="2023-05-22T18:00:00",
            duration="2h 45m",
            agenda=HttpUrl("https://example.com/agenda3"),
            video=HttpUrl("https://example.com/video3"),
            clip_id="54321",
        ),
    ]

    # Insert meetings
    print("\n=== Inserting meetings ===")
    for meeting in meetings:
        success = await dynamo_service.put_meeting(meeting)
        if success:
            print(f"Successfully inserted: {meeting}")
        else:
            print(f"Failed to insert: {meeting}")

    # Query meetings by name
    print("\n=== Querying meetings by name ===")
    city_council_meetings = await dynamo_service.query_meetings_by_name("City Council")
    print(f"Found {len(city_council_meetings)} City Council meetings:")
    for meeting in city_council_meetings:
        print(f"  - {meeting}")

    # Query meetings by date
    print("\n=== Querying meetings by date ===")
    may16_meetings = await dynamo_service.query_meetings_by_date("2023-05-16T10:00:00")
    print(f"Found {len(may16_meetings)} meetings on May 16, 2023:")
    for meeting in may16_meetings:
        print(f"  - {meeting}")

    # Query meetings by clip_id
    print("\n=== Querying meetings by clip_id ===")
    clip_meetings = await dynamo_service.query_meetings_by_clip_id("67890")
    print(f"Found {len(clip_meetings)} meetings with clip_id '67890':")
    for meeting in clip_meetings:
        print(f"  - {meeting}")

    # Get a specific meeting
    print("\n=== Getting a specific meeting ===")
    specific_meeting = await dynamo_service.get_meeting(
        "Planning Commission", "2023-05-16T10:00:00"
    )
    if specific_meeting:
        print(f"Found specific meeting: {specific_meeting}")
    else:
        print("Specific meeting not found")

    # Update meeting using the dictionary-based method
    print("\n=== Updating meeting (dictionary-based) ===")
    update_success = await dynamo_service.update_meeting(
        "Planning Commission",
        "2023-05-16T10:00:00",
        {
            "duration": "2h 0m",  # Changed from 1h 30m to 2h 0m
            "clip_id": "67890-updated",
        },
    )
    if update_success:
        print("Successfully updated Planning Commission meeting")
        # Get the updated meeting to verify changes
        updated_meeting = await dynamo_service.get_meeting(
            "Planning Commission", "2023-05-16T10:00:00"
        )
        if updated_meeting:
            print(f"Updated meeting: {updated_meeting}")
    else:
        print("Failed to update meeting")

    # Query meetings with updated clip_id
    print("\n=== Querying meetings by updated clip_id ===")
    updated_clip_meetings = await dynamo_service.query_meetings_by_clip_id(
        "67890-updated"
    )
    print(f"Found {len(updated_clip_meetings)} meetings with clip_id '67890-updated':")
    for meeting in updated_clip_meetings:
        print(f"  - {meeting}")

    # Update meeting using the model-based method
    print("\n=== Updating meeting (model-based) ===")
    # Create a partial model with only the fields to update
    updated_model = Meeting(
        meeting="City Council",
        date="2023-05-15T18:00:00",
        duration="3h 0m",  # Changed from 2h 15m to 3h 0m
        video=HttpUrl("https://example.com/video1-new"),
    )

    update_success = await dynamo_service.update_meeting_from_model(
        "City Council", "2023-05-15T18:00:00", updated_model
    )

    if update_success:
        print("Successfully updated City Council meeting")
        # Get the updated meeting to verify changes
        updated_meeting = await dynamo_service.get_meeting(
            "City Council", "2023-05-15T18:00:00"
        )
        if updated_meeting:
            print(f"Updated meeting: {updated_meeting}")
    else:
        print("Failed to update meeting")

    # List all meetings
    print("\n=== Listing all meetings ===")
    all_meetings = await dynamo_service.list_all_meetings()
    print(f"Found {len(all_meetings)} total meetings:")
    for meeting in all_meetings:
        print(f"  - {meeting}")

    # Delete a meeting
    print("\n=== Deleting a meeting ===")
    delete_success = await dynamo_service.delete_meeting(
        "Planning Commission", "2023-05-16T10:00:00"
    )
    if delete_success:
        print("Successfully deleted Planning Commission meeting")
    else:
        print("Failed to delete meeting")

    # Verify deletion by listing all meetings again
    print("\n=== Verifying deletion ===")
    remaining_meetings = await dynamo_service.list_all_meetings()
    print(f"Remaining meetings ({len(remaining_meetings)}):")
    for meeting in remaining_meetings:
        print(f"  - {meeting}")


if __name__ == "__main__":
    asyncio.run(main())
