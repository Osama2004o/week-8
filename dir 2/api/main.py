"""
FastAPI Application Entry Point
===============================
Deploys the Agentic Hybrid RAG system as a production-grade FastAPI application
with voice query integration (Groq Whisper), OCR processing, and multi-agent workflows.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from api.dependencies import get_pipeline
from api.routes import documents, query, reports, system, voice
from config.settings import API_HOST, API_PORT, GROQ_STT_MODEL, LLM_MODEL, STT_PROVIDER


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for pre-warming dependencies."""
    print("=" * 60)
    print("  🚀 Starting Agentic RAG & Voice AI Platform")
    print(f"  • LLM Model: {LLM_MODEL}")
    print(f"  • STT Provider: {STT_PROVIDER} ({GROQ_STT_MODEL})")
    print("=" * 60)
    # Eagerly initialize or verify persistent ChromaDB pipeline
    try:
        pipeline = get_pipeline()
        stats = pipeline.get_stats()
        print(f"  ✓ Knowledge Base initialized ({stats['total_chunks']} chunks stored)")
    except Exception as e:
        print(f"  ⚠ Knowledge base warning on startup: {e}")
    yield
    print("  🛑 Shutting down Agentic RAG Platform...")


app = FastAPI(
    title="Agentic Hybrid RAG & Voice AI Platform",
    description=(
        "Production-ready FastAPI deployment for Agentic Hybrid RAG.\n\n"
        "Features:\n"
        "- **Multi-Agent RAG Orchestrator**: 3-agent pipeline (Retriever, Analyst, Answer).\n"
        "- **Voice Query Integration**: Real-time microphone audio transcription with Groq Whisper.\n"
        "- **Knowledge Base & Ingestion**: Format-aware loaders for PDF, DOCX, TXT, PPTX, WAV, Web, Wikipedia.\n"
        "- **Image OCR Processing**: RapidOCR image text extraction into ChromaDB.\n"
        "- **Report Generator Agent**: LangChain tool-calling agent producing executive PDF reports."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
api_v1_prefix = "/api/v1"
app.include_router(system.router, prefix=api_v1_prefix)
app.include_router(documents.router, prefix=api_v1_prefix)
app.include_router(query.router, prefix=api_v1_prefix)
app.include_router(voice.router, prefix=api_v1_prefix)
app.include_router(reports.router, prefix=api_v1_prefix)

# Top-level health convenience route
@app.get("/health", tags=["System Operations"], include_in_schema=False)
def root_health():
    return system.get_health()


# Static web UI for interactive browser experience
STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


@app.get("/", response_class=HTMLResponse, tags=["Web Interface"], include_in_schema=False)
@app.get("/ui", response_class=HTMLResponse, tags=["Web Interface"], include_in_schema=False)
def serve_ui():
    """Serves the interactive single-page application for voice & text queries."""
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return HTMLResponse("<h2>Agentic RAG & Voice Platform is running. Visit <a href='/docs'>/docs</a>.</h2>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=True)
