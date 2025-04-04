"""
DynamoDB service for storing and querying Meeting objects.
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

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

    def is_configured(self) -> bool:
        """Check if AWS credentials are configured."""
        required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
        return all(var in os.environ for var in required_vars)

    def create_table_if_not_exists(self) -> bool:
        """Create the DynamoDB table if it doesn't exist."""
        if not self.is_configured():
            print("AWS credentials not configured")
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
                    table = self.dynamodb.create_table(
                        TableName=self.table_name,
                        KeySchema=[
                            {
                                "AttributeName": "meeting",
                                "KeyType": "HASH",
                            },  # Partition key
                            {"AttributeName": "date", "KeyType": "RANGE"},  # Sort key
                        ],
                        AttributeDefinitions=[
                            {"AttributeName": "meeting", "AttributeType": "S"},
                            {"AttributeName": "date", "AttributeType": "S"},
                            {"AttributeName": "clip_id", "AttributeType": "S"},
                        ],
                        ProvisionedThroughput={
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5,
                        },
                        GlobalSecondaryIndexes=[
                            {
                                "IndexName": "DateIndex",
                                "KeySchema": [
                                    {"AttributeName": "date", "KeyType": "HASH"},
                                ],
                                "Projection": {"ProjectionType": "ALL"},
                                "ProvisionedThroughput": {
                                    "ReadCapacityUnits": 5,
                                    "WriteCapacityUnits": 5,
                                },
                            },
                            {
                                "IndexName": "ClipIdIndex",
                                "KeySchema": [
                                    {"AttributeName": "clip_id", "KeyType": "HASH"},
                                ],
                                "Projection": {"ProjectionType": "ALL"},
                                "ProvisionedThroughput": {
                                    "ReadCapacityUnits": 5,
                                    "WriteCapacityUnits": 5,
                                },
                            },
                        ],
                    )
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

    @staticmethod
    def _convert_decimal_to_float(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Decimal values to float in a dictionary."""
        for key, value in obj.items():
            if isinstance(value, Decimal):
                obj[key] = float(value)
            elif isinstance(value, dict):
                obj[key] = DynamoDBService._convert_decimal_to_float(value)
        return obj

    @staticmethod
    def _prepare_item_for_dynamodb(meeting: Meeting) -> Dict[str, Any]:
        """Convert Meeting object to DynamoDB item format."""
        # Convert to dict and ensure all fields have proper types for DynamoDB
        item = meeting.model_dump()

        # Convert any URL objects to strings
        if item.get("agenda"):
            item["agenda"] = str(item["agenda"])
        if item.get("video"):
            item["video"] = str(item["video"])

        return item

    async def put_meeting(self, meeting: Meeting) -> bool:
        """Insert or update a Meeting in DynamoDB."""
        if not self.is_configured():
            print("AWS credentials not configured")
            return False

        try:
            item = self._prepare_item_for_dynamodb(meeting)
            self.table.put_item(Item=item)
            print(f"Meeting '{meeting.meeting}' on {meeting.date} saved to DynamoDB")
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
                item = self._convert_decimal_to_float(response["Item"])
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
                item = self._convert_decimal_to_float(item)
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
                item = self._convert_decimal_to_float(item)
                meetings.append(Meeting.model_validate(item))

            # Handle pagination if needed
            while "LastEvaluatedKey" in response:
                response = self.table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                for item in response.get("Items", []):
                    item = self._convert_decimal_to_float(item)
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

    async def update_meeting_from_model(
        self, meeting_name: str, date: str, meeting: Meeting
    ) -> bool:
        """Update a meeting using a Meeting model."""
        # Convert the model to a dict and remove None values
        update_data = {
            k: v
            for k, v in self._prepare_item_for_dynamodb(meeting).items()
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

    def add_clip_id_index(self) -> bool:
        """Add ClipIdIndex to an existing DynamoDB table."""
        if not self.is_configured():
            print("AWS credentials not configured")
            return False

        try:
            # Update the table to add the new GSI
            client = boto3.client("dynamodb")
            response = client.update_table(
                TableName=self.table_name,
                AttributeDefinitions=[
                    {"AttributeName": "clip_id", "AttributeType": "S"}
                ],
                GlobalSecondaryIndexUpdates=[
                    {
                        "Create": {
                            "IndexName": "ClipIdIndex",
                            "KeySchema": [
                                {"AttributeName": "clip_id", "KeyType": "HASH"}
                            ],
                            "Projection": {"ProjectionType": "ALL"},
                            "ProvisionedThroughput": {
                                "ReadCapacityUnits": 5,
                                "WriteCapacityUnits": 5,
                            },
                        }
                    }
                ],
            )
            print(f"Adding ClipIdIndex to table '{self.table_name}'")
            print(f"Status: {response['TableDescription']['TableStatus']}")
            return True
        except ClientError as e:
            if "ResourceInUseException" in str(e):
                print(f"Table '{self.table_name}' is currently being modified")
                return False
            elif "ValidationException" in str(e) and "already exists" in str(e):
                print(
                    f"Index 'ClipIdIndex' already exists on table '{self.table_name}'"
                )
                return True
            else:
                print(f"Error adding index: {e}")
                return False
