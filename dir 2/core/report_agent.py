"""
Report Generator Agent
======================
A LangChain tool-calling agent that turns the Orchestrator's result (question,
answer, analysis, sources) into a PDF report. It controls the whole design
(layout, fonts, sizes, colors, spacing) through the tools in core/report_tools.py.
"""

import os
from datetime import datetime
from typing import Any, Dict, Optional

from langchain.agents import create_agent

from config.settings import REPORT_MAX_STEPS, REPORT_OUTPUT_DIR
from core.analyst_agent import _get_llm
from core.report_tools import ReportBuilder, make_report_tools


SYSTEM_PROMPT = """You are the Report Generator Agent. Build a professional PDF report
from the given question, answer, analysis and sources, using ONLY the design tools.

1. Call set_layout and set_theme first (page, margins, font, sizes, colors, spacing).
2. Add content top to bottom: title, then sections like Summary, Answer, Analysis,
   Key Findings and Sources. Use tables for numbers and highlight boxes for key points.
3. Never invent facts, numbers or sources. Follow the user's style instructions.

When finished, reply with one short sentence describing the report."""


def run_report_agent(
    result: Dict[str, Any],
    instructions: str = "",
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generates a PDF report from an Orchestrator result.

    Args:
        result:       Dict with "question", "answer", "analysis", "sources".
        instructions: Optional style requests, e.g. "formal, navy, Times font".
        output_path:  Where to save the PDF (default: reports/report_<time>.pdf).

    Returns:
        {"pdf_path", "summary", "tool_calls"}
    """
    report = ReportBuilder()
    agent = create_agent(_get_llm(), make_report_tools(report), system_prompt=SYSTEM_PROMPT)

    prompt = f"Style instructions: {instructions or 'clean and professional'}\n\n" + "\n\n".join(
        f"{key.title()}:\n{result.get(key, '')}" for key in ("question", "answer", "analysis", "sources")
    )
    messages = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"recursion_limit": REPORT_MAX_STEPS},
    )["messages"]

    if not report.blocks:  # the model added nothing → still save the answer
        report.blocks.append(report.paragraph(result.get("answer", ""), report.style()))

    if output_path is None:
        os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(REPORT_OUTPUT_DIR, f"report_{datetime.now():%Y%m%d_%H%M%S}.pdf")

    return {
        "pdf_path": report.save(output_path),
        "summary": messages[-1].content,
        "tool_calls": [call for msg in messages for call in getattr(msg, "tool_calls", [])],
    }
