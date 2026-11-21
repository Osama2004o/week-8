import io
from unittest.mock import MagicMock, patch
import pytest

from core.voice import (
    transcribe_audio,
    validate_audio_filename,
    validate_audio_size,
    run_voice_query,
)


def test_validate_audio_filename_valid():
    assert validate_audio_filename("recording.wav") == "recording.wav"
    assert validate_audio_filename("path/to/my_audio.mp3") == "my_audio.mp3"
    assert validate_audio_filename("audio.webm") == "audio.webm"
    assert validate_audio_filename("speech.ogg") == "speech.ogg"
    assert validate_audio_filename("voice.m4a") == "voice.m4a"


def test_validate_audio_filename_invalid_extension():
    with pytest.raises(ValueError, match="Unsupported audio format"):
        validate_audio_filename("notes.pdf")

    with pytest.raises(ValueError, match="Unsupported audio format"):
        validate_audio_filename("script.py")


def test_validate_audio_filename_traversal():
    assert validate_audio_filename("../../../recording.wav") == "recording.wav"
    assert validate_audio_filename("C:\\Users\\test\\audio.wav") == "audio.wav"


def test_validate_audio_size():
    validate_audio_size(1024)  # 1 KB valid
    validate_audio_size(24 * 1024 * 1024)  # 24 MB valid

    with pytest.raises(ValueError, match="empty"):
        validate_audio_size(0)

    with pytest.raises(ValueError, match="too large"):
        validate_audio_size(26 * 1024 * 1024, max_mb=25)


@patch("core.voice.get_groq_client")
def test_transcribe_audio_groq_success(mock_get_client):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "What is agentic RAG?"
    mock_resp.language = "en"
    mock_resp.duration = 3.5
    mock_client.audio.transcriptions.create.return_value = mock_resp
    mock_get_client.return_value = mock_client

    dummy_audio = b"dummy_audio_bytes"
    result = transcribe_audio(
        audio_source=dummy_audio,
        filename="query.wav",
        provider="groq",
        model="whisper-large-v3-turbo",
    )

    assert result["text"] == "What is agentic RAG?"
    assert result["provider"] == "groq"
    assert result["model"] == "whisper-large-v3-turbo"
    assert result["language"] == "en"


@patch("core.voice.get_groq_client")
@patch("core.voice._transcribe_with_faster_whisper")
def test_transcribe_audio_fallback_on_groq_failure(mock_fallback, mock_get_client):
    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.side_effect = RuntimeError("Groq rate limit")
    mock_get_client.return_value = mock_client

    mock_fallback.return_value = {
        "text": "Fallback transcribed text",
        "provider": "faster-whisper",
        "model": "base",
        "language": "en",
        "duration": 2.0,
    }

    dummy_audio = b"dummy_audio_bytes"
    result = transcribe_audio(
        audio_source=dummy_audio,
        filename="query.wav",
        provider="groq",
    )

    assert result["provider"] == "faster-whisper"
    assert result["text"] == "Fallback transcribed text"
    mock_fallback.assert_called_once()


@patch("core.voice.transcribe_audio")
@patch("core.voice.run_orchestrator")
def test_run_voice_query_success(mock_orchestrator, mock_transcribe):
    mock_transcribe.return_value = {
        "text": "Tell me about RAG architecture",
        "provider": "groq",
        "model": "whisper-large-v3-turbo",
        "language": "en",
    }
    mock_orchestrator.return_value = {
        "question": "Tell me about RAG architecture",
        "answer": "RAG combines retrieval with LLM synthesis [1].",
        "sources": "[1] doc.pdf, page 1",
        "evidence": [{"chunk_id": "c1", "content": "RAG evidence"}],
        "analysis": "Analyzed successfully",
        "analyst_tool_calls": [],
        "answer_tool_calls": [],
        "execution_time_seconds": 1.5,
    }

    pipeline = MagicMock()
    result = run_voice_query(
        audio_source=b"test_audio",
        pipeline=pipeline,
        filename="question.wav",
    )

    assert result["question"] == "Tell me about RAG architecture"
    assert "RAG combines retrieval" in result["answer"]
    assert result["transcription"]["model"] == "whisper-large-v3-turbo"
    mock_orchestrator.assert_called_once_with(
        query="Tell me about RAG architecture",
        pipeline=pipeline,
        chat_history=None,
        max_analyst_loops=2,
        source_style="numbered",
    )


@patch("core.voice.transcribe_audio")
def test_run_voice_query_silent_audio(mock_transcribe):
    mock_transcribe.return_value = {
        "text": "   ",
        "provider": "groq",
        "model": "whisper-large-v3-turbo",
    }
    with pytest.raises(ValueError, match="Could not extract speech"):
        run_voice_query(audio_source=b"silent_audio", pipeline=MagicMock())
