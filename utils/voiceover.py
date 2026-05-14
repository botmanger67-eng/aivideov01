import os
import requests
import logging
from pathlib import Path
from typing import Optional

# Configure module-level logger
logger = logging.getLogger(__name__)

# Constants
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # 'Rachel' – a high-quality, natural voice

def generate_voiceover(
    script_text: str,
    voice_id: Optional[str] = None,
    output_file: Optional[str] = None,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> bytes:
    """
    Convert script text to high-quality MP3 audio narration using ElevenLabs TTS.

    Args:
        script_text: The text to convert to speech.
        voice_id: ElevenLabs voice ID. Defaults to 'Rachel'.
        output_file: Optional file path to save the MP3 audio.
        stability: Voice stability (0.0 - 1.0). Lower = more emotional range.
        similarity_boost: How much to boost similarity to the original voice (0.0 - 1.0).

    Returns:
        Audio bytes (MP3). If output_file is provided, also saves to disk.

    Raises:
        ValueError: If API key is not set.
        requests.RequestException: On API communication failures.
    """
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY environment variable not set.")

    voice = voice_id or DEFAULT_VOICE_ID
    url = f"{BASE_URL}/text-to-speech/{voice}"

    headers = {
        "Accept": "audio/mpeg",
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": script_text,
        "model_id": "eleven_monolingual_v1",  # supports 29 languages if switched to multilingual
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
        },
    }

    try:
        logger.info(
            "Generating voiceover (voice: %s, text length: %d chars)",
            voice,
            len(script_text),
        )
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        audio_bytes = response.content

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            logger.info("Voiceover saved to %s", output_file)

        return audio_bytes

    except requests.exceptions.RequestException as e:
        logger.error("ElevenLabs API request failed: %s", e, exc_info=True)
        raise
    except Exception as e:
        logger.error("Unexpected error during voiceover generation: %s", e, exc_info=True)
        raise