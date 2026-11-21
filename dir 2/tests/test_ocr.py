"""
Unit & Integration Tests for Image Upload & OCR
===============================================
Tests image validation, Pillow preprocessing, RapidOCR line/confidence
formatting, LangChain loader routing, ChromaDB ingestion (file path and
uploaded bytes), and Answer Agent citation compatibility.
"""

from __future__ import annotations

import io
import os
import sys
from typing import List
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from PIL import Image, ImageDraw, ImageFont

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.ocr as ocr_module
from core.answer_tools import citation_formatter, source_formatter
from core.loaders import document_loader_branch
from core.ocr import (
    _format_ocr_lines,
    _normalize_ocr_items,
    extract_text_from_image,
    load_image_bytes_with_ocr,
    load_image_with_ocr,
    preprocess_image,
    validate_image_filename,
)
from database.chroma_pipeline import KnowledgeBasePipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image_bytes(
    fmt: str = "PNG",
    mode: str = "RGB",
    size: tuple[int, int] = (320, 120),
    text: str | None = None,
) -> bytes:
    """Create an in-memory image (optionally containing rendered text)."""
    bg = (255, 255, 255, 255) if mode == "RGBA" else (255, 255, 255) if mode == "RGB" else 255
    img = Image.new(mode, size, color=bg)
    if text:
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default(size=28)
        except TypeError:
            font = ImageFont.load_default()
        fill = (0, 0, 0, 255) if mode == "RGBA" else (0, 0, 0) if mode == "RGB" else 0
        draw.text((20, 35), text, fill=fill, font=font)

    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class _DeterministicEmbeddingFunction:
    """Lightweight ChromaDB-compatible embedding function for offline tests."""

    def name(self) -> str:
        return "deterministic-test-ef"

    def _embed(self, texts: List[str]) -> List[List[float]]:
        vectors = []
        for text in texts:
            lowered = text.lower()
            # Simple keyword-sensitive 8D vector so similarity search ranks matches reliably
            vec = [
                float(lowered.count("invoice")),
                float(lowered.count("total")),
                float(lowered.count("rag")),
                float(lowered.count("ocr")),
                float(lowered.count("420")),
                float(lowered.count("python")),
                float(len(lowered) % 17) / 17.0,
                1.0,
            ]
            vectors.append(vec)
        return vectors

    def __call__(self, input: List[str]) -> List[List[float]]:
        return self._embed(input)

    def embed_query(self, input: List[str]) -> List[List[float]]:
        return self._embed(input)


# ---------------------------------------------------------------------------
# Filename Validation & Preprocessing Tests
# ---------------------------------------------------------------------------


def test_validate_image_filename_sanitizes_and_accepts_supported_formats():
    assert validate_image_filename("notes.PNG") == "notes.PNG"
    assert validate_image_filename("../../folder/scan.jpeg") == "scan.jpeg"
    assert validate_image_filename(r"C:\fakepath\receipt.webp") == "receipt.webp"
    assert validate_image_filename("diagram.tiff") == "diagram.tiff"


@pytest.mark.parametrize("bad_name", ["", "   ", "document.pdf", "script.exe", "noext", "../.."])
def test_validate_image_filename_rejects_invalid_names(bad_name):
    with pytest.raises(ValueError):
        validate_image_filename(bad_name)


def test_preprocess_image_converts_rgba_and_grayscale_to_rgb():
    rgba_bytes = _make_image_bytes(fmt="PNG", mode="RGBA", size=(100, 50))
    rgb_img, info = preprocess_image(rgba_bytes)
    assert rgb_img.mode == "RGB"
    assert info == {"width": 100, "height": 50, "format": "PNG"}

    gray_bytes = _make_image_bytes(fmt="BMP", mode="L", size=(80, 40))
    gray_img, gray_info = preprocess_image(gray_bytes)
    assert gray_img.mode == "RGB"
    assert gray_info == {"width": 80, "height": 40, "format": "BMP"}


def test_preprocess_image_errors_on_invalid_missing_or_oversized(tmp_path):
    with pytest.raises(FileNotFoundError):
        preprocess_image(str(tmp_path / "missing.png"))

    with pytest.raises(ValueError, match="empty"):
        preprocess_image(b"")

    with pytest.raises(ValueError, match="not a valid"):
        preprocess_image(b"not-an-image")

    img_bytes = _make_image_bytes(fmt="PNG", size=(10, 10))
    with pytest.raises(ValueError, match="exceeds maximum size"):
        preprocess_image(img_bytes, max_size_mb=0)


