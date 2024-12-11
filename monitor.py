import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import magic
from processors import process_video_file, process_image
from config import VIDEO_EXTENSIONS, IMAGE_EXTENSIONS, get_config
from db_config import SessionLocal
from crud import get_file_by_path, add_or_update_file
from datetime import datetime
import ffmpeg
from email_utils import send_email

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("monitor")

def detect_file_type(file_path):
    """
    Detect the MIME type and extension of a file using the magic library.
    """
    try:
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(file_path)
        ext = os.path.splitext(file_path)[-1].lower()
        if not mime_type:
            raise ValueError(f"Could not determine MIME type for {file_path}")
        return mime_type, ext
    except Exception as e:
        logger.error(f"Error detecting file type for {file_path}: {e}")
        raise

def extract_duration(file_path):
    """
    Use FFprobe to extract the duration of a video file.
    """
    try:
        probe = ffmpeg.probe(file_path)
        return float(probe['format']['duration'])
    except Exception as e:
        logger.warning(f"Failed to extract duration for {file_path}: {e}")
        return None

def extract_video_metadata(file_path):
    """
    Use FFprobe to extract video metadata such as codec and bitrate.
    """
    try:
        probe = ffmpeg.probe(file_path, v='error', select_streams='v:0', show_entries='stream=codec_name,bit_rate')
        codec = probe['streams'][0]['codec_name']
        bitrate = int(probe['streams'][0]['bit_rate']) if 'bit_rate' in probe['streams'][0] else None
        return codec, bitrate
    except Exception as e:
        logger.warning(f"Failed to extract metadata for {file_path}: {e}")
        return None, None

class MediaFileHandler(FileSystemEventHandler):
    """
    Custom handler for processing new and existing media files.
    """
    def __init__(self, target_folder):
        super().__init__()
        self.target_folder = target_folder

    def on_created(self, event):
        """
        Triggered when a file is created in the target directory.
        """
        if not event.is_directory:
            file_path = event.src_path
            logger.info(f"New file detected: {file_path}")
            if self.wait_for_file_complete(file_path):
                self.process_file(file_path)
            else:
                logger.warning(f"File {file_path} could not be stabilized for processing.")

    def process_existing_files(self):
        """
        Process all existing files in the target directory.
        """
        for root, _, files in os.walk(self.target_folder):
            for file in files:
                if file.startswith("."):  # Skip hidden/system files like .DS_Store
                    logger.info(f"Ignoring hidden/system file: {file}")
                    continue
                file_path = os.path.join(root, file)
                if self.wait_for_file_complete(file_path):
                    self.process_file(file_path)

    def wait_for_file_complete(self, file_path, timeout=600):
        """
        Wait until the file is fully written by checking its size stability.
        """
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < timeout:
            try:
                current_size = os.path.getsize(file_path)
                if current_size == last_size:
                    return True
                last_size = current_size
                time.sleep(2)
            except FileNotFoundError:
                logger.warning(f"File {file_path} was deleted before processing.")
                return False

        logger.error(f"File {file_path} did not stabilize within the timeout period.")
        return False

    def process_file(self, file_path):
        """
        Process a single media file for NSFW detection and database tracking.
        """
        db = SessionLocal()

        # Get the file's last modified time
        last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))

        # Check if the file is already in the database
        existing_file = get_file_by_path(db, file_path)
        if existing_file and existing_file.last_modified >= last_modified:
            logger.info(f"File {file_path} already processed.")
            db.close()
            return

        try:
            mime_type, ext = detect_file_type(file_path)

            if mime_type.startswith("video/") and ext in VIDEO_EXTENSIONS:
                logger.info(f"Processing video file: {file_path} (MIME: {mime_type})")
                duration = extract_duration(file_path)
                codec, bitrate = extract_video_metadata(file_path)
                result = process_video_file(file_path)

                if result and result.get("nsfw", 0) > get_config("NSFW_THRESHOLD", 0.8):
                    logger.warning(f"NSFW content detected in video: {file_path}")
                    subject = f"NSFW Content Detected: {file_path}"
                    body = f"""
                    File: {file_path}
                    NSFW Score: {result['nsfw']}
                    Duration: {duration} seconds
                    Codec: {codec}
                    Bitrate: {bitrate}
                    """
                    send_email(subject, body)
                    logger.info(f"Email notification sent for file: {file_path}")

                elif result:
                    logger.info(f"Video is safe: {file_path}")

                add_or_update_file(db, file_path, last_modified, duration, result.get("nsfw", 0), codec, bitrate)

            elif mime_type.startswith("image/") and ext in IMAGE_EXTENSIONS:
                logger.info(f"Processing image file: {file_path} (MIME: {mime_type})")
                result = process_image(file_path)

                if result and result.get("nsfw", 0) > get_config("NSFW_THRESHOLD", 0.8):
                    logger.warning(f"NSFW content detected in image: {file_path}")
                    subject = f"NSFW Content Detected: {file_path}"
                    body = f"""
                    File: {file_path}
                    NSFW Score: {result['nsfw']}
                    """
                    send_email(subject, body)
                    logger.info(f"Email notification sent for file: {file_path}")

                elif result:
                    logger.info(f"Image is safe: {file_path}")

                add_or_update_file(db, file_path, last_modified, None, result.get("nsfw", 0), None, None)

            else:
                logger.warning(f"Unsupported file type: {file_path} (MIME: {mime_type})")

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
        finally:
            db.close()

def monitor_folder(target_folder):
    """
    Set up and start monitoring the target folder.
    """
    logger.info(f"Starting folder monitor on: {target_folder}")
    event_handler = MediaFileHandler(target_folder)
    logger.info("Processing existing files in the target folder...")
    event_handler.process_existing_files()

    observer = Observer()
    observer.schedule(event_handler, path=target_folder, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

if __name__ == "__main__":
    target_folder = get_config("MEDIA_FOLDER")
    if not os.path.exists(target_folder):
        logger.error(f"Target folder does not exist: {target_folder}")
        exit(1)

    monitor_folder(target_folder)