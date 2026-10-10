from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.router import api_router
from app.core.config import settings

# Production build of the React UI (created by `npm run build` in frontend/)
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

# Create the main FastAPI app instance
app = FastAPI(
    title="AI Database Agent",
    description="An intelligent agent for interacting with databases using natural language",
    version="1.0.0"
)

# Include the main router in the app with the prefix /api/v1
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
def read_root():
    """
    Root endpoint that shows the service health status.
    """
    return {"status": "ok", "message": "AI Database Agent is running!"}

# Serve the Persian chat UI at /ui, once it has been built
if FRONTEND_DIST.is_dir():
    app.mount("/ui", StaticFiles(directory=FRONTEND_DIST, html=True), name="ui")
