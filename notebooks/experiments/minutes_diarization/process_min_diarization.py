from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from openai import OpenAI
import json

import tiktoken

# Initialize OpenAI client
client = OpenAI()


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using PyPDFLoader."""
    loader = PyPDFLoader(str(pdf_path))
    pages = loader.load()
    return "\n".join(page.page_content for page in pages)


def get_diarization():
    """Get the diarization data from the JSON file."""
    diarization_path = Path(
        "./notebooks/experiments/minutes_diarization/regular_council_meeting___2025_02_26.diarized.json"
    )
    if not diarization_path.exists():
        raise FileNotFoundError("Diarization JSON file not found")

    with open(diarization_path, "r") as f:
        return json.load(f)


def simplify_diarization(transcript_data):
    def format_timestamp(seconds: float) -> str:
        """Convert seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    # Create formatted HTML output
    speaker_lines = ["Meeting Script - Combined by Speaker"]

    current_speaker = None
    current_text = []
    current_start = None

    for segment in transcript_data["segments"]:
        if current_speaker != segment["speaker"]:
            # Output previous speaker's text
            if current_speaker:
                timestamp = format_timestamp(current_start)
                wrapped_text = " ".join(current_text)
                speaker_lines.append(
                    f"[{timestamp}] {current_speaker}:\n{wrapped_text}\n"
                )

            # Start new speaker
            current_speaker = segment["speaker"]
            current_text = [segment["text"].strip()]
            current_start = segment["start"]
        else:
            # Continue current speaker
            current_text.append(segment["text"].strip())

    # Output final speaker
    if current_speaker:
        timestamp = format_timestamp(current_start)
        wrapped_text = " ".join(current_text)
        speaker_lines.append(f"[{timestamp}] {current_speaker}:\n{wrapped_text}")
    return "\n".join(speaker_lines)


def match_speakers_with_chatgpt(minutes_text, diarization):
    """Use ChatGPT to match speakers from diarization with names from minutes."""
    # Format diarization data for the prompt

    prompt = f"""I have a city council meeting minutes document and a diarization of the audio recording.
The diarization has identified different speakers but doesn't know their names.
Please analyze the minutes text and match the speakers from the diarization with the names mentioned in the minutes.

Minutes text:
{minutes_text}

Diarization segments:
{diarization}

For each speaker in the diarization, please identify who they are based on the minutes text.
If you can't determine who they are, mark them as "Unknown".
Format your response as a JSON object where the keys are the speaker numbers (e.g., "SPEAKER_00")
and the values are the identified names or "Unknown".
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that analyzes meeting minutes and audio diarization to identify speakers.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


def main():
    minutes_path = Path(
        "./notebooks/experiments/minutes_diarization/test_data/25-173-2_25-173-2 2025-02-26 5PM Minutes.pdf"
    )
    # Extract text from PDF
    minutes_text = extract_text_from_pdf(minutes_path)

    # Get diarization data
    diarization = get_diarization()

    simple_diarization = simplify_diarization(diarization)
    print(simple_diarization)

    encoding = tiktoken.encoding_for_model("gpt-4o-mini")

    print(
        f"Diarization segments length: {len(encoding.encode(str(simple_diarization)))}"
    )
    print(f"Minutes text length: {len(encoding.encode(minutes_text))}")

    # Use ChatGPT to match speakers
    speaker_matches = match_speakers_with_chatgpt(minutes_text, simple_diarization)
    print(speaker_matches)


if __name__ == "__main__":
    main()
