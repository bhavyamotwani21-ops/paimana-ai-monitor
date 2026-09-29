from __future__ import annotations

from io import BytesIO
import html
from pathlib import Path
import re

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.risk_engine import (
    DATA_QUALITY_INDICATOR_CODES,
    HISTORICAL_DATA_PATH,
    REVIEW_PRIORITY_DISCLAIMER,
    SUBSTANTIVE_INDICATOR_CODES,
    generate_monitoring_indicators,
    generate_review_priorities,
    load_historical_projects,
)
from src.ui import apply_shared_styles, render_page_header


PAGE_CSS = """
<style>
    .reports-supporting { color: #66727F; font-size: 0.94rem; margin: 0.1rem 0 0.45rem; }
    .reports-filter-title { color: #17365D; font-size: 0.9rem; font-weight: 700; letter-spacing: 0.025em; margin: 0 0 0.3rem; text-transform: uppercase; }
    .reports-section-title { color: #17365D; font-size: 1.18rem; font-weight: 700; margin: 1.05rem 0 0.45rem; }
    .reports-kpi { background: #FFFFFF; border: 1px solid #D9DEE5; border-top: 3px solid #17365D; border-radius: 5px; box-sizing: border-box; min-height: 108px; padding: 0.8rem 0.9rem; }
    .reports-kpi-label { color: #66727F; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.03em; line-height: 1.3; margin: 0; text-transform: uppercase; }
    .reports-kpi-value { color: #17365D; font-size: 1.22rem; font-weight: 750; line-height: 1.3; margin: 0.4rem 0 0; overflow-wrap: anywhere; }
    .reports-note { background: #F2F4F7; border-left: 3px solid #D99024; color: #495765; font-size: 0.86rem; line-height: 1.5; margin: 0.7rem 0; padding: 0.7rem 0.85rem; }
    .reports-source { border-top: 1px solid #D9DEE5; color: #66727F; font-size: 0.82rem; margin-top: 1rem; padding-top: 0.65rem; }
    [data-testid="stDataFrame"], [data-testid="stVerticalBlockBorderWrapper"] { background: #FFFFFF !important; border-color: #D9DEE5 !important; box-shadow: none !important; }
    [data-testid="stSelectbox"] div[role="group"], div[data-baseweb="select"] > div { background: #FFFFFF !important; border-color: #D9DEE5 !important; color: #1F2933 !important; }
    [data-testid="stSelectbox"] input, div[data-baseweb="select"] input, div[data-baseweb="select"] span { color: #1F2933 !important; -webkit-text-fill-color: #1F2933 !important; }
    [data-testid="stSelectbox"] button svg, div[data-baseweb="select"] svg { color: #17365D !important; fill: #17365D !important; }
    [data-testid="stSelectbox"] label p, .stSelectbox label p { color: #1F2933 !important; font-weight: 650; }
    div[role="listbox"], div[role="option"] { background: #FFFFFF !important; color: #1F2933 !important; }
    div[role="option"]:hover, div[role="option"][aria-selected="true"] { background: #F2F4F7 !important; color: #102A43 !important; }
</style>
"""

NAVY = colors.HexColor("#17365D")
DARK_NAVY = colors.HexColor("#102A43")
SAFFRON = colors.HexColor("#D99024")
TEXT = colors.HexColor("#1F2933")
SECONDARY = colors.HexColor("#66727F")
BORDER = colors.HexColor("#D9DEE5")
LIGHT = colors.HexColor("#F2F4F7")
WHITE = colors.white

INDICATOR_LABELS = {
    "COST_REVIEW": "Cost Review",
    "SCHEDULE_REVIEW": "Schedule Review",
    "PROGRESS_STAGNATION_REVIEW": "Progress Stagnation Review",
    "EXPENDITURE_PROGRESS_REVIEW": "Expenditure-Progress Review",
    "REVISED_COST_UNAVAILABLE": "Revised Cost Unavailable",
    "REVISED_DOC_UNAVAILABLE": "Revised DoC Unavailable",
    "PHYSICAL_PROGRESS_UNAVAILABLE": "Physical Progress Unavailable",
}


