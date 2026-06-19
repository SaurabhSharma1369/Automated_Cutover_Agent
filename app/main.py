from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.tasks import router as tasks_router
from app.api.v1.users import router as users_router  # Import the new router

app = FastAPI(title=settings.PROJECT_NAME)

# Register our v1 API endpoints
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")  # Attach the users routes

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "message": "Backend engine is up, running, and all core routers are attached!"
    }