from __future__ import annotations

import hashlib
import html
import importlib
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import src.risk_engine as risk_engine
from src.ui import apply_shared_styles, render_page_header


# Streamlit can retain an older imported module while rerunning a changed page.
# Reload the engine before binding its public API so newly added warning symbols
# are available without requiring the application process to be restarted.
risk_engine = importlib.reload(risk_engine)

HISTORICAL_DATA_PATH = risk_engine.HISTORICAL_DATA_PATH
REVIEW_PRIORITY_DISCLAIMER = risk_engine.REVIEW_PRIORITY_DISCLAIMER
EARLY_WARNING_DISCLAIMER = risk_engine.EARLY_WARNING_DISCLAIMER
add_monitoring_comparisons = risk_engine.add_monitoring_comparisons
generate_early_warning_status = risk_engine.generate_early_warning_status
generate_early_warnings = risk_engine.generate_early_warnings
generate_monitoring_indicators = risk_engine.generate_monitoring_indicators
generate_review_priorities = risk_engine.generate_review_priorities
load_historical_projects = risk_engine.load_historical_projects


PAGE_CSS = """
<style>
    .risk-context-note {
        background: #F2F4F7;
        border-left: 3px solid #D99024;
        color: #495765;
        font-size: 0.9rem;
        line-height: 1.5;
        margin: 1.1rem 0 1.25rem;
        padding: 0.75rem 0.9rem;
    }

    .risk-section-title {
        color: #102A43;
        font-size: 1.15rem;
        font-weight: 700;
        margin: 1.45rem 0 0.7rem;
    }

    .risk-filter-title {
        color: #17365D;
        font-size: 0.92rem;
        font-weight: 700;
        letter-spacing: 0.025em;
        margin: 0 0 0.35rem;
        text-transform: uppercase;
    }

    .risk-summary-card {
        background: #FFFFFF;
        border: 1px solid #D9DEE5;
        border-top: 3px solid #17365D;
        border-radius: 5px;
        min-height: 92px;
        padding: 0.85rem 1rem;
    }

    .risk-summary-label {
        color: #66727F;
        font-size: 0.79rem;
        font-weight: 650;
        letter-spacing: 0.035em;
        margin: 0;
        text-transform: uppercase;
    }

    .risk-summary-value {
        color: #17365D;
        font-size: 1.7rem;
        font-weight: 750;
        line-height: 1.15;
        margin: 0.45rem 0 0;
    }

    .risk-detail-panel {
        background: #FFFFFF;
        border: 1px solid #D9DEE5;
        border-left: 4px solid #17365D;
        border-radius: 5px;
        margin-bottom: 0.8rem;
        padding: 1rem 1.1rem;
    }

    .risk-detail-name {
        color: #102A43;
        font-size: 1.1rem;
        font-weight: 700;
        line-height: 1.4;
        margin: 0 0 0.85rem;
    }

    .risk-detail-grid {
        display: grid;
        gap: 0.75rem 1.25rem;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        padding-bottom: 0.8rem;

    }

    .risk-detail-item {
        min-width: 0;
    }

    .risk-detail-label {
        color: #66727F;
        display: block;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: 0.2rem;
        text-transform: uppercase;
    }

    .risk-detail-value {
        color: #1F2933;
        display: block;
        font-size: 0.88rem;
        line-height: 1.45;
        overflow-wrap: anywhere;
    }

    .risk-priority {
        border: 1px solid #D9DEE5;
        border-radius: 3px;
        display: inline-block;
        font-size: 0.78rem;
        font-weight: 750;
        letter-spacing: 0.04em;
        margin-left: 0.35rem;
        padding: 0.15rem 0.5rem;
    }

    .risk-priority-high {
        background: #FFFFFF;
        border-color: #17365D;
        color: #102A43;
    }

    .risk-priority-medium {
        background: #FFF9EF;
        border-color: #D99024;
        color: #70450B;
    }

    .risk-priority-normal {
        background: #F2F4F7;
        color: #495765;
    }

    .risk-priority-explanation {
        border-top: 1px solid #E7EAF0;
        color: #1F2933;
        font-size: 0.92rem;
        line-height: 1.55;
        margin: 1.4rem 0 0;
        padding-top: 1.1rem;
    }

    .risk-indicator-card {
        background: #FFFFFF;
        border: 1px solid #D9DEE5;
        border-left: 3px solid #17365D;
        border-radius: 5px;
        margin-bottom: 0.85rem;
        padding: 1rem 1.05rem;
    }

    .risk-indicator-header {
        align-items: flex-start;
        display: flex;
        gap: 1rem;
        justify-content: space-between;
    }

    .risk-indicator-title {
        color: #102A43;
        font-size: 1rem;
        font-weight: 700;
        line-height: 1.4;
        margin: 0;
    }

    .risk-indicator-category {
        background: #F2F4F7;
        border: 1px solid #D9DEE5;
        border-radius: 3px;
        color: #17365D;
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 650;
        margin-top: 0.4rem;
        padding: 0.16rem 0.45rem;
    }

    .risk-indicator-code {
        background: #FFFFFF;
        border: 1px solid #D9DEE5;
        border-radius: 3px;
        color: #66727F;
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: 0.76rem;
        font-weight: 650;
        letter-spacing: 0.025em;
        margin: 0;
        padding: 0.2rem 0.45rem;
        white-space: nowrap;
    }

    .risk-indicator-explanation {
        color: #1F2933;
        font-size: 0.9rem;
        line-height: 1.55;
        margin: 0.8rem 0 0;
    }

    .risk-evidence-grid {
        background: #F7F8FA;
        border: 1px solid #E4E8ED;
        display: grid;
        gap: 0;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin-top: 0.9rem;
    }

    .risk-evidence-item {
        border-right: 1px solid #E4E8ED;
        min-width: 0;
        padding: 0.7rem 0.8rem;
    }

    .risk-evidence-item:last-child {
        border-right: 0;
    }

    .risk-evidence-label {
        color: #66727F;
        font-size: 0.76rem;
        font-weight: 650;
        margin: 0 0 0.2rem;
        text-transform: uppercase;
    }

    .risk-evidence-value {
        color: #1F2933;
        font-size: 0.9rem;
        margin: 0;
        overflow-wrap: anywhere;
    }

    [data-testid="stDataFrame"] {
        background: #FFFFFF !important;
        border: 1px solid #D9DEE5;
        border-radius: 4px;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF !important;
        border-color: #D9DEE5 !important;
        box-shadow: none !important;
        color: #1F2933 !important;
    }

    [data-testid="stSelectbox"] div[role="group"],
    div[data-baseweb="select"] > div {
        background: #FFFFFF !important;
        border-color: #D9DEE5 !important;
        border-radius: 3px;
        color: #1F2933 !important;
    }

    [data-testid="stSelectbox"] input,
    div[data-baseweb="select"] input,
    div[data-baseweb="select"] span {
        color: #1F2933 !important;
        -webkit-text-fill-color: #1F2933 !important;
    }

    [data-testid="stSelectbox"] button svg,
    div[data-baseweb="select"] svg {
        fill: #17365D !important;
        color: #17365D !important;
    }

    [data-testid="stTextInput"] input,
    .stTextInput input {
        background: #FFFFFF !important;
        border-color: #D9DEE5 !important;
        color: #1F2933 !important;
        -webkit-text-fill-color: #1F2933 !important;
    }

    [data-testid="stSelectbox"] label p,
    [data-testid="stTextInput"] label p,
    .stSelectbox label p,
    .stTextInput label p {
        color: #1F2933 !important;
        font-weight: 650;
    }

    div[role="listbox"] {
        background: #FFFFFF !important;
        border: 1px solid #D9DEE5 !important;
    }

    div[role="option"] {
        background: #FFFFFF !important;
        color: #1F2933 !important;
    }

    div[role="option"]:hover,
    div[role="option"][aria-selected="true"] {
        background: #F2F4F7 !important;
        color: #102A43 !important;
    }

    /* Risk-page rhythm and restrained semantic status treatments. */
    .risk-context-note { background: #F4F7FA; margin: 1rem 0 1.6rem; padding: 0.7rem 0.9rem; }
    .risk-section-title { margin: 1.85rem 0 0.85rem; }
    .risk-summary-card { border-top: 0; border-left: 4px solid #17365D; min-height: 104px; padding: 0.95rem 1rem; }
    .risk-summary-high { background: #FFF9F9; border-left-color: #A64747; }
    .risk-summary-medium { background: #FFFBF3; border-left-color: #C47B19; }
    .risk-summary-normal { background: #F8FBF8; border-left-color: #4F7A5A; }
    .risk-summary-high .risk-summary-value { color: #8F3535; }
    .risk-summary-medium .risk-summary-value { color: #9A5B08; }
    .risk-summary-normal .risk-summary-value { color: #3F6849; }
    .risk-priority-high { background: #FFF4F4; border-color: #B75A5A; color: #8F3535; }
    .risk-priority-normal { background: #F2F8F3; border-color: #72927A; color: #3F6849; }
    .risk-indicator-card { margin-bottom: 0.7rem; padding: 0.8rem 0.95rem; }
    .risk-indicator-code { background: transparent; border: 0; color: #7A8794; font-size: 0.68rem; padding: 0.15rem 0; }
    .risk-indicator-explanation { margin-top: 0.5rem; }
    .risk-evidence-grid { margin-top: 0.65rem; }
    .risk-evidence-item { padding: 0.55rem 0.7rem; }

    .risk-section-intro { color: #566574; font-size: 0.88rem; line-height: 1.5; margin: -0.45rem 0 0.45rem; }
    .risk-record-count { color: #495765; font-size: 0.8rem; font-weight: 650; margin: 0.75rem 0 1.05rem; text-align: right; }
    .risk-warning-summary { background: #FFFFFF; border: 1px solid #D9DEE5; border-left: 4px solid #D99024; border-radius: 4px; display: grid; grid-template-columns: 1fr 0.7fr 2.3fr; margin-bottom: 0.875rem; padding: 0.95rem 1rem; }
    .risk-warning-summary-item { padding: 0.1rem 0.9rem; }
    .risk-warning-summary-item + .risk-warning-summary-item { border-left: 1px solid #E4E8ED; }
    .risk-warning-disclaimer { color: #66727F; font-size: 0.8rem; line-height: 1.45; margin: 0 0 1.375rem; }
    .risk-indicator-card.risk-warning-card { margin-bottom: 1rem; }
    .risk-warning-status { display: inline-block; margin: 0.25rem 0 0; }
    .risk-status-no-current-warning { background: #F2F4F7; border-color: #A4AFBA; color: #495765; }
    .risk-status-watch { background: #FFF9EF; border-color: #D9A45C; color: #80500D; }
    .risk-status-elevated { background: #FFF5E6; border-color: #C47B19; color: #8D5207; }
    .risk-status-high-attention { background: #FFF4F4; border-color: #B75A5A; color: #8F3535; }
    .risk-warning-evidence { background: #F7F8FA; border-left: 2px solid #D9DEE5; color: #364554; font-size: 0.84rem; line-height: 1.5; margin-top: 0.6rem; padding: 0.5rem 0.7rem; }
    .risk-schedule-flow { align-items: stretch; display: flex; gap: 0.5rem; margin: 0.4rem 0 0.9rem; }
    .risk-schedule-node { background: #FFFFFF; border: 1px solid #D9DEE5; border-radius: 3px; flex: 1; padding: 0.7rem 0.8rem; }
    .risk-schedule-node-latest { border-left: 3px solid #D99024; }
    .risk-schedule-arrow { align-self: center; color: #8090A0; font-size: 1.1rem; }
    .risk-attention-panel { background: #F7F8FA; border: 1px solid #D9DEE5; border-left: 4px solid #17365D; border-radius: 3px; color: #1F2933; margin-bottom: 1.5rem; padding: 0.8rem 1rem; }
    .risk-attention-panel ul { margin: 0; padding-left: 1.25rem; }
    .risk-attention-panel li { line-height: 1.55; margin: 0.25rem 0; }
    .risk-section-title.risk-trend-title { margin: 0.625rem 0 0.75rem; }
    .risk-project-summary { background: #FFFFFF; border: 1px solid #D9DEE5; border-left: 4px solid #17365D; border-radius: 4px; padding: 0.9rem 1rem; }
    .risk-project-summary-name { color: #102A43; font-size: 1.08rem; font-weight: 700; line-height: 1.4; margin: 0 0 0.75rem; }
    .risk-project-status-row { display: grid; gap: 0.75rem; grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .risk-project-status-item { border-right: 1px solid #E4E8ED; min-width: 0; padding-right: 0.7rem; }
    .risk-project-status-item:last-child { border-right: 0; }
    .risk-project-status-value { color: #17365D; display: block; font-size: 1.05rem; font-weight: 750; margin-top: 0.25rem; }
    .risk-project-key-risks { border-top: 1px solid #E7EAF0; margin-top: 0.8rem; padding-top: 0.7rem; }
    .risk-project-key-risks ul { margin: 0.35rem 0 0; padding-left: 1.25rem; }
    .risk-project-key-risks li { color: #1F2933; font-size: 0.86rem; line-height: 1.5; margin: 0.18rem 0; }
    .risk-project-data-quality { color: #66727F; font-size: 0.8rem; margin: 0.65rem 0 0; }
    .risk-actions-panel { background: #FFFFFF; border: 1px solid #D9DEE5; border-left: 4px solid #17365D; border-radius: 3px; padding: 0.25rem 1rem; }
    .risk-action-item { padding: 0.7rem 0; }
    .risk-action-item + .risk-action-item { border-top: 1px solid #E7EAF0; }
    .risk-action-title { color: #102A43; font-size: 0.9rem; font-weight: 700; margin: 0; }
    .risk-action-copy { color: #364554; font-size: 0.84rem; line-height: 1.5; margin: 0.25rem 0 0; }
    div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stSelectbox"]) { border-left: 4px solid #17365D !important; padding: 0.35rem 0.5rem; }

    @media (max-width: 760px) {
        .risk-detail-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .risk-evidence-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .risk-evidence-item:nth-child(2) {
            border-right: 0;
        }

        .risk-evidence-item:nth-child(-n+2) {
            border-bottom: 1px solid #E4E8ED;
        }

        .risk-warning-summary { grid-template-columns: 1fr; }
        .risk-warning-summary-item + .risk-warning-summary-item { border-left: 0; border-top: 1px solid #E4E8ED; margin-top: 0.6rem; padding-top: 0.7rem; }
        .risk-schedule-flow { flex-direction: column; }
        .risk-schedule-arrow { transform: rotate(90deg); }
        .risk-project-status-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .risk-project-status-item:nth-child(2) { border-right: 0; }
    }
</style>
"""