@st.cache_data(show_spinner=False)
def _load_report_data(
    historical_file_modified_ns: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    del historical_file_modified_ns
    history = load_historical_projects()
    indicators = generate_monitoring_indicators(history)
    priorities = generate_review_priorities(history, indicators)
    return history, indicators, priorities


def _month_label(report_month: str) -> str:
    return pd.Period(report_month, freq="M").strftime("%B %Y")


def _is_available(value: object) -> bool:
    return value is not None and not pd.isna(value) and bool(str(value).strip())


def _plain(value: object) -> str:
    return str(value).strip() if _is_available(value) else "Not available"


def _format_number(value: object) -> str:
    if not _is_available(value):
        return "Not available"
    return f"{float(value):,.2f}".rstrip("0").rstrip(".")


def _format_crore(value: object, currency_symbol: str = "₹") -> str:
    if not _is_available(value):
        return "Not available"
    return f"{currency_symbol}{float(value):,.2f} crore"


def _format_percentage(value: object) -> str:
    if not _is_available(value):
        return "Not available"
    return f"{float(value):,.2f}".rstrip("0").rstrip(".") + "%"


def _availability(series: pd.Series) -> pd.Series:
    values = series.astype("string").str.strip()
    return values.notna() & values.ne("")


def _progress_distribution(values: pd.Series) -> list[tuple[str, int]]:
    available = pd.to_numeric(values, errors="coerce").dropna()
    return [
        ("0-25%", int(available.between(0, 25, inclusive="both").sum())),
        ("26-50%", int((available.gt(25) & available.le(50)).sum())),
        ("51-75%", int((available.gt(50) & available.le(75)).sum())),
        ("76-99%", int((available.gt(75) & available.lt(100)).sum())),
        ("100%", int(available.eq(100).sum())),
    ]


def _build_report_context(
    history: pd.DataFrame,
    indicators: pd.DataFrame,
    priorities: pd.DataFrame,
    report_month: str,
    ministry: str,
) -> dict[str, object]:
    snapshot = history.loc[history["report_month"].eq(report_month)].copy()
    month_indicators = indicators.loc[
        indicators["report_month"].eq(report_month)
    ].copy()
    month_priorities = priorities.loc[
        priorities["report_month"].eq(report_month)
    ].copy()
    if ministry != "All Ministries":
        snapshot = snapshot.loc[snapshot["ministry"].eq(ministry)].copy()
        month_indicators = month_indicators.loc[
            month_indicators["ministry"].eq(ministry)
        ].copy()
        month_priorities = month_priorities.loc[
            month_priorities["ministry"].eq(ministry)
        ].copy()

    project_count = int(snapshot["project_id"].nunique())
    original_cost = snapshot["original_cost_cr"].sum(min_count=1)
    expenditure = snapshot["cumulative_expenditure_cr"].sum(min_count=1)
    financial_ratio = (
        float(expenditure) / float(original_cost) * 100
        if pd.notna(original_cost)
        and float(original_cost) > 0
        and pd.notna(expenditure)
        else None
    )
    revised_mask = snapshot["revised_cost_available"].fillna(False).astype(bool)
    revised_available = int(revised_mask.sum())
    revised_cost = (
        snapshot.loc[revised_mask, "revised_cost_cr"].sum(min_count=1)
        if revised_available
        else None
    )
    physical_available = int(snapshot["physical_progress_pct"].notna().sum())
    revised_doc_mask = _availability(snapshot["revised_doc"])
    priority_counts = month_priorities["review_priority"].value_counts()
    substantive = month_indicators.loc[
        month_indicators["indicator_code"].isin(SUBSTANTIVE_INDICATOR_CODES)
    ].copy()
    data_quality = month_indicators.loc[
        month_indicators["indicator_code"].isin(DATA_QUALITY_INDICATOR_CODES)
    ].copy()

    return {
        "report_month": report_month,
        "report_month_label": _month_label(report_month),
        "ministry": ministry,
        "snapshot": snapshot,
        "indicators": month_indicators,
        "priorities": month_priorities,
        "substantive_indicators": substantive,
        "data_quality_indicators": data_quality,
        "project_count": project_count,
        "original_cost": original_cost,
        "revised_cost": revised_cost,
        "revised_available": revised_available,
        "revised_unavailable": project_count - revised_available,
        "expenditure": expenditure,
        "financial_ratio": financial_ratio,
        "median_progress": snapshot["physical_progress_pct"].median(skipna=True),
        "physical_available": physical_available,
        "physical_unavailable": project_count - physical_available,
        "revised_doc_available": int(revised_doc_mask.sum()),
        "revised_doc_unavailable": int(project_count - revised_doc_mask.sum()),
        "sector_summary": snapshot.groupby("sector", dropna=False)["project_id"]
        .nunique()
        .sort_values(ascending=False),
        "progress_distribution": _progress_distribution(
            snapshot["physical_progress_pct"]
        ),
        "priority_counts": {
            priority: int(priority_counts.get(priority, 0))
            for priority in ("HIGH", "MEDIUM", "NORMAL")
        },
        "source_reports": sorted(
            snapshot["source_report"].dropna().astype(str).unique().tolist()
        ),
    }


def _register_pdf_fonts() -> tuple[str, str, str]:
    candidates = [
        (
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("C:/Windows/Fonts/segoeuib.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
    ]
    for regular_path, bold_path in candidates:
        if regular_path.exists() and bold_path.exists():
            if "PAIMANARegular" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("PAIMANARegular", str(regular_path)))
                pdfmetrics.registerFont(TTFont("PAIMANABold", str(bold_path)))
            return "PAIMANARegular", "PAIMANABold", "₹"
    return "Helvetica", "Helvetica-Bold", "INR "


def _pdf_paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html.escape(_plain(value)), style)


def _pdf_footer(canvas, document, regular_font: str) -> None:
    canvas.saveState()
    width, _ = landscape(A4)
    canvas.setStrokeColor(BORDER)
    canvas.line(14 * mm, 11 * mm, width - 14 * mm, 11 * mm)
    canvas.setFont(regular_font, 7)
    canvas.setFillColor(SECONDARY)
    canvas.drawString(14 * mm, 7 * mm, "UJAGAR prototype monitoring report")
    canvas.drawRightString(
        width - 14 * mm, 7 * mm, f"Page {document.page}"
    )
    canvas.restoreState()


def _build_pdf(context: dict[str, object]) -> bytes:
    regular_font, bold_font, currency_symbol = _register_pdf_fonts()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title=f"UJAGAR Monitoring Report - {context['report_month_label']}",
        author="UJAGAR prototype",
    )
    base_styles = getSampleStyleSheet()
    styles = {
        "cover_brand": ParagraphStyle(
            "CoverBrand",
            parent=base_styles["Title"],
            fontName=bold_font,
            fontSize=27,
            leading=32,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=5 * mm,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base_styles["Heading1"],
            fontName=bold_font,
            fontSize=19,
            leading=24,
            textColor=DARK_NAVY,
            alignment=TA_CENTER,
            spaceAfter=8 * mm,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base_styles["Heading1"],
            fontName=bold_font,
            fontSize=15,
            leading=18,
            textColor=DARK_NAVY,
            spaceBefore=2 * mm,
            spaceAfter=3 * mm,
        ),
        "subsection": ParagraphStyle(
            "Subsection",
            parent=base_styles["Heading2"],
            fontName=bold_font,
            fontSize=10,
            leading=13,
            textColor=NAVY,
            spaceBefore=2 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base_styles["BodyText"],
            fontName=regular_font,
            fontSize=8.5,
            leading=12,
            textColor=TEXT,
            spaceAfter=2 * mm,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base_styles["BodyText"],
            fontName=regular_font,
            fontSize=6.4,
            leading=8.2,
            textColor=TEXT,
        ),
        "small_bold": ParagraphStyle(
            "SmallBold",
            parent=base_styles["BodyText"],
            fontName=bold_font,
            fontSize=6.4,
            leading=8.2,
            textColor=WHITE,
        ),
        "cover_body": ParagraphStyle(
            "CoverBody",
            parent=base_styles["BodyText"],
            fontName=regular_font,
            fontSize=10,
            leading=15,
            textColor=TEXT,
            alignment=TA_CENTER,
        ),
        "note": ParagraphStyle(
            "Note",
            parent=base_styles["BodyText"],
            fontName=regular_font,
            fontSize=8,
            leading=11,
            textColor=SECONDARY,
        ),
    }

    def heading(text: str) -> list[object]:
        return [
            Paragraph(html.escape(text), styles["section"]),
            HRFlowable(width="100%", thickness=1, color=SAFFRON, spaceAfter=3 * mm),
        ]

    def table_style(header: bool = True, font_size: float = 7.2) -> TableStyle:
        commands = [
            ("FONTNAME", (0, 0), (-1, -1), regular_font),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [WHITE, LIGHT]),
        ]
        if header:
            commands.extend(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ]
            )
        return TableStyle(commands)

    story: list[object] = [
        Spacer(1, 18 * mm),
        Paragraph("UJAGAR", styles["cover_brand"]),
        HRFlowable(
            width="28%", thickness=2, color=SAFFRON, hAlign="CENTER", spaceAfter=7 * mm
        ),
        Paragraph("Infrastructure Project Monitoring Report", styles["cover_title"]),
    ]
    cover_info = [
        ["Report Month", context["report_month_label"]],
        ["Ministry", context["ministry"]],
        ["Source Report(s)", ", ".join(context["source_reports"]) or "Not available"],
    ]
    cover_table = Table(cover_info, colWidths=[48 * mm, 135 * mm], hAlign="CENTER")
    cover_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), bold_font),
                ("FONTNAME", (1, 0), (1, -1), regular_font),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend(
        [
            cover_table,
            Spacer(1, 9 * mm),
            Paragraph(
                "Generated from reported PAIMANA project data for monitoring and review.",
                styles["cover_body"],
            ),
            Spacer(1, 4 * mm),
            Paragraph(
                "This prototype-generated document is not an official MoSPI-issued report.",
                styles["cover_body"],
            ),
            PageBreak(),
        ]
    )

    story.extend(heading("1. Portfolio Summary"))
    summary_rows = [
        ["Measure", "Reported Value"],
        ["Ongoing Projects", f"{context['project_count']:,}"],
        ["Original Cost", _format_crore(context["original_cost"], currency_symbol)],
        ["Latest Revised Cost", _format_crore(context["revised_cost"], currency_symbol)],
        [
            "Revised Cost Coverage",
            f"Available for {context['revised_available']:,} of {context['project_count']:,} projects",
        ],
        ["Cumulative Expenditure", _format_crore(context["expenditure"], currency_symbol)],
        ["Financial Expenditure Ratio", _format_percentage(context["financial_ratio"])],
        ["Median Reported Physical Progress", _format_percentage(context["median_progress"])],
    ]
    summary_table = Table(summary_rows, colWidths=[75 * mm, 105 * mm], hAlign="LEFT")
    summary_table.setStyle(table_style(font_size=8))
    story.extend(
        [
            summary_table,
            Spacer(1, 3 * mm),
            Paragraph(
                "Financial Expenditure Ratio is cumulative expenditure as a percentage of original project cost. It is not physical progress.",
                styles["note"],
            ),
            Spacer(1, 4 * mm),
        ]
    )

    story.extend(heading("2. Portfolio Breakdown"))
    story.append(Paragraph("Sector-wise Project Summary", styles["subsection"]))
    sector_rows = [["Sector", "Project Count"]] + [
        [_plain(sector), f"{int(count):,}"]
        for sector, count in context["sector_summary"].items()
    ]
    sector_table = LongTable(
        sector_rows, colWidths=[145 * mm, 35 * mm], repeatRows=1, hAlign="LEFT"
    )
    sector_table.setStyle(table_style())
    story.extend([sector_table, Spacer(1, 4 * mm)])

    distribution_rows = [["Physical Progress Band", "Project Count"]] + [
        [band, f"{count:,}"] for band, count in context["progress_distribution"]
    ]
    distribution_table = Table(
        distribution_rows, colWidths=[75 * mm, 35 * mm], hAlign="LEFT"
    )
    distribution_table.setStyle(table_style())
    coverage_rows = [
        ["Reported Field", "Available", "Unavailable"],
        [
            "Physical Progress",
            f"{context['physical_available']:,}",
            f"{context['physical_unavailable']:,}",
        ],
        [
            "Revised Cost",
            f"{context['revised_available']:,}",
            f"{context['revised_unavailable']:,}",
        ],
        [
            "Revised DoC",
            f"{context['revised_doc_available']:,}",
            f"{context['revised_doc_unavailable']:,}",
        ],
    ]
    coverage_table = Table(
        coverage_rows, colWidths=[70 * mm, 35 * mm, 35 * mm], hAlign="LEFT"
    )
    coverage_table.setStyle(table_style())
    story.append(
        KeepTogether(
            [
                Paragraph("Physical Progress Distribution", styles["subsection"]),
                distribution_table,
                Spacer(1, 4 * mm),
                Paragraph("Data Coverage", styles["subsection"]),
                coverage_table,
                Spacer(1, 2 * mm),
                Paragraph(
                    "Missing data denotes reporting availability only and is not a project-performance assessment.",
                    styles["note"],
                ),
            ]
        )
    )

    story.extend([PageBreak(), *heading("3. Project Register")])
    snapshot = context["snapshot"].sort_values(
        ["project_name", "project_id"], kind="stable"
    )
    register_headers = [
        "Project ID",
        "Project Name",
        "Ministry",
        "Sector",
        "State",
        "Original Cost",
        "Revised Cost",
        "Expenditure",
        "Physical Progress",
        "Revised DoC",
    ]
    register_rows: list[list[object]] = [
        [Paragraph(header, styles["small_bold"]) for header in register_headers]
    ]
    for _, row in snapshot.iterrows():
        revised_value = (
            _format_crore(row["revised_cost_cr"], currency_symbol)
            if bool(row["revised_cost_available"])
            else "Not available"
        )
        register_rows.append(
            [
                _pdf_paragraph(row["project_id"], styles["small"]),
                _pdf_paragraph(row["project_name"], styles["small"]),
                _pdf_paragraph(row["ministry"], styles["small"]),
                _pdf_paragraph(row["sector"], styles["small"]),
                _pdf_paragraph(row["state"], styles["small"]),
                _pdf_paragraph(
                    _format_crore(row["original_cost_cr"], currency_symbol),
                    styles["small"],
                ),
                _pdf_paragraph(revised_value, styles["small"]),
                _pdf_paragraph(
                    _format_crore(row["cumulative_expenditure_cr"], currency_symbol),
                    styles["small"],
                ),
                _pdf_paragraph(
                    _format_percentage(row["physical_progress_pct"]), styles["small"]
                ),
                _pdf_paragraph(row["revised_doc"], styles["small"]),
            ]
        )
    register_table = LongTable(
        register_rows,
        colWidths=[15 * mm, 48 * mm, 37 * mm, 32 * mm, 25 * mm, 27 * mm, 27 * mm, 28 * mm, 25 * mm, 23 * mm],
        repeatRows=1,
        splitByRow=1,
    )
    register_table.setStyle(table_style(font_size=6.2))
    story.append(register_table)

    story.extend([PageBreak(), *heading("4. Monitoring Review")])
    priority_rows = [["Review Priority", "Project Count"]] + [
        [priority, f"{context['priority_counts'][priority]:,}"]
        for priority in ("HIGH", "MEDIUM", "NORMAL")
    ]
    priority_table = Table(
        priority_rows, colWidths=[65 * mm, 35 * mm], hAlign="LEFT"
    )
    priority_table.setStyle(table_style())
    story.extend(
        [
            priority_table,
            Spacer(1, 2 * mm),
            Paragraph(
                "NORMAL means no substantive monitoring indicator triggered under the current prototype rules; it does not mean safe.",
                styles["note"],
            ),
            Spacer(1, 4 * mm),
            Paragraph("Projects with Substantive Monitoring Indicators", styles["subsection"]),
        ]
    )
    substantive = context["substantive_indicators"]
    priority_by_project = context["priorities"].set_index("project_id")
    monitoring_rows: list[list[object]] = [
        [
            Paragraph("Project ID", styles["small_bold"]),
            Paragraph("Project Name", styles["small_bold"]),
            Paragraph("Review Priority", styles["small_bold"]),
            Paragraph("Monitoring Indicators", styles["small_bold"]),
            Paragraph("Supporting Evidence", styles["small_bold"]),
        ]
    ]
    for project_id, project_indicators in substantive.groupby(
        "project_id", sort=False
    ):
        priority = priority_by_project.loc[project_id]
        indicator_text = "; ".join(
            INDICATOR_LABELS.get(code, code)
            for code in project_indicators["indicator_code"].tolist()
        )
        evidence_text = " ".join(
            str(value).strip()
            for value in project_indicators["explanation"].tolist()
            if _is_available(value)
        )
        monitoring_rows.append(
            [
                _pdf_paragraph(project_id, styles["small"]),
                _pdf_paragraph(priority["project_name"], styles["small"]),
                _pdf_paragraph(priority["review_priority"], styles["small"]),
                _pdf_paragraph(indicator_text, styles["small"]),
                _pdf_paragraph(evidence_text, styles["small"]),
            ]
        )
    if len(monitoring_rows) == 1:
        story.append(
            Paragraph(
                "No substantive monitoring indicators are present for this report selection.",
                styles["body"],
            )
        )
    else:
        monitoring_table = LongTable(
            monitoring_rows,
            colWidths=[22 * mm, 65 * mm, 28 * mm, 50 * mm, 96 * mm],
            repeatRows=1,
            splitByRow=1,
        )
        monitoring_table.setStyle(table_style(font_size=6.2))
        story.append(monitoring_table)

    story.extend([Spacer(1, 5 * mm), *heading("5. Data Quality Notes")])
    data_quality = context["data_quality_indicators"]
    quality_rows = [["Data-quality Indicator", "Affected Projects"]]
    for code in DATA_QUALITY_INDICATOR_CODES:
        affected = int(
            data_quality.loc[data_quality["indicator_code"].eq(code), "project_id"]
            .astype("string")
            .nunique()
        )
        quality_rows.append([INDICATOR_LABELS.get(code, code), f"{affected:,}"])
    quality_table = Table(
        quality_rows, colWidths=[95 * mm, 35 * mm], hAlign="LEFT"
    )
    quality_table.setStyle(table_style())
    story.extend(
        [
            quality_table,
            Spacer(1, 2 * mm),
            Paragraph(
                "Data-quality indicators describe reported-field availability and do not increase Review Priority or establish poor project performance.",
                styles["note"],
            ),
        ]
    )

    story.extend([PageBreak(), *heading("6. Source & Methodology")])
    methodology = [
        f"Source report(s): {', '.join(context['source_reports']) or 'Not available'}.",
        "This UJAGAR prototype uses reported PAIMANA project information from the processed historical dataset.",
        "Historical observations are compared across available reporting months where applicable.",
        "Monitoring indicators are transparent rule-based screening signals produced by the existing prototype engine.",
        "Review Priority is derived from the number of substantive monitoring indicators under the existing prototype logic. Data-quality indicators do not increase priority.",
        "Missing values are not automatically treated as zero. August row-level revised cost remains unavailable under the validated cleaning policy.",
        "Expenditure is financial information and is not physical progress. Physical progress uses only reported physical_progress_pct values.",
    ]
    for item in methodology:
        story.append(Paragraph(f"- {html.escape(item)}", styles["body"]))
    story.extend(
        [
            Spacer(1, 5 * mm),
            Paragraph("Disclaimer", styles["section"]),
            HRFlowable(width="100%", thickness=1, color=SAFFRON, spaceAfter=3 * mm),
            Paragraph(
                "Review priorities and monitoring indicators shown in this prototype are screening aids for monitoring and review. They are not official MoSPI risk classifications, predictions, or determinations of project performance.",
                styles["body"],
            ),
            Paragraph(
                "This generated document is a prototype output and is not an official MoSPI-issued report.",
                styles["body"],
            ),
        ]
    )

    document.build(
        story,
        onFirstPage=lambda canvas, doc: _pdf_footer(canvas, doc, regular_font),
        onLaterPages=lambda canvas, doc: _pdf_footer(canvas, doc, regular_font),
    )
    return buffer.getvalue()


