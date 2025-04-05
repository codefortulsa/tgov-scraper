"""
DynamoDB service for storing and querying Meeting objects.
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel

from src.models.meeting import Meeting


class DynamoDBService:
    """Service for interacting with DynamoDB to store and retrieve Meeting objects."""

    def __init__(self, table_name: str = "Meetings"):
        """Initialize the DynamoDB service."""
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        self.schema_path = Path(__file__).parent / "schema.json"
        self.table_schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """Load the DynamoDB table schema from JSON file."""
        try:
            with open(self.schema_path, "r") as f:
                schema = json.load(f)
                if self.table_name != schema.get("TableName"):
                    schema["TableName"] = self.table_name
                return schema
        except FileNotFoundError:
            print(f"Schema file not found at {self.schema_path}")
            return {}
        except json.JSONDecodeError:
            print(f"Invalid JSON in schema file at {self.schema_path}")
            return {}

    def is_configured(self) -> bool:
        """Check if AWS credentials are configured."""
        required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
        return all(var in os.environ for var in required_vars)

    def create_table_if_not_exists(self) -> bool:
        """Create the DynamoDB table if it doesn't exist."""
        if not self.is_configured():
            print("AWS credentials not configured")
            return False

        if not self.table_schema:
            print("Table schema not loaded")
            return False

        try:
            # Check if table exists
            self.dynamodb.meta.client.describe_table(TableName=self.table_name)
            print(f"Table '{self.table_name}' already exists")
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                # Create the table
                try:
                    table = self.dynamodb.create_table(**self.table_schema)
                    # Wait for the table to be created
                    table.meta.client.get_waiter("table_exists").wait(
                        TableName=self.table_name
                    )
                    print(f"Table '{self.table_name}' created successfully")
                    return True
                except ClientError as create_error:
                    print(f"Failed to create table: {create_error}")
                    return False
            else:
                print(f"Error checking table existence: {e}")
                return False

    async def put_meeting(self, meeting: Meeting) -> bool:
        """Insert or update a Meeting in DynamoDB."""
        if not self.is_configured():
            print("AWS credentials not configured")
            return False

        try:
            item = meeting.model_dump()
            self.table.put_item(Item=item)
            print(f"Meeting '{meeting.name}' on {meeting.date} saved to DynamoDB")
            return True
        except ClientError as e:
            print(f"Error putting meeting: {e}")
            return False

    async def get_meeting(self, meeting_name: str, date: str) -> Optional[Meeting]:
        """Get a specific Meeting by its name and date."""
        if not self.is_configured():
            print("AWS credentials not configured")
            return None

        try:
            response = self.table.get_item(Key={"meeting": meeting_name, "date": date})

            if "Item" in response:
                return Meeting.model_validate(item)
            else:
                print(f"No meeting found with name '{meeting_name}' and date '{date}'")
                return None
        except ClientError as e:
            print(f"Error getting meeting: {e}")
            return None

    async def query_meetings_by_name(self, meeting_name: str) -> List[Meeting]:
        """Query meetings by name."""
        if not self.is_configured():
            print("AWS credentials not configured")
            return []

        try:
            response = self.table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("meeting").eq(
                    meeting_name
                )
            )

            meetings = []
            for item in response.get("Items", []):
                meetings.append(Meeting.model_validate(item))

            return meetings
        except ClientError as e:
            print(f"Error querying meetings by name: {e}")
            return []

    async def query_meetings_by_date(self, date: str) -> List[Meeting]:
        """Query meetings by date using the GSI."""
        if not self.is_configured():
            print("AWS credentials not configured")
            return []

        try:
            response = self.table.query(
                IndexName="DateIndex",
                KeyConditionExpression=boto3.dynamodb.conditions.Key("date").eq(date),
            )

            meetings = []
            for item in response.get("Items", []):
                item = self._convert_decimal_to_float(item)
                meetings.append(Meeting.model_validate(item))

            return meetings
        except ClientError as e:
            print(f"Error querying meetings by date: {e}")
            return []

    async def list_all_meetings(self) -> List[Meeting]:
        """List all meetings in the table."""
        if not self.is_configured():
            print("AWS credentials not configured")
            return []

        try:
            response = self.table.scan()

            meetings = []
            for item in response.get("Items", []):
                meetings.append(Meeting.model_validate(item))

            # Handle pagination if needed
            while "LastEvaluatedKey" in response:
                response = self.table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                for item in response.get("Items", []):
                    meetings.append(Meeting.model_validate(item))

            return meetings
        except ClientError as e:
            print(f"Error listing all meetings: {e}")
            return []

    async def update_meeting(
        self, meeting_name: str, date: str, update_data: Dict[str, Any]
    ) -> bool:
        """Update specific attributes of a meeting without replacing the entire item."""
        if not self.is_configured():
            print("AWS credentials not configured")
            return False

        # Don't allow updating the primary key attributes
        if "meeting" in update_data or "date" in update_data:
            print("Cannot update primary key attributes (meeting, date)")
            return False

        try:
            # Build the update expression and attribute values
            update_expression_parts = []
            expression_attribute_values = {}

            for key, value in update_data.items():
                update_expression_parts.append(f"#{key} = :{key}")
                expression_attribute_values[f":{key}"] = value

            # Build expression attribute names (to handle reserved words)
            expression_attribute_names = {f"#{key}": key for key in update_data.keys()}

            # Construct the complete update expression
            update_expression = "SET " + ", ".join(update_expression_parts)

            self.table.update_item(
                Key={"meeting": meeting_name, "date": date},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="UPDATED_NEW",
            )

            print(f"Updated meeting '{meeting_name}' on {date}")
            return True
        except ClientError as e:
            print(f"Error updating meeting: {e}")
            return False

    async def update(self, meeting_name: str, date: str, meeting: Meeting) -> bool:
        """Update a meeting using a Meeting model."""
        # Convert the model to a dict and remove None values
        update_data = {
            k: v
            for k, v in meeting.model_dump().items()
            if v is not None and k not in ["meeting", "date"]
        }

        # Only update if there are fields to update
        if not update_data:
            print("No fields to update")
            return False

        return await self.update_meeting(meeting_name, date, update_data)

    async def delete_meeting(self, meeting_name: str, date: str) -> bool:
        """Delete a meeting by name and date."""
        if not self.is_configured():
            print("AWS credentials not configured")
            return False

        try:
            self.table.delete_item(Key={"meeting": meeting_name, "date": date})
            print(f"Meeting '{meeting_name}' on {date} deleted")
            return True
        except ClientError as e:
            print(f"Error deleting meeting: {e}")
            return False

    async def query_meetings_by_clip_id(self, clip_id: str) -> List[Meeting]:
        """Query meetings by clip_id using the ClipIdIndex GSI."""
        if not self.is_configured():
            print("AWS credentials not configured")
            return []

        # Handle None clip_id
        if not clip_id:
            print("Clip ID cannot be None or empty")
            return []

        try:
            response = self.table.query(
                IndexName="ClipIdIndex",
                KeyConditionExpression=boto3.dynamodb.conditions.Key("clip_id").eq(
                    clip_id
                ),
            )

            meetings = []
            for item in response.get("Items", []):
                item = self._convert_decimal_to_float(item)
                meetings.append(Meeting.model_validate(item))

            return meetings
        except ClientError as e:
            print(f"Error querying meetings by clip_id: {e}")
            return []
