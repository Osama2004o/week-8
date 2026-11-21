import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_pipeline
from api.main import app


@pytest.fixture
def mock_pipeline():
    mock = MagicMock()
    mock.get_stats.return_value = {
        "collection_name": "test_collection",
        "persist_directory": "/tmp/chroma",
        "total_chunks": 42,
        "unique_sources_count": 2,
        "sources": ["paper.pdf", "notes.docx"],
    }
    mock.ingest.return_value = {
        "status": "success",
        "source": "sample.pdf",
        "chunks_ingested": 5,
        "message": "Successfully ingested 5 chunks.",
    }
    mock.ingest_batch.return_value = [
        {"status": "success", "source": "doc1.txt", "chunks_ingested": 2},
        {"status": "success", "source": "doc2.txt", "chunks_ingested": 3},
    ]
    mock.ingest_image_bytes.return_value = {
        "status": "success",
        "source": "image.png",
        "chunks_ingested": 1,
        "extracted_text_length": 150,
        "ocr_confidence": 0.95,
    }
    mock.list_sources.return_value = ["paper.pdf", "notes.docx"]
    mock.delete_source.return_value = {
        "status": "success",
        "deleted_source": "paper.pdf",
        "remaining_chunks": 20,
    }
    mock.clear.return_value = {
        "status": "success",
        "message": "Knowledge base cleared.",
    }
    return mock


@pytest.fixture
def client(mock_pipeline):
    app.dependency_overrides[get_pipeline] = lambda: mock_pipeline
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ── System Endpoints Tests ──

def test_health_endpoints(client):
    res1 = client.get("/health")
    assert res1.status_code == 200
    assert res1.json()["status"] == "healthy"

    res2 = client.get("/api/v1/health")
    assert res2.status_code == 200
    data = res2.json()
    assert data["status"] == "healthy"
    assert "llm_model" in data
    assert "stt_model" in data


def test_stats_endpoint(client, mock_pipeline):
    res = client.get("/api/v1/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_chunks"] == 42
    assert data["sources"] == ["paper.pdf", "notes.docx"]
    mock_pipeline.get_stats.assert_called_once()


