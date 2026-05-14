"""
visual_sourcer.py

Provides the VisualSourcer class to interact with the Pixabay API,
searching for high-resolution stock videos and images, downloading them
for use in video assembly. Uses 4K quality where available.
"""

import os
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import requests

# Configure logger
logger = logging.getLogger(__name__)


class VisualSourcer:
    """
    Handles searching and downloading of stock media from Pixabay.
    Supports both videos and images, with a focus on 4K resolution.
    """

    VIDEO_ENDPOINT = "https://pixabay.com/api/videos/"
    IMAGE_ENDPOINT = "https://pixabay.com/api/"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the VisualSourcer with an API key.
        The key can be passed directly or read from the PIXABAY_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("PIXABAY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Pixabay API key not provided. Set PIXABAY_API_KEY environment variable."
            )

    def search_videos(
        self, query: str, max_results: int = 5, min_width: int = 1920, min_height: int = 1080
    ) -> List[Dict[str, Any]]:
        """
        Search Pixabay for videos matching the query.

        Args:
            query: Search keywords.
            max_results: Maximum number of video results to return.
            min_width: Minimum video width (default 1920px).
            min_height: Minimum video height (default 1080px).

        Returns:
            A list of video result dictionaries with keys:
                id, pageURL, tags, duration, picture_id,
                videos: dict with quality levels (large, medium, small, tiny),
                user, userImageURL
        """
        params = {
            "key": self.api_key,
            "q": query,
            "per_page": min(max_results, 200),
            "min_width": min_width,
            "min_height": min_height,
            "safesearch": "true",
            "order": "popular",
        }
        try:
            response = requests.get(self.VIDEO_ENDPOINT, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            videos = data.get("hits", [])
            logger.info(f"Found {len(videos)} video(s) for query '{query}'.")
            return videos[:max_results]
        except requests.RequestException as e:
            logger.error(f"Error searching videos for '{query}': {e}")
            return []

    def search_images(
        self, query: str, max_results: int = 5, min_width: int = 1920, min_height: int = 1080
    ) -> List[Dict[str, Any]]:
        """
        Search Pixabay for images (photos) matching the query.

        Args:
            query: Search keywords.
            max_results: Maximum number of image results to return.
            min_width: Minimum image width.
            min_height: Minimum image height.

        Returns:
            A list of image result dictionaries with keys:
                id, pageURL, tags, webformatURL, largeImageURL, user, etc.
        """
        params = {
            "key": self.api_key,
            "q": query,
            "image_type": "photo",
            "per_page": min(max_results, 200),
            "min_width": min_width,
            "min_height": min_height,
            "safesearch": "true",
            "order": "popular",
        }
        try:
            response = requests.get(self.IMAGE_ENDPOINT, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            images = data.get("hits", [])
            logger.info(f"Found {len(images)} image(s) for query '{query}'.")
            return images[:max_results]
        except requests.RequestException as e:
            logger.error(f"Error searching images for '{query}': {e}")
            return []

    @staticmethod
    def get_best_video_url(video_hit: dict) -> Optional[str]:
        """
        Extract the best available video URL (4K 'large') from a video search hit.

        Args:
            video_hit: A video result dictionary from search_videos.

        Returns:
            URL string for the large video, or None if not available.
        """
        videos = video_hit.get("videos", {})
        # 'large' corresponds to 3840x2160 (4K)
        return videos.get("large", {}).get("url")

    @staticmethod
    def get_best_image_url(image_hit: dict) -> Optional[str]:
        """
        Extract the largest available image URL from an image search hit.

        Args:
            image_hit: An image result dictionary from search_images.

        Returns:
            URL string (largeImageURL) or None.
        """
        return image_hit.get("largeImageURL")

    def download_media(self, url: str, output_path: Path) -> bool:
        """
        Download a media file from the given URL and save it to output_path.

        Args:
            url: The direct media URL.
            output_path: Path where the file will be saved.

        Returns:
            True if download succeeded, False otherwise.
        """
        if not url:
            logger.warning("No URL provided for download.")
            return False

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # If file exists, skip download (or optionally overwrite)
            if output_path.exists():
                logger.info(f"File already exists at {output_path}, skipping download.")
                return True

            logger.info(f"Downloading from {url}...")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Successfully saved to {output_path}")
            return True
        except requests.RequestException as e:
            logger.error(f"Download failed: {e}")
            # Remove partially downloaded file
            if output_path.exists():
                output_path.unlink()
            return False

    def fetch_top_video(
        self, query: str, output_dir: Path, filename: Optional[str] = None
    ) -> Optional[Path]:
        """
        Convenience method: search for the best 4K video matching query,
        download it, and return the file path.

        Args:
            query: Search keywords.
            output_dir: Directory to save the video.
            filename: Optional custom filename (without extension). If None, uses query.

        Returns:
            Path to the downloaded video file, or None if unsuccessful.
        """
        videos = self.search_videos(query, max_results=1)
        if not videos:
            logger.warning(f"No videos found for '{query}'")
            return None

        best_video = videos[0]
        video_url = self.get_best_video_url(best_video)
        if not video_url:
            logger.warning("No high-resolution video URL found.")
            return None

        # Determine filename
        safe_name = filename or query.replace(" ", "_")[:50]  # limit length
        video_path = output_dir / f"{safe_name}.mp4"

        if self.download_media(video_url, video_path):
            return video_path
        return None

    def fetch_top_image(
        self, query: str, output_dir: Path, filename: Optional[str] = None
    ) -> Optional[Path]:
        """
        Convenience method: search for the best high-resolution image matching query,
        download it, and return the file path.

        Args:
            query: Search keywords.
            output_dir: Directory to save the image.
            filename: Optional custom filename (without extension).

        Returns:
            Path to the downloaded image file, or None if unsuccessful.
        """
        images = self.search_images(query, max_results=1)
        if not images:
            logger.warning(f"No images found for '{query}'")
            return None

        best_image = images[0]
        image_url = self.get_best_image_url(best_image)
        if not image_url:
            logger.warning("No high-resolution image URL found.")
            return None

        # Determine extension from URL or default to jpg
        ext = "jpg"
        if image_url:
            base = image_url.split("?")[0]
            if "." in base:
                ext = base.rsplit(".", 1)[-1].lower()
                if ext not in ["jpg", "jpeg", "png", "webp"]:
                    ext = "jpg"

        safe_name = filename or query.replace(" ", "_")[:50]
        image_path = output_dir / f"{safe_name}.{ext}"

        if self.download_media(image_url, image_path):
            return image_path
        return None


def main():
    """Simple test routine if the module is run directly."""
    logging.basicConfig(level=logging.INFO)
    try:
        sourcer = VisualSourcer()
    except ValueError as e:
        logger.error(e)
        return

    query = "nature landscape"
    output = Path("./test_media")
    video_path = sourcer.fetch_top_video(query, output)
    if video_path:
        print(f"Video saved to {video_path}")
    image_path = sourcer.fetch_top_image(query, output)
    if image_path:
        print(f"Image saved to {image_path}")


if __name__ == "__main__":
    main()