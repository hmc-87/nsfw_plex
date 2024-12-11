from db_config import Base, engine
from models import MediaFile

def init_db():
    # Create the tables in the database
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()