def _csv_bytes(context: dict[str, object]) -> bytes:
    snapshot = context["snapshot"].copy()
    export_columns = [
        "report_month",
        "project_id",
        "project_name",
        "ministry",
        "sector",
        "agency",
        "state",
        "approval_date",
        "start_date",
        "original_target_doc",
        "revised_doc",
        "original_cost_cr",
        "revised_cost_cr",
        "revised_cost_available",
        "cumulative_expenditure_cr",
        "physical_progress_pct",
        "source_report",
    ]
    return snapshot[export_columns].to_csv(index=False).encode("utf-8-sig")


def _safe_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return cleaned[:45] or "Selection"


def _render_kpi(label: str, value: str) -> None:
    st.html(
        f'<div class="reports-kpi"><p class="reports-kpi-label">'
        f'{html.escape(label)}</p><p class="reports-kpi-value">'
        f'{html.escape(value)}</p></div>'
    )


apply_shared_styles()
st.html(PAGE_CSS)
render_page_header("Reports", "Monitoring Reports & Downloads")
st.markdown(
    '<p class="reports-supporting">Generate structured reports from reported '
    'PAIMANA project data and rule-based monitoring indicators.</p>',
    unsafe_allow_html=True,
)

try:
    history, indicators, priorities = _load_report_data(
        HISTORICAL_DATA_PATH.stat().st_mtime_ns
    )
