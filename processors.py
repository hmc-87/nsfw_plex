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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import magic
from config import get_config, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, ARCHIVE_EXTENSIONS
from db_config import SessionLocal

# Configure logging
logger = logging.getLogger(__name__)

# Set the cache directory for transformers
os.environ["HF_HOME"] = os.getenv("HF_HOME", "~/.cache/huggingface")

# Initialize NSFW detection model
pipe = pipeline("image-classification", model="Falconsai/nsfw_image_detection", device=-1)


def detect_file_type(file_path):
    """
    Detect the MIME type and extension of a file using the magic library.
    """
    try:
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(file_path)
        ext = mime_type.split("/")[-1]
        return mime_type, f".{ext}"
    except Exception as e:
        logger.error(f"Error detecting file type: {e}")
        raise Exception(f"Error detecting file type: {str(e)}")


def extract_video_metadata(file_path):
    """Use FFprobe to extract video metadata such as codec and bitrate."""
    try:
        # FFprobe command to get codec and bitrate
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,bit_rate',
            '-of', 'default=noprint_wrappers=1', file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise Exception(f"FFprobe error: {result.stderr.decode().strip()}")

        # Parse the output
        output = result.stdout.decode().strip().split('\n')
        codec = None
        bitrate = None

        for line in output:
            if 'codec_name' in line:
                codec = line.split('=')[1]
            if 'bit_rate' in line:
                val = line.split('=')[1]
                bitrate = int(val) if val.isdigit() else None

        return codec, bitrate
    except Exception as e:
        logger.error(f"Error extracting video metadata: {e}")
        raise


class VideoProcessor:
    def __init__(self, video_path):
        self.video_path = video_path
        self.temp_dir = None

    def _extract_keyframes(self):
        """Extract keyframes from the video using FFmpeg."""
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Extracting frames from video: {self.video_path}")
        extract_cmd = [
            'ffmpeg',
            '-i', self.video_path,
            '-vf', 'fps=1',  # One frame per second
            '-t', str(get_config("FFMPEG_TIME_LIMIT")),  # Time limit for processing
            '-q:v', '2',  # High-quality JPEG
            '-y',  # Overwrite files
            os.path.join(self.temp_dir, 'frame-%03d.jpg')  # Output pattern
        ]

        try:
            result = subprocess.run(
                extract_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=get_config("FFMPEG_TIMEOUT")
            )

            if result.returncode != 0:
                raise Exception(f"FFmpeg error: {result.stderr.decode().strip()}")

            frames = sorted(glob.glob(os.path.join(self.temp_dir, 'frame-*.jpg')))
            if not frames:
                raise Exception("No frames extracted from video.")

            logger.info(f"Extracted {len(frames)} frames successfully.")

            # Optional: slight delay to ensure filesystem sync
            #time.sleep(0.5)

            # Double-check frames exist
            for frame in frames:
                if not os.path.exists(frame):
                    logger.warning(f"Frame listed but not found on disk: {frame}")

            return frames

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg frame extraction timed out.")
            raise Exception("Frame extraction timed out.")
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
            # We do not clean up here to inspect frames if needed.
            # Cleanup will happen in process() if something fails later.
            raise

    def _process_frame(self, frame_path):
        """Analyze a single frame using the NSFW model."""
        logger.info(f"Attempting to open frame: {frame_path}")
        if not os.path.exists(frame_path):
            logger.error(f"Frame {frame_path} does not exist at processing time.")
            return None

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
            frame_files = self._extract_keyframes()

            # Process frames in parallel
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(self._process_frame, frame) for frame in frame_files]
                for future in as_completed(futures):
                    result = future.result()
                    if result and result['nsfw'] > get_config("NSFW_THRESHOLD"):
                        logger.info("NSFW content detected in video frame.")
                        return result

            logger.info("No NSFW content detected in video.")
            return {"nsfw": 0, "normal": 1}

        except Exception as e:
            logger.error(f"Error processing video: {e}")
            raise
        finally:
            # Cleanup temporary files regardless of success or error
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

    # Extract video metadata (codec, bitrate)
    codec, bitrate = extract_video_metadata(video_path)

    # Process video for NSFW detection
    result = processor.process()

    # Return both NSFW results and video metadata (codec and bitrate)
    return {
        'nsfw': result['nsfw'],
        'normal': result['normal'],
        'codec': codec,
        'bitrate': bitrate
    }


def process_pdf_file(pdf_stream):
    """Analyze the content of a PDF file."""
    try:
        logger.info("Analyzing PDF file...")
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        total_pages = len(doc)
        logger.info(f"PDF contains {total_pages} pages.")

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
                    if result['nsfw'] > get_config("NSFW_THRESHOLD"):
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
        # Add your archive handling logic here if needed
        return {"status": "success", "message": f"Archive {filename} processed successfully."}
    except Exception as e:
        logger.error(f"Error analyzing archive file: {e}")
        return {"status": "error", "message": str(e)}