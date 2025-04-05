#!/usr/bin/env python3
"""
Setup script for creating the DynamoDB table.
This should be run once to initialize the database.
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


def load_schema(schema_path: Path) -> Dict[str, Any]:
    """Load the DynamoDB table schema from JSON file."""
    try:
        with open(schema_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Schema file not found at {schema_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Invalid JSON in schema file at {schema_path}")
        return {}


def is_aws_configured() -> bool:
    """Check if AWS credentials are configured."""
    required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    return all(var in os.environ for var in required_vars)


def create_table(table_name: str, schema: Dict[str, Any]) -> bool:
    """Create the DynamoDB table if it doesn't exist."""
    if not is_aws_configured():
        print(
            "AWS credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
        )
        return False

    if not schema:
        print("Table schema is empty")
        return False

    # Set the table name in the schema
    schema["TableName"] = table_name

    dynamodb = boto3.resource("dynamodb")

    try:
        # Check if table exists
        dynamodb.meta.client.describe_table(TableName=table_name)
        print(f"Table '{table_name}' already exists")
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            # Create the table
            try:
                table = dynamodb.create_table(**schema)
                # Wait for the table to be created
                table.meta.client.get_waiter("table_exists").wait(TableName=table_name)
                print(f"Table '{table_name}' created successfully")
                return True
            except ClientError as create_error:
                print(f"Failed to create table: {create_error}")
                return False
        else:
            print(f"Error checking table existence: {e}")
            return False


def main():
    """Main function to set up the DynamoDB table."""
    parser = argparse.ArgumentParser(description="Set up DynamoDB table")
    parser.add_argument(
        "--table-name",
        default="TGOV-Meetings",
        help="Name of the DynamoDB table to create",
    )
    parser.add_argument(
        "--schema-path",
        default=str(Path(__file__).parent.parent / "db" / "schema.json"),
        help="Path to the schema JSON file",
    )
    args = parser.parse_args()

    # Load environment variables from .env file
    load_dotenv()

    # Load the schema
    schema_path = Path(args.schema_path)
    schema = load_schema(schema_path)

    if not schema:
        print("Failed to load schema. Exiting.")
        return 1

    # Create the table
    if create_table(args.table_name, schema):
        print("DynamoDB setup completed successfully.")
        return 0
    else:
        print("DynamoDB setup failed.")
        return 1


if __name__ == "__main__":
    exit(main())
