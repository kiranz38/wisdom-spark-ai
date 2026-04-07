"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.api.routes.wisdom import router as wisdom_router
from src.api.routes.crawler import router as crawler_router
from src.mcp_server.server import mcp

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "An open wisdom repository feeding AI the distilled wisdom of humanity's "
        "philosophical traditions — Stoicism, Buddhism, Vedanta, Ubuntu, Taoism, "
        "Sufism, Jainism, Indigenous wisdom, Existentialism, and Positive Psychology."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wisdom_router, prefix=settings.api_prefix)
app.include_router(crawler_router, prefix=settings.api_prefix)

# Mount MCP server for AI agent consumption
app.mount("/mcp", mcp.streamable_http_app())


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": (
            "An open wisdom repository feeding AI the distilled wisdom of "
            "humanity's philosophical traditions."
        ),
        "traditions": [
            "Stoicism", "Buddhism", "Advaita Vedanta", "Ubuntu", "Taoism",
            "Confucianism", "Sufism", "Jainism", "Indigenous Wisdom",
            "Existentialism", "Positive Psychology", "Islamic Ethics",
            "Jewish Wisdom", "Sikh Philosophy", "Greek Philosophy",
            "African Proverbial Wisdom", "Christian Mysticism",
        ],
        "endpoints": {
            "api": f"{settings.api_prefix}/wisdom/",
            "crawler_stats": f"{settings.api_prefix}/crawler/stats",
            "mcp": "/mcp/",
            "docs": "/docs",
            "health": "/health",
        },
    }
