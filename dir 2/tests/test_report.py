"""
Unit & Integration Tests for the Report Generator Agent and its design tools.
The LLM is replaced by a scripted fake model.
"""

from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from reportlab.lib.pagesizes import A4, LETTER, landscape

from core.report_agent import run_report_agent
from core.report_tools import ReportBuilder, make_report_tools


class FakeToolLLM(GenericFakeChatModel):
    """Fake chat model that replays scripted messages and accepts tools."""

    def bind_tools(self, tools, **kwargs):
        return self


def tool_calls(*calls):
    return AIMessage(content="", tool_calls=[
        {"name": name, "args": args, "id": f"call_{i}"} for i, (name, args) in enumerate(calls)
    ])


@pytest.fixture
def builder():
    report = ReportBuilder()
    return report, {t.name: t for t in make_report_tools(report)}


RESULT = {
    "question": "Which model is more accurate?",
    "answer": "CNN achieves 92% accuracy versus 88% for LSTM [1].",
    "analysis": "CNN outperforms LSTM by 4 points.",
    "sources": "[1] paper_a.pdf, page 4",
}


# ---------------------------------------------------------------------------
# Tool Tests
# ---------------------------------------------------------------------------

def test_layout_and_theme(builder):
    report, tools = builder
    tools["set_layout"].invoke({"page_size": "Letter", "orientation": "landscape", "margin_cm": 1.5})
    tools["set_theme"].invoke({"font": "times", "font_size": 12, "line_spacing": 1.6})

    assert report.page_size == landscape(LETTER)
    assert report.font == "times"
    style = report.style(bold=True, italic=True)
    assert style.fontName == "Times-BoldItalic"
    assert style.leading == pytest.approx(12 * 1.6)


def test_unknown_values_fall_back_to_defaults(builder):
    report, tools = builder
    tools["set_layout"].invoke({"page_size": "B9"})
    assert report.page_size == A4
    assert report.style(font="comic-sans").fontName == "Helvetica"
    assert report.style(align="diagonal").alignment == 0  # left


def test_content_tools_add_blocks(builder, tmp_path):
    report, tools = builder
    tools["add_title"].invoke({"title": "Benchmark Report", "subtitle": "Nov 2026"})
    tools["add_heading"].invoke({"text": "Results", "level": 2, "text_color": "#C0392B"})
    tools["add_paragraph"].invoke({"text": "CNN is <b>better</b> & faster.", "italic": True})
    tools["add_bullet_list"].invoke({"items": ["one", "two"], "numbered": True})
    tools["add_table"].invoke({"headers": ["Model", "Acc"], "rows": [["CNN", "92"], ["LSTM", "88"]]})
    tools["add_highlight_box"].invoke({"text": "Key finding"})
    tools["add_divider"].invoke({})
    tools["add_spacer"].invoke({"height_cm": 1})
    tools["add_page_break"].invoke({})
    assert len(report.blocks) > 9

    path = report.save(str(tmp_path / "report.pdf"))
    with open(path, "rb") as f:
        assert f.read(4) == b"%PDF"


def test_invalid_markup_is_escaped(builder):
    report, _ = builder
    para = report.paragraph("x < 5 and <broken", report.style())
    assert "&lt;" in para.text


# ---------------------------------------------------------------------------
# Agent Tests
# ---------------------------------------------------------------------------

def test_report_agent_builds_pdf_from_tool_calls(tmp_path):
    llm = FakeToolLLM(messages=iter([
        tool_calls(
            ("set_theme", {"font": "times", "accent_color": "navy"}),
            ("add_title", {"title": "Model Accuracy Report"}),
        ),
        tool_calls(
            ("add_heading", {"text": "Answer"}),
            ("add_highlight_box", {"text": RESULT["answer"]}),
            ("add_table", {"headers": ["Model", "Accuracy"], "rows": [["CNN", "92%"], ["LSTM", "88%"]]}),
        ),
        AIMessage(content="A formal report in Times with a navy accent."),
    ]))
    out_file = tmp_path / "out.pdf"

    with patch("core.report_agent._get_llm", return_value=llm):
        result = run_report_agent(RESULT, instructions="formal", output_path=str(out_file))

    assert result["pdf_path"] == str(out_file)
    assert out_file.read_bytes().startswith(b"%PDF")
    assert result["summary"].startswith("A formal report")
    assert [c["name"] for c in result["tool_calls"]] == [
        "set_theme", "add_title", "add_heading", "add_highlight_box", "add_table",
    ]


def test_report_agent_falls_back_when_no_content(tmp_path):
    llm = FakeToolLLM(messages=iter([AIMessage(content="Done.")]))
    out_file = tmp_path / "fallback.pdf"

    with patch("core.report_agent._get_llm", return_value=llm):
        result = run_report_agent(RESULT, output_path=str(out_file))

    assert out_file.read_bytes().startswith(b"%PDF")
    assert result["tool_calls"] == []
