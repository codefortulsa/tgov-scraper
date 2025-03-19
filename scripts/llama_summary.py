#!/usr/bin/env python3
"""
AI Summary generator for Tulsa Government Access Television meetings.

This script processes meetings that need summarization in summaries.jsonl,
and uses an AI model to generate summaries for them.
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import aiohttp
from dotenv import load_dotenv


# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.models.meeting import MeetingSummary
from collect_summaries import load_summaries
from src.documents import read_pdf

from collect_summaries import SUMMARY_FILE

# Load environment variables from .env file
load_dotenv()


# GitHub AI Inference API endpoint (Llama-3.3-70B-Instruct)
GITHUB_API_ENDPOINT = "https://models.inference.ai.azure.com/chat/completions"
MODEL_NAME = "Llama-3.3-70B-Instruct"

# Get GitHub token from environment variable
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


async def get_summary_text(summary: MeetingSummary) -> str:
    """Uses MeetingSummary object to get the summary text."""
    try:
        agenda_text = await read_pdf(summary.meeting.agenda)
        return agenda_text
    except aiohttp.InvalidUrlClientError as e:
        print(f"Error: Invalid URL in agenda link: {summary.meeting.agenda}")
        return f"Agenda Unavailable: {summary.meeting.agenda}"
    except Exception as e:
        print(f"Error accessing agenda: {e}")
        return f"Agenda Unavailable: {summary.meeting.agenda}"


async def summarize_with_llama(summary: MeetingSummary) -> str:
    """
    Generate a summary for a meeting using GitHub's AI model.

    Args:
        summary_data: Summary data dictionary

    Returns:
        Generated summary text
    """
    if not GITHUB_TOKEN:
        print(
            "Warning: GITHUB_TOKEN environment variable not set. Using placeholder summary."
        )
        return "[PLACEHOLDER] Unable to generate AI summary - no GitHub token provided."

    try:
        # Format the meeting information for the prompt
        meeting_info = await get_summary_text(summary)

        # Prepare the request payload
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a government meeting summarizer. Your task is to create concise, informative summaries of government meetings.",
                },
                {
                    "role": "user",
                    "content": f"Please generate a summary for this government meeting. Focus on the key topics discussed, decisions made, and any notable public comments. If exact details aren't available, provide a general summary of what typically happens in this type of meeting.\n\n{meeting_info}",
                },
            ],
            "temperature": 0.7,
            "max_tokens": 500,
            "model": MODEL_NAME,
        }

        # Make the API request
        headers = {"Content-Type": "application/json", "api-key": GITHUB_TOKEN}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                GITHUB_API_ENDPOINT, json=payload, headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    else:
                        print(f"Error: Unexpected response format: {result}")
                else:
                    error_text = await response.text()
                    print(
                        f"Error: API request failed with status {response.status}: {error_text}"
                    )

        # Fallback to placeholder if API call fails
        return f"[PLACEHOLDER] This meeting ({summary.get('meeting_name')}) summary will be generated automatically."

    except Exception as e:
        print(f"Error generating summary: {e}")
        return f"[PLACEHOLDER] Error generating summary: {str(e)}"


async def update_summaries(summaries: List[MeetingSummary]) -> List[MeetingSummary]:
    new_summaries = []

    # Process each summary that needs updating
    for summary in summaries:
        print(
            f"Generating summary for meeting: {summary.meeting.meeting} ({summary.meeting.date})"
        )

        # Generate the AI summary
        ai_summary = await summarize_with_llama(summary)
        # Update the summary data
        summary.summary = ai_summary
        summary.summarization_date = datetime.now(timezone.utc).isoformat()
        summary.needs_summarization = False

        # Update the dictionary
        new_summaries.append(summary)

    print(f"Updated {len(new_summaries)} summaries.")

    # Convert back to list
    return new_summaries


async def save_summaries(summaries: List[MeetingSummary]) -> None:
    """
    Save summaries to the summaries.jsonl file.

    Args:
        summaries: List of MeetingSummary objects
    """
    # Save to original location
    with SUMMARY_FILE.open("w") as f:
        for summary in summaries:
            # Convert the Pydantic model to a dictionary with proper serialization options
            # By default, HttpUrl objects are not JSON serializable
            summary_dict = summary.model_dump(mode="json")
            f.write(json.dumps(summary_dict) + "\n")
    print(f"Saved {len(summaries)} summaries to {SUMMARY_FILE}.")


async def main() -> None:
    """Main function to generate AI summaries for meetings."""
    # Load existing summaries
    summaries = await load_summaries()
    # Find summaries that need generation
    already_summarized = [s for s in summaries if not s.needs_summarization]
    new_summaries = [s for s in summaries if s.needs_summarization]

    if not new_summaries:
        print("No summaries need generation. Exiting.")
        return

    # Update the summaries with AI-generated content
    updated_summaries = await update_summaries(new_summaries)

    # Combine existing and updated summaries
    all_summaries = already_summarized + updated_summaries

    # Save the updated summaries
    await save_summaries(all_summaries)


if __name__ == "__main__":
    asyncio.run(main())
