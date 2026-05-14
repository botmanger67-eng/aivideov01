"""
Video assembler module using MoviePy to compose final MP4 video from audio,
visual assets (images/videos), and text overlays.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    clips_array,
    concatenate_videoclips,
)

logger = logging.getLogger(__name__)


@dataclass
class Segment:
    """
    Represents a visual segment with optional text overlay.
    """
    media_path: str  # path to image or video file
    start_time: float  # in seconds from video start
    duration: float
    text: Optional[str] = None
    text_style: Optional[Dict] = None  # overrides to default text style
    position: str = 'center'  # 'center', 'bottom', custom tuple


class VideoAssembler:
    """
    Assembles final MP4 video by synchronizing audio with visual clips
    and adding text overlays using MoviePy.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize assembler with configuration.

        Args:
            config: Dictionary with optional keys:
                - output_size (tuple): (width, height), default (1080, 1920)
                - fps (int): frames per second, default 24
                - codec (str): video codec, default 'libx264'
                - audio_codec (str): audio codec, default 'aac'
                - font (str): font name/path for text, default 'Arial'
                - font_size (int): default font size, default 60
                - text_color (str): default text color, default 'white'
                - stroke_color (str): default stroke color, default 'black'
                - stroke_width (int): default stroke width, default 2
                - text_position (str or tuple): default position, default ('center', 'bottom')
        """
        default_config = {
            'output_size': (1080, 1920),  # vertical short video
            'fps': 24,
            'codec': 'libx264',
            'audio_codec': 'aac',
            'font': 'Arial',
            'font_size': 60,
            'text_color': 'white',
            'stroke_color': 'black',
            'stroke_width': 2,
            'text_position': ('center', 'bottom'),
        }
        self.config = {**default_config, **(config or {})}
        self._validate_config()

    def _validate_config(self) -> None:
        """Ensure required config keys are present."""
        required = ['output_size', 'fps', 'codec', 'audio_codec']
        for key in required:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")

    def assemble_video(
        self,
        segments: List[Segment],
        audio_path: Union[str, Path],
        output_path: Union[str, Path],
    ) -> Path:
        """
        Create final MP4 video file from segments and audio.

        Args:
            segments: List of Segment objects defining visual clips and text.
            audio_path: Path to audio file (e.g., MP3).
            output_path: Where to save the final video file.

        Returns:
            Path to the generated video file.

        Raises:
            FileNotFoundError: If audio file doesn't exist.
            ValueError: If segments are empty or invalid.
            Exception: On MoviePy processing errors.
        """
        audio_path = Path(audio_path)
        output_path = Path(output_path)

        if not audio_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if not segments:
            raise ValueError("At least one segment is required.")

        # Create output directory if necessary
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load audio to determine duration
        try:
            audio_clip = AudioFileClip(str(audio_path))
            total_duration = audio_clip.duration
            logger.info(f"Audio duration: {total_duration:.2f}s")
        except Exception as e:
            raise RuntimeError(f"Failed to load audio: {e}") from e

        clips_to_composite = []
        loaded_clips = []  # keep track for cleanup

        try:
            for i, seg in enumerate(segments):
                # Validate segment data
                if seg.duration <= 0:
                    raise ValueError(f"Segment {i}: duration must be positive.")
                if seg.start_time < 0:
                    raise ValueError(f"Segment {i}: start_time cannot be negative.")
                if seg.start_time + seg.duration > total_duration:
                    logger.warning(
                        f"Segment {i} exceeds audio length. Trimming to fit."
                    )
                    seg.duration = max(0, total_duration - seg.start_time)

                # Load visual asset
                media_path = Path(seg.media_path)
                if not media_path.is_file():
                    raise FileNotFoundError(f"Media file missing: {media_path}")

                # Determine if image or video based on extension
                suffix = media_path.suffix.lower()
                if suffix in ('.jpg', '.jpeg', '.png', '.bmp', '.webp'):
                    clip = ImageClip(str(media_path))
                elif suffix in ('.mp4', '.mov', '.avi', '.webm', '.mkv'):
                    clip = VideoFileClip(str(media_path))
                else:
                    # Treat as image by default (ImageClip will raise if unsupported)
                    clip = ImageClip(str(media_path))

                # Resize and set duration/start
                clip = clip.resize(self.config['output_size'])
                if seg.duration > clip.duration:
                    # Loop if visual is shorter than required duration
                    clip = clip.loop(duration=seg.duration)
                else:
                    clip = clip.set_duration(seg.duration)
                clip = clip.set_start(seg.start_time)
                clips_to_composite.append(clip)
                loaded_clips.append(clip)

                # Add text overlay if text provided
                if seg.text:
                    text_style = {
                        'font': self.config['font'],
                        'fontsize': self.config['font_size'],
                        'color': self.config['text_color'],
                        'stroke_color': self.config['stroke_color'],
                        'stroke_width': self.config['stroke_width'],
                    }
                    if seg.text_style:
                        text_style.update(seg.text_style)

                    position = seg.position
                    if position == 'center':
                        position = ('center', 'center')
                    elif position == 'bottom':
                        position = ('center', 0.8)
                    else:
                        # Assume tuple is given, keep as is
                        pass

                    txt_clip = TextClip(
                        seg.text,
                        font=text_style['font'],
                        fontsize=text_style['fontsize'],
                        color=text_style['color'],
                        stroke_color=text_style['stroke_color'],
                        stroke_width=text_style['stroke_width'],
                        method='caption',  # word-wrap if needed
                        size=(self.config['output_size'][0] * 0.9, None),
                    )
                    txt_clip = txt_clip.set_start(seg.start_time).set_duration(seg.duration)
                    txt_clip = txt_clip.set_position(position)
                    clips_to_composite.append(txt_clip)
                    loaded_clips.append(txt_clip)

            # Create composite video with black background
            video = CompositeVideoClip(
                clips_to_composite,
                size=self.config['output_size'],
            )
            # Ensure video duration matches audio (could be shorter if segments end early)
            # Pad with black if needed, but we trust segments cover whole audio
            video = video.set_duration(total_duration)

            # Set audio
            video = video.set_audio(audio_clip)

            # Write final file
            logger.info(f"Writing video to {output_path}...")
            video.write_videofile(
                str(output_path),
                fps=self.config['fps'],
                codec=self.config['codec'],
                audio_codec=self.config['audio_codec'],
                temp_audiofile=str(output_path.with_suffix('.temp.mp3')),
                remove_temp=True,
                threads=4,  # adjust based on environment
                verbose=False,
                logger=None,
            )
            logger.info("Video assembly complete.")
            return output_path

        except Exception as e:
            logger.exception("Failed to assemble video.")
            raise
        finally:
            # Cleanup all clips to free memory
            loaded_clips.append(audio_clip)
            for clip in loaded_clips:
                try:
                    clip.close()
                except Exception:
                    pass

    def preview_segment_timeline(self, segments: List[Segment]) -> None:
        """Utility to log timeline of segments for debugging."""
        for i, seg in enumerate(segments):
            logger.info(
                f"Segment {i}: start={seg.start_time:.2f}s, "
                f"dur={seg.duration:.2f}s, text={seg.text[:30] if seg.text else 'None'}"
            )


# Example usage (can be used by the API service)
if __name__ == "__main__":
    # Quick test with dummy data
    from pathlib import Path

    assembler = VideoAssembler()
    # Dummy audio file required for actual run – here we just show object creation
    print("VideoAssembler ready.")