def test_ui_endpoints(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Agentic Hybrid RAG" in res.text

    res_ui = client.get("/ui")
    assert res_ui.status_code == 200


# ── Document & Ingestion Endpoints Tests ──

def test_ingest_path(client, mock_pipeline):
    res = client.post("/api/v1/documents/ingest-path", json={"source": "wiki:AI"})
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    mock_pipeline.ingest.assert_called_with("wiki:AI")


def test_ingest_batch(client, mock_pipeline):
    res = client.post("/api/v1/documents/ingest-batch", json={"sources": ["a.txt", "b.txt"]})
    assert res.status_code == 200
    data = res.json()
    assert data["total_sources"] == 2
    assert len(data["results"]) == 2


def test_ingest_file_document(client, mock_pipeline):
    file_content = b"Sample document content"
    res = client.post(
        "/api/v1/documents/ingest-file",
        files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_ingest_image_ocr(client, mock_pipeline):
    image_content = b"fake_png_data"
    res = client.post(
        "/api/v1/documents/ingest-image",
        files={"file": ("test.png", io.BytesIO(image_content), "image/png")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["ocr_confidence"] == 0.95
    mock_pipeline.ingest_image_bytes.assert_called_once()


def test_list_and_delete_documents(client, mock_pipeline):
    # List
    res = client.get("/api/v1/documents")
    assert res.status_code == 200
    assert res.json()["total_sources"] == 2

    # Delete single source
    res_del = client.delete("/api/v1/documents/paper.pdf")
    assert res_del.status_code == 200
    assert res_del.json()["deleted_source"] == "paper.pdf"

    # Clear all
    res_clear = client.delete("/api/v1/documents")
    assert res_clear.status_code == 200
    assert res_clear.json()["status"] == "success"


# ── Query Endpoint Tests ──

@patch("api.routes.query.run_orchestrator")
def test_query_endpoint_success(mock_orchestrator, client):
    mock_orchestrator.return_value = {
        "question": "What is RAG?",
        "answer": "RAG is retrieval-augmented generation [1].",
        "sources": "[1] doc.pdf, page 1",
        "evidence": [{"chunk_id": "c1", "content": "text"}],
        "analysis": "Analyzed successfully",
        "analyst_tool_calls": [],
        "answer_tool_calls": [],
        "execution_time_seconds": 1.2,
    }

    res = client.post(
        "/api/v1/query",
        json={"query": "What is RAG?", "source_style": "numbered", "max_analyst_loops": 2},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["question"] == "What is RAG?"
    assert "RAG is retrieval-augmented generation" in data["answer"]
    assert data["sources"] == "[1] doc.pdf, page 1"
    assert data["execution_time_seconds"] == 1.2


@patch("api.routes.query.run_orchestrator")
def test_query_endpoint_with_document_objects(mock_orchestrator, client):
    from langchain_core.documents import Document
    mock_orchestrator.return_value = {
        "question": "What is RAG?",
        "answer": "Answer with citations [1].",
        "sources": "[1] test.pdf, page 1",
        "evidence": [
            Document(page_content="Text from chunk 1", metadata={"source": "test.pdf", "page": 1}),
            Document(page_content="Text from chunk 2", metadata={"source": "test.pdf", "page": 2}),
        ],
        "analysis": "Analyzed successfully",
        "analyst_tool_calls": [],
        "answer_tool_calls": [],
        "execution_time_seconds": 1.0,
    }

    res = client.post("/api/v1/query", json={"query": "What is RAG?"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["evidence"]) == 2
    assert data["evidence"][0]["content"] == "Text from chunk 1"
    assert data["evidence"][0]["metadata"]["source"] == "test.pdf"


def test_query_endpoint_empty_query(client):
    res = client.post("/api/v1/query", json={"query": "   "})
    assert res.status_code == 400


# ── Voice Endpoint Tests ──

@patch("api.routes.voice.transcribe_audio")
def test_voice_transcribe_endpoint(mock_transcribe, client):
    mock_transcribe.return_value = {
        "text": "How does vector search work?",
        "provider": "groq",
        "model": "whisper-large-v3-turbo",
        "language": "en",
        "duration": 2.5,
    }
    dummy_wav = b"RIFF....WAVEfmt ...."
    res = client.post(
        "/api/v1/voice/transcribe",
        files={"audio_file": ("test.wav", io.BytesIO(dummy_wav), "audio/wav")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["text"] == "How does vector search work?"
    assert data["provider"] == "groq"
    assert data["model"] == "whisper-large-v3-turbo"


@patch("api.routes.voice.run_voice_query")
def test_voice_query_endpoint(mock_run_voice, client):
    mock_run_voice.return_value = {
        "transcription": {
            "text": "Explain hybrid retrieval",
            "provider": "groq",
            "model": "whisper-large-v3-turbo",
            "language": "en",
            "duration": 3.0,
        },
        "question": "Explain hybrid retrieval",
        "answer": "Hybrid retrieval combines BM25 and vector search [1].",
        "sources": "[1] hybrid_rag.pdf, page 2",
        "evidence": [{"chunk_id": "c2", "content": "BM25 + Chroma"}],
        "analysis": "Hybrid search performed",
        "analyst_tool_calls": [],
        "answer_tool_calls": [],
        "execution_time_seconds": 2.1,
    }
    dummy_wav = b"RIFF....WAVEfmt ...."
    res = client.post(
        "/api/v1/voice/query",
        files={"audio_file": ("mic.webm", io.BytesIO(dummy_wav), "audio/webm")},
        data={"source_style": "numbered", "max_analyst_loops": 2},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["transcription"]["text"] == "Explain hybrid retrieval"
    assert data["transcription"]["model"] == "whisper-large-v3-turbo"
    assert data["question"] == "Explain hybrid retrieval"
    assert "Hybrid retrieval combines BM25" in data["answer"]


@patch("api.routes.voice.run_voice_query")
def test_voice_query_with_document_objects(mock_run_voice, client):
    from langchain_core.documents import Document
    mock_run_voice.return_value = {
        "transcription": {
            "text": "Voice test",
            "provider": "groq",
            "model": "whisper-large-v3-turbo",
            "language": "en",
            "duration": 1.0,
        },
        "question": "Voice test",
        "answer": "Voice answer [1].",
        "sources": "[1] audio.wav",
        "evidence": [
            Document(page_content="Voice evidence chunk", metadata={"source": "audio.wav"}),
        ],
        "analysis": "Analysis",
        "analyst_tool_calls": [],
        "answer_tool_calls": [],
        "execution_time_seconds": 0.8,
    }
    dummy_wav = b"RIFF....WAVEfmt ...."
    res = client.post(
        "/api/v1/voice/query",
        files={"audio_file": ("mic.webm", io.BytesIO(dummy_wav), "audio/webm")},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["evidence"]) == 1
    assert data["evidence"][0]["content"] == "Voice evidence chunk"
    assert data["evidence"][0]["metadata"]["source"] == "audio.wav"


def test_voice_query_invalid_format(client):
    res = client.post(
        "/api/v1/voice/query",
        files={"audio_file": ("malicious.exe", io.BytesIO(b"data"), "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "Unsupported audio format" in res.json()["detail"]


# ── Report Endpoint Tests ──

@patch("api.routes.reports.run_report_agent")
def test_reports_generate_and_download(mock_report_agent, client, tmp_path):
    # Mock report agent output
    dummy_pdf = tmp_path / "report_test.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 test pdf content")

    mock_report_agent.return_value = {
        "pdf_path": str(dummy_pdf),
        "summary": "Report built successfully",
        "tool_calls": [],
    }

    res = client.post(
        "/api/v1/reports/generate",
        json={
            "result": {
                "question": "Q",
                "answer": "A",
                "analysis": "Analysis",
                "sources": "Sources",
            },
            "instructions": "navy style",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["download_url"].startswith("/api/v1/reports/download/")
