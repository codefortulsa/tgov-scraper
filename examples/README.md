# DynamoDB Service for Meeting Objects

This directory contains examples of how to use the DynamoDB service for storing and querying `Meeting` objects.

## Setup

1. Make sure you have AWS credentials set up:

   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=your_preferred_region  # e.g., us-west-2
   ```

   Alternatively, create a `.env` file in the project root with these variables.

2. Install the required dependencies:

   ```bash
   poetry add boto3 python-dotenv
   ```

## Running the example

```bash
python examples/dynamo_example.py
```

This will:
1. Create a DynamoDB table named "ExampleMeetings" if it doesn't exist
2. Insert sample meeting data
3. Query meetings by name, date, and clip_id
4. Demonstrate retrieving specific meetings
5. Update meetings using both dictionary-based and model-based methods
6. List all meetings in the table
7. Delete a meeting and verify the deletion

## Using in your code

```python
from src.dynamo import DynamoDBService
from src.models.meeting import Meeting

# Initialize the service
dynamo_service = DynamoDBService(table_name="YourTableName")

# Create the table if it doesn't exist
dynamo_service.create_table_if_not_exists()

# Save a meeting
meeting = Meeting(
    meeting="City Council",
    date="2023-05-15T18:00:00",
    duration="2h 15m",
    clip_id="12345"
)
await dynamo_service.put_meeting(meeting)

# Query meetings by various attributes
city_council_meetings = await dynamo_service.query_meetings_by_name("City Council")
meetings_on_date = await dynamo_service.query_meetings_by_date("2023-05-15T18:00:00")
meetings_with_clip = await dynamo_service.query_meetings_by_clip_id("12345")

# Get a specific meeting
specific_meeting = await dynamo_service.get_meeting("City Council", "2023-05-15T18:00:00")

# Update a meeting (dictionary-based approach)
await dynamo_service.update_meeting(
    "City Council",
    "2023-05-15T18:00:00",
    {
        "duration": "3h 0m",
        "clip_id": "new-clip-id"
    }
)

# Update a meeting (model-based approach)
updated_model = Meeting(
    meeting="City Council",  # Required but not updated
    date="2023-05-15T18:00:00",  # Required but not updated
    duration="3h 30m",  # Will be updated
    video=HttpUrl("https://example.com/new-video-url")  # Will be updated
)
await dynamo_service.update_meeting_from_model(
    "City Council",
    "2023-05-15T18:00:00",
    updated_model
)

# List all meetings
all_meetings = await dynamo_service.list_all_meetings()

# Delete a meeting
await dynamo_service.delete_meeting("City Council", "2023-05-15T18:00:00")
```

## Available Indexes

The DynamoDB table includes the following indexes:

1. Primary Key: Composite key of `meeting` (partition key) and `date` (sort key)
2. DateIndex: Global Secondary Index on `date` (allows querying all meetings on a specific date)
3. ClipIdIndex: Global Secondary Index on `clip_id` (allows querying meetings by their clip ID)
