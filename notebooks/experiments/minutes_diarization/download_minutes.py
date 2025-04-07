from pathlib import Path
import re
import requests
from selectolax.parser import HTMLParser


def download_minutes_pdfs():
    folder = "test_data"
    base_url = "https://www.cityoftulsa.org/apps/CouncilDocuments"
    Path("./notebooks/experiments/test_data").mkdir(parents=True, exist_ok=True)

    for item_num in range(47711, 48000):
        url = f"{base_url}?item={item_num}"
        print(f"Checking page: {url}")

        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch page {item_num}")
            break

        # Parse the HTML using selectolax
        tree = HTMLParser(response.content)

        # Find all rows that contain filename divs
        rows = tree.css("div.row")

        for row in rows:
            # Find the filename div in this row
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


download_minutes_pdfs()
