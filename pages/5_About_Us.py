from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from src.risk_engine import HISTORICAL_DATA_PATH, load_historical_projects
from src.ui import apply_shared_styles, render_page_header


PAGE_CSS = """
<style>
    .about-intro { color: #1F2933; font-size: 0.96rem; line-height: 1.65; max-width: 980px; }
    .about-section { margin-top: 2rem; }
    .about-section-title { color: #17365D; font-size: 1.2rem; font-weight: 700; margin: 0 0 0.7rem; }
    .about-copy { color: #364554; font-size: 0.92rem; line-height: 1.6; margin: 0 0 0.8rem; max-width: 1040px; }
    .about-highlight { background: #FFFFFF; border: 1px solid #D9DEE5; border-left: 4px solid #D99024; border-radius: 4px; color: #17365D; font-size: 0.9rem; font-weight: 700; letter-spacing: 0.025em; margin-top: 1rem; padding: 0.75rem 0.9rem; }
    .about-grid { display: grid; gap: 0.8rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .about-grid-three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .about-card { background: #FFFFFF; border: 1px solid #D9DEE5; border-radius: 5px; min-width: 0; padding: 0.85rem 0.95rem; }
    .about-card-accent { border-top: 3px solid #17365D; }
    .about-card-title { color: #102A43; font-size: 0.92rem; font-weight: 700; line-height: 1.4; margin: 0; }
    .about-card-copy { color: #495765; font-size: 0.84rem; line-height: 1.55; margin: 0.35rem 0 0; }
    .about-card-meta { color: #66727F; font-size: 0.74rem; font-weight: 700; letter-spacing: 0.035em; margin: 0 0 0.25rem; text-transform: uppercase; }
    .about-flow { display: grid; gap: 0.55rem; grid-template-columns: repeat(6, minmax(0, 1fr)); }
    .about-flow-item { background: #FFFFFF; border: 1px solid #D9DEE5; border-radius: 4px; min-width: 0; padding: 0.75rem; position: relative; }
    .about-flow-item:not(:last-child)::after { color: #D99024; content: "→"; font-weight: 700; position: absolute; right: -0.45rem; top: 42%; z-index: 1; }
    .about-architecture { border-left: 3px solid #17365D; margin: 0.4rem 0 0.9rem; padding-left: 0.85rem; }
    .about-architecture-step { color: #1F2933; font-size: 0.88rem; font-weight: 650; line-height: 1.45; padding: 0.25rem 0; }
    .about-architecture-arrow { color: #D99024; font-size: 0.8rem; padding-left: 0.25rem; }
    .about-months { color: #17365D; font-size: 0.88rem; font-weight: 700; margin: 0.6rem 0 0; }
    .about-note { background: #F2F4F7; border-left: 3px solid #D99024; color: #495765; font-size: 0.84rem; line-height: 1.55; margin-top: 0.85rem; padding: 0.7rem 0.85rem; }
    .about-status-grid { display: grid; gap: 0.65rem; grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .about-status { background: #FFFFFF; border: 1px solid #D9DEE5; border-radius: 4px; padding: 0.7rem 0.8rem; }
    .about-status-count { color: #66727F; font-size: 0.78rem; margin: 0; }
    .about-status-value { border: 1px solid #A4AFBA; border-radius: 3px; color: #495765; display: inline-block; font-size: 0.75rem; font-weight: 750; margin-top: 0.35rem; padding: 0.15rem 0.4rem; }
    .about-status-amber { background: #FFF9EF; border-color: #D99024; color: #70450B; }
    .about-status-red { background: #FFF4F4; border-color: #B75A5A; color: #8F3535; }
    .about-status-green { background: #F2F8F3; border-color: #72927A; color: #3F6849; }
    .about-list { color: #364554; font-size: 0.86rem; line-height: 1.6; margin: 0.4rem 0 0; padding-left: 1.15rem; }
    .about-list li { margin: 0.18rem 0; }
    .about-methodology { background: #FFFFFF; border: 1px solid #D9DEE5; border-left: 4px solid #17365D; border-radius: 4px; color: #1F2933; font-size: 0.9rem; line-height: 1.6; padding: 0.9rem 1rem; }
    .about-disclaimer { background: #F2F4F7; border: 1px solid #D9DEE5; border-radius: 4px; color: #495765; font-size: 0.82rem; line-height: 1.55; margin-top: 2rem; padding: 0.8rem 0.9rem; }
    @media (max-width: 900px) {
        .about-grid, .about-grid-three { grid-template-columns: 1fr; }
        .about-flow { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .about-flow-item::after { display: none; }
        .about-status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 560px) {
        .about-flow, .about-status-grid { grid-template-columns: 1fr; }
    }
</style>
"""