except (FileNotFoundError, ValueError) as exc:
    st.error(f"Report data could not be loaded: {exc}")
    st.stop()

months = sorted(history["report_month"].dropna().unique().tolist())
if not months:
    st.warning("No reporting snapshots are currently available.")
    st.stop()

st.markdown('<p class="reports-filter-title">Report Configuration</p>', unsafe_allow_html=True)
with st.container(border=True):
    month_column, ministry_column = st.columns([1, 2])
    with month_column:
        selected_month = st.selectbox(
            "Report Month",
            months,
            index=len(months) - 1,
            format_func=_month_label,
        )
    ministries = sorted(
        history.loc[history["report_month"].eq(selected_month), "ministry"]
        .dropna()
        .unique()
        .tolist()
    )
    with ministry_column:
        selected_ministry = st.selectbox(
            "Ministry", ["All Ministries", *ministries]
        )
    generate_clicked = st.button(
        "Generate Report", type="primary", use_container_width=True
    )

selection_signature = (selected_month, selected_ministry)
if generate_clicked:
    context = _build_report_context(
        history, indicators, priorities, selected_month, selected_ministry
    )
    if not len(context["snapshot"]):
        st.warning("No report records match the selected filters.")
        st.stop()
    with st.spinner("Generating complete PDF report..."):
        pdf_bytes = _build_pdf(context)
    st.session_state["paimana_generated_report"] = {
        "signature": selection_signature,
        "context": context,
        "pdf": pdf_bytes,
        "csv": _csv_bytes(context),
    }

