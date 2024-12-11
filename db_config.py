from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database configuration
DATABASE_URL = "sqlite:///nsfw_plex.db"

# Create engine and session
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Base for ORM models
Base = declarative_base()