#!/usr/bin/env python3
"""
Government Access Television Meeting Scraper

This module provides functions to scrape meeting data from Government Access
Television websites.
"""

import re
from typing import Dict, List, Sequence
from urllib.parse import urljoin

import aiohttp
import pandas as pd
from selectolax.parser import HTMLParser

from src.aws import is_aws_configured
from src.local_store import read_meetings, write_meetings

from .models.meeting import Meeting
from datetime import datetime
import dateparser

BASE_URL = "https://tulsa-ok.granicus.com/ViewPublisher.php?view_id=4"
TGOV_BUCKET_NAME = "tgov-meetings"
MEETINGS_REGISTRY_PATH = "data/meetings.jsonl"


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


async def parse_meetings(html: str) -> List[Meeting]:
    parser = HTMLParser(html)

    # Find all tables with meeting data
    tables = parser.css("table.listingTable")
    if not tables:
        return []

    meetings = []

    # Process each table
    for table in tables:
        for row in table.css("tr.listingRow"):
            name_cells = row.css('td.listItem[headers^="Name"]')
            meeting_name = name_cells[0].text().strip() if name_cells else "Unknown"

            date_cell = row.css_first('td.listItem[headers^="Date"]')
            meeting_date = dateparser.parse(date_cell.text())

            duration_cells = row.css('td.listItem[headers^="Duration"]')
            duration_str = (
                duration_cells[0].text().strip() if duration_cells else "Unknown"
            )
            minutes = duration_to_minutes(duration_str)
            meeting_duration = (
                f"{minutes // 60}:{minutes % 60:02d}"
                if minutes is not None
                else "Unknown"
            )

            meeting_data = {
                "meeting": meeting_name,
                "date": meeting_date,
                "duration": meeting_duration,
                "agenda": None,
                "clip_id": None,
                "video": None,
            }

            # Extract agenda link if available
            agenda_cells = row.css('td.listItem:has(a[href*="AgendaViewer.php"])')
            agenda_link = agenda_cells[0].css_first("a") if agenda_cells else None
            if agenda_link is not None:
                meeting_data["agenda"] = urljoin(
                    BASE_URL, agenda_link.attributes.get("href")
                )

            # Extract video link if available
            video_cells = row.css('td.listItem[headers^="VideoLink"]')
            video_cell = video_cells[0] if video_cells else None
            if video_cell is not None:
                video_link = video_cell.css_first("a")

                onclick = video_link.attributes.get("onclick", "")
                onclick_match = re.search(
                    r"window\.open\(['\"](//[^'\"]+)['\"]", onclick
                )
                clip_id_exp = r"clip_id=(\d+)"

                if onclick_match:
                    meeting_data["video"] = f"https:{onclick_match.group(1)}"
                    clip_id_match = re.search(clip_id_exp, onclick)
                    if clip_id_match:
                        meeting_data["clip_id"] = clip_id_match.group(1)
                    else:
                        meeting_data["clip_id"] = None
                if not meeting_data["video"]:
                    href = video_link.attributes.get("href", "")
                    if href.startswith("javascript:"):
                        clip_id_match = re.search(clip_id_exp, href)
                        if clip_id_match:
                            clip_id = clip_id_match.group(1)
                            meeting_data["clip_id"] = clip_id
                            meeting_data["video"] = (
                                f"https://tulsa-ok.granicus.com/MediaPlayer.php?view_id=4&clip_id={clip_id}"
                            )
                        else:
                            meeting_data["video"] = urljoin(BASE_URL, href)

            meetings.append(Meeting(**meeting_data))

    return meetings


async def get_tgov_meetings() -> Sequence[Meeting]:
    """
    Fetch and parse meeting data from the Government Access Television website.

    Returns:
        A list of Meeting objects containing meeting data
    """
    async with aiohttp.ClientSession() as session:
        html = await fetch_page(BASE_URL, session)
        meetings = await parse_meetings(html)
        return meetings


def duration_to_minutes(duration):
    if not duration or pd.isna(duration):
        return None

    # Parse duration in format "00h 39m"
    try:
        hours = 0
        minutes = 0

        if "h" in duration:
            hours_part = duration.split("h")[0].strip()
            hours = int(hours_part)

        if "m" in duration:
            if "h" in duration:
                minutes_part = duration.split("h")[1].split("m")[0].strip()
            else:
                minutes_part = duration.split("m")[0].strip()
            minutes = int(minutes_part)

        return hours * 60 + minutes
    except:
        return None


def get_registry_meetings() -> Sequence[Meeting]:
    if is_aws_configured():
        print(f"Getting registry from DynamoDB.")
        return list(Meeting.scan())
    else:
        print(f"Getting registry from local store")
        return read_meetings()


def write_registry_meetings(meetings: Sequence[Meeting]) -> Sequence[Meeting]:
    if is_aws_configured():
        print(f"Writing registry to DynamoDB.")
        with Meeting.batch_writer():
            for meeting in meetings:
                if meeting.clip_id:
                    meeting.save()
                else:
                    print(f"Skipping meeting with missing clip_id: {meeting}")
    else:
        print(f"Writing registry to local store")
        write_meetings(meetings)

    return meetings
