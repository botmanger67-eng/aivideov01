import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SecretManager:
    """
    Securely retrieves API keys and other secrets from environment variables
    (e.g., Replit Secrets). Provides methods for specific keys and a generic
    getter with validation and logging.
    """

    @staticmethod
    def _get_env_var(key: str, required: bool = True) -> Optional[str]:
        """
        Fetch an environment variable, with optional requirement.
        Raises EnvironmentError if required and missing; logs warnings otherwise.
        """
        value = os.getenv(key)
        if value is None or value == "":
            if required:
                logger.critical(f"Missing required environment variable: {key}")
                raise EnvironmentError(f"Environment variable '{key}' is not set or empty.")
            else:
                logger.warning(f"Optional environment variable '{key}' is not set or empty.")
                return None
        return value

    @classmethod
    def get_deepseek_api_key(cls) -> str:
        """Return DeepSeek API key."""
        return cls._get_env_var("DEEPSEEK_API_KEY", required=True)

    @classmethod
    def get_elevenlabs_api_key(cls) -> str:
        """Return ElevenLabs API key."""
        return cls._get_env_var("ELEVENLABS_API_KEY", required=True)

    @classmethod
    def get_pixabay_api_key(cls) -> str:
        """Return Pixabay API key."""
        return cls._get_env_var("PIXABAY_API_KEY", required=True)

    @classmethod
    def get_secret(cls, key: str, required: bool = True) -> Optional[str]:
        """Generic method to retrieve any secret by its environment variable name."""
        return cls._get_env_var(key, required)