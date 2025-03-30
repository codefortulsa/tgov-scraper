# this file will contain granicus specific functions

import re
import aiohttp
from selectolax.parser import HTMLParser
from src.models.meeting import GranicusPlayerPage


async def get_video_player(player_url: str) -> GranicusPlayerPage:
    """
        Extract video stream and download URLs from a Granicus player page

    Args:
        player_url: URL of the Granicus player page

    Returns:
        GranicusPlayerPage object containing stream and download URLs
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(player_url) as response:
            if response.status != 200:
                raise Exception(
                    f"Failed to fetch {player_url}, status code: {response.status}"
                )
            html = await response.text()

        # Parse the HTML to find the video URL
        parser = HTMLParser(html)

        # Look for video source elements or embedded player URLs
        video_urls = []
        for source in parser.css("source, video"):
            if src := source.attributes.get("src"):
                video_urls.append(src)

        # Also look for embedded player URLs in scripts
        for script in parser.css("script"):
            if script.text():
                # Look for URLs in the script content
                matches = re.findall(
                    r'(?:http|https)://[^\s<>"]+?(?:\.mp4|/playlist\.m3u8)',
                    script.text(),
                )
                video_urls.extend(matches)

        if not video_urls:
            return GranicusPlayerPage(url=player_url)

        # Get the first URL that matches our patterns
        stream_url = video_urls[0]

        # Extract organization and video ID using patterns from download_m3u8.py
        mp4_match = re.search(
            r"_definst_/mp4:([^/]+)/([^/]+)/([^/]+?)(?:\.mp4|/playlist\.m3u8)",
            stream_url,
        )

        if mp4_match:
            archive_type = mp4_match.group(1)
            organization = mp4_match.group(2)
            video_id = mp4_match.group(3)
            # http://archive-video.granicus.com/tulsa-ok/tulsa-ok_843d30f2-b631-4a16-8018-a2a31930be70.mp4
            file_url = (
                f"http://archive-video.granicus.com/{organization}/{video_id}.mp4"
            )
            return GranicusPlayerPage(
                url=player_url,
                stream_url=stream_url,
                download_url=file_url,
            )
        # Return just stream URL if download URL not found
        return GranicusPlayerPage(url=player_url, stream_url=stream_url)
