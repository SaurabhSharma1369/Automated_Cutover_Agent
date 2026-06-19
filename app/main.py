from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "message": "Backend engine is up and running!"
    }
@app.get("/add/{a}/{b}")
def add(a: int, b: int):
    return a + b