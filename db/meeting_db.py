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

from src.models.meeting import Meeting, MeetingQuery


class DynamoDBService:
    """Service for interacting with DynamoDB to store and retrieve Meeting objects."""

    def __init__(self, table_name: str = "Meetings"):
        """Initialize the DynamoDB service."""
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    async def save(self, meeting: Meeting) -> bool:
        """Insert or update a Meeting in DynamoDB."""

        try:
            item = meeting.model_dump()
            self.table.put_item(Item=item)
            print(f"Meeting '{meeting.name}' on {meeting.date} saved to DynamoDB")
            return True
        except ClientError as e:
            print(f"Error putting meeting: {e}")
            return False

    async def query(self, query: MeetingQuery) -> List[Meeting]:
        """
        Query meetings based on the provided MeetingQuery object.
        Uses the most efficient index based on which fields are set in the query.
        If multiple fields are set, returns only meetings matching all criteria.
        """
        try:
            # Get the non-None values from the query
            query_dict = {k: v for k, v in query.model_dump().items() if v is not None}

            # If no query parameters, return empty list
            if not query_dict:
                print("No query parameters provided")
                return []

            # Choose the appropriate query method based on which fields are set
            if "meeting" in query_dict:
                # Query by meeting name (primary key)
                key_condition = boto3.dynamodb.conditions.Key("meeting").eq(query.name)

                # If date is also specified, use it as a range condition
                if "date" in query_dict:
                    key_condition = key_condition & boto3.dynamodb.conditions.Key(
                        "date"
                    ).eq(query.date)

                response = self.table.query(KeyConditionExpression=key_condition)

            elif "date" in query_dict:
                # Query by date using DateIndex
                response = self.table.query(
                    IndexName="DateIndex",
                    KeyConditionExpression=boto3.dynamodb.conditions.Key("date").eq(
                        query.date
                    ),
                )

            elif "clip_id" in query_dict:
                # Query by clip_id using ClipIdIndex
                response = self.table.query(
                    IndexName="ClipIdIndex",
                    KeyConditionExpression=boto3.dynamodb.conditions.Key("clip_id").eq(
                        query.clip_id
                    ),
                )

            else:
                print(
                    "Invalid query: must specify at least one of meeting, date, or clip_id"
                )
                return []

            # Process the results
            meetings = []
            for item in response.get("Items", []):
                meetings.append(Meeting.model_validate(item))

            # Handle pagination if needed
            while "LastEvaluatedKey" in response:
                # Use the appropriate pagination method based on which query was used
                if "meeting" in query_dict:
                    response = self.table.query(
                        KeyConditionExpression=key_condition,
                        ExclusiveStartKey=response["LastEvaluatedKey"],
                    )
                elif "date" in query_dict:
                    response = self.table.query(
                        IndexName="DateIndex",
                        KeyConditionExpression=boto3.dynamodb.conditions.Key("date").eq(
                            query.date
                        ),
                        ExclusiveStartKey=response["LastEvaluatedKey"],
                    )
                elif "clip_id" in query_dict:
                    response = self.table.query(
                        IndexName="ClipIdIndex",
                        KeyConditionExpression=boto3.dynamodb.conditions.Key(
                            "clip_id"
                        ).eq(query.clip_id),
                        ExclusiveStartKey=response["LastEvaluatedKey"],
                    )

                for item in response.get("Items", []):
                    meetings.append(Meeting.model_validate(item))

            return meetings

        except ClientError as e:
            print(f"Error querying meetings: {e}")
            return []

    async def all(self) -> List[Meeting]:
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

    async def update(self, meeting: Meeting) -> bool:
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

    async def delete(self, meeting: MeetingQuery) -> bool:

        try:
            self.table.delete_item(Key={"meeting": meeting.name, "date": meeting.date})
            print(f"Meeting '{meeting.name}' on {meeting.date} deleted")
            return True
        except ClientError as e:
            print(f"Error deleting meeting: {e}")
            return False
