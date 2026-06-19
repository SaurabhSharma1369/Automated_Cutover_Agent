from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 1. Create the SQLAlchemy engine using the database connection string from your config
# The connect_args={"check_same_thread": False} is only required if using SQLite,
# but for PostgreSQL, we can keep the setup clean and robust.
engine = create_engine(settings.DATABASE_URL)

# 2. Create a session factory instance 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Create a dependency wrapper function for FastAPI's dependency injection layer
def get_db():
    """
    Creates a standalone database transaction session for a single API request,
    and reliably closes it once the request lifecycle terminates.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()