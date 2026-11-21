"""
System & Health Routes
======================
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from api.dependencies import get_pipeline
from api.schemas import HealthResponse, StatsResponse
from config.settings import GROQ_STT_MODEL, LLM_MODEL, STT_PROVIDER
from database.chroma_pipeline import KnowledgeBasePipeline

router = APIRouter(tags=["System Operations"])


@router.get("/health", response_model=HealthResponse, summary="System Health Check")
def get_health() -> HealthResponse:
    """Returns the operational status, active LLM and STT configurations."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        llm_model=LLM_MODEL,
        stt_provider=STT_PROVIDER,
        stt_model=GROQ_STT_MODEL,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/stats", response_model=StatsResponse, summary="Knowledge Base Statistics")
def get_stats(pipeline: KnowledgeBasePipeline = Depends(get_pipeline)) -> StatsResponse:
    """Returns persistent ChromaDB collection stats and ingested document counts."""
    stats = pipeline.get_stats()
    return StatsResponse(
        collection_name=stats["collection_name"],
        persist_directory=stats["persist_directory"],
        total_chunks=stats["total_chunks"],
        unique_sources_count=stats["unique_sources_count"],
        sources=stats["sources"],
    )