@st.cache_data(show_spinner=False)
def _available_months(modified_ns: int) -> list[str]:
    del modified_ns
    history = load_historical_projects()
    return sorted(history["report_month"].dropna().unique().tolist())


def _month_label(value: str) -> str:
    return pd.Period(value, freq="M").strftime("%B %Y")


def _section(title: str, copy: str | None = None) -> None:
    copy_html = f'<p class="about-copy">{html.escape(copy)}</p>' if copy else ""
    st.html(
        f'<section class="about-section"><h2 class="about-section-title">'
        f'{html.escape(title)}</h2>{copy_html}</section>'
    )


def _cards(items: list[tuple[str, str]], columns: int = 2) -> None:
    grid_class = "about-grid about-grid-three" if columns == 3 else "about-grid"
    cards = "".join(
        f'<article class="about-card about-card-accent"><h3 class="about-card-title">'
        f'{html.escape(title)}</h3><p class="about-card-copy">{html.escape(copy)}</p></article>'
        for title, copy in items
    )
    st.html(f'<div class="{grid_class}">{cards}</div>')


def _grouped_list(groups: list[tuple[str, list[str]]]) -> None:
    cards = "".join(
        f'<article class="about-card"><h3 class="about-card-title">{html.escape(title)}</h3>'
        f'<ul class="about-list">{"".join(f"<li>{html.escape(item)}</li>" for item in items)}</ul></article>'
        for title, items in groups
    )
    st.html(f'<div class="about-grid">{cards}</div>')


apply_shared_styles()
st.html(PAGE_CSS)
render_page_header(
    "About PAIMANA AI Monitor",
    "Early Warning & Project Intelligence for Infrastructure Monitoring",
)

st.html(
    """
    <div class="about-intro">
        <p>PAIMANA AI Monitor is a decision-support prototype designed to strengthen the monitoring of large Central Sector infrastructure projects using historical PAIMANA reporting data.</p>
        <p>Instead of treating each monthly report as an isolated snapshot, the platform connects project records across reporting periods and analyzes changes in cost, schedule, expenditure and physical progress.</p>
        <p>The objective is to help monitoring officers identify which projects need attention, understand why they were flagged, and determine what should be reviewed next.</p>
    </div>
    <div class="about-highlight">Monitor → Detect → Explain → Review → Act</div>
    """
)

_section("Why PAIMANA AI Monitor?")
st.html(
    """
    <div class="about-copy">
        <p>Infrastructure monitoring involves large portfolios containing projects across multiple ministries and sectors.</p>
        <p>Monthly project reports contain valuable information such as project cost, cumulative expenditure, physical progress and expected completion dates. However, identifying meaningful changes across reporting periods can require repeated manual comparison.</p>
        <p>A project may show multiple signals simultaneously — for example, rising expenditure, unchanged physical progress, a revised completion date and increasing project cost.</p>
        <p>Individually these are reporting fields. Viewed together and over time, they can identify projects that may require closer monitoring.</p>
    </div>
    """
)
_cards(
    [
        ("Reactive Monitoring", "Important changes can become clearer only after comparing multiple reporting periods."),
        ("Fragmented Signals", "Cost, expenditure, schedule and physical progress often need to be reviewed together."),
        ("Monitoring at Scale", "A structured prioritization layer helps officers identify where deeper review may be required."),
    ],
    columns=3,
)

