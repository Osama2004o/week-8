"""
Voice Interaction & Speech-To-Text Routes
==========================================
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from api.dependencies import get_pipeline
from api.schemas import TranscriptionResponse, VoiceQueryResponse
from config.settings import GROQ_STT_MODEL, STT_PROVIDER
from core.voice import (
    run_voice_query,
    transcribe_audio,
    validate_audio_filename,
    validate_audio_size,
)
from database.chroma_pipeline import KnowledgeBasePipeline

router = APIRouter(prefix="/voice", tags=["Voice Query & Speech-To-Text"])


@router.post("/query", response_model=VoiceQueryResponse, summary="Execute Voice Query from Microphone/Audio")
async def voice_query_endpoint(
    audio_file: UploadFile = File(..., description="Recorded audio from microphone (.wav, .mp3, .webm, .ogg, .m4a)"),
    source_style: str = Form("numbered", description="Source citation style ('numbered', 'bullet', 'table')"),
    max_analyst_loops: int = Form(2, description="Max feedback loops for Analyst Agent"),
    language: Optional[str] = Form(None, description="Optional spoken language code (e.g. 'en', 'ar')"),
    model: Optional[str] = Form(None, description="Groq STT model override (default: whisper-large-v3-turbo)"),
    pipeline: KnowledgeBasePipeline = Depends(get_pipeline),
) -> VoiceQueryResponse:
    """
    Handles voice query interaction:
    1. Receives audio captured via user's microphone or uploaded audio file.
    2. Transcribes speech into text using Groq Whisper (model specified in .env).
    3. Runs the Agentic Hybrid RAG pipeline with the transcribed question.
    4. Returns both transcription details and the synthesized, cited answer.
    """
    filename = audio_file.filename or "recording.wav"
    try:
        safe_name = validate_audio_filename(filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    audio_bytes = await audio_file.read()
    try:
        validate_audio_size(len(audio_bytes))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        result = run_voice_query(
            audio_source=audio_bytes,
            pipeline=pipeline,
            filename=safe_name,
            source_style=source_style,
            max_analyst_loops=max_analyst_loops,
            language=language,
            model=model or GROQ_STT_MODEL,
        )

        transcription_info = result["transcription"]
        return VoiceQueryResponse(
            transcription=TranscriptionResponse(
                text=transcription_info.get("text", ""),
                provider=transcription_info.get("provider", STT_PROVIDER),
                model=transcription_info.get("model", GROQ_STT_MODEL),
                language=transcription_info.get("language"),
                duration=transcription_info.get("duration"),
            ),
            question=result.get("question", ""),
            answer=result.get("answer", ""),
            sources=result.get("sources", ""),
            evidence=result.get("evidence", []),
            analysis=result.get("analysis", ""),
            analyst_tool_calls=result.get("analyst_tool_calls", []),
            answer_tool_calls=result.get("answer_tool_calls", []),
            execution_time_seconds=result.get("execution_time_seconds", 0.0),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice query processing failed: {str(e)}",
        )


@router.post("/transcribe", response_model=TranscriptionResponse, summary="Transcribe Audio to Text (STT)")
async def voice_transcribe_endpoint(
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = Form(None, description="Optional language code (e.g. 'en', 'ar')"),
    model: Optional[str] = Form(None, description="Groq STT model override"),
) -> TranscriptionResponse:
    """
    Transcribes audio to text using Groq Whisper with fallback to Faster-Whisper.
    """
    filename = audio_file.filename or "recording.wav"
    try:
        safe_name = validate_audio_filename(filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    audio_bytes = await audio_file.read()
    try:
        validate_audio_size(len(audio_bytes))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        transcription_info = transcribe_audio(
            audio_source=audio_bytes,
            filename=safe_name,
            language=language,
            model=model or GROQ_STT_MODEL,
        )
        return TranscriptionResponse(
            text=transcription_info.get("text", ""),
            provider=transcription_info.get("provider", STT_PROVIDER),
            model=transcription_info.get("model", GROQ_STT_MODEL),
            language=transcription_info.get("language"),
            duration=transcription_info.get("duration"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio transcription failed: {str(e)}",
        )