INDICATOR_LABELS = {
    "COST_REVIEW": "Cost Review",
    "SCHEDULE_REVIEW": "Schedule Review",
    "PROGRESS_STAGNATION_REVIEW": "Progress Stagnation",
    "EXPENDITURE_PROGRESS_REVIEW": "Expenditure-Progress Review",
    "REVISED_COST_UNAVAILABLE": "Revised Cost Unavailable",
    "REVISED_DOC_UNAVAILABLE": "Revised DoC Unavailable",
    "PHYSICAL_PROGRESS_UNAVAILABLE": "Physical Progress Unavailable",
}

INDICATOR_CATEGORY_OPTIONS = [
    "All Categories",
    "Cost Review",
    "Schedule Review",
    "Progress Review",
    "Expenditure-Progress Review",
    "Data Quality Review",
]

PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "NORMAL": 2}

REVIEW_ACTIONS = {
    "PROGRESS_SLOWDOWN": (
        "Review execution momentum",
        "Review recent milestone-level progress, compare planned versus reported physical progress where available, identify activities with slowing execution, and request an updated recovery/execution plan from the implementing agency.",
    ),
    "REPEATED_STAGNATION": (
        "Verify project progress",
        "Confirm whether physical work is actually stalled or whether reporting has not been updated. Review pending milestones and request the latest status and next expected milestone date.",
    ),
    "PROGRESS_STAGNATION_REVIEW": (
        "Review stagnant physical progress",
        "Verify the latest reported physical progress, review inactive or delayed milestones, and request an updated implementation status.",
    ),
    "EXPENDITURE_PROGRESS": (
        "Reconcile expenditure with physical progress",
        "Review expenditure incurred during the period and verify the corresponding physical work, procurement, or other supported project activity. Request supporting progress evidence where required.",
    ),
    "SCHEDULE": (
        "Review schedule extension",
        "Review the reason for the revised completion date, identify the activities driving the extension, and request the latest milestone/recovery schedule.",
    ),
    "COST_REVIEW": (
        "Review cost escalation",
        "Compare original and revised project cost, review approved scope or estimate changes, and identify the major reported cost-escalation components.",
    ),
    "REVISED_COST_UNAVAILABLE": (
        "Request updated revised cost",
        "Obtain the latest approved revised project cost before performing a complete cost-escalation assessment.",
    ),
    "REVISED_DOC_UNAVAILABLE": (
        "Request updated completion date",
        "Obtain the current expected/revised completion date before assessing schedule movement.",
    ),
    "PHYSICAL_PROGRESS_UNAVAILABLE": (
        "Request updated physical progress",
        "Obtain the latest physical-progress reporting before evaluating execution performance.",
    ),
}

