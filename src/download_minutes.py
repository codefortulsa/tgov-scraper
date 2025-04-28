import os
from pathlib import Path
import requests
import boto3
import botocore
from selectolax.parser import HTMLParser
from dateutil.parser import parse

from src.models.minutes import Minutes

ENV = os.getenv("ENV")
S3_BUCKET = os.getenv("S3_BUCKET")
MINUTES_FOLDER = os.getenv("MINUTES_FOLDER")

s3_client = boto3.client("s3")


def check_if_file_exists(path: Path, filename: str) -> bool:
    if ENV == "local":
        full_filepath = path / filename
        if full_filepath.exists():
            return True
        return False
    else:
        print(f"{S3_BUCKET} {MINUTES_FOLDER} {filename}")
        s3_client = boto3.client("s3")
        s3_key = f"{MINUTES_FOLDER}/{filename}"
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
            return True
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                raise e


def add_file_to_s3(pdf_response: requests.Response, filename: str):
    s3_key = f"{MINUTES_FOLDER}/{filename}"
    s3_client.upload_fileobj(pdf_response.raw, S3_BUCKET, s3_key)


def download_minutes_pdfs(last_minutes_page: int = 47711):
    folder = "test_data"
    base_url = "https://www.cityoftulsa.org/apps/CouncilDocuments"
    path = Path(f"./tmp/{folder}")
    path.mkdir(parents=True, exist_ok=True)
    print(f"Downloading minutes to {path}")
    minutes = []

    for item_num in range(47711, 48000):
        url = f"{base_url}?item={item_num}"
        print(f"Checking page: {url}")

        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch page {item_num}")
            break

        # Parse the HTML using selectolax
        tree = HTMLParser(response.content)

        # Find all divs with class "row"
        rows = tree.css("div.row")

        for row in rows:
            # Find divs with class "fileName"
            filename_div = row.css_first("div.fileName")
            if not filename_div:
                continue

            filename = filename_div.text().strip()
            if "minutes" not in filename.lower():
                continue

            # Find the hidden div with the document ID
            doc_id_div = row.css_first("div.pdfString.hidden")
            if not doc_id_div:
                print(f"No document ID found for {filename}")
                continue

            doc_id = doc_id_div.text().strip()
            pdf_url = f"https://www.cityoftulsa.org/apps/COTDisplayDocument/?DocumentType=CouncilDocument&DocumentIdentifiers={doc_id}"

            if check_if_file_exists(path, filename):
                print(f"File already exists, skipping: {filename}")
                continue

            print(f"Downloading: {filename}")
            pdf_response = requests.get(pdf_url, stream=True)

            full_filepath = path / filename
            if pdf_response.status_code == 200:
                if ENV == "local":
                    with open(full_filepath, "wb") as f:
                        for chunk in pdf_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                else:
                    add_file_to_s3(pdf_response, filename)
                print(f"Successfully downloaded {filename}")
                last_minutes_page = item_num
                meeting_date_str = " ".join(filename.split(" ")[-3:-1]).strip()
                meeting_date = parse(meeting_date_str)
                minutes.append(
                    Minutes(file=filename, meeting_date=meeting_date, doc_id=doc_id)
                )
            else:
                print(f"Failed to download {filename}")

        item_num += 1
    return minutes, last_minutes_page


if __name__ == "__main__":
    minutes, last_minutes_page = download_minutes_pdfs()
    print(f"Last minutes page: {last_minutes_page}")
    print(f"Minutes: {minutes}")