generated = st.session_state.get("paimana_generated_report")
if not generated or generated.get("signature") != selection_signature:
    st.info("Choose the report configuration and select Generate Report.")
    st.stop()

context = generated["context"]
st.markdown('<p class="reports-section-title">Report Preview</p>', unsafe_allow_html=True)
st.caption(
    f"{context['report_month_label']} | {context['ministry']} | "
    f"{context['project_count']:,} projects"
)

summary_columns = st.columns(4)
with summary_columns[0]:
    _render_kpi("Ongoing Projects", f"{context['project_count']:,}")
with summary_columns[1]:
    _render_kpi("Original Cost", _format_crore(context["original_cost"]))
with summary_columns[2]:
    _render_kpi("Latest Revised Cost", _format_crore(context["revised_cost"]))
with summary_columns[3]:
    _render_kpi("Cumulative Expenditure", _format_crore(context["expenditure"]))

secondary_columns = st.columns(3)
with secondary_columns[0]:
    _render_kpi("Financial Expenditure Ratio", _format_percentage(context["financial_ratio"]))
with secondary_columns[1]:
    _render_kpi("Median Reported Physical Progress", _format_percentage(context["median_progress"]))
with secondary_columns[2]:
    _render_kpi(
        "Revised Cost Coverage",
        f"{context['revised_available']:,} of {context['project_count']:,}",
    )

