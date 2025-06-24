"""
Migration script to add s3_path field to existing meeting records.
"""

from dyntastic import A
from src.models.meeting import Meeting


def migrate_s3_path():
    """
    Add s3_path field to all existing meeting records that don't have it.
    """
    print("Starting migration to add s3_path field to existing meetings...")

    # Get all meetings
    meetings = Meeting.scan()
    updated_count = 0

    for meeting in meetings:
        # Check if s3_path field exists and is None
        if not hasattr(meeting, "s3_path") or meeting.s3_path is None:
            print(f"Updating meeting: {meeting.meeting} ({meeting.date})")
            meeting.s3_path = None
            meeting.save()
            updated_count += 1

    print(f"Migration complete. Updated {updated_count} meetings.")


if __name__ == "__main__":
    migrate_s3_path()
