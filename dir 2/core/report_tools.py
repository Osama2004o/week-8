"""
Report Tools
============
Design tools the Report Generator Agent calls to build a PDF with ReportLab.
`make_report_tools(report)` returns tools that all edit the same ReportBuilder:
layout, theme (fonts, sizes, colors, spacing), titles, headings, paragraphs,
lists, tables, highlight boxes, spacers, dividers and page breaks.
"""

from typing import List, Optional
from xml.sax.saxutils import escape

from langchain_core.tools import tool
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, ListFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
)

# Built-in PDF fonts: regular, bold, italic, bold-italic
FONTS = {
    "helvetica": ["Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique"],
    "times": ["Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic"],
    "courier": ["Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique"],
}
ALIGN = {"left": 0, "center": 1, "right": 2, "justify": 4}


def color(value: str):
    """Color name ('navy') or hex ('#1F3A5F'); unknown values become black."""
    return colors.toColor(value, colors.black)


class ReportBuilder:
    """Holds the layout, theme and content blocks of one report."""

    def __init__(self):
        self.page_size, self.margin, self.footer = A4, 2 * cm, ""
        self.font, self.font_size, self.line_spacing = "helvetica", 11, 1.4
        self.text_color, self.heading_color, self.accent_color = "#222222", "#1F3A5F", "#2E86C1"
        self.blocks = []

    @property
    def width(self) -> float:
        return self.page_size[0] - 2 * self.margin

    def style(self, size=None, text_color=None, bold=False, italic=False, align="left", font=None):
        """Paragraph style; anything not given comes from the theme."""
        size = size or self.font_size
        variants = FONTS.get((font or self.font).lower(), FONTS["helvetica"])
        return ParagraphStyle(
            "custom",
            fontName=variants[bold + 2 * italic],
            fontSize=size,
            leading=size * self.line_spacing,
            textColor=color(text_color or self.text_color),
            alignment=ALIGN.get(align.lower(), 0),
            spaceAfter=6,
        )

    @staticmethod
    def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
        """Keeps inline tags like <b>; escapes the text if the markup is invalid."""
        try:
            return Paragraph(text, style)
        except ValueError:
            return Paragraph(escape(text), style)

    def save(self, path: str) -> str:
        """Renders the PDF with the footer text and page numbers on every page."""
        def footer(canvas, doc):
            canvas.setFont(FONTS["helvetica"][0], 8)
            canvas.setFillColor(colors.grey)
            canvas.drawString(self.margin, self.margin / 2, self.footer)
            canvas.drawRightString(self.page_size[0] - self.margin, self.margin / 2, f"Page {doc.page}")

        doc = SimpleDocTemplate(path, pagesize=self.page_size, leftMargin=self.margin,
                                rightMargin=self.margin, topMargin=self.margin, bottomMargin=self.margin)
        doc.build(self.blocks, onFirstPage=footer, onLaterPages=footer)
        return path


