"""
Knowledge Base & Document Ingestion Routes
==========================================
"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.dependencies import get_pipeline
from api.schemas import (
    BatchIngestResponse,
    ClearResponse,
    DeleteSourceResponse,
    DocumentListResponse,
    IngestBatchRequest,
    IngestPathRequest,
    IngestResponse,
)
from config.settings import SUPPORTED_IMAGE_EXTENSIONS
from database.chroma_pipeline import KnowledgeBasePipeline

router = APIRouter(prefix="/documents", tags=["Knowledge Base & Ingestion"])


@router.post("/ingest-path", response_model=IngestResponse, summary="Ingest Document by Path or URL")
def ingest_path(
    payload: IngestPathRequest,
    pipeline: KnowledgeBasePipeline = Depends(get_pipeline),
) -> IngestResponse:
    """
    Ingests a document from a local file path, web URL, or Wikipedia topic ('wiki:Topic').
    """
    try:
        result = pipeline.ingest(payload.source)
        return IngestResponse(
            status=result.get("status", "success"),
            source=result.get("source", payload.source),
            chunks_ingested=result.get("chunks_ingested", 0),
            message=result.get("message"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to ingest source: {str(e)}",
        )


@router.post("/ingest-batch", response_model=BatchIngestResponse, summary="Ingest Batch of Sources")
def ingest_batch(
    payload: IngestBatchRequest,
    pipeline: KnowledgeBasePipeline = Depends(get_pipeline),
) -> BatchIngestResponse:
    """Ingests multiple document paths or URLs in a single batch."""
    try:
        raw_results = pipeline.ingest_batch(payload.sources)
        results = [
            IngestResponse(
                status=r.get("status", "success"),
                source=r.get("source", ""),
                chunks_ingested=r.get("chunks_ingested", 0),
                message=r.get("message"),
            )
            for r in raw_results
        ]
        return BatchIngestResponse(total_sources=len(results), results=results)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to ingest batch: {str(e)}",
        )


@router.post("/ingest-file", response_model=IngestResponse, summary="Upload & Ingest Document File")
async def ingest_file(
    file: UploadFile = File(..., description="Document file (.pdf, .docx, .txt, .pptx, etc.)"),
    pipeline: KnowledgeBasePipeline = Depends(get_pipeline),
) -> IngestResponse:
    """
    Uploads and ingests a document into the ChromaDB vector database.
    Supports PDF, DOCX, TXT, PPTX, WAV, and OCR-capable images.
    """
    filename = file.filename or "uploaded_document"
    _, ext = os.path.splitext(filename.lower())

    # Read uploaded bytes
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    # If it is an image, route through OCR bytes ingestion directly
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        try:
            result = pipeline.ingest_image_bytes(contents, filename=filename)
            return IngestResponse(
                status=result.get("status", "success"),
                source=result.get("source", filename),
                chunks_ingested=result.get("chunks_ingested", 0),
                message=result.get("message"),
                extracted_text_length=result.get("extracted_text_length"),
                ocr_confidence=result.get("ocr_confidence"),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OCR ingestion failed: {str(e)}",
            )

    # For other documents, save to a temp file and ingest
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = pipeline.ingest(tmp_path)
        # Fix source name to reflect original filename
        return IngestResponse(
            status=result.get("status", "success"),
            source=filename,
            chunks_ingested=result.get("chunks_ingested", 0),
            message=result.get("message"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document ingestion failed: {str(e)}",
        )
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@router.post("/ingest-image", response_model=IngestResponse, summary="Upload Image for OCR Ingestion")
async def ingest_image(
    file: UploadFile = File(..., description="Image file (.png, .jpg, .jpeg, .webp, .bmp, .tiff)"),
    pipeline: KnowledgeBasePipeline = Depends(get_pipeline),
) -> IngestResponse:
    """
    Uploads an image containing text, extracts text via RapidOCR, and stores it in the vector DB.
    """
    filename = file.filename or "image.png"
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    try:
        result = pipeline.ingest_image_bytes(contents, filename=filename)
        return IngestResponse(
            status=result.get("status", "success"),
            source=result.get("source", filename),
            chunks_ingested=result.get("chunks_ingested", 0),
            message=result.get("message"),
            extracted_text_length=result.get("extracted_text_length"),
            ocr_confidence=result.get("ocr_confidence"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OCR processing failed: {str(e)}",
        )


@router.get("", response_model=DocumentListResponse, summary="List All Ingested Documents")
def list_documents(
    pipeline: KnowledgeBasePipeline = Depends(get_pipeline),
) -> DocumentListResponse:
    """Returns a list of all distinct document sources indexed in the knowledge base."""
    sources = pipeline.list_sources()
    return DocumentListResponse(total_sources=len(sources), sources=sources)


@router.delete("/{source:path}", response_model=DeleteSourceResponse, summary="Delete Document by Source Identifier")
def delete_document(
    source: str,
    pipeline: KnowledgeBasePipeline = Depends(get_pipeline),
) -> DeleteSourceResponse:
    """Deletes all chunks associated with a specific document source."""
    result = pipeline.delete_source(source)
    return DeleteSourceResponse(
        status=result.get("status", "success"),
        deleted_source=result.get("deleted_source", source),
        remaining_chunks=result.get("remaining_chunks", 0),
    )


@router.delete("", response_model=ClearResponse, summary="Clear Entire Knowledge Base")
def clear_knowledge_base(
    pipeline: KnowledgeBasePipeline = Depends(get_pipeline),
) -> ClearResponse:
    """Removes all indexed chunks and empties the knowledge base."""
    result = pipeline.clear()
    return ClearResponse(
        status=result.get("status", "success"),
        message=result.get("message", "Knowledge base cleared."),
    )