_section(
    "Our Approach",
    "PAIMANA AI Monitor transforms historical project reporting into a continuous monitoring workflow. Instead of asking only what the current status is, the system also examines what changed since the previous reporting period and whether a concerning pattern is beginning to emerge.",
)
workflow = [
    ("Historical PAIMANA Data", "Uses reported monthly infrastructure project information."),
    ("Month-to-Month Comparison", "Connects project records across consecutive reporting periods."),
    ("Monitoring Indicators", "Identifies reported cost, schedule, expenditure and progress conditions."),
    ("Early Warning Signals", "Detects emerging patterns across multiple consecutive reporting periods."),
    ("Review Priority", "Prioritizes projects for monitoring review using transparent deterministic rules."),
    ("Recommended Review Actions", "Suggests practical next review steps based on active monitoring conditions."),
]
workflow_html = "".join(
    f'<article class="about-flow-item"><h3 class="about-card-title">{html.escape(title)}</h3>'
    f'<p class="about-card-copy">{html.escape(copy)}</p></article>'
    for title, copy in workflow
)
st.html(f'<div class="about-flow">{workflow_html}</div>')

_section(
    "How PAIMANA AI Monitor Works",
    "The platform processes monthly PAIMANA infrastructure project reports and builds a normalized historical project dataset. Records are connected using Project ID so that project values can be compared across available reporting months.",
)
architecture = [
    "Official PAIMANA Monthly Reports",
    "Data Extraction & Validation",
    "Historical Project Dataset",
    "Month-to-Month Comparison Engine",
    "Monitoring Indicators",
    "Early Warning Engine",
    "Review Priority",
    "Recommended Review Actions",
    "Dashboards & Reports",
]
architecture_html = "".join(
    f'<div class="about-architecture-step">{html.escape(step)}</div>'
    + ('<div class="about-architecture-arrow">↓</div>' if index < len(architecture) - 1 else "")
    for index, step in enumerate(architecture)
)
try:
    months = _available_months(HISTORICAL_DATA_PATH.stat().st_mtime_ns)
except (FileNotFoundError, ValueError):
    months = []
months_text = " → ".join(_month_label(month) for month in months)
st.html(
    f'<div class="about-architecture">{architecture_html}</div>'
    + (f'<p class="about-months">Available sequence: {html.escape(months_text)}</p>' if months_text else "")
)

_section(
    "Monitoring Indicators",
    "The monitoring engine uses transparent deterministic rules. Each indicator is tied directly to reported project values.",
)
_cards(
    [
        ("Cost Review", "Triggered when an available revised project cost is greater than the original project cost."),
        ("Schedule Review", "Triggered when the revised completion date moves later compared with the previous consecutive reporting period."),
        ("Progress Stagnation Review", "Triggered when reported physical progress remains unchanged between consecutive reporting periods."),
        ("Expenditure–Progress Review", "Triggered when cumulative expenditure increases while reported physical progress remains unchanged."),
    ]
)
st.html('<div class="about-note">Monitoring indicators are screening signals for review. They do not by themselves establish the cause of a project issue.</div>')