# ---------------------------------------------------------------------------
# OCR Output Normalization & Line Ordering Tests
# ---------------------------------------------------------------------------


def test_normalize_ocr_items_handles_tuple_and_v2_objects():
    raw_tuple = (
        [[[[0, 0], [50, 0], [50, 20], [0, 20]], "Hello", 0.95]],
        [0.01, 0.01, 0.01],
    )
    normalized = _normalize_ocr_items(raw_tuple)
    assert len(normalized) == 1
    assert normalized[0][1] == "Hello"
    assert normalized[0][2] == pytest.approx(0.95)

    v2_obj = MagicMock()
    v2_obj.boxes = [[[0, 0], [40, 0], [40, 15], [0, 15]]]
    v2_obj.txts = ["World"]
    v2_obj.scores = [0.88]
    normalized_v2 = _normalize_ocr_items(v2_obj)
    assert len(normalized_v2) == 1
    assert normalized_v2[0][1] == "World"

    assert _normalize_ocr_items((None, [])) == []


def test_format_ocr_lines_filters_confidence_and_sorts_reading_order():
    items = [
        # Second line (y ~ 50)
        ([[[10, 45], [80, 45], [80, 65], [10, 65]], "Second line", 0.90]),
        # First line right half (y ~ 15, x = 120)
        ([[[120, 10], [200, 10], [200, 30], [120, 30]], "World", 0.92]),
        # First line left half (y ~ 15, x = 10)
        ([[[10, 10], [100, 10], [100, 30], [10, 30]], "Hello", 0.96]),
        # Low confidence noise (filtered out)
        ([[[10, 80], [60, 80], [60, 95], [10, 95]], "noise", 0.15]),
    ]

    text, avg_conf, line_count = _format_ocr_lines(items, min_confidence=0.3)
    assert text == "Hello World\nSecond line"
    assert line_count == 2
    assert avg_conf == pytest.approx((0.90 + 0.92 + 0.96) / 3, abs=1e-4)


# ---------------------------------------------------------------------------
# Extraction & Loader Integration Tests
# ---------------------------------------------------------------------------


def test_extract_and_load_image_with_mocked_engine(tmp_path):
    img_path = tmp_path / "receipt.png"
    img_bytes = _make_image_bytes(fmt="PNG", size=(200, 100))
    img_path.write_bytes(img_bytes)

    mock_engine = MagicMock(
        return_value=(
            [
                [[[10, 10], [180, 10], [180, 35], [10, 35]], "Invoice #1042", 0.97],
                [[[10, 50], [180, 50], [180, 75], [10, 75]], "Total: $420", 0.93],
            ],
            [0.02],
        )
    )

    with patch.object(ocr_module, "get_ocr_engine", return_value=mock_engine):
        result = extract_text_from_image(str(img_path))
        assert result["text"] == "Invoice #1042\nTotal: $420"
        assert result["line_count"] == 2
        assert result["confidence"] == pytest.approx(0.95)

        docs = load_image_with_ocr(str(img_path))
        assert len(docs) == 1
        assert docs[0].page_content == "Invoice #1042\nTotal: $420"
        assert docs[0].metadata["source"] == str(img_path)
        assert docs[0].metadata["source_type"] == "image_ocr"
        assert docs[0].metadata["ocr_engine"] == "rapidocr"

        byte_docs = load_image_bytes_with_ocr(img_bytes, "../../upload_receipt.png")
        assert len(byte_docs) == 1
        assert byte_docs[0].metadata["source"] == "upload_receipt.png"


def test_load_image_returns_empty_list_when_no_text_detected():
    img_bytes = _make_image_bytes(fmt="PNG", size=(100, 100))
    mock_engine = MagicMock(return_value=(None, []))

    with patch.object(ocr_module, "get_ocr_engine", return_value=mock_engine):
        docs = load_image_bytes_with_ocr(img_bytes, "blank.png")
        assert docs == []