def make_report_tools(report: ReportBuilder) -> list:
    """Creates the design tools, all bound to the same ReportBuilder."""

    @tool
    def set_layout(page_size: str = "A4", orientation: str = "portrait",
                   margin_cm: float = 2.0, footer_text: str = "") -> str:
        """Sets the page layout. Call first. page_size: 'A4' or 'Letter'.
        orientation: 'portrait' or 'landscape'. footer_text appears on every page."""
        size = LETTER if page_size.lower() == "letter" else A4
        report.page_size = landscape(size) if orientation.lower() == "landscape" else size
        report.margin, report.footer = margin_cm * cm, footer_text
        return "Layout set."

    @tool
    def set_theme(font: str = "helvetica", font_size: float = 11, line_spacing: float = 1.4,
                  text_color: str = "#222222", heading_color: str = "#1F3A5F",
                  accent_color: str = "#2E86C1") -> str:
        """Sets the default style. Call before adding content.
        font: 'helvetica' (modern), 'times' (formal) or 'courier' (monospace).
        Colors are names or hex codes. accent_color is used for dividers, bullets,
        table headers and highlight boxes. line_spacing: e.g. 1.2 tight, 1.5 airy."""
        report.font, report.font_size, report.line_spacing = font, font_size, line_spacing
        report.text_color, report.heading_color, report.accent_color = text_color, heading_color, accent_color
        return "Theme set."

    @tool
    def add_title(title: str, subtitle: str = "") -> str:
        """Adds the report title and an optional subtitle (e.g. the question or a date)."""
        report.blocks.append(report.paragraph(title, report.style(26, report.heading_color, bold=True)))
        if subtitle:
            report.blocks.append(report.paragraph(subtitle, report.style(13, "grey", italic=True)))
        return "Title added."

    @tool
    def add_heading(text: str, level: int = 1, text_color: Optional[str] = None) -> str:
        """Adds a section heading. level: 1 (section), 2 (sub-section) or 3 (minor)."""
        size = {1: 18, 2: 15}.get(level, 12.5)
        report.blocks += [Spacer(1, size * 0.6), report.paragraph(
            text, report.style(size, text_color or report.heading_color, bold=True))]
        return "Heading added."

    @tool
    def add_paragraph(text: str, font_size: Optional[float] = None, text_color: Optional[str] = None,
                      font: Optional[str] = None, bold: bool = False, italic: bool = False,
                      align: str = "justify") -> str:
        """Adds body text. align: left, center, right or justify. Inline tags allowed:
        <b>bold</b>, <i>italic</i>, <u>underline</u>, <font color='red'>colored</font>."""
        report.blocks.append(report.paragraph(
            text, report.style(font_size, text_color, bold, italic, align, font)))
        return "Paragraph added."

    @tool
    def add_bullet_list(items: List[str], numbered: bool = False) -> str:
        """Adds a bulleted or numbered list. Items may use inline tags like <b>."""
        report.blocks.append(ListFlowable(
            [report.paragraph(item, report.style()) for item in items],
            bulletType="1" if numbered else "bullet",
            bulletColor=color(report.accent_color),
            bulletFontSize=report.font_size,
        ))
        return "List added."

    @tool
    def add_table(headers: List[str], rows: List[List[str]]) -> str:
        """Adds a table with a colored header row. Best for numbers, comparisons and sources."""
        header_style = report.style(9.5, "white", bold=True)
        cell_style = report.style(9.5)
        data = [[report.paragraph(str(h), header_style) for h in headers]]
        data += [[report.paragraph(str(cell), cell_style) for cell in row] for row in rows]
        report.blocks += [Table(data, colWidths=report.width / len(headers), repeatRows=1, style=[
            ("BACKGROUND", (0, 0), (-1, 0), color(report.accent_color)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F8")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]), Spacer(1, 10)]
        return "Table added."

    @tool
    def add_highlight_box(text: str, background_color: str = "#EAF2F8") -> str:
        """Adds a colored box for a key finding, the main answer or a warning."""
        report.blocks += [Table([[report.paragraph(text, report.style())]], colWidths=report.width, style=[
            ("BACKGROUND", (0, 0), (-1, -1), color(background_color)),
            ("LINEBEFORE", (0, 0), (0, -1), 4, color(report.accent_color)),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]), Spacer(1, 10)]
        return "Highlight box added."

    @tool
    def add_spacer(height_cm: float = 0.5) -> str:
        """Adds vertical white space."""
        report.blocks.append(Spacer(1, height_cm * cm))
        return "Spacer added."

    @tool
    def add_divider() -> str:
        """Adds a horizontal line in the accent color to separate sections."""
        report.blocks.append(HRFlowable(width="100%", color=color(report.accent_color), spaceAfter=8))
        return "Divider added."

    @tool
    def add_page_break() -> str:
        """Starts a new page."""
        report.blocks.append(PageBreak())
        return "Page break added."

    return [set_layout, set_theme, add_title, add_heading, add_paragraph, add_bullet_list,
            add_table, add_highlight_box, add_spacer, add_divider, add_page_break]
