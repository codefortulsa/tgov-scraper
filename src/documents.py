import os
import io
import asyncio
import aiohttp
from typing import Optional

from pydantic import HttpUrl
import fitz  # PyMuPDF


def clean_pdf_text(pdf_text: str) -> str:
    """
    Clean up text extracted from a PDF by removing special characters
    and normalizing whitespace.

    Args:
        pdf_text: Raw text extracted from PDF

    Returns:
        Cleaned text with normalized spacing
    """
    import re

    # Replace non-breaking spaces with regular spaces
    text = pdf_text.replace("\xa0", " ")

    # Replace other common problematic characters
    text = text.replace("\u2003", " ")  # em space
    text = text.replace("\u2002", " ")  # en space
    text = text.replace("\u200b", "")  # zero-width space
    text = text.replace("\u2013", "-")  # en dash
    text = text.replace("\u2014", "--")  # em dash
    text = text.replace("\u2018", "'")  # left single quote
    text = text.replace("\u2019", "'")  # right single quote
    text = text.replace("\u201c", '"')  # left double quote
    text = text.replace("\u201d", '"')  # right double quote

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove repeated spaces
    text = re.sub(r" +", " ", text)

    # Remove repeated newlines (but preserve paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Trim leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text


async def read_pdf(url: HttpUrl, timeout: Optional[int] = 60) -> str:
    """
    Asynchronously download and extract text from a PDF document.

    Args:
        url: HTTP URL to the PDF file
        timeout: Request timeout in seconds

    Returns:
        Extracted text content from the PDF
    """
    url_str = url.unicode_string() if hasattr(url, "unicode_string") else str(url)

    async with aiohttp.ClientSession() as session:
        async with session.get(url_str, timeout=timeout) as response:
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if not content_type.lower().startswith("application/pdf"):
                print(
                    f"Warning: URL might not contain a PDF (Content-Type: {content_type})"
                )

            pdf_content = await response.read()

            # Use BytesIO to create an in-memory file-like object
            pdf_file = io.BytesIO(pdf_content)

            # Extract text using PyMuPDF (more reliable than PyPDF2)
            doc = fitz.open(stream=pdf_file, filetype="pdf")
            text_content = ""

            # Extract text from all pages with proper handling
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Get text with preservation of reading order
                text_content += page.get_text("text") + "\n\n"

            return clean_pdf_text(text_content)
