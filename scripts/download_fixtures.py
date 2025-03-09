#!/usr/bin/env python3
"""
Script to download fixture files for testing.
"""

import asyncio
import os
from pathlib import Path
import sys

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp
from src.meetings import fetch_page, BASE_URL


async def download_fixtures() -> None:
    """
    Download fixture files for testing.
    """
    # Create the fixtures directory if it doesn't exist
    fixtures_dir = Path("tests") / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        # Download the homepage
        homepage_path = fixtures_dir / "tgov_homepage.html"
        print(f"Downloading homepage from {BASE_URL}...")
        homepage_html = await fetch_page(BASE_URL, session)
        with open(homepage_path, "w", encoding="utf-8") as f:
            f.write(homepage_html)
        print(f"Homepage saved to {homepage_path}")

        # Download the video player page
        video_player_url = (
            "https://tulsa-ok.granicus.com/player/clip/6412?view_id=4&redirect=true"
        )
        video_player_path = fixtures_dir / "video_player.html"
        print(f"Downloading video player page from {video_player_url}...")
        video_player_html = await fetch_page(video_player_url, session)
        with open(video_player_path, "w", encoding="utf-8") as f:
            f.write(video_player_html)
        print(f"Video player page saved to {video_player_path}")


if __name__ == "__main__":
    asyncio.run(download_fixtures())
