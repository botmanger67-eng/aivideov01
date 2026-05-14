import os
import json
import logging
from typing import Dict, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------
# DeepSeek API configuration
# --------------------------------------------------------------------------------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"          # DeepSeek-V3

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY environment variable is not set.")

# Create the OpenAI-compatible client for DeepSeek
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# --------------------------------------------------------------------------------
# System prompt used for script generation
# --------------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are an expert viral content scriptwriter. Given a topic, create a highly engaging 
short-form video script (total 30-60 seconds) that maximizes retention. The script 
must be broken into segments, each with a duration (in seconds) and a visual keyword 
that can be used to find stock footage for that segment. Also provide a list of 5-10 
overall keywords related to the topic that capture its essence (useful for general 
video search). Use viral techniques: strong hook in the first 3 seconds, pattern 
interrupts, curiosity gaps, trends, and a clear call-to-action at the end.

Output ONLY a valid JSON object with the following structure:
{
  "segments": [
    {
      "text": "Script text for this segment (keep it short and punchy, fitting the duration)",
      "duration": 3,
      "visual_keyword": "a phrase that describes a scene for stock footage"
    }
  ],
  "keywords": ["keyword1", "keyword2", "..."]
}

Ensure the total duration is between 30 and 60 seconds. Each segment's text should be 
spoken within its duration. No extra commentary."""

# --------------------------------------------------------------------------------
# Main public function
# --------------------------------------------------------------------------------
def generate_viral_script(topic: str) -> dict:
    """
    Generate a viral short-form video script and associated keywords for a given topic.

    Uses DeepSeek-V3 to produce a structured script consisting of multiple time-stamped
    segments, each with a visual keyword for stock footage, and a list of overall topic
    keywords.

    Args:
        topic: The main topic or idea for the video. Must be a non-empty string.

    Returns:
        A dictionary with the following keys:
            - "segments": list of dicts, each containing:
                - "text" (str): spoken script text.
                - "duration" (int/float): duration in seconds.
                - "visual_keyword" (str): keyword for stock footage search.
            - "keywords": list of str, high-level keywords related to the topic.

    Raises:
        ValueError: If the topic is empty.
        RuntimeError: If the API call fails or the response cannot be parsed.
    """
    # ----------------------------------------------------------------------------
    # Input validation
    # ----------------------------------------------------------------------------
    if not topic.strip():
        raise ValueError("Topic must be a non-empty string.")

    logger.info(f"Generating viral script for topic: '{topic}'")

    # ----------------------------------------------------------------------------
    # Call DeepSeek API
    # ----------------------------------------------------------------------------
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Topic: {topic}"},
            ],
            temperature=0.7,
            max_tokens=1000,       # generous limit for JSON response
            top_p=0.9,
        )
    except Exception as exc:
        logger.error(f"DeepSeek API call failed: {exc}")
        raise RuntimeError(f"DeepSeek API call failed: {exc}") from exc

    raw_output = response.choices[0].message.content.strip()
    logger.debug(f"Raw model output (first 200 chars): {raw_output[:200]}...")

    # ----------------------------------------------------------------------------
    # Extract and parse JSON from the response
    # ----------------------------------------------------------------------------
    try:
        # Handle possible markdown code fencing
        if raw_output.startswith("```json"):
            raw_output = raw_output[len("```json"):]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip()

        script_data = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        logger.error(f"Failed to parse JSON from model output: {exc}")
        raise RuntimeError(
            f"Model output is not valid JSON. Output: {raw_output}"
        ) from exc

    # ----------------------------------------------------------------------------
    # Validate the parsed data structure
    # ----------------------------------------------------------------------------
    if not isinstance(script_data, dict):
        raise RuntimeError("Output JSON is not a dictionary.")

    if "segments" not in script_data or "keywords" not in script_data:
        raise RuntimeError(
            "Output JSON missing required keys 'segments' or 'keywords'."
        )

    segments = script_data["segments"]
    if not isinstance(segments, list):
        raise RuntimeError("'segments' must be a list.")

    for idx, seg in enumerate(segments):
        if not isinstance(seg, dict):
            raise RuntimeError(f"Segment {idx} is not a dictionary.")
        required_keys = {"text", "duration", "visual_keyword"}
        if not required_keys.issubset(seg.keys()):
            missing = required_keys - seg.keys()
            raise RuntimeError(
                f"Segment {idx} missing required keys: {missing}"
            )

    keywords = script_data["keywords"]
    if not isinstance(keywords, list):
        raise RuntimeError("'keywords' must be a list.")

    # Optional: warn if the total duration is outside the recommended range
    total_duration = sum(seg["duration"] for seg in segments)
    if not (30 <= total_duration <= 60):
        logger.warning(
            f"Total script duration {total_duration}s is outside the recommended 30-60s range."
        )

    logger.info(
        f"Script generated successfully: {len(segments)} segments, "
        f"{total_duration}s total, {len(keywords)} keywords."
    )
    return script_data