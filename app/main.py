from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.core.database import engine
from app.models.models import Base
from app.api.v1.router import router as api_router
from app.workspace.services.scheduler_service import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC: Runs before the server starts taking requests ---
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    
    yield  # Your FastAPI web routes run here while the app is alive
    
    # --- SHUTDOWN LOGIC: Runs when you stop the container ---
    shutdown_scheduler()

# Initialize FastAPI with the lifespan context manager
app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.include_router(api_router)

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "message": "Backend engine is up, running, and all core routers are attached!"
    }