_section(
    "Early Warning System",
    "The Early Warning System looks beyond a single reporting period and searches for developing patterns across consecutive months.",
)
_cards(
    [
        ("Progress Slowdown", "Detects when physical progress is still increasing but the latest gain is lower than the previous gain. Example: April → May: +6 percentage points; May → June: +2 percentage points."),
        ("Repeated Stagnation", "Detects unchanged reported physical progress across multiple consecutive reporting periods. Example: June: 69%; July: 69%; August: 69%."),
        ("Expenditure–Progress Divergence", "Detects cumulative expenditure increasing while reported physical progress does not increase."),
        ("Schedule Deterioration", "Detects when the revised completion date moves later compared with the previous reporting period."),
    ]
)
status_items = [
    ("0 signals", "NO CURRENT WARNING", ""),
    ("1 signal", "WATCH", "about-status-amber"),
    ("2 signals", "ELEVATED", "about-status-amber"),
    ("3+ signals", "HIGH ATTENTION", "about-status-red"),
]
status_html = "".join(
    f'<div class="about-status"><p class="about-status-count">{count}</p>'
    f'<span class="about-status-value {css}">{label}</span></div>'
    for count, label, css in status_items
)
st.html(f'<div class="about-status-grid">{status_html}</div><div class="about-note">The Early Warning Status is a screening aid, not a prediction of project failure.</div>')

_section("Review Priority")
priority_html = "".join(
    [
        '<div class="about-status"><p class="about-status-count">0 substantive monitoring indicators</p><span class="about-status-value about-status-green">NORMAL</span></div>',
        '<div class="about-status"><p class="about-status-count">1 substantive monitoring indicator</p><span class="about-status-value about-status-amber">MEDIUM</span></div>',
        '<div class="about-status"><p class="about-status-count">2 or more substantive monitoring indicators</p><span class="about-status-value about-status-red">HIGH</span></div>',
    ]
)
st.html(
    f'<div class="about-grid about-grid-three">{priority_html}</div>'
    '<p class="about-copy">Data-quality conditions do not increase Review Priority. Missing information is reported separately rather than treated as evidence of project risk.</p>'
    '<ul class="about-list"><li>Revised Cost Unavailable</li><li>Revised Completion Date Unavailable</li><li>Physical Progress Unavailable</li></ul>'
)

_section(
    "Project Risk Summary",
    "For each selected project, PAIMANA AI Monitor brings together the most important monitoring information into a single summary.",
)
_cards(
    [(label, "Presented from the selected project-month's calculated monitoring context.") for label in ["Review Priority", "Early Warning Status", "Monitoring Indicators", "Early Warnings", "Key Risks"]]
)

_section(
    "Recommended Review Actions",
    "PAIMANA AI Monitor does not stop at identifying a monitoring condition. It maps active conditions to practical areas for officer review.",
)
_cards(
    [
        ("Progress Slowdown — Review execution momentum", "Review recent milestone-level progress, compare planned and reported physical progress where available, identify slowing activities and request an updated recovery or execution plan."),
        ("Repeated Stagnation — Verify project progress", "Confirm whether the project has genuinely stalled or whether reported progress has not been updated, review pending milestones and request the latest implementation status."),
        ("Expenditure–Progress Divergence — Reconcile expenditure with physical progress", "Review expenditure incurred during the period and verify the corresponding physical work, procurement or reported activity."),
        ("Schedule Deterioration — Review schedule extension", "Review the revised completion date, available reasons for the change and the latest milestone or recovery schedule."),
        ("Cost Review — Review cost escalation", "Compare original and revised project costs and review available information regarding approved estimate or scope changes."),
    ]
)
st.html('<div class="about-note">Recommended Review Actions support officer review. They are not administrative decisions.</div>')

_section("Current Prototype Capabilities")
_grouped_list(
    [
        ("Portfolio Monitoring", ["Reporting-month and ministry filtering", "Sector-level analysis", "State-wise project monitoring", "Portfolio cost and expenditure views"]),
        ("Project-Level Analysis", ["Historical project drill-down", "Cost and expenditure history", "Physical-progress history", "Completion-schedule history"]),
        ("Risk & Alerts", ["Monitoring indicators", "Early Warning System and status", "Review Priority and Project Risk Summary", "Key Risks and Recommended Review Actions", "Priority and warning trends", "Expenditure versus progress and schedule movement"]),
        ("Analytics", ["Portfolio, cost and expenditure trends", "Financial expenditure ratio", "Median progress and progress distribution", "Ministry and sector composition", "Schedule and data-quality coverage"]),
        ("Reporting", ["PDF report export", "Project-data CSV export"]),
    ]
)