def test_document_loader_branch_routes_images_and_keeps_pdf():
    fake_pdf_doc = [Document(page_content="PDF text", metadata={"source": "doc.pdf", "page": 0})]

    with (
        patch.object(ocr_module, "get_ocr_engine") as mock_ocr_getter,
        patch("core.loaders.PyMuPDFLoader") as mock_pdf_cls,
    ):
        mock_pdf_cls.return_value.load.return_value = fake_pdf_doc
        pdf_res = document_loader_branch.invoke("doc.pdf")
        assert pdf_res == fake_pdf_doc
        mock_pdf_cls.assert_called_once_with("doc.pdf")
        mock_ocr_getter.assert_not_called()

    # Verify image extensions route through document_loader_branch into OCR extraction
    mock_engine = MagicMock(
        return_value=([[[[0, 0], [50, 0], [50, 20], [0, 20]], "Diagram Text", 0.9]], [])
    )
    img_bytes = _make_image_bytes(fmt="JPEG", size=(120, 60))
    tmp_jpg = os.path.join(os.path.dirname(__file__), "_tmp_route_test.jpg")
    try:
        with open(tmp_jpg, "wb") as f:
            f.write(img_bytes)
        with patch.object(ocr_module, "get_ocr_engine", return_value=mock_engine):
            res = document_loader_branch.invoke(tmp_jpg)
            assert len(res) == 1
            assert res[0].page_content == "Diagram Text"
            assert res[0].metadata["source_type"] == "image_ocr"
    finally:
        if os.path.exists(tmp_jpg):
            os.remove(tmp_jpg)


# ---------------------------------------------------------------------------
# KnowledgeBasePipeline & Citation End-to-End Tests
# ---------------------------------------------------------------------------


def test_pipeline_ingest_uploaded_image_and_retrieve(tmp_path):
    db_dir = tmp_path / "chroma_test_db"
    upload_dir = tmp_path / "saved_uploads"
    img_bytes = _make_image_bytes(fmt="PNG", size=(300, 100))

    mock_engine = MagicMock(
        return_value=(
            [
                [[[10, 10], [260, 10], [260, 40], [10, 40]], "Invoice Total is 420 USD", 0.98],
            ],
            [0.01],
        )
    )

    with (
        patch(
            "database.chroma_pipeline.SentenceTransformerEmbeddingFunction",
            return_value=_DeterministicEmbeddingFunction(),
        ),
        patch.object(ocr_module, "get_ocr_engine", return_value=mock_engine),
    ):
        pipeline = KnowledgeBasePipeline(
            persist_directory=str(db_dir),
            collection_name="ocr_test_collection",
        )

        res = pipeline.ingest_uploaded_image(
            file_bytes=img_bytes,
            filename="../../invoice_march.png",
            save_to_disk=True,
            upload_dir=str(upload_dir),
        )

        assert res["status"] == "success"
        assert res["source_type"] == "image_ocr"
        assert res["chunks_ingested"] == 1
        assert res["ocr_confidence"] == pytest.approx(0.98)
        assert os.path.isfile(upload_dir / "invoice_march.png")

        # Also test in-memory upload (no disk write) + retrieval + citation formatting
        res_mem = pipeline.ingest_uploaded_image(
            file_bytes=img_bytes,
            filename="in_memory_note.png",
            save_to_disk=False,
        )
        assert res_mem["status"] == "success"
        assert res_mem["source"] == "in_memory_note.png"

        retrieved_docs = pipeline.retrieve_as_documents("What is the invoice total?", k=2)
        assert len(retrieved_docs) >= 1
        assert any("420" in doc.page_content for doc in retrieved_docs)
        assert all(doc.metadata["source_type"] == "image_ocr" for doc in retrieved_docs)

        # Verify Answer Agent citation/source formatters handle image_ocr Documents cleanly
        cited = citation_formatter.invoke(
            {
                "text": "The invoice total is 420 USD [E1].",
                "evidence_mapping": retrieved_docs,
                "style": "numeric",
            }
        )
        assert "[1]" in cited

        sources_block = source_formatter.invoke(
            {
                "sources": retrieved_docs,
                "style": "numbered",
                "cited_ids": ["E1"],
            }
        )
        assert "SOURCES:" in sources_block
        assert any(
            name in sources_block for name in ("invoice_march.png", "in_memory_note.png")
        )


def test_real_rapidocr_extracts_text_from_generated_image():
    """Verify real RapidOCR + Pillow extraction on a freshly rendered text image."""
    pytest.importorskip("rapidocr_onnxruntime")

    img_bytes = _make_image_bytes(
        fmt="PNG",
        mode="RGB",
        size=(520, 140),
        text="AGENTIC HYBRID RAG OCR 2026",
    )
    result = extract_text_from_image(img_bytes)

    extracted_upper = result["text"].upper()
    assert result["line_count"] >= 1
    assert result["confidence"] > 0.3
    assert "RAG" in extracted_upper or "OCR" in extracted_upper or "HYBRID" in extracted_upper
