#!/usr/bin/env python3
"""
Tests for the video URL extraction functionality.
"""

import asyncio
import os
from pathlib import Path
import pytest
from unittest.mock import patch, AsyncMock

import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.videos import get_video_url, get_video_url


@pytest.fixture
def video_player_fixture_path():
    """Path to the video player fixture file"""
    return Path(__file__).parent / "fixtures" / "video_player.html"


@pytest.fixture
def player_html(video_player_fixture_path):
    """Load the player HTML from the fixture file"""
    with open(video_player_fixture_path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.mark.asyncio
async def test_extract_video_url_from_fixture(player_html):
    """Test that the video URL is correctly extracted from the fixture HTML"""
    # Mock the fetch_page function to return our fixture HTML
    with patch("src.videos.fetch_page", AsyncMock(return_value=player_html)):
        # Use a dummy URL since we're mocking the fetch
        url = await get_video_url("https://example.com/player")

        # Assert that we found a URL
        assert url is not None

        # Check that it's an m3u8 URL
        assert url.endswith(".m3u8")

        # The specific URL from our fixture
        expected_url = "https://archive-stream.granicus.com/OnDemand/_definst_/mp4:archive/tulsa-ok/tulsa-ok_843d30f2-b631-4a16-8018-a2a31930be70.mp4/playlist.m3u8"
        assert url == expected_url


@pytest.mark.asyncio
async def test_get_video_url_wrapper():
    """Test that the get_video_url wrapper function works correctly"""
    # Mock both fetch_page and extract_video_url functions
    with patch("src.videos.fetch_page", AsyncMock(return_value="dummy html")), patch(
        "src.videos.extract_video_url",
        AsyncMock(return_value="https://example.com/video.m3u8"),
    ):
        url = await get_video_url("https://example.com/player")
        assert url == "https://example.com/video.m3u8"


@pytest.mark.asyncio
async def test_extract_video_url_javascript_variable():
    """Test extracting video URL from JavaScript variable"""
    html_with_js_var = """
    <html>
    <head>
        <script>video_url="https://example.com/video.m3u8"</script>
    </head>
    <body>
        <div>Test content</div>
    </body>
    </html>
    """

    with patch("src.videos.fetch_page", AsyncMock(return_value=html_with_js_var)):
        url = await get_video_url("https://example.com/player")
        assert url == "https://example.com/video.m3u8"


@pytest.mark.asyncio
async def test_extract_video_url_not_found():
    """Test behavior when no video URL is found"""
    html_without_video = """
    <html>
    <body>
        <div>No video here</div>
    </body>
    </html>
    """

    with patch("src.videos.fetch_page", AsyncMock(return_value=html_without_video)):
        url = await get_video_url("https://example.com/player")
        assert url is None


@pytest.mark.asyncio
async def test_extract_video_url_with_real_url():
    """
    Test with a real URL (optional integration test).
    This test is marked as optional and can be skipped with -m "not integration"
    """
    pytest.skip("Skipping integration test by default")

    page_url = "https://tulsa-ok.granicus.com/player/clip/6412?view_id=4&redirect=true"
    url = await get_video_url(page_url)

    # Assert that we found a URL
    assert url is not None

    # Check that it's an m3u8 URL
    assert url.endswith(".m3u8")
