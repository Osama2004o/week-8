"""
Voice Query & Speech-To-Text (STT) Module
==========================================
Provides voice interaction capabilities:
    1. Transcribes spoken questions from audio files/streams using Groq Whisper
       (defaulting to model configured in .env, e.g. `whisper-large-v3-turbo`)
       with automatic fallback to local Faster-Whisper.
    2. Integrates voice query transcription directly with the Agentic RAG Orchestrator.
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union

from config.settings import (
    AUDIO_MAX_SIZE_MB,
    AUDIO_UPLOAD_DIR,
    GROQ_API_KEY,
    GROQ_STT_MODEL,
    STT_PROVIDER,
    SUPPORTED_AUDIO_EXTENSIONS,
)
from core.loaders import get_whisper_model
from core.orchestrator import run_orchestrator

_groq_client: Any = None


def get_groq_client(api_key: Optional[str] = None) -> Any:
    """Lazily initialize and cache the Groq client."""
    global _groq_client
    key = api_key or GROQ_API_KEY
    if not key:
        return None

    if _groq_client is None:
        try:
            from groq import Groq
            _groq_client = Groq(api_key=key)
        except ImportError:
            return None
    return _groq_client


def validate_audio_filename(filename: str) -> str:
    """Sanitize filename and ensure it has a supported audio extension."""
    if not filename or not isinstance(filename, str):
        raise ValueError("Audio filename must be a non-empty string.")

    safe_name = os.path.basename(filename.replace("\\", "/").strip())
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError(f"Invalid audio filename: '{filename}'.")

    ext = Path(safe_name).suffix.lower()
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise ValueError(
            f"Unsupported audio format '{ext}'. Supported formats: {supported}."
        )

    return safe_name


def validate_audio_size(size_bytes: int, max_mb: int = AUDIO_MAX_SIZE_MB) -> None:
    """Ensure audio size does not exceed the allowed limit."""
    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        size_mb = size_bytes / (1024 * 1024)
        raise ValueError(
            f"Audio file is too large ({size_mb:.2f}MB). Maximum allowed is {max_mb}MB."
        )
    if size_bytes == 0:
        raise ValueError("Audio file is empty (0 bytes).")


def _transcribe_with_groq(
    audio_file_or_tuple: Any,
    model: str,
    api_key: Optional[str] = None,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """Transcribe audio using Groq Whisper API."""
    client = get_groq_client(api_key=api_key)
    if client is None:
        raise RuntimeError("Groq API client is not configured or GROQ_API_KEY is missing.")

    kwargs: Dict[str, Any] = {
        "model": model,
        "file": audio_file_or_tuple,
        "response_format": "verbose_json",
    }
    if language:
        kwargs["language"] = language

    response = client.audio.transcriptions.create(**kwargs)
    text = (getattr(response, "text", "") or "").strip()
    detected_lang = getattr(response, "language", language or "en")
    duration = getattr(response, "duration", None)

    return {
        "text": text,
        "provider": "groq",
        "model": model,
        "language": detected_lang,
        "duration": duration,
    }


def _transcribe_with_faster_whisper(
    file_path: str,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """Transcribe audio locally using Faster-Whisper."""
    whisper_model = get_whisper_model()
    kwargs: Dict[str, Any] = {"beam_size": 5}
    if language:
        kwargs["language"] = language

    segments, info = whisper_model.transcribe(file_path, **kwargs)
    text = " ".join(segment.text.strip() for segment in segments).strip()

    return {
        "text": text,
        "provider": "faster-whisper",
        "model": "base",
        "language": getattr(info, "language", language or "en"),
        "duration": getattr(info, "duration", None),
    }


def transcribe_audio(
    audio_source: Union[str, bytes, BinaryIO],
    filename: str = "query.wav",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    language: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transcribes audio into text.

    Args:
        audio_source: Path to audio file, or raw bytes, or file-like binary stream.
        filename: Original filename (used for extension validation and Groq multipart payload).
        provider: 'groq' or 'faster-whisper' (defaults to STT_PROVIDER or 'groq').
        model: Whisper model name (defaults to GROQ_STT_MODEL in settings).
        language: Optional language code (e.g. 'en', 'ar').
        api_key: Optional Groq API key override.

    Returns:
        Dict with 'text', 'provider', 'model', 'language', 'duration'.
    """
    safe_name = validate_audio_filename(filename)
    chosen_provider = (provider or STT_PROVIDER or "groq").lower()
    chosen_model = model or GROQ_STT_MODEL or "whisper-large-v3-turbo"

    # Prepare bytes and temporary file if needed
    temp_path: Optional[str] = None
    audio_bytes: bytes

    try:
        if isinstance(audio_source, (str, Path)):
            file_path = str(audio_source)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            validate_audio_size(os.path.getsize(file_path))
            with open(file_path, "rb") as f:
                audio_bytes = f.read()
            temp_path = file_path
        elif isinstance(audio_source, bytes):
            validate_audio_size(len(audio_source))
            audio_bytes = audio_source
            suffix = Path(safe_name).suffix or ".wav"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                temp_path = tmp.name
        else:
            audio_bytes = audio_source.read()
            validate_audio_size(len(audio_bytes))
            suffix = Path(safe_name).suffix or ".wav"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                temp_path = tmp.name

        # If provider is groq, attempt Groq first
        if chosen_provider == "groq":
            try:
                # Pass tuple: (filename, bytes_stream)
                file_tuple = (safe_name, io.BytesIO(audio_bytes))
                return _transcribe_with_groq(
                    audio_file_or_tuple=file_tuple,
                    model=chosen_model,
                    api_key=api_key,
                    language=language,
                )
            except Exception as e:
                # If Groq key is missing or call fails, gracefully fallback to local faster-whisper
                print(f"[Voice] Groq transcription failed ({e}). Falling back to local Faster-Whisper...")
                return _transcribe_with_faster_whisper(temp_path, language=language)

        # Fallback / explicit local Faster-Whisper
        return _transcribe_with_faster_whisper(temp_path, language=language)

    finally:
        # If we created a temp file (and didn't receive an existing on-disk path), clean it up
        if temp_path and not isinstance(audio_source, (str, Path)) and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def run_voice_query(
    audio_source: Union[str, bytes, BinaryIO],
    pipeline: Any,
    filename: str = "query.wav",
    chat_history: Optional[List[Dict[str, str]]] = None,
    max_analyst_loops: int = 2,
    source_style: str = "numbered",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes an end-to-end Voice Query RAG workflow:
    1. Transcribes audio to text using Groq Whisper (or local fallback).
    2. Runs the 3-agent Orchestrator pipeline.
    3. Returns transcription info alongside the synthesized answer and sources.
    """
    # 1. Transcribe voice input
    transcription_result = transcribe_audio(
        audio_source=audio_source,
        filename=filename,
        provider=provider,
        model=model,
        language=language,
    )
    query_text = transcription_result.get("text", "").strip()
    if not query_text:
        raise ValueError("Could not extract speech from the provided audio or audio is silent.")

    # 2. Run Orchestrator with the transcribed query
    orchestrator_result = run_orchestrator(
        query=query_text,
        pipeline=pipeline,
        chat_history=chat_history,
        max_analyst_loops=max_analyst_loops,
        source_style=source_style,
    )

    # 3. Assemble unified response
    return {
        "transcription": transcription_result,
        "question": query_text,
        "answer": orchestrator_result["answer"],
        "sources": orchestrator_result["sources"],
        "evidence": orchestrator_result["evidence"],
        "analysis": orchestrator_result["analysis"],
        "analyst_tool_calls": orchestrator_result.get("analyst_tool_calls", []),
        "answer_tool_calls": orchestrator_result.get("answer_tool_calls", []),
        "execution_time_seconds": orchestrator_result.get("execution_time_seconds", 0.0),
    }
