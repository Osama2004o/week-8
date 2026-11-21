"""
Image Upload & OCR Loader
=========================
Extracts text from uploaded or on-disk images using Pillow preprocessing and
lazily initialized RapidOCR (`rapidocr-onnxruntime`), returning LangChain
Document objects ready for chunking, embedding, and hybrid RAG retrieval.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

import numpy as np
from langchain_core.documents import Document
from PIL import Image, ImageOps, UnidentifiedImageError

from config.settings import (
    OCR_MAX_IMAGE_SIZE_MB,
    OCR_MIN_CONFIDENCE,
    SUPPORTED_IMAGE_EXTENSIONS,
)

# Lazy singleton so importing core/database does not load ONNX OCR models
# until an image is actually processed.
_ocr_engine: Any = None


def get_ocr_engine() -> Any:
    """Lazily initialize and cache the RapidOCR engine on first use."""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            from rapidocr import RapidOCR  # type: ignore[no-redef]
        _ocr_engine = RapidOCR()
    return _ocr_engine


def validate_image_filename(filename: str) -> str:
    """Sanitize an uploaded filename and validate its image extension."""
    if not filename or not isinstance(filename, str):
        raise ValueError("Image filename must be a non-empty string.")

    # Normalize Windows/POSIX separators before taking basename to prevent traversal.
    safe_name = os.path.basename(filename.replace("\\", "/").strip())
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError(f"Invalid image filename: {filename!r}")

    _, ext = os.path.splitext(safe_name.lower())
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        raise ValueError(
            f"Unsupported image format '{ext or 'none'}' for '{safe_name}'. "
            f"Supported formats: {supported}"
        )
    return safe_name


def _read_image_bytes(
    image_source: Union[str, os.PathLike[str], bytes, bytearray, BinaryIO],
    max_size_bytes: int,
) -> Tuple[bytes, str]:
    """Read image bytes from a path, raw bytes, or binary stream with size validation."""
    if isinstance(image_source, (str, os.PathLike)):
        path = Path(image_source)
        if not path.is_file():
            raise FileNotFoundError(f"Image file not found: {path}")
        size = path.stat().st_size
        if size == 0:
            raise ValueError(f"Image file is empty: {path}")
        if size > max_size_bytes:
            raise ValueError(
                f"Image file '{path.name}' exceeds maximum size of "
                f"{max_size_bytes // (1024 * 1024)} MB."
            )
        return path.read_bytes(), path.suffix.lower()

    if isinstance(image_source, (bytes, bytearray)):
        raw = bytes(image_source)
    elif hasattr(image_source, "read"):
        raw = image_source.read()
    else:
        raise TypeError(
            "image_source must be a file path, bytes, or binary file-like object."
        )

    if not raw:
        raise ValueError("Uploaded image payload is empty.")
    if len(raw) > max_size_bytes:
        raise ValueError(
            f"Uploaded image exceeds maximum size of "
            f"{max_size_bytes // (1024 * 1024)} MB."
        )
    return raw, ""


def preprocess_image(
    image_source: Union[str, os.PathLike[str], bytes, bytearray, BinaryIO],
    max_size_mb: int = OCR_MAX_IMAGE_SIZE_MB,
) -> Tuple[Image.Image, Dict[str, Any]]:
    """Load an image, normalize EXIF orientation, and convert it to RGB."""
    max_size_bytes = max_size_mb * 1024 * 1024
    raw_bytes, ext = _read_image_bytes(image_source, max_size_bytes)

    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            img.load()
            img_format = (img.format or ext.lstrip(".") or "unknown").upper()
            transposed = ImageOps.exif_transpose(img)
            rgb_image = transposed.convert("RGB")
    except UnidentifiedImageError as exc:
        raise ValueError("Input is not a valid or readable image file.") from exc

    info = {
        "width": rgb_image.width,
        "height": rgb_image.height,
        "format": img_format,
    }
    return rgb_image, info


def _normalize_ocr_items(raw_output: Any) -> List[Tuple[Any, str, float]]:
    """Normalize RapidOCR outputs across rapidocr-onnxruntime and rapidocr versions."""
    if raw_output is None:
        return []

    # rapidocr-onnxruntime returns (results_list, elapse)
    if isinstance(raw_output, tuple) and len(raw_output) >= 1:
        raw_output = raw_output[0]

    if raw_output is None:
        return []

    # Newer rapidocr v2+ objects expose .boxes, .txts, .scores
    if hasattr(raw_output, "txts") and hasattr(raw_output, "scores"):
        txts = getattr(raw_output, "txts") or []
        scores = getattr(raw_output, "scores") or []
        boxes = getattr(raw_output, "boxes", None)
        items: List[Tuple[Any, str, float]] = []
        for idx, text in enumerate(txts):
            score = float(scores[idx]) if idx < len(scores) else 1.0
            box = boxes[idx] if boxes is not None and idx < len(boxes) else None
            items.append((box, str(text), score))
        return items

    if not isinstance(raw_output, list):
        return []

    items = []
    for entry in raw_output:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        box = entry[0]
        text = str(entry[1])
        score = float(entry[2]) if len(entry) >= 3 and entry[2] is not None else 1.0
        items.append((box, text, score))
    return items


def _box_metrics(box: Any) -> Tuple[float, float, float]:
    """Return (y_center, x_left, height) for a 4-point polygon bounding box."""
    if not box:
        return 0.0, 0.0, 0.0
    try:
        xs = [float(pt[0]) for pt in box]
        ys = [float(pt[1]) for pt in box]
        y_min, y_max = min(ys), max(ys)
        return (y_min + y_max) / 2.0, min(xs), max(y_max - y_min, 1.0)
    except (TypeError, ValueError, IndexError):
        return 0.0, 0.0, 0.0


def _format_ocr_lines(
    items: List[Tuple[Any, str, float]],
    min_confidence: float,
) -> Tuple[str, float, int]:
    """Filter low-confidence detections and reconstruct reading-order lines."""
    filtered: List[Tuple[float, float, float, str, float]] = []
    for box, text, conf in items:
        cleaned = text.strip()
        if not cleaned or conf < min_confidence:
            continue
        y_center, x_left, height = _box_metrics(box)
        filtered.append((y_center, x_left, height, cleaned, conf))

    if not filtered:
        return "", 0.0, 0

    # Sort top-to-bottom first, then cluster detections on the same visual line.
    filtered.sort(key=lambda item: (item[0], item[1]))
    heights = sorted(item[2] for item in filtered if item[2] > 0)
    line_tolerance = (heights[len(heights) // 2] * 0.5) if heights else 10.0

    lines: List[List[Tuple[float, float, str]]] = []
    for y_center, x_left, _, text, _ in filtered:
        if not lines:
            lines.append([(y_center, x_left, text)])
            continue
        last_line_y = sum(item[0] for item in lines[-1]) / len(lines[-1])
        if abs(y_center - last_line_y) <= line_tolerance:
            lines[-1].append((y_center, x_left, text))
        else:
            lines.append([(y_center, x_left, text)])

    formatted_lines = [
        " ".join(seg[2] for seg in sorted(line, key=lambda seg: seg[1]))
        for line in lines
    ]
    avg_conf = round(sum(item[4] for item in filtered) / len(filtered), 4)
    return "\n".join(formatted_lines), avg_conf, len(formatted_lines)


def extract_text_from_image(
    image_source: Union[str, os.PathLike[str], bytes, bytearray, BinaryIO],
    min_confidence: float = OCR_MIN_CONFIDENCE,
) -> Dict[str, Any]:
    """Run Python OCR on an image path, bytes, or stream and return text + metadata."""
    rgb_image, image_info = preprocess_image(image_source)
    image_array = np.asarray(rgb_image)

    engine = get_ocr_engine()
    raw_output = engine(image_array)
    items = _normalize_ocr_items(raw_output)
    text, avg_confidence, line_count = _format_ocr_lines(
        items, min_confidence=min_confidence
    )

    return {
        "text": text,
        "confidence": avg_confidence,
        "line_count": line_count,
        "width": image_info["width"],
        "height": image_info["height"],
        "format": image_info["format"],
    }


def _build_ocr_documents(
    ocr_result: Dict[str, Any],
    source_name: str,
) -> List[Document]:
    """Convert non-empty OCR output into LangChain Document objects."""
    text = ocr_result.get("text", "").strip()
    if not text:
        return []

    return [
        Document(
            page_content=text,
            metadata={
                "source": source_name,
                "source_type": "image_ocr",
                "ocr_engine": "rapidocr",
                "ocr_confidence": ocr_result["confidence"],
                "ocr_line_count": ocr_result["line_count"],
                "image_width": ocr_result["width"],
                "image_height": ocr_result["height"],
                "image_format": ocr_result["format"],
            },
        )
    ]


def load_image_with_ocr(
    file_path: str,
    source_name: Optional[str] = None,
    min_confidence: float = OCR_MIN_CONFIDENCE,
) -> List[Document]:
    """Extract text from an image file on disk and return LangChain Documents."""
    validate_image_filename(file_path)
    ocr_result = extract_text_from_image(file_path, min_confidence=min_confidence)
    return _build_ocr_documents(ocr_result, source_name=source_name or file_path)


def load_image_bytes_with_ocr(
    file_bytes: bytes,
    filename: str,
    source_name: Optional[str] = None,
    min_confidence: float = OCR_MIN_CONFIDENCE,
) -> List[Document]:
    """Extract text from uploaded image bytes and return LangChain Documents."""
    safe_name = validate_image_filename(filename)
    ocr_result = extract_text_from_image(file_bytes, min_confidence=min_confidence)
    return _build_ocr_documents(ocr_result, source_name=source_name or safe_name)
