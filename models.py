from sqlalchemy import Column, String, Integer, Float, DateTime
from datetime import datetime
from db_config import Base

class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, nullable=False)
    last_modified = Column(DateTime, nullable=False, default=datetime.utcnow)
    duration = Column(Float, nullable=True)  # Duration in seconds
    nsfw_score = Column(Float, nullable=True)  # NSFW detection score
    codec = Column(String, nullable=True)  # Video codec
    bitrate = Column(Integer, nullable=True)  # Bitrate in kbps

    def __repr__(self):
        return f"<MediaFile(id={self.id}, file_path={self.file_path}, last_modified={self.last_modified}, duration={self.duration}, nsfw_score={self.nsfw_score}, codec={self.codec}, bitrate={self.bitrate})>"