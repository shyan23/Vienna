"""FastAPI application entry point."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.routes.api import router

load_dotenv()

app = FastAPI(title="Vienna Traffic Router", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# Serve the frontend static files. In development the public/ folder may not
# exist yet; mount only if present so uvicorn still boots during early sprints.
_public_dir = Path(__file__).resolve().parent.parent / "public"
if _public_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_public_dir), html=True), name="static")


@app.get("/_meta")
async def meta():
    return {
        "app": "vienna-traffic-router",
        "version": "1.0.0",
        "graph_path": os.getenv("VIENNA_GRAPH_PATH", "data/vienna_graph.json"),
    }
