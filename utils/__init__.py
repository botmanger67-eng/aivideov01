"""
utils package for the autonomous short-form video generator.

Contains submodules for interacting with external APIs (DeepSeek, ElevenLabs,
Pixabay) and for video assembly using MoviePy. Also provides shared utilities
such as configuration loading, logging setup, and custom exceptions.
"""

# -----------------------------------------------------------------------------
# Optional convenience imports – guarded to avoid ImportError if a submodule
# has not yet been created. These can be uncommented / modified as the project
# grows.
# -----------------------------------------------------------------------------

try:
    from .config import load_config, settings
except ImportError:
    pass

try:
    from .logging import setup_logger
except ImportError:
    pass

try:
    from .exceptions import VideoGenerationError
except ImportError:
    pass

try:
    from .video_builder import VideoBuilder
except ImportError:
    pass

__all__ = [
    "load_config",
    "settings",
    "setup_logger",
    "VideoGenerationError",
    "VideoBuilder",
]