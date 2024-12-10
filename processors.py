from transformers import pipeline
import subprocess
import numpy as np
from PIL import Image
import fitz
import io
import logging
import tempfile
import os
import shutil
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from config import (
    MAX_FILE_SIZE, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS,
    NSFW_THRESHOLD, FFMPEG_MAX_FRAMES, FFMPEG_TIMEOUT,
    FFMPEG_TIME_LIMIT, ARCHIVE_EXTENSIONS
)

# Configure logging
logger = logging.getLogger(__name__)

# Set the cache directory for transformers
os.environ["TRANSFORMERS_CACHE"] = "/Users/kyle_wils/Nextcloud/Development/nsfw-plex/cache"

# Initialize NSFW detection model
pipe = pipeline("image-classification", model="Falconsai/nsfw_image_detection", device=-1)


class VideoProcessor:
    def __init__(self, video_path):
        self.video_path = video_path
        self.temp_dir = None

    def _extract_keyframes(self):
        """Extract keyframes from the video using FFmpeg."""
        try:
            # Create a temporary directory for extracted frames
            self.temp_dir = tempfile.mkdtemp()
            logger.info(f"Extracting frames from video: {self.video_path}")

            # FFmpeg command for frame extraction
            extract_cmd = [
                'ffmpeg',
                '-i', self.video_path,
                '-vf', f'fps=1',  # One frame per second
                '-t', str(FFMPEG_TIME_LIMIT),  # Time limit for processing
                '-q:v', '2',  # High-quality JPEG
                '-y',  # Overwrite files
                os.path.join(self.temp_dir, 'frame-%03d.jpg')  # Output pattern
            ]

            # Run the FFmpeg command
            result = subprocess.run(
                extract_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=FFMPEG_TIMEOUT
            )

            if result.returncode != 0:
                raise Exception(f"FFmpeg error: {result.stderr.decode().strip()}")

            # Collect all extracted frames
            frames = sorted(glob.glob(os.path.join(self.temp_dir, 'frame-*.jpg')))
            if not frames:
                raise Exception("No frames extracted from video.")

            logger.info(f"Extracted {len(frames)} frames successfully.")
            return frames

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg frame extraction timed out.")
            raise Exception("Frame extraction timed out.")
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
            raise
        finally:
            # Cleanup in case of an error
            if self.temp_dir and not os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _process_frame(self, frame_path):
        """Analyze a single frame using the NSFW model."""
        try:
            with Image.open(frame_path) as img:
                result = process_image(img)
                return result
        except Exception as e:
            logger.error(f"Error processing frame {frame_path}: {e}")
            return None

    def process(self):
        """Main function for video processing."""
        try:
            # Extract frames
            frame_files = self._extract_keyframes()

            # Process each frame in parallel
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(self._process_frame, frame) for frame in frame_files]
                for future in as_completed(futures):
                    result = future.result()
                    if result and result['nsfw'] > NSFW_THRESHOLD:
                        logger.info(f"NSFW content detected in video frame.")
                        return result

            logger.info("No NSFW content detected in video.")
            return {"nsfw": 0, "normal": 1}

        except Exception as e:
            logger.error(f"Error processing video: {e}")
            raise
        finally:
            # Cleanup temporary files
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info("Temporary files cleaned up.")


def process_image(image):
    """Analyze an image using the NSFW model."""
    try:
        logger.info("Analyzing image for NSFW content...")
        result = pipe(image)
        nsfw_score = next((item['score'] for item in result if item['label'] == 'nsfw'), 0)
        normal_score = next((item['score'] for item in result if item['label'] == 'normal'), 1)
        logger.info(f"Image analyzed: NSFW={nsfw_score:.3f}, Normal={normal_score:.3f}")
        return {
            'nsfw': nsfw_score,
            'normal': normal_score
        }
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise Exception("Error analyzing image.")


def process_video_file(video_path):
    """Entry point for processing videos."""
    processor = VideoProcessor(video_path)
    return processor.process()


def process_pdf_file(pdf_stream):
    """Analyze the content of a PDF file."""
    try:
        logger.info("Analyzing PDF file...")
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        total_pages = len(doc)
        logger.info(f"PDF contains {total_pages} pages.")

        last_result = None
        for page_num in range(total_pages):
            page = doc[page_num]
            images = page.get_images()

            for img in images:
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]

                    image = Image.open(io.BytesIO(image_bytes))
                    result = process_image(image)
                    if result['nsfw'] > NSFW_THRESHOLD:
                        logger.info(f"NSFW content detected on page {page_num + 1}.")
                        return result

                except Exception as e:
                    logger.error(f"Error processing image on page {page_num + 1}: {e}")

        logger.info("No NSFW content detected in PDF.")
        return {"nsfw": 0, "normal": 1}

    except Exception as e:
        logger.error(f"Error analyzing PDF: {e}")
        raise Exception("Error analyzing PDF.")


def process_archive(filepath, filename):
    """Placeholder function to analyze archive files."""
    try:
        logger.info(f"Processing archive file: {filename}")
        # Example logic for handling archive files (if needed)
        return {"status": "success", "message": f"Archive {filename} processed successfully."}
    except Exception as e:
        logger.error(f"Error analyzing archive file: {e}")
        return {"status": "error", "message": str(e)}