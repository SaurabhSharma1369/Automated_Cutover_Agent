from app.core.database import engine
from app.models.models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_Reset")

def reset_database():
    logger.info("⚠️  Dropping all database tables...")
    # This deletes all tables defined in your models
    Base.metadata.drop_all(bind=engine)
    
    logger.info("✨ Recreating all database tables from scratch...")
    # This rebuilds them fresh
    Base.metadata.create_all(bind=engine)
    
    logger.info("✅ Database successfully reset and ready for new data!")

if __name__ == "__main__":
    # Add a quick safety prompt just in case!
    confirm = input("This will DELETE ALL DATA. Are you sure? (y/n): ")
    if confirm.lower() == 'y':
        reset_database()
    else:
        print("Database reset cancelled.")