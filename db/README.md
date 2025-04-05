# DynamoDB Database Setup and Usage

## Setting Up the Database

The `setup.py` script creates the DynamoDB table used to store meeting data. This should be run once before using the application for the first time.

### Prerequisites

1. AWS credentials configured in your environment:
   - Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in your environment or in a `.env` file at the project root
   - Ensure the AWS account has permissions to create and manage DynamoDB tables

2. Required Python packages:
   ```bash
   poetry add boto3 python-dotenv
   ```

### Running the Setup Script

Basic usage with default settings:
```bash
poetry run python db/setup.py
```

Custom table name:
```bash
poetry run python db/setup.py --table-name MyCustomTable
```

Custom schema path:
```bash
poetry run python db/setup.py --schema-path /path/to/schema.json
```

The script is idempotent - you can run it multiple times without creating duplicate tables.

## Table Structure

The DynamoDB table uses the following structure:

- **Primary Key:**
  - Partition Key: `name` (String) - The name of the meeting
  - Sort Key: `date` (String) - The date and time of the meeting

- **Secondary Indexes:**
  - `DateIndex` - Allows querying meetings by date
  - `ClipIdIndex` - Allows querying meetings by clip ID

- **Main Attributes:**
  - `meeting` - Name of the meeting (String)
  - `date` - Date and time of the meeting (String)
  - `clip_id` - Granicus clip ID (String, optional)
  - `value` - Map containing index values and all other meeting attributes

## Data Storage Pattern

Meeting data follows this pattern:
- Core identification fields (`name`, `date`, `clip_id`) are stored as top-level attributes to allow for efficient querying
- All other meeting details (duration, agenda URL, video URL, etc.) are stored in a single `value` map attribute

## Limitations
- You cannot directly query or filter based on attributes inside the `value` map
