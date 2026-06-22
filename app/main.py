from fastapi import FastAPI
from app.core.config import settings
from app.core.database import engine
from app.models.models import Base
from app.api.v1.router import router as api_router
from app.services.scheduler import start_scheduler, shutdown_scheduler

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    shutdown_scheduler()

app.include_router(api_router)

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "message": "Backend engine is up, running, and all core routers are attached!"
    }