st.markdown('<p class="reports-section-title">Monitoring Summary</p>', unsafe_allow_html=True)
priority_columns = st.columns(3)
for column, priority in zip(priority_columns, ("HIGH", "MEDIUM", "NORMAL"), strict=True):
    with column:
        _render_kpi(priority, f"{context['priority_counts'][priority]:,}")
st.caption(
    "Review Priority is the existing prototype screening priority. NORMAL does not mean safe."
)

st.markdown('<p class="reports-section-title">Data Coverage</p>', unsafe_allow_html=True)
coverage_preview = pd.DataFrame(
    [
        {
            "Reported Field": "Physical Progress",
            "Available": context["physical_available"],
            "Unavailable": context["physical_unavailable"],
        },
        {
            "Reported Field": "Revised Cost",
            "Available": context["revised_available"],
            "Unavailable": context["revised_unavailable"],
        },
        {
            "Reported Field": "Revised DoC",
            "Available": context["revised_doc_available"],
            "Unavailable": context["revised_doc_unavailable"],
        },
    ]
)
st.dataframe(coverage_preview, hide_index=True, use_container_width=True)
st.markdown(
    '<div class="reports-note">Missing data indicates reporting availability only. '
    'It is not automatically treated as zero or as poor project performance.</div>',
    unsafe_allow_html=True,
)

source_text = ", ".join(context["source_reports"]) or "Not available"
st.markdown(
    f'<p class="reports-source"><strong>Source:</strong> {html.escape(source_text)}</p>',
    unsafe_allow_html=True,
)

filename_base = f"UJAGAR_Monitoring_Report_{_safe_filename_part(context['report_month_label'])}"
if context["ministry"] != "All Ministries":
    filename_base += f"_{_safe_filename_part(context['ministry'])}"
st.markdown(
    '<p class="reports-section-title">Download Actions</p>',
    unsafe_allow_html=True,
)
download_columns = st.columns(2)
with download_columns[0]:
    st.download_button(
        "Download Full PDF Report",
        data=generated["pdf"],
        file_name=f"{filename_base}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )
with download_columns[1]:
    st.download_button(
        "Download Project Data CSV",
        data=generated["csv"],
        file_name=f"{filename_base}_Project_Data.csv",
        mime="text/csv",
        type="secondary",
        use_container_width=True,
    )
