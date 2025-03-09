#!/usr/bin/env python3
"""
Utility functions for working with video streams from Granicus player pages.
"""

import asyncio
import re
import tempfile
import os
import io
from typing import Optional, Tuple, BinaryIO
from urllib.request import urlopen
import time

import aiohttp
from selectolax.parser import HTMLParser
import m3u8
import requests
from pydub import AudioSegment


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


async def extract_video_url(html: str) -> Optional[str]:
    """
    Extract the video URL from HTML content of a Granicus player page.

    Args:
        html: The HTML content of the page

    Returns:
        The video URL if found, None otherwise
    """
    # Find the video_url JavaScript variable
    js_var_match: Optional[re.Match] = re.search(r'video_url="([^"]+)"', html)
    if js_var_match:
        return js_var_match.group(1)

    return None


async def get_video_url(url: str) -> Optional[str]:
    """
    Extract the video URL from a Granicus player page.

    Args:
        url: The URL of the Granicus player page

    Returns:
        The video URL if found, None otherwise
    """
    async with aiohttp.ClientSession() as session:
        try:
            html: str = await fetch_page(url, session)
            return await extract_video_url(html)
        except Exception as e:
            # Log the error (in a real application)
            # print(f"Error fetching video URL: {e}")
            return None
