import os
from dotenv import load_dotenv
import logging

# Ensure configuration is loaded only once
if not globals().get("CONFIG_LOADED"):
    CONFIG_LOADED = True

    # Load environment variables from .env
    load_dotenv()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
    )
    logger = logging.getLogger("config")

    # Default configuration values
    DEFAULT_CONFIG = {
        "MAX_FILE_SIZE": 20 * 1024 * 1024 * 1024,  # 20GB
        "NSFW_THRESHOLD": float(os.getenv("NSFW_THRESHOLD", 0.8)),
        "FFMPEG_MAX_FRAMES": int(os.getenv("FFMPEG_MAX_FRAMES", 20)),
        "FFMPEG_TIMEOUT": int(os.getenv("FFMPEG_TIMEOUT", 1800)),
        "FFMPEG_TIME_LIMIT": os.getenv("FFMPEG_TIME_LIMIT", "00:03:00"),  # Default to 3 minutes
        "CHECK_ALL_FILES": int(os.getenv("CHECK_ALL_FILES", 0)),
        "MAX_INTERVAL_SECONDS": int(os.getenv("MAX_INTERVAL_SECONDS", 30)),
        # Email settings
        "SMTP_SERVER": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "SMTP_PORT": int(os.getenv("SMTP_PORT", 587)),
        "FROM_EMAIL": os.getenv("FROM_EMAIL"),
        "FROM_PASSWORD": os.getenv("FROM_PASSWORD"),
        "TO_EMAIL": os.getenv("TO_EMAIL"),
        # Media folder
        "MEDIA_FOLDER": os.getenv("MEDIA_FOLDER", "/media"),
        # HF_HOME Cache Directory for Transformers
        "HF_HOME": os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface")),
    }

    CONFIG_PATH = os.getenv("CONFIG_PATH", None)  # Allow overriding config path via environment

    # Load configuration from file
    config_values = DEFAULT_CONFIG.copy()

    def get_config(key, default=None):
        """
        Retrieve a configuration value.
        Priority order: Environment variable > Configuration file > Default value.
        """
        return config_values.get(key, DEFAULT_CONFIG.get(key, default))

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
        "DEFAULT_CONFIG",
        "MIME_TO_EXT",
        "IMAGE_EXTENSIONS",
        "VIDEO_EXTENSIONS",
        "ARCHIVE_EXTENSIONS",
        "IMAGE_MIME_TYPES",
        "VIDEO_MIME_TYPES",
        "ARCHIVE_MIME_TYPES",
        "PDF_MIME_TYPES",
        "SUPPORTED_MIME_TYPES",
        "get_config",
    ]

    # Set Transformers cache directory if specified
    hf_home = get_config("HF_HOME")
    if hf_home:
        os.environ["TRANSFORMERS_CACHE"] = hf_home
        logger.info(f"Transformers cache directory set to: {hf_home}")

logger.info("Configuration fully initialized.")