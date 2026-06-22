import logging
from app.core.database import SessionLocal, engine # 👈 Make sure engine is imported!
from app.models.models import Base                 # 👈 Make sure Base is imported!
from app.services.ingestion import IngestionService

logging.basicConfig(level=logging.INFO)

def initialize_system():
    # 🚀 Force SQLAlchemy to physically construct all tables in PostgreSQL if missing
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("📊 Processing master spreadsheet configuration...")
        
        # This reads the sheet and populates Postgres with your system source of truth
        result = IngestionService.import_tasks_from_excel(
            file_path="cutover_master.xlsx", 
            db=db
        )
        print(f"✅ Success! Database populated with {result['imported']} active tasks.")

    except Exception as e:
        print(f"❌ Ingestion failed: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    initialize_system()