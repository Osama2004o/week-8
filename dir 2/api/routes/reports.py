"""
Report Generator Agent Routes
=============================
"""

from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from api.schemas import ReportGenerateRequest, ReportGenerateResponse
from config.settings import REPORT_OUTPUT_DIR
from core.report_agent import run_report_agent

router = APIRouter(prefix="/reports", tags=["Report Generator Agent"])


@router.post("/generate", response_model=ReportGenerateResponse, summary="Generate PDF Report")
def generate_report(payload: ReportGenerateRequest) -> ReportGenerateResponse:
    """
    Invokes the Report Generator Agent to produce a PDF report from query results.
    """
    try:
        os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
        out_path = None
        if payload.filename:
            safe_name = os.path.basename(payload.filename.replace("\\", "/"))
            if not safe_name.endswith(".pdf"):
                safe_name += ".pdf"
            out_path = os.path.join(REPORT_OUTPUT_DIR, safe_name)

        agent_result = run_report_agent(
            result=payload.result,
            instructions=payload.instructions or "clean and professional",
            output_path=out_path,
        )

        pdf_path = agent_result["pdf_path"]
        filename = os.path.basename(pdf_path)
        download_url = f"/api/v1/reports/download/{filename}"

        return ReportGenerateResponse(
            status="success",
            pdf_path=pdf_path,
            filename=filename,
            download_url=download_url,
            summary=agent_result.get("summary", "PDF report generated successfully."),
            tool_calls=agent_result.get("tool_calls", []),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}",
        )


@router.get("/download/{filename}", summary="Download Generated PDF Report")
def download_report(filename: str):
    """Downloads a previously generated PDF report file."""
    safe_name = os.path.basename(filename.replace("\\", "/"))
    pdf_path = os.path.join(REPORT_OUTPUT_DIR, safe_name)
    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report file '{safe_name}' not found.",
        )
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=safe_name,
    )
