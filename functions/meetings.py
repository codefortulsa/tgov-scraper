#!/usr/bin/env python3
"""
Government Access Television Meeting Scraper

This module provides functions to scrape meeting data from Government Access
Television websites.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import aiohttp
from selectolax.parser import HTMLParser

from .models.meeting import Meeting

BASE_URL = "https://tulsa-ok.granicus.com/ViewPublisher.php?view_id=4"


async def fetch_page(url: str, session: aiohttp.ClientSession) -> str:
    """
    Fetch the HTML content of a page.

    Args:
        url: The URL to fetch
        session: An aiohttp ClientSession

    Returns:
        The HTML content as a string
    """
    async with session.get(url) as response:
        if response.status != 200:
            raise Exception(f"Failed to fetch {url}, status code: {response.status}")
        return await response.text()


async def parse_meetings(html: str) -> List[Dict[str, str]]:
    """
    Parse the meeting data from the HTML content.

    Args:
        html: The HTML content of the page

    Returns:
        A list of dictionaries containing meeting data
    """
    parser = HTMLParser(html)

    # Find all tables with meeting data
    tables = parser.css("table.listingTable")
    if not tables:
        return []

    meetings = []

    # Process each table
    for table in tables:
        # Find the tbody section which contains the actual meeting rows
        tbody = table.css_first("tbody")
        if not tbody:
            continue

        # Process each row in the tbody
        for row in tbody.css("tr"):
            cells = row.css("td")
            if len(cells) < 5:
                continue

            meeting_data = {
                "meeting": cells[0].text().strip(),
                "date": cells[1].text().strip(),
                "duration": cells[2].text().strip(),
                "agenda": None,
                "video": None,
            }

            # Extract agenda link if available
            agenda_cell = cells[3]
            agenda_link = agenda_cell.css_first("a")
            if agenda_link and agenda_link.attributes.get("href"):
                meeting_data["agenda"] = urljoin(
                    BASE_URL, agenda_link.attributes.get("href")
                )

            # Extract video link if available
            video_cell = cells[4]
            video_link = video_cell.css_first("a")
            if video_link:
                # First try to extract from onclick attribute
                onclick = video_link.attributes.get("onclick", "")
                if onclick:
                    # Look for window.open pattern
                    if "window.open(" in onclick:
                        # Extract URL from window.open('URL', ...)
                        start_quote = onclick.find("'", onclick.find("window.open("))
                        end_quote = onclick.find("'", start_quote + 1)
                        if start_quote > 0 and end_quote > start_quote:
                            video_url = onclick[start_quote + 1 : end_quote]
                            # Handle protocol-relative URLs (starting with //)
                            if video_url.startswith("//"):
                                video_url = f"https:{video_url}"
                            meeting_data["video"] = video_url

                # If onclick extraction failed, try href
                if meeting_data["video"] is None and video_link.attributes.get("href"):
                    href = video_link.attributes.get("href")
                    # Handle javascript: hrefs
                    if href.startswith("javascript:"):
                        # Try to extract clip_id from the onclick attribute again
                        # This handles cases where href is javascript:void(0) but onclick has the real URL
                        if meeting_data["video"] is None and "clip_id=" in onclick:
                            start_idx = onclick.find("clip_id=")
                            end_idx = onclick.find("'", start_idx)
                            if start_idx > 0 and end_idx > start_idx:
                                clip_id = onclick[start_idx + 8 : end_idx]
                                meeting_data["video"] = (
                                    f"https://tulsa-ok.granicus.com/MediaPlayer.php?view_id=4&clip_id={clip_id}"
                                )
                    else:
                        meeting_data["video"] = urljoin(BASE_URL, href)

            meetings.append(meeting_data)

    return meetings


async def get_meetings() -> List[Meeting]:
    """
    Fetch and parse meeting data from the Government Access Television website.

    Returns:
        A list of Meeting objects containing meeting data
    """
    async with aiohttp.ClientSession() as session:
        html = await fetch_page(BASE_URL, session)
        meeting_dicts = await parse_meetings(html)

        # Convert dictionaries to Meeting objects
        meetings = [Meeting(**meeting_dict) for meeting_dict in meeting_dicts]
        return meetings