REVIEW_ACTION_ORDER = [
    "PROGRESS_SLOWDOWN",
    "REPEATED_STAGNATION",
    "PROGRESS_STAGNATION_REVIEW",
    "EXPENDITURE_PROGRESS",
    "SCHEDULE",
    "COST_REVIEW",
    "REVISED_COST_UNAVAILABLE",
    "REVISED_DOC_UNAVAILABLE",
    "PHYSICAL_PROGRESS_UNAVAILABLE",
]


@st.cache_data(show_spinner=False)
def _load_monitoring_data(
    historical_file_modified_ns: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    del historical_file_modified_ns
    history = load_historical_projects()
    indicators = generate_monitoring_indicators(history)
    priorities = generate_review_priorities(history, indicators)
    warnings = generate_early_warnings(history, indicators)
    warning_status = generate_early_warning_status(history, warnings)
    return history, indicators, priorities, warnings, warning_status


def _month_label(report_month: str) -> str:
    return pd.Period(report_month, freq="M").strftime("%B %Y")


def _humanize_indicator_list(value: object) -> str:
    if value is None or pd.isna(value) or not str(value).strip():
        return "None"
    codes = [code.strip() for code in str(value).split(",") if code.strip()]
    return ", ".join(INDICATOR_LABELS.get(code, code) for code in codes)


def _safe(value: object) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return html.escape(str(value))


def _format_number(value: object) -> str:
    rendered = f"{float(value):,.2f}".rstrip("0").rstrip(".")
    return rendered


def _format_evidence_value(indicator: pd.Series, field: str) -> str:
    value = indicator[field]
    if value is None or pd.isna(value):
        return "Not available"

    code = indicator["indicator_code"]
    if code in {"COST_REVIEW", "EXPENDITURE_PROGRESS_REVIEW"}:
        formatted = f"₹{_format_number(value)} crore"
        if code == "COST_REVIEW" and field == "change_value":
            percentage = indicator.get("change_percent")
            if percentage is not None and pd.notna(percentage):
                formatted += f" ({_format_number(percentage)}%)"
        return formatted
    if code == "PROGRESS_STAGNATION_REVIEW":
        suffix = " percentage points" if field == "change_value" else "%"
        return f"{_format_number(value)}{suffix}"
    if code == "SCHEDULE_REVIEW" and field == "change_value":
        return f"{int(value)} month(s)"
    return str(value)


def _warning_evidence_text(warning: pd.Series) -> str:
    code = warning["warning_code"]
    if code in {"PROGRESS_SLOWDOWN", "REPEATED_STAGNATION"}:
        return (
            f"{warning['earliest_report_month']}: {_format_number(warning['earliest_physical_progress_pct'])}%; "
            f"{warning['previous_report_month']}: {_format_number(warning['previous_physical_progress_pct'])}%; "
            f"{warning['report_month']}: {_format_number(warning['current_physical_progress_pct'])}%. "
            f"Interval gains: {_format_number(warning['previous_progress_gain_pct_points'])} pp, "
            f"{_format_number(warning['current_progress_gain_pct_points'])} pp."
        )
    if code == "PROGRESS_STAGNATION_REVIEW":
        return (
            f"{warning['previous_report_month']}: {_format_number(warning['previous_physical_progress_pct'])}%; "
            f"{warning['report_month']}: {_format_number(warning['current_physical_progress_pct'])}%."
        )
    if code == "EXPENDITURE_PROGRESS_DIVERGENCE":
        return (
            f"{warning['previous_report_month']} to {warning['report_month']}: expenditure "
            f"₹{_format_number(warning['previous_expenditure_cr'])} crore → "
            f"₹{_format_number(warning['current_expenditure_cr'])} crore; physical progress "
            f"{_format_number(warning['previous_physical_progress_pct'])}% → "
            f"{_format_number(warning['current_physical_progress_pct'])}%."
        )
    if code == "SCHEDULE_DETERIORATION":
        return (
            f"{warning['previous_report_month']} to {warning['report_month']}: Revised DoC "
            f"{warning['previous_revised_doc']} → {warning['current_revised_doc']} "
            f"(+{int(warning['extension_months'])} months)."
        )
    return ""


def _recommended_review_actions(
    project_indicators: pd.DataFrame,
    active_warnings: pd.DataFrame,
) -> list[tuple[str, str]]:
    """Map active rule codes to a deduplicated, prioritized action list."""
    active_codes = set(project_indicators["indicator_code"].dropna().astype(str))
    active_codes.update(active_warnings["warning_code"].dropna().astype(str))

    if active_codes & {
        "EXPENDITURE_PROGRESS_REVIEW",
        "EXPENDITURE_PROGRESS_DIVERGENCE",
    }:
        active_codes.add("EXPENDITURE_PROGRESS")
    if active_codes & {"SCHEDULE_REVIEW", "SCHEDULE_DETERIORATION"}:
        active_codes.add("SCHEDULE")

    return [
        REVIEW_ACTIONS[code]
        for code in REVIEW_ACTION_ORDER
        if code in active_codes
    ][:4]


def _render_summary_card(label: str, value: int) -> None:
    status_class = {
        "HIGH Priority": "risk-summary-high",
        "MEDIUM Priority": "risk-summary-medium",
        "NORMAL Priority": "risk-summary-normal",
    }.get(label, "")
    st.markdown(
        f"""
        <div class="risk-summary-card {status_class}">
            <p class="risk-summary-label">{html.escape(label)}</p>
            <p class="risk-summary-value">{value:,}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


apply_shared_styles()
st.html(PAGE_CSS)
render_page_header(
    "Risk & Alerts",
    "Rule-based monitoring indicators derived from reported PAIMANA project data.",
)

st.markdown(
    f"""
    <div class="risk-context-note">
        {html.escape(REVIEW_PRIORITY_DISCLAIMER)} Monitoring indicators are
        screening signals based on reported data; they are not predictions.
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    history, indicators, priorities, warnings, warning_status = _load_monitoring_data(
        HISTORICAL_DATA_PATH.stat().st_mtime_ns
    )
except (FileNotFoundError, ValueError) as exc:
    st.error(f"Monitoring data could not be loaded: {exc}")
    st.stop()

available_months = sorted(priorities["report_month"].dropna().unique().tolist())
if not available_months:
    st.warning("No monitoring records are currently available.")
    st.stop()

st.markdown('<p class="risk-filter-title">Filters</p>', unsafe_allow_html=True)
with st.container(border=True):
    month_column, ministry_column, priority_column = st.columns([1, 1.7, 1.15])
    with month_column:
        selected_month = st.selectbox(
            "Report Month",
            available_months,
            index=len(available_months) - 1,
            format_func=_month_label,
        )

    month_ministries = sorted(
        priorities.loc[
            priorities["report_month"].eq(selected_month), "ministry"
        ].dropna().unique().tolist()
    )
    with ministry_column:
        selected_ministry = st.selectbox(
            "Ministry", ["All Ministries", *month_ministries]
        )
    with priority_column:
        selected_priority = st.selectbox(
            "Review Priority", ["All Priorities", "HIGH", "MEDIUM", "NORMAL"]
        )

    category_column, search_column = st.columns([1.25, 1.75])
    with category_column:
        selected_category = st.selectbox(
            "Indicator Category", INDICATOR_CATEGORY_OPTIONS
        )
    with search_column:
        project_search = st.text_input(
            "Project Search", placeholder="Project ID or project name"
        ).strip()

context_projects = priorities.loc[priorities["report_month"].eq(selected_month)].copy()
if selected_ministry != "All Ministries":
    context_projects = context_projects.loc[
        context_projects["ministry"].eq(selected_ministry)
    ]
if project_search:
    search_pattern = re.escape(project_search)
    search_matches = context_projects["project_id"].astype("string").str.contains(
        search_pattern, case=False, na=False
    ) | context_projects["project_name"].astype("string").str.contains(
        search_pattern, case=False, na=False
    )
    context_projects = context_projects.loc[search_matches]

if selected_category != "All Categories":
    category_project_ids = set(
        indicators.loc[
            indicators["report_month"].eq(selected_month)
            & indicators["indicator_category"].eq(selected_category),
            "project_id",
        ].astype("string")
    )
    context_projects = context_projects.loc[
        context_projects["project_id"].astype("string").isin(category_project_ids)
    ]

summary_counts = context_projects["review_priority"].value_counts()
st.markdown(
    '<p class="risk-section-title">Portfolio Review Summary</p>',
    unsafe_allow_html=True,
)
summary_columns = st.columns(4)
with summary_columns[0]:
    _render_summary_card("Projects Monitored", len(context_projects))
with summary_columns[1]:
    _render_summary_card("HIGH Priority", int(summary_counts.get("HIGH", 0)))
with summary_columns[2]:
    _render_summary_card("MEDIUM Priority", int(summary_counts.get("MEDIUM", 0)))
with summary_columns[3]:
    _render_summary_card("NORMAL Priority", int(summary_counts.get("NORMAL", 0)))

st.markdown(
    """
    <div style="
        padding-top: 14px;
        padding-bottom: 32px;
        color: #8A96A3;
        font-size: 0.82rem;
        line-height: 1.45;
    ">
        Summary cards reflect Report Month, Ministry, Indicator Category, and Project Search.
        Review Priority narrows the table only.
    </div>
    """,
    unsafe_allow_html=True,
)


filtered_projects = context_projects.copy()
if selected_priority != "All Priorities":
    filtered_projects = filtered_projects.loc[
        filtered_projects["review_priority"].eq(selected_priority)
    ]

filtered_projects["_priority_order"] = filtered_projects["review_priority"].map(
    PRIORITY_ORDER
)
filtered_projects["_project_name_order"] = filtered_projects[
    "project_name"
].astype("string").str.casefold()
filtered_projects = filtered_projects.sort_values(
    ["_priority_order", "_project_name_order", "project_id"], kind="stable"
).reset_index(drop=True)

st.markdown(
    '<p class="risk-section-title">Projects for Monitoring Review</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="risk-section-intro">Select a row to inspect its monitoring indicators. '
    'NORMAL means no substantive indicator triggered under the current prototype rules; '
    'it does not mean safe.</p>',
    unsafe_allow_html=True,
)

if filtered_projects.empty:
    st.info("No monitoring records match the selected filters.")
    st.stop()

table_data = pd.DataFrame(
    {
        "Project ID": filtered_projects["project_id"],
        "Project Name": filtered_projects["project_name"],
        "Ministry": filtered_projects["ministry"],
        "Sector": filtered_projects["sector"],
        "Review Priority": filtered_projects["review_priority"],
        "Substantive Indicators": filtered_projects[
            "triggered_substantive_indicators"
        ].map(_humanize_indicator_list),
        "Data Quality Indicators": filtered_projects[
            "triggered_data_quality_indicators"
        ].map(_humanize_indicator_list),
    }
)
styled_table = table_data.style.set_properties(
    **{
        "background-color": "#FFFFFF",
        "color": "#1F2933",
        "border-color": "#D9DEE5",
    }
)
styled_table = styled_table.map(
    lambda value: {
        "HIGH": "color: #8F3535; font-weight: 700; background-color: #FFF4F4",
        "MEDIUM": "color: #8D5207; font-weight: 700; background-color: #FFF9EF",
        "NORMAL": "color: #3F6849; font-weight: 700; background-color: #F2F8F3",
    }.get(str(value), ""),
    subset=["Review Priority"],
).set_table_styles(
    [{"selector": "th", "props": [("background-color", "#F2F4F7"), ("color", "#102A43"), ("font-weight", "700")]}]
)

st.markdown(
    f'<p class="risk-record-count">Showing {len(table_data):,} project-month record(s)</p>',
    unsafe_allow_html=True,
)
filter_signature = "|".join(
    [
        selected_month,
        selected_ministry,
        selected_priority,
        selected_category,
        project_search.casefold(),
    ]
)
table_key = "risk_project_table_" + hashlib.sha1(
    filter_signature.encode("utf-8")
).hexdigest()[:12]
table_event = st.dataframe(
    styled_table,
    hide_index=True,
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-row",
    key=table_key,
    column_config={
        "Project ID": st.column_config.TextColumn(width="small"),
        "Project Name": st.column_config.TextColumn(width="large"),
        "Ministry": st.column_config.TextColumn(width="medium"),
        "Sector": st.column_config.TextColumn(width="medium"),
        "Review Priority": st.column_config.TextColumn(width="small"),
        "Substantive Indicators": st.column_config.TextColumn(width="large"),
        "Data Quality Indicators": st.column_config.TextColumn(width="large"),
    },
)

selected_rows = table_event.selection.rows
if not selected_rows:
    st.info("Select a project row to view Monitoring Review Details.")
    st.stop()

selected_project = filtered_projects.iloc[selected_rows[0]]
project_id = str(selected_project["project_id"])
project_month = selected_project["report_month"]
priority_class = str(selected_project["review_priority"]).lower()
project_indicators = indicators.loc[
    indicators["report_month"].eq(project_month)
    & indicators["project_id"].astype("string").eq(project_id)
].copy()
indicator_order = {code: index for index, code in enumerate(INDICATOR_LABELS)}
project_indicators["_indicator_order"] = project_indicators["indicator_code"].map(
    indicator_order
)
project_indicators = project_indicators.sort_values("_indicator_order", kind="stable")
current_warning_status = warning_status.loc[
    warning_status["report_month"].eq(project_month)
    & warning_status["project_id"].astype("string").eq(project_id)
].iloc[0]
active_warnings = warnings.loc[
    warnings["report_month"].eq(project_month)
    & warnings["project_id"].astype("string").eq(project_id)
].copy()
warning_status_class = str(current_warning_status["early_warning_status"]).lower().replace(" ", "-")

substantive_indicators = project_indicators.loc[
    project_indicators["indicator_category"].ne("Data Quality Review")
]
data_quality_indicators = project_indicators.loc[
    project_indicators["indicator_category"].eq("Data Quality Review")
]
key_risk_explanations = list(active_warnings["explanation"].dropna().astype(str))
key_risk_explanations.extend(
    substantive_indicators["explanation"].dropna().astype(str).tolist()
)
key_risk_explanations = list(dict.fromkeys(key_risk_explanations))[:3]
if key_risk_explanations:
    key_risks_html = "<ul>" + "".join(
        f"<li>{_safe(explanation)}</li>" for explanation in key_risk_explanations
    ) + "</ul>"
else:
    key_risks_html = (
        '<p class="risk-project-data-quality">No active substantive monitoring or '
        "early-warning signal was detected for this reporting snapshot.</p>"
    )
data_quality_html = ""
if not data_quality_indicators.empty:
    quality_labels = " · ".join(
        data_quality_indicators["indicator_title"].dropna().astype(str).tolist()
    )
    data_quality_html = (
        f'<p class="risk-project-data-quality"><strong>Data Quality:</strong> '
        f"{_safe(quality_labels)}</p>"
    )

st.markdown(
    '<p class="risk-section-title">Project Risk Summary</p>',
    unsafe_allow_html=True,
)
st.html(
    f"""
    <section class="risk-project-summary">
        <p class="risk-project-summary-name">{_safe(selected_project['project_name'])}</p>
        <div class="risk-project-status-row">
            <div class="risk-project-status-item">
                <span class="risk-detail-label">Review Priority</span>
                <span class="risk-priority risk-priority-{priority_class}">{_safe(selected_project['review_priority'])}</span>
            </div>
            <div class="risk-project-status-item">
                <span class="risk-detail-label">Early Warning Status</span>
                <span class="risk-priority risk-status-{warning_status_class}">{_safe(current_warning_status['early_warning_status'])}</span>
            </div>
            <div class="risk-project-status-item">
                <span class="risk-detail-label">Monitoring Indicators</span>
                <span class="risk-project-status-value">{int(selected_project['substantive_indicator_count'])}</span>
            </div>
            <div class="risk-project-status-item">
                <span class="risk-detail-label">Early Warnings</span>
                <span class="risk-project-status-value">{int(current_warning_status['active_warning_count'])}</span>
            </div>
        </div>
        <div class="risk-project-key-risks">
            <span class="risk-detail-label">Key Risks</span>
            {key_risks_html}
            {data_quality_html}
        </div>
    </section>
    """
)

st.markdown(
    '<p class="risk-section-title">Monitoring Review Details</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f"""
    <section class="risk-detail-panel">
        <p class="risk-detail-name">{_safe(selected_project['project_name'])}</p>
        <div class="risk-detail-grid">
            <div class="risk-detail-item">
                <span class="risk-detail-label">Project ID</span>
                <span class="risk-detail-value">{_safe(project_id)}</span>
            </div>
            <div class="risk-detail-item">
                <span class="risk-detail-label">Ministry</span>
                <span class="risk-detail-value">{_safe(selected_project['ministry'])}</span>
            </div>
            <div class="risk-detail-item">
                <span class="risk-detail-label">Sector</span>
                <span class="risk-detail-value">{_safe(selected_project['sector'])}</span>
            </div>
            <div class="risk-detail-item">
                <span class="risk-detail-label">Report Month</span>
                <span class="risk-detail-value">{_safe(_month_label(project_month))}</span>
            </div>
            <div class="risk-detail-item">
                <span class="risk-detail-label">Source Report</span>
                <span class="risk-detail-value">{_safe(selected_project['source_report'])}</span>
            </div>
            <div class="risk-detail-item">
                <span class="risk-detail-label">Review Priority</span>
                <span class="risk-priority risk-priority-{priority_class}">
                    {_safe(selected_project['review_priority'])}
                </span>
            </div>
        </div>
        <p class="risk-priority-explanation">
            {_safe(selected_project['priority_explanation'])}
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="risk-section-title">Triggered Monitoring Indicators</p>',
    unsafe_allow_html=True,
)
if project_indicators.empty:
    st.info(
        "No substantive monitoring indicators triggered under the current prototype "
        "rules for this reporting snapshot."
    )
else:
    for _, indicator in project_indicators.iterrows():
        evidence = [
            ("Previous Value", _format_evidence_value(indicator, "previous_value")),
            ("Current Value", _format_evidence_value(indicator, "current_value")),
            ("Change Value", _format_evidence_value(indicator, "change_value")),
            ("Source Report", indicator["source_report"]),
        ]
        evidence_html = "".join(
            f"""
            <div class="risk-evidence-item">
                <p class="risk-evidence-label">{html.escape(label)}</p>
                <p class="risk-evidence-value">{_safe(value)}</p>
            </div>
            """
            for label, value in evidence
        )
        is_data_quality = indicator["indicator_category"] == "Data Quality Review"
        evidence_section = "" if is_data_quality else f'<div class="risk-evidence-grid">{evidence_html}</div>'
        st.markdown(
            f"""
            <section class="risk-indicator-card">
                <div class="risk-indicator-header">
                    <div>
                        <p class="risk-indicator-title">{_safe(indicator['indicator_title'])}</p>
                        <span class="risk-indicator-category">
                            {_safe(indicator['indicator_category'])}
                        </span>
                    </div>
                    <p class="risk-indicator-code">{_safe(indicator['indicator_code'])}</p>
                </div>
                <p class="risk-indicator-explanation">{_safe(indicator['explanation'])}</p>
                {evidence_section}
            </section>
            """,
            unsafe_allow_html=True,
        )

st.markdown(
    '<p class="risk-section-title">Early Warning Analysis</p>',
    unsafe_allow_html=True,
)
active_signal_text = str(current_warning_status["active_warning_names"] or "None").replace(", ", " · ")
st.markdown(
    f"""
    <section class="risk-warning-summary">
            <div class="risk-warning-summary-item">
                <span class="risk-detail-label">Early Warning Status</span>
                <span class="risk-priority risk-warning-status risk-status-{warning_status_class}">{_safe(current_warning_status['early_warning_status'])}</span>
            </div>
            <div class="risk-warning-summary-item">
                <span class="risk-detail-label">Active Warnings</span>
                <span class="risk-summary-value">{int(current_warning_status['active_warning_count'])}</span>
            </div>
            <div class="risk-warning-summary-item">
                <span class="risk-detail-label">Active Signals</span>
                <span class="risk-detail-value">{_safe(active_signal_text)}</span>
            </div>
    </section>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    f'<p class="risk-warning-disclaimer">{html.escape(EARLY_WARNING_DISCLAIMER)}</p>',
    unsafe_allow_html=True,
)

if active_warnings.empty:
    st.info("No current early-warning condition was detected from the available consecutive reporting history.")
else:
    for _, warning in active_warnings.iterrows():
        evidence_text = _warning_evidence_text(warning)
        st.markdown(
            f"""
            <section class="risk-indicator-card risk-warning-card">
                <p class="risk-indicator-title">{_safe(warning['warning_name'])}</p>
                <p class="risk-indicator-explanation">{_safe(warning['explanation'])}</p>
                <div class="risk-warning-evidence">{_safe(evidence_text)}</div>
            </section>
            """,
            unsafe_allow_html=True,
        )

st.markdown('<p class="risk-section-title">Why This Project Needs Attention</p>', unsafe_allow_html=True)
if active_warnings.empty:
    st.info("No active evidence-based early-warning explanation is available for this reporting snapshot.")
else:
    attention_items = "".join(
        f"<li>{_safe(explanation)}</li>" for explanation in active_warnings["explanation"]
    )
    st.markdown(
        f'<section class="risk-attention-panel"><ul>{attention_items}</ul></section>',
        unsafe_allow_html=True,
    )

st.markdown('<p class="risk-section-title">Recommended Review Actions</p>', unsafe_allow_html=True)
recommended_actions = _recommended_review_actions(project_indicators, active_warnings)
if not recommended_actions:
    st.info("No specific review action is currently generated from the active monitoring rules.")
else:
    actions_html = "".join(
        f"""
        <div class="risk-action-item">
            <p class="risk-action-title">{_safe(title)}</p>
            <p class="risk-action-copy">{_safe(action)}</p>
        </div>
        """
        for title, action in recommended_actions
    )
    st.html(f'<section class="risk-actions-panel">{actions_html}</section>')

project_history = history.loc[history["project_id"].astype("string").eq(project_id)].copy()
project_history["_period"] = pd.PeriodIndex(project_history["report_month"], freq="M")
project_history = project_history.sort_values("_period")
project_priorities = priorities.loc[priorities["project_id"].astype("string").eq(project_id)].copy()
project_priorities["_period"] = pd.PeriodIndex(project_priorities["report_month"], freq="M")
project_priorities = project_priorities.sort_values("_period")
project_warning_status = warning_status.loc[
    warning_status["project_id"].astype("string").eq(project_id)
].copy()
project_warning_status["_period"] = pd.PeriodIndex(project_warning_status["report_month"], freq="M")
project_warning_status = project_warning_status.sort_values("_period")

valid_three_month_windows = 0
if len(project_history) >= 3:
    periods = project_history["_period"].map(lambda value: value.ordinal)
    progress_present = project_history["physical_progress_pct"].notna()
    valid_three_month_windows = int(
        ((periods.diff().eq(1)) & (periods.diff().shift(1).eq(1))
         & progress_present & progress_present.shift(1).fillna(False)
         & progress_present.shift(2).fillna(False)).sum()
    )
if valid_three_month_windows == 0:
    st.warning("Insufficient consecutive history is available for the three-month Progress Slowdown and Repeated Stagnation rules. This is not treated as evidence of safety.")

trend_columns = st.columns(2)
priority_values = project_priorities["review_priority"].map({"NORMAL": 0, "MEDIUM": 1, "HIGH": 2})
with trend_columns[0]:
    st.markdown('<p class="risk-section-title risk-trend-title">Review Priority Trend</p>', unsafe_allow_html=True)
    priority_figure = go.Figure(go.Scatter(
        x=project_priorities["report_month"], y=priority_values, mode="lines+markers",
        line={"color": "#17365D", "width": 2}, marker={"size": 8},
        text=project_priorities["review_priority"], hovertemplate="%{x}<br>%{text}<extra></extra>",
    ))
    priority_figure.update_layout(height=310, margin={"l": 45, "r": 15, "t": 10, "b": 35}, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", showlegend=False)
    priority_figure.update_yaxes(tickmode="array", tickvals=[0, 1, 2], ticktext=["NORMAL", "MEDIUM", "HIGH"], range=[-0.15, 2.15], gridcolor="#E7EAF0")
    st.plotly_chart(priority_figure, use_container_width=True, config={"displayModeBar": False})
with trend_columns[1]:
    st.markdown('<p class="risk-section-title risk-trend-title">Warning Signal Trend</p>', unsafe_allow_html=True)
    warning_figure = go.Figure(go.Scatter(
        x=project_warning_status["report_month"], y=project_warning_status["active_warning_count"],
        mode="lines+markers", line={"color": "#D99024", "width": 2}, marker={"size": 8},
        text=project_warning_status["active_warning_names"],
        hovertemplate="%{x}<br>Distinct warnings: %{y}<br>%{text}<extra></extra>",
    ))
    warning_figure.update_layout(height=310, margin={"l": 45, "r": 15, "t": 10, "b": 35}, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", showlegend=False)
    warning_figure.update_yaxes(title="Distinct warnings", rangemode="tozero", dtick=1, gridcolor="#E7EAF0")
    st.plotly_chart(warning_figure, use_container_width=True, config={"displayModeBar": False})

st.markdown('<p class="risk-section-title">Expenditure vs Physical Progress</p>', unsafe_allow_html=True)
history_figure = go.Figure()
history_figure.add_trace(go.Scatter(
    x=project_history["report_month"], y=project_history["cumulative_expenditure_cr"],
    name="Cumulative expenditure (₹ crore)", mode="lines+markers", line={"color": "#17365D"},
    hovertemplate="%{x}<br>₹%{y:,.2f} crore<extra></extra>",
))
history_figure.add_trace(go.Scatter(
    x=project_history["report_month"], y=project_history["physical_progress_pct"],
    name="Physical progress (%)", mode="lines+markers", line={"color": "#D99024"}, yaxis="y2",
    hovertemplate="%{x}<br>%{y:,.2f}%<extra></extra>",
))
history_figure.update_layout(
    height=380, margin={"l": 65, "r": 65, "t": 15, "b": 40}, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
    yaxis={"title": "Cumulative expenditure (₹ crore)", "gridcolor": "#E7EAF0"},
    yaxis2={"title": "Physical progress (%)", "overlaying": "y", "side": "right", "range": [0, 100]},
    legend={"orientation": "h", "y": -0.18},
)
st.plotly_chart(history_figure, use_container_width=True, config={"displayModeBar": False})
st.caption("The two series use separate axes and units; ₹ crore and percentage values are not directly equivalent. Missing observations are not replaced with zero.")

st.markdown('<p class="risk-section-title">Schedule Movement</p>', unsafe_allow_html=True)
schedule_rows = project_history.loc[project_history["revised_doc"].notna()].copy()
if schedule_rows.empty:
    st.info("No valid reported Revised DoC observations are available for this project.")
else:
    schedule_comparisons = add_monitoring_comparisons(project_history.drop(columns="_period"))
    schedule_comparisons = schedule_comparisons.loc[schedule_comparisons["revised_doc"].notna()]
    original_docs = project_history["original_target_doc"].dropna().astype(str).unique().tolist()
    revised_docs = schedule_comparisons["revised_doc"].astype(str).tolist()
    schedule_nodes: list[tuple[str, str, bool]] = []
    if original_docs:
        schedule_nodes.append(("Original Target", original_docs[0], False))
    if revised_docs:
        schedule_nodes.append(("First Reported Revised", revised_docs[0], False))
        if len(revised_docs) > 1:
            schedule_nodes.append(("Latest Reported Revised", revised_docs[-1], True))
    schedule_flow = '<span class="risk-schedule-arrow">→</span>'.join(
        f"""
        <div class="risk-schedule-node {'risk-schedule-node-latest' if latest else ''}">
            <span class="risk-detail-label">{html.escape(label)}</span>
            <span class="risk-detail-value">{html.escape(value)}</span>
        </div>
        """
        for label, value, latest in schedule_nodes
    )
    st.markdown(f'<div class="risk-schedule-flow">{schedule_flow}</div>', unsafe_allow_html=True)
    schedule_table = pd.DataFrame({
        "Report Month": schedule_comparisons["report_month"].map(_month_label),
        "Reported Revised DoC": schedule_comparisons["revised_doc"],
        "Extension from Previous Report": schedule_comparisons["revised_doc_extension_months"].map(
            lambda value: f"+{int(value)} months" if pd.notna(value) and value > 0 else "—"
        ),
    })
    st.dataframe(schedule_table, hide_index=True, use_container_width=True)
