"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from common.db import engine, Base
from services.claims import routes as claims_routes
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.warning(f"Database table creation note: {e}")

app = FastAPI(
    title="RCM Workflow Engine",
    description="Async, event-driven backend for medical claims lifecycle management",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(claims_routes.router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "RCM Workflow Engine",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

