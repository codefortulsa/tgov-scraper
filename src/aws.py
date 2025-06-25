import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from pydantic import HttpUrl


def is_aws_configured():
    required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"]
    return True
    # return all(var in os.environ for var in required_vars)


s3_client = boto3.client("s3")


def create_bucket_if_not_exists(bucket_name):
    try:
        # Check if the bucket exists by listing its objects
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' already exists.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            # Bucket does not exist, create it
            try:
                s3_client.create_bucket(Bucket=bucket_name)
                print(f"Bucket '{bucket_name}' created.")
            except ClientError as error:
                print(f"Failed to create bucket '{bucket_name}': {error}")
        else:
            # Handle other ClientError exceptions
            print(f"Client error: {e}")


def upload_to_s3(file_path, bucket_name, s3_path):
    try:
        s3_client.upload_file(file_path, bucket_name, s3_path)
        print(f"Uploaded {file_path} to {bucket_name}/{s3_path}")
        return True
    except (NoCredentialsError, PartialCredentialsError) as e:
        print(f"Failed to upload to S3: {str(e)}")
        return False


def save_content_to_s3(content, bucket_name, s3_key, content_type):
    response = s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=content.encode("utf-8"),
        ContentType=content_type,
    )
    region = s3_client.meta.region_name
    url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
    return HttpUrl(url)


def get_video_from_s3(bucket_name, s3_path):
    try:
        # Create output directory if it doesn't exist
        output_dir = Path("data/video")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Define output path
        output_path = output_dir / Path(s3_path).name

        # Download file from S3
        s3_client.download_file(bucket_name, s3_path, str(output_path))
        print(f"Downloaded {s3_path} from S3 to {output_path}")
        return output_path
    except ClientError as e:
        print(f"Failed to get video from S3: {str(e)}")
        return None
