"""
RAG Query Routes
================
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_pipeline
from api.schemas import QueryRequest, QueryResponse
from core.orchestrator import run_orchestrator
from database.chroma_pipeline import KnowledgeBasePipeline

router = APIRouter(prefix="/query", tags=["Agentic RAG Query"])


@router.post("", response_model=QueryResponse, summary="Execute 3-Agent Hybrid RAG Query")
def execute_query(
    payload: QueryRequest,
    pipeline: KnowledgeBasePipeline = Depends(get_pipeline),
) -> QueryResponse:
    """
    Executes the complete Agentic Hybrid RAG workflow:
    1. Retriever Agent (LangGraph hybrid semantic + BM25 search + reranking)
    2. Analyst Agent (Numerical reasoning, table extraction, and evidence feedback loop)
    3. Answer Agent (Source citation formatting and verification)
    """
    clean_query = payload.query.strip()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty.",
        )

    try:
        result = run_orchestrator(
            query=clean_query,
            pipeline=pipeline,
            chat_history=payload.chat_history,
            max_analyst_loops=payload.max_analyst_loops or 2,
            source_style=payload.source_style or "numbered",
        )
        return QueryResponse(
            question=result.get("question", clean_query),
            answer=result.get("answer", ""),
            sources=result.get("sources", ""),
            evidence=result.get("evidence", []),
            analysis=result.get("analysis", ""),
            analyst_tool_calls=result.get("analyst_tool_calls", []),
            answer_tool_calls=result.get("answer_tool_calls", []),
            execution_time_seconds=result.get("execution_time_seconds", 0.0),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agentic query execution failed: {str(e)}",
        )
