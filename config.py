import os
import rarfile
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8',
)
logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    "MAX_FILE_SIZE": 20 * 1024 * 1024 * 1024,  # 20GB
    "NSFW_THRESHOLD": 0.8,
    "FFMPEG_MAX_FRAMES": 20,
    "FFMPEG_TIMEOUT": 1800,
    "FFMPEG_TIME_LIMIT": "00:03:00",  # 3 minutes
    "CHECK_ALL_FILES": 0,
    "MAX_INTERVAL_SECONDS": 30,
}

CONFIG_PATH = "/tmp/config"


def load_config_from_file(file_path=CONFIG_PATH):
    """Load configuration from a file and merge it with default values."""
    config = DEFAULT_CONFIG.copy()

    if not os.path.exists(file_path):
        logger.warning(f"Configuration file {file_path} not found, using default values.")
        return config

    try:
        logger.info(f"Loading configuration from {file_path}...")
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        key, value = map(str.strip, line.split("=", 1))
                        if key.upper() in config:
                            # Infer the type of the default value
                            default_type = type(config[key.upper()])
                            config[key.upper()] = default_type(value)
                            logger.info(f"Loaded config: {key.upper()} = {config[key.upper()]}")
                        else:
                            logger.warning(f"Unknown config key: {key}. Ignoring.")
                    except ValueError:
                        logger.warning(f"Invalid config line: {line}. Skipping.")
    except Exception as e:
        logger.error(f"Error reading configuration file: {e}")
    return config


# Load configuration from file
config_values = load_config_from_file()

# Update global variables with the loaded configuration
globals().update(config_values)

# Log final configuration
logger.info("Final configuration values:")
for key, value in config_values.items():
    logger.info(f"{key}: {value}")

# MIME type to file extension mapping
MIME_TO_EXT = {
    # Image formats
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/x-tiff": ".tiff",
    "image/x-tga": ".tga",
    "image/x-portable-pixmap": ".ppm",
    "image/x-portable-graymap": ".pgm",
    "image/x-portable-bitmap": ".pbm",
    "image/x-portable-anymap": ".pnm",
    "image/svg+xml": ".svg",
    "image/x-pcx": ".pcx",
    "image/vnd.adobe.photoshop": ".psd",
    "image/vnd.microsoft.icon": ".ico",
    "image/heif": ".heif",
    "image/heic": ".heic",
    "image/avif": ".avif",
    "image/jxl": ".jxl",
    # PDF format
    "application/pdf": ".pdf",
    # Video formats
    "video/mp4": ".mp4",
    "video/x-msvideo": ".avi",
    "video/x-matroska": ".mkv",
    "video/quicktime": ".mov",
    "video/x-ms-wmv": ".wmv",
    "video/webm": ".webm",
    "video/MP2T": ".ts",
    "video/x-flv": ".flv",
    "video/3gpp": ".3gp",
    "video/3gpp2": ".3g2",
    "video/x-m4v": ".m4v",
    "video/mxf": ".mxf",
    "video/x-ogm": ".ogm",
    "video/vnd.rn-realvideo": ".rv",
    "video/dv": ".dv",
    "video/x-ms-asf": ".asf",
    "video/x-f4v": ".f4v",
    "video/vnd.dlna.mpeg-tts": ".m2ts",
    "video/x-raw": ".yuv",
    "video/mpeg": ".mpg",
    "video/x-mpeg": ".mpeg",
    "video/divx": ".divx",
    "video/x-vob": ".vob",
    "video/x-m2v": ".m2v",
    # Archive formats
    "application/x-rar-compressed": ".rar",
    "application/x-rar": ".rar",
    "application/vnd.rar": ".rar",
    "application/zip": ".zip",
    "application/x-7z-compressed": ".7z",
    "application/gzip": ".gz",
    "application/x-tar": ".tar",
    "application/x-bzip2": ".bz2",
    "application/x-xz": ".xz",
    "application/x-lzma": ".lzma",
    "application/x-zstd": ".zst",
    "application/vnd.ms-cab-compressed": ".cab",
}

# File extension sets
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tga", ".ppm", ".pgm", ".pbm", ".pnm", ".svg", ".pcx", ".psd", ".ico", ".heif", ".heic", ".avif", ".jxl"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm", ".ts", ".flv", ".3gp", ".3g2", ".m4v", ".mxf", ".ogm", ".rv", ".dv", ".asf", ".f4v", ".m2ts", ".yuv", ".mpg", ".mpeg", ".divx", ".vob", ".m2v"}
ARCHIVE_EXTENSIONS = {".7z", ".rar", ".zip", ".gz", ".tar", ".bz2", ".xz", ".lzma", ".zst", ".cab"}

# MIME type sets
IMAGE_MIME_TYPES = {mime for mime, ext in MIME_TO_EXT.items() if mime.startswith("image/")}
VIDEO_MIME_TYPES = {mime for mime, ext in MIME_TO_EXT.items() if mime.startswith("video/")}
ARCHIVE_MIME_TYPES = {mime for mime, ext in MIME_TO_EXT.items() if mime.startswith("application/") and any(keyword in mime for keyword in ["zip", "rar", "7z", "gzip", "tar", "bzip2", "xz", "lzma", "zstd", "cab"])}
PDF_MIME_TYPES = {"application/pdf"}

# Supported MIME types
SUPPORTED_MIME_TYPES = IMAGE_MIME_TYPES | VIDEO_MIME_TYPES | ARCHIVE_MIME_TYPES | PDF_MIME_TYPES

# Exported configuration
__all__ = [
    "MIME_TO_EXT",
    "IMAGE_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "ARCHIVE_EXTENSIONS",
    "IMAGE_MIME_TYPES",
    "VIDEO_MIME_TYPES",
    "ARCHIVE_MIME_TYPES",
    "PDF_MIME_TYPES",
    "SUPPORTED_MIME_TYPES",
    *DEFAULT_CONFIG.keys(),
]