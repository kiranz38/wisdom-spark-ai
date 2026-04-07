"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.api.routes.wisdom import router as wisdom_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "An open wisdom repository feeding AI the distilled wisdom of humanity's "
        "philosophical traditions — Stoicism, Buddhism, Vedanta, Ubuntu, Taoism, and more."
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


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}
