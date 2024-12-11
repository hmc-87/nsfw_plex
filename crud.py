import logging
from sqlalchemy.orm import Session
from models import MediaFile
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

def get_file_by_path(db: Session, file_path: str):
    """
    Retrieve a file record by its path.
    """
    try:
        file = db.query(MediaFile).filter(MediaFile.file_path == file_path).first()
        if file:
            logger.info(f"File found in database: {file_path}")
        else:
            logger.info(f"File not found in database: {file_path}")
        return file
    except Exception as e:
        logger.error(f"Error retrieving file by path {file_path}: {e}")
        raise

def add_or_update_file(db: Session, file_path: str, last_modified: datetime, duration: float, nsfw_score: float, codec: str, bitrate: int):
    """
    Add a new file record or update an existing one with codec and bitrate information.
    """
    try:
        file = get_file_by_path(db, file_path)
        if file:
            # Update existing record
            logger.info(f"Updating existing file record: {file_path}")
            file.last_modified = last_modified
            file.duration = duration
            file.nsfw_score = nsfw_score
            file.codec = codec
            file.bitrate = bitrate
        else:
            # Add a new record
            logger.info(f"Adding new file record: {file_path}")
            file = MediaFile(
                file_path=file_path,
                last_modified=last_modified,
                duration=duration,
                nsfw_score=nsfw_score,
                codec=codec,
                bitrate=bitrate
            )
            db.add(file)
        db.commit()
        logger.info(f"File record committed to database: {file_path}")
        return file
    except Exception as e:
        logger.error(f"Error adding or updating file {file_path}: {e}")
        db.rollback()
        raise