_section(
    "Explainability & Auditability",
    "A core design principle of PAIMANA AI Monitor is that every monitoring flag should be understandable. Instead of only showing HIGH, the system can show supporting evidence such as: “Cumulative expenditure increased while reported physical progress remained unchanged.”",
)
_grouped_list(
    [("Evidence available to users", ["Reporting period", "Previous value", "Current value", "Change value", "Source report", "Triggered monitoring condition"])]
)

_section(
    "Data Quality Awareness",
    "Infrastructure reporting data can contain missing or unavailable information. PAIMANA AI Monitor identifies these conditions explicitly instead of silently replacing unavailable values with zero.",
)
_cards(
    [
        ("Revised Cost Unavailable", "Reported separately as a data-quality condition."),
        ("Revised DoC Unavailable", "Reported separately as a data-quality condition."),
        ("Physical Progress Unavailable", "Reported separately as a data-quality condition."),
    ],
    columns=3,
)
st.html('<div class="about-note">Data-quality conditions are displayed separately from substantive monitoring risks.</div>')

_section("Technology Stack")
_cards(
    [
        ("Application", "Streamlit"),
        ("Core Language", "Python"),
        ("Data Processing", "Pandas + NumPy"),
        ("Visualization", "Plotly"),
        ("Historical Report Extraction", "pdfplumber"),
        ("Reporting", "ReportLab"),
        ("Version Control", "GitHub"),
        ("Deployment", "Streamlit Community Cloud"),
    ]
)

_section("Current Methodology")
st.html(
    """
    <div class="about-methodology">
        PAIMANA AI Monitor currently uses transparent rule-based monitoring and historical trend analysis rather than a trained predictive machine-learning model.<br><br>
        This approach allows every monitoring signal to be linked directly to reported project values and clearly explained to the user.<br><br>
        The architecture can later incorporate validated statistical or machine-learning models without replacing the transparent evidence layer.
    </div>
    """
)

_section("Design Principles")
_cards(
    [
        ("Transparent", "Monitoring decisions are based on visible deterministic rules."),
        ("Evidence-Based", "Each indicator is linked to reported project values and reporting periods."),
        ("Human-in-the-Loop", "The system supports monitoring officers rather than replacing administrative judgement."),
        ("Data-Aware", "Missing information is handled explicitly as a data-quality condition."),
        ("Explainable", "Users can see why a project was flagged and what changed."),
        ("Action-Oriented", "Monitoring results lead to suggested areas for further review."),
    ]
)

_section("Future Scope", "The following items are future work and are not current prototype capabilities.")
_cards(
    [
        ("Longer Historical Coverage", "Integrate additional monthly PAIMANA reports to strengthen trend analysis."),
        ("Statistical Baselines", "Identify unusual project behaviour relative to historical patterns."),
        ("Validated Predictive Models", "Explore delay or cost-risk estimation only after sufficient historical outcome data and model validation are available."),
        ("Explainable Machine Learning", "Retain transparent evidence alongside any future predictive signals."),
        ("Cross-Project Benchmarking", "Compare projects with similar sectors, ministries or implementation characteristics."),
        ("PAIMANA Copilot", "Provide a grounded conversational interface for explaining project history, monitoring indicators, early warnings and recommended review actions."),
    ]
)

_section("Data Source")
st.html(
    '<p class="about-copy">Source: PAIMANA / Infrastructure &amp; Project Monitoring Division monthly infrastructure project reporting data used in this prototype.</p>'
    + (f'<p class="about-months">Available reporting months: {html.escape(", ".join(_month_label(month) for month in months))}</p>' if months else "")
)

st.html(
    '<div class="about-disclaimer">PAIMANA AI Monitor is a prototype decision-support tool developed for demonstration purposes. Monitoring indicators, early-warning statuses, review priorities and recommended review actions generated by the prototype are not official MoSPI/IPMD classifications, findings or administrative decisions.</div>'
)
