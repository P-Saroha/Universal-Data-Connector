"""Universal Data Connector — FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, data
from app.routers.llm import router as llm_router
from app.utils.logging import configure_logging

configure_logging(settings.LOG_LEVEL)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A unified data connector that exposes CRM, support-ticket, and "
        "analytics data through voice-optimised endpoints designed for "
        "LLM function calling."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow everything in dev; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(data.router)
app.include_router(llm_router)
