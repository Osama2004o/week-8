"""
FastAPI Dependencies
====================
Provides dependency injection helpers for knowledge base pipelines and configurations.
"""

from __future__ import annotations

from typing import Optional
from database.chroma_pipeline import KnowledgeBasePipeline

_shared_pipeline: Optional[KnowledgeBasePipeline] = None


def get_pipeline() -> KnowledgeBasePipeline:
    """
    Returns a shared singleton KnowledgeBasePipeline instance.
    Can be overridden in tests via app.dependency_overrides[get_pipeline].
    """
    global _shared_pipeline
    if _shared_pipeline is None:
        _shared_pipeline = KnowledgeBasePipeline()
    return _shared_pipeline


def set_pipeline(pipeline: Optional[KnowledgeBasePipeline]) -> None:
    """Explicitly set or reset the shared pipeline instance (useful in tests)."""
    global _shared_pipeline
    _shared_pipeline = pipeline
