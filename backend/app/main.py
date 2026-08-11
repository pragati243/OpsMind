"""FastAPI application assembly."""

from fastapi import FastAPI

from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router

app = FastAPI(title="Keystone")
app.include_router(health_router)
app.include_router(chat_router)
