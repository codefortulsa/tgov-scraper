from datetime import datetime
import aiohttp
import re

from pathlib import Path
from fastapi import File
from prefect import task
from pydantic import BaseModel
from selectolax.parser import HTMLParser

from src.meetings import fetch_page


class Minutes(BaseModel):
    file: File
    meeting_date: datetime
    doc_id: str


@task
async def get_new_minutes(last_minutes_page: int):
    # TODO: Get last minutes page # from registry
    # last_minutes_page = 47711
    step_up_to = 100
    base_url = "https://www.cityoftulsa.org/apps/CouncilDocuments"

    for item_num in range(last_minutes_page + 1, last_minutes_page + step_up_to):
        url = f"{base_url}?item={item_num}"
        print(f"Checking page: {url}")

        async with aiohttp.ClientSession() as session:
            response = await fetch_page(url, session)

        # Parse the HTML using selectolax
        tree = HTMLParser(response.content)

        # Find all rows
        rows = tree.css("div.row")

        for row in rows:
            # Find the fileName div in this row
            filename_div = row.css_first("div.fileName")
            if not filename_div:
                continue

            filename = filename_div.text().strip()
            if "minutes" not in filename.lower():
                continue

            # Check if file already exists
            full_filepath = Path(folder) / filename
            if full_filepath.exists():
                print(f"File already exists, skipping: {filename}")
                continue

            # Find the hidden div with the document ID
            doc_id_div = row.css_first("div.pdfString.hidden")
            if not doc_id_div:
                print(f"No document ID found for {filename}")
                continue

            doc_id = doc_id_div.text().strip()
            pdf_url = f"https://www.cityoftulsa.org/apps/COTDisplayDocument/?DocumentType=CouncilDocument&DocumentIdentifiers={doc_id}"

            print(f"Downloading: {filename}")
            pdf_response = requests.get(pdf_url, stream=True)

            if pdf_response.status_code == 200:
                with open(full_filepath, "wb") as f:
                    for chunk in pdf_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Successfully downloaded {filename}")
            else:
                print(f"Failed to download {filename}")

        item_num += 1
    pass
