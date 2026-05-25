"""TransitSight - Main Application Entry Point.

A web-based smart public transport crowd predictor.
Integrates data.gov.my APIs with Google AI Studio (Gemini API).
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.database import init_db
from app.services.transit_service import TransitDataService
from app.routers import prediction, feedback, admin, authority
import os

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Smart public transport crowd predictor for Malaysian transit",
)

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_db()
    TransitDataService.seed_default_routes()

# Mount API routers
app.include_router(prediction.router)
app.include_router(feedback.router)
app.include_router(admin.router)
app.include_router(authority.router)

# Serve static frontend files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(static_dir, "index.html"))

    @app.get("/dashboard")
    async def serve_dashboard():
        return FileResponse(os.path.join(static_dir, "dashboard.html"))

    @app.get("/route")
    async def serve_route():
        return FileResponse(os.path.join(static_dir, "route.html"))

    @app.get("/admin")
    async def serve_admin():
        return FileResponse(os.path.join(static_dir, "admin.html"))

    @app.get("/authority")
    async def serve_authority():
        return FileResponse(os.path.join(static_dir, "authority.html"))

    @app.get("/profile")
    async def serve_profile():
        return FileResponse(os.path.join(static_dir, "profile.html"))
