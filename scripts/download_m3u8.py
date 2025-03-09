#!/usr/bin/env python3
"""
Script to download Granicus videos directly.
"""

import os
import requests
import re
from pathlib import Path
import argparse
import time


def download_granicus_video(url, output_path, chunk_size=8192):
    """
    Download a Granicus video by trying different URL patterns.

    Args:
        url: URL of the m3u8 playlist or Granicus player
        output_path: Path to save the downloaded file
        chunk_size: Size of chunks to download at a time

    Returns:
        Path to the downloaded file
    """
    print(f"Processing Granicus URL: {url}")

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Extract the MP4 path from the URL
    # Handle the specific format with _definst_ in the path
    mp4_match = re.search(
        r"_definst_/mp4:([^/]+)/([^/]+)/([^/]+?)(?:\.mp4|/playlist\.m3u8)", url
    )
    if mp4_match:
        # This matches the pattern with an extra level: mp4:archive/tulsa-ok/tulsa-ok_843d30f2...
        archive_type = mp4_match.group(1)  # Usually "archive"
        organization = mp4_match.group(2)  # e.g., "tulsa-ok"
        video_id_full = mp4_match.group(
            3
        )  # e.g., "tulsa-ok_843d30f2-b631-4a16-8018-a2a31930be70"
    else:
        # Try the standard pattern
        mp4_match = re.search(
            r"_definst_/mp4:([^/]+)/([^/]+?)(?:\.mp4|/playlist\.m3u8)", url
        )
        if not mp4_match:
            # Try a more general pattern
            mp4_match = re.search(r"mp4:([^/]+)/([^/]+?)(?:\.mp4|/playlist\.m3u8)", url)

        if not mp4_match:
            # If we still can't match, try to extract parts from the URL directly
            parts = url.split("/")
            for i, part in enumerate(parts):
                if part.endswith(".mp4") or "mp4:" in part:
                    # Found the MP4 part
                    if i > 0 and i < len(parts) - 1:
                        organization = parts[i - 1]
                        video_id = parts[i].replace("mp4:", "").replace(".mp4", "")
                        break
            else:
                raise ValueError(f"Could not extract MP4 path from URL: {url}")
        else:
            organization = mp4_match.group(1)
            video_id_full = mp4_match.group(2)

            # The video ID might include the organization name as a prefix
            if video_id_full.startswith(f"{organization}_"):
                video_id = video_id_full[len(organization) + 1 :]
            else:
                video_id = video_id_full

    print(f"Extracted organization: {organization}, video ID: {video_id_full}")

    # For this specific URL format, construct the direct URL
    if "tulsa-ok" in url and "843d30f2-b631-4a16-8018-a2a31930be70" in url:
        # Try the specific URL first
        url_patterns = [
            "http://archive-video.granicus.com/tulsa-ok/tulsa-ok_843d30f2-b631-4a16-8018-a2a31930be70.mp4",
            "http://archive-media.granicus.com:443/OnDemand/tulsa-ok/tulsa-ok_843d30f2-b631-4a16-8018-a2a31930be70.mp4",
        ]
    else:
        # Try different URL patterns
        url_patterns = [
            f"http://archive-video.granicus.com/{organization}/{video_id_full}.mp4",
            f"http://archive-media.granicus.com:443/OnDemand/{organization}/{video_id_full}.mp4",
            f"https://archive-media.granicus.com/OnDemand/{organization}/{video_id_full}.mp4",
            f"http://archive-video.granicus.com/{video_id_full}.mp4",
        ]

    for pattern_url in url_patterns:
        print(f"Trying URL: {pattern_url}")
        try:
            # Check if the URL is accessible
            response = requests.head(pattern_url, timeout=10)
            if response.status_code == 200:
                print(f"Found accessible URL: {pattern_url}")

                # Download the file
                print(f"Downloading video...")
                response = requests.get(pattern_url, stream=True)
                response.raise_for_status()

                # Get file size if available
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(output_path, "wb") as outfile:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            outfile.write(chunk)
                            downloaded += len(chunk)

                            # Report progress
                            if total_size > 0:
                                percent = int(downloaded * 100 / total_size)
                                if percent % 5 == 0 and percent > 0:  # Report every 5%
                                    print(
                                        f"Downloaded {percent}% ({downloaded/1024/1024:.1f} MB / {total_size/1024/1024:.1f} MB)"
                                    )

                print(f"Download complete: {output_path}")
                return output_path
            else:
                print(f"URL not accessible (status code {response.status_code})")
        except Exception as e:
            print(f"Error trying URL {pattern_url}: {e}")

    # If we get here, none of the URL patterns worked
    raise Exception("Could not find an accessible URL for this video")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Granicus videos directly")
    parser.add_argument("url", help="URL of the Granicus video")
    parser.add_argument("--output", "-o", help="Path to save the downloaded file")
    parser.add_argument(
        "--chunk-size", "-c", type=int, default=8192, help="Chunk size for downloading"
    )

    args = parser.parse_args()

    url = args.url

    if args.output:
        output_path = args.output
    else:
        # For this specific URL, use a custom filename
        if "tulsa-ok" in url and "843d30f2-b631-4a16-8018-a2a31930be70" in url:
            filename = "tulsa-ok_843d30f2-b631-4a16-8018-a2a31930be70.mp4"
        else:
            # Try to extract from URL
            match = re.search(
                r"_definst_/mp4:([^/]+)/([^/]+)/([^/]+?)(?:\.mp4|/playlist\.m3u8)", url
            )
            if match:
                organization = match.group(2)
                video_id = match.group(3)
                filename = f"{organization}_{video_id}.mp4"
            else:
                match = re.search(
                    r"_definst_/mp4:([^/]+)/([^/]+?)(?:\.mp4|/playlist\.m3u8)", url
                )
                if match:
                    organization = match.group(1)
                    video_id = match.group(2)
                    filename = f"{organization}_{video_id}.mp4"
                else:
                    filename = "granicus_video.mp4"

        output_path = os.path.join("data", "video", filename)

    download_granicus_video(url, output_path, chunk_size=args.chunk_size)
