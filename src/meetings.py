#!/usr/bin/env python3
"""
Government Access Television Meeting Scraper

This module provides functions to scrape meeting data from Government Access
Television websites.
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin

import aiohttp
import pytz
from selectolax.parser import HTMLParser

from .models.meeting import Meeting

BASE_URL = "https://tulsa-ok.granicus.com/ViewPublisher.php?view_id=4"
CENTRAL_TZ = pytz.timezone("America/Chicago")


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


def parse_date_string(date_str: str) -> Optional[datetime]:
    """
    Parse the date string into a datetime object with Central timezone.

    Args:
        date_str: The raw date string from HTML

    Returns:
        A datetime object with Central timezone or None if parsing fails
    """
    # Replace non-breaking spaces with regular spaces
    date_str = date_str.replace("\u00a0", " ")

    # Replace multiple spaces with a single space
    date_str = re.sub(r"\s+", " ", date_str)

    # Find the month, day, year, and time parts
    # Pattern typically looks like "March 12, 2025 - 5:00 PM"
    match = re.search(
        r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4}).*?(\d{1,2}):(\d{2})\s*([APM]{2})",
        date_str,
    )

    if match:
        month_str, day_str, year_str, hour_str, minute_str, am_pm = match.groups()

        # Convert month name to number
        try:
            month_num = datetime.strptime(month_str, "%B").month
        except ValueError:
            # Try abbreviated month name
            try:
                month_num = datetime.strptime(month_str, "%b").month
            except ValueError:
                return None

        # Convert to integers
        day = int(day_str)
        year = int(year_str)
        hour = int(hour_str)
        minute = int(minute_str)

        # Adjust hour for PM
        if am_pm.upper() == "PM" and hour < 12:
            hour += 12
        elif am_pm.upper() == "AM" and hour == 12:
            hour = 0

        # Create naive datetime
        naive_dt = datetime(year, month_num, day, hour, minute)

        # Localize to Central Time
        return CENTRAL_TZ.localize(naive_dt)

    return None


def clean_date_string(date_str: str) -> str:
    """
    Clean up the date string by removing extra whitespace, newlines, and normalizing formats.

    Args:
        date_str: The raw date string from HTML

    Returns:
        A cleaned date string in the format "Month Day, Year - Time"
    """
    # Replace non-breaking spaces with regular spaces
    date_str = date_str.replace("\u00a0", " ")

    # Replace multiple spaces with a single space
    date_str = re.sub(r"\s+", " ", date_str)

    # Find the month, day, year, and time parts
    # Pattern typically looks like "March 12, 2025 - 5:00 PM"
    match = re.search(
        r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4}).*?(\d{1,2}:\d{2}\s*[APM]{2})", date_str
    )

    if match:
        month, day, year, time = match.groups()
        # Format consistently
        return f"{month} {day}, {year} - {time}"

    # If the regex doesn't match, do basic cleanup
    return date_str.strip()


async def parse_meetings(html: str) -> List[Dict[str, Any]]:
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

            # Parse the date string into a datetime object
            date_text = cells[1].text()
            date_obj = parse_date_string(date_text)

            # Get a cleaned date string as a fallback
            date_str = clean_date_string(date_text)

            meeting_data = {
                "meeting": cells[0].text().strip(),
                "date": date_obj.isoformat() if date_obj else date_str,
                "date_display": date_str,  # Keep a human-readable version
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
