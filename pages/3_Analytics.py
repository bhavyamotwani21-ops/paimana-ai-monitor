from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.risk_engine import HISTORICAL_DATA_PATH, load_historical_projects
from src.ui import apply_shared_styles, render_page_header


PAGE_CSS = """
<style>
.page-heading-rule {
    display: none;
}
.page-heading {
    margin-bottom: 0.45rem !important;
}

.page-introduction {
    margin-bottom: 1.2rem !important;
}
    .analytics-supporting {
    color: #66727F;
    font-size: 0.94rem;
    line-height: 1.45;
    margin: 0 0 1.25rem;
}
    .analytics-filter-title { color: #17365D; font-size: 0.9rem; font-weight: 700; letter-spacing: 0.025em; margin: 0 0 0.55rem; text-transform: uppercase; }
    .analytics-context {
    color: #66727F;
    font-size: 0.84rem;
    line-height: 1.45;
    margin: 0 0 0.75rem;
}
    .analytics-section-title { color: #17365D; font-size: 1.18rem; font-weight: 700; margin: 1.65rem 0 0.4rem; }
    .analytics-section-note { color: #66727F; font-size: 0.84rem; margin: 0 0 0.65rem; }
    .analytics-kpi {
    background: #FFFFFF;
    border: 1px solid #D9DEE5;
    border-top: 3px solid #17365D;
    border-radius: 5px;
    box-sizing: border-box;
    height: 132px;
    padding: 1rem 1.1rem;
}   
    .analytics-chart-title {
    color: #1F2933;
    font-size: 1rem;
    font-weight: 700;
    line-height: 1.35;
    margin: 0 0 0.8rem;
}
    .analytics-kpi-label { color: #66727F; font-size: 0.73rem; font-weight: 700; letter-spacing: 0.03em; line-height: 1.3; margin: 0; text-transform: uppercase; }
    .analytics-kpi-value { color: #17365D; font-size: 1.28rem; font-weight: 750; line-height: 1.25; margin: 0.4rem 0 0; overflow-wrap: anywhere; }
    .analytics-coverage-note {
    background: #F2F4F7;
    border-left: 3px solid #D99024;
    color: #495765;
    font-size: 0.86rem;
    line-height: 1.5;
    margin: 1rem 0 1.8rem;
    padding: 0.8rem 1rem;
}
    [data-testid="stPlotlyChart"] {
    background: #FFFFFF;
    border: 1px solid #D9DEE5;
    border-radius: 5px;
    padding: 0.35rem 0.5rem 0.3rem;
    margin-bottom: 0.8rem;
}
    [data-testid="stDataFrame"], [data-testid="stVerticalBlockBorderWrapper"] { background: #FFFFFF !important; border-color: #D9DEE5 !important; box-shadow: none !important; }
    [data-testid="stSelectbox"] div[role="group"], div[data-baseweb="select"] > div { background: #FFFFFF !important; border-color: #D9DEE5 !important; color: #1F2933 !important; }
    [data-testid="stSelectbox"] input, div[data-baseweb="select"] input, div[data-baseweb="select"] span { color: #1F2933 !important; -webkit-text-fill-color: #1F2933 !important; }
    [data-testid="stSelectbox"] button svg, div[data-baseweb="select"] svg { color: #17365D !important; fill: #17365D !important; }
    [data-testid="stSelectbox"] label p, .stSelectbox label p { color: #1F2933 !important; font-weight: 650; }
    div[role="listbox"], div[role="option"] { background: #FFFFFF !important; color: #1F2933 !important; }
    div[role="option"]:hover, div[role="option"][aria-selected="true"] { background: #F2F4F7 !important; color: #102A43 !important; }
</style>
"""

NAVY = "#17365D"
SAFFRON = "#D99024"
SLATE = "#66727F"
LIGHT_COLORS = ["#17365D", "#315A83", "#6684A3", "#D99024", "#AAB7C4"]
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}


@st.cache_data(show_spinner=False)
def _load_history(historical_file_modified_ns: int) -> pd.DataFrame:
    del historical_file_modified_ns
    return load_historical_projects()


def _month_label(report_month: str) -> str:
    return pd.Period(report_month, freq="M").strftime("%B %Y")


def _format_crore(value: object) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"₹{float(value):,.2f} crore"


def _format_percentage(value: object) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"{float(value):,.2f}%"


def _render_kpi(label: str, value: str) -> None:
    st.html(
        f'<div class="analytics-kpi"><p class="analytics-kpi-label">'
        f'{html.escape(label)}</p><p class="analytics-kpi-value">'
        f'{html.escape(value)}</p></div>'
    )


def _section(title: str, note: str | None = None) -> None:
    st.markdown(
        f'<p class="analytics-section-title">{html.escape(title)}</p>',
        unsafe_allow_html=True,
    )
    if note:
        st.markdown(
            f'<p class="analytics-section-note">{html.escape(note)}</p>',
            unsafe_allow_html=True,
        )


def _line_chart(
    x: list[str],
    y: list[float],
    y_title: str,
    hover_template: str,
    *,
    suffix: str = "",
) -> go.Figure:
    labels = [_month_label(month) for month in x]
    figure = go.Figure(
        go.Scatter(
            x=labels,
            y=y,
            mode="lines+markers+text",
            line={"color": NAVY, "width": 2.5},
            marker={"color": SAFFRON, "size": 7},
            text=[f"{value:,.2f}{suffix}" for value in y],
            textposition="top center",
            hovertemplate=hover_template,
        )
    )
    figure.update_layout(
        height=290,
        margin={"l": 35, "r": 18, "t": 24, "b": 40},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "Segoe UI, Arial, sans-serif", "color": "#1F2933"},
        showlegend=False,
    )
    figure.update_xaxes(type="category")
    figure.update_yaxes(
        title=y_title, gridcolor="#E7EAF0", rangemode="tozero", zeroline=False
    )
    return figure


def _progress_band_counts(frame: pd.DataFrame, months: list[str]) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for month in months:
        values = pd.to_numeric(
            frame.loc[frame["report_month"].eq(month), "physical_progress_pct"],
            errors="coerce",
        ).dropna()
        records.extend(
            [
                {"report_month": month, "band": "0–25%", "count": int(values.between(0, 25, inclusive="both").sum())},
                {"report_month": month, "band": "26–50%", "count": int((values.gt(25) & values.le(50)).sum())},
                {"report_month": month, "band": "51–75%", "count": int((values.gt(50) & values.le(75)).sum())},
                {"report_month": month, "band": "76–99%", "count": int((values.gt(75) & values.lt(100)).sum())},
                {"report_month": month, "band": "100%", "count": int(values.eq(100).sum())},
            ]
        )
    return pd.DataFrame(records)


apply_shared_styles()
st.html(PAGE_CSS)
render_page_header("Analytics", "Portfolio Trends & Comparative Analysis")
st.markdown(
    '<p class="analytics-supporting">Descriptive analysis of reported PAIMANA '
    'project data across available reporting months.</p>',
    unsafe_allow_html=True,
)

try:
    history = _load_history(HISTORICAL_DATA_PATH.stat().st_mtime_ns)
except (FileNotFoundError, ValueError) as exc:
    st.error(f"Historical project data could not be loaded: {exc}")
    st.stop()

st.markdown('<p class="analytics-filter-title">Filters</p>', unsafe_allow_html=True)
with st.container(border=True):
    ministry_column, sector_column = st.columns(2)
    ministries = sorted(history["ministry"].dropna().unique().tolist())
    with ministry_column:
        selected_ministry = st.selectbox("Ministry", ["All Ministries", *ministries])

    ministry_context = history
    if selected_ministry != "All Ministries":
        ministry_context = ministry_context.loc[
            ministry_context["ministry"].eq(selected_ministry)
        ]
    sectors = sorted(ministry_context["sector"].dropna().unique().tolist())
    with sector_column:
        selected_sector = st.selectbox("Sector", ["All Sectors", *sectors])

analytics_data = ministry_context.copy()
if selected_sector != "All Sectors":
    analytics_data = analytics_data.loc[analytics_data["sector"].eq(selected_sector)]

if analytics_data.empty:
    st.info("No analytics records match the selected filters.")
    st.stop()

months = sorted(analytics_data["report_month"].dropna().unique().tolist())
latest_month = months[-1]
latest_snapshot = analytics_data.loc[analytics_data["report_month"].eq(latest_month)]
latest_project_count = int(latest_snapshot["project_id"].nunique())
latest_original_cost = latest_snapshot["original_cost_cr"].sum(min_count=1)
latest_expenditure = latest_snapshot["cumulative_expenditure_cr"].sum(min_count=1)
latest_median_progress = latest_snapshot["physical_progress_pct"].median(skipna=True)

_section("Latest Snapshot")
st.markdown(
    f'<p class="analytics-context"><strong>Latest available reporting snapshot:</strong> '
    f'{html.escape(_month_label(latest_month))}</p>',
    unsafe_allow_html=True,
)
kpi_columns = st.columns(4)
with kpi_columns[0]:
    _render_kpi("Ongoing Projects", f"{latest_project_count:,}")
with kpi_columns[1]:
    _render_kpi("Original Cost", _format_crore(latest_original_cost))
with kpi_columns[2]:
    _render_kpi("Cumulative Expenditure", _format_crore(latest_expenditure))
with kpi_columns[3]:
    _render_kpi("Median Reported Physical Progress", _format_percentage(latest_median_progress))

monthly = (
    analytics_data.groupby("report_month", sort=True)
    .agg(
        projects=("project_id", "nunique"),
        original_cost=("original_cost_cr", lambda values: values.sum(min_count=1)),
        expenditure=("cumulative_expenditure_cr", lambda values: values.sum(min_count=1)),
        median_progress=("physical_progress_pct", "median"),
    )
    .reindex(months)
)
monthly["financial_ratio"] = monthly["expenditure"].div(monthly["original_cost"]).mul(100)

_section(
    "Portfolio Over Time",
    "Projects present in each reported ongoing-project snapshot.",
)
if len(months) >= 2:
    project_figure = _line_chart(
        months,
        monthly["projects"].astype(float).tolist(),
        "Projects",
        "%{x}<br>%{y:,.0f} projects<extra></extra>",
    )
    project_figure.update_traces(text=[f"{value:,.0f}" for value in monthly["projects"]])
    st.plotly_chart(project_figure, use_container_width=True, config=PLOT_CONFIG)
else:
    st.caption("Only one reporting month is available in this filter context.")

_section("Financial Analytics")
financial_columns = st.columns(2)
with financial_columns[0]:
    st.markdown("**Original Cost Trend**")
    if len(months) >= 2:
        st.plotly_chart(
            _line_chart(months, monthly["original_cost"].tolist(), "₹ crore", "%{x}<br>₹%{y:,.2f} crore<extra></extra>"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )
    else:
        st.caption("Only one reported observation is available.")
with financial_columns[1]:
    st.markdown("**Cumulative Expenditure Trend**")
    if len(months) >= 2:
        st.plotly_chart(
            _line_chart(months, monthly["expenditure"].tolist(), "₹ crore", "%{x}<br>₹%{y:,.2f} crore<extra></extra>"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )
    else:
        st.caption("Only one reported observation is available.")

st.markdown("**Financial Expenditure Ratio Trend**")
st.caption("Cumulative expenditure as a percentage of original project cost.")
if len(months) >= 2:
    st.plotly_chart(
        _line_chart(months, monthly["financial_ratio"].tolist(), "Financial Expenditure Ratio (%)", "%{x}<br>%{y:,.2f}%<extra></extra>", suffix="%"),
        use_container_width=True,
        config=PLOT_CONFIG,
    )
else:
    st.caption("Only one reported observation is available.")

revised_available_latest = int(
    latest_snapshot["revised_cost_available"].fillna(False).astype(bool).sum()
)
st.markdown(
    f'<div class="analytics-coverage-note"><strong>Revised-cost coverage:</strong> '
    f'available for {revised_available_latest:,} of {latest_project_count:,} projects '
    f'in {_month_label(latest_month)}. No revised-cost trend is shown where row-level '
    f'coverage is unavailable.</div>',
    unsafe_allow_html=True,
)

_section("Physical Progress Analytics")
physical_columns = st.columns(2)
with physical_columns[0]:
    st.markdown(
    '<p class="analytics-chart-title">Median Reported Physical Progress (%)</p>',
    unsafe_allow_html=True,
)
    if len(months) >= 2:
        valid_median = monthly["median_progress"].dropna()
        st.plotly_chart(
            _line_chart(valid_median.index.tolist(), valid_median.tolist(), "Median Reported Physical Progress (%)", "%{x}<br>%{y:,.2f}%<extra></extra>", suffix="%"),
            use_container_width=True,
            config=PLOT_CONFIG,
        )
    else:
        st.caption("Only one reporting month is available in this filter context.")
with physical_columns[1]:
    st.markdown(
    '<p class="analytics-chart-title">Physical Progress Distribution by Month</p>',
    unsafe_allow_html=True,
)
    distribution = _progress_band_counts(analytics_data, months)
    distribution_figure = go.Figure()
    for index, band in enumerate(["0–25%", "26–50%", "51–75%", "76–99%", "100%"]):
        band_data = distribution.loc[distribution["band"].eq(band)]
        distribution_figure.add_bar(
            name=band,
            x=band_data["report_month"].map(_month_label),
            y=band_data["count"],
            marker_color=LIGHT_COLORS[index],
            hovertemplate=f"{band}<br>%{{x}}: %{{y:,}} projects<extra></extra>",
        )
    distribution_figure.update_layout(
        barmode="stack",
        height=290,
        margin={"l": 35, "r": 18, "t": 16, "b": 40},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "Segoe UI, Arial, sans-serif", "color": "#1F2933"},
        legend={"orientation": "h", "y": -0.2},
    )
    distribution_figure.update_yaxes(title="Projects", gridcolor="#E7EAF0", zeroline=False)
    st.plotly_chart(distribution_figure, use_container_width=True, config=PLOT_CONFIG)

_section(
    "Portfolio Composition",
    f"Latest available reporting snapshot: {_month_label(latest_month)}.",
)
composition_columns = st.columns(2 if selected_ministry == "All Ministries" else 1)
composition_index = 0
sector_counts = latest_snapshot.groupby("sector")["project_id"].nunique().sort_values()
if selected_ministry == "All Ministries":
    ministry_counts = latest_snapshot.groupby("ministry")["project_id"].nunique().sort_values()
    composition_height = max(
        360,
        min(620, 24 * max(len(ministry_counts), len(sector_counts)) + 80),
    )
    with composition_columns[composition_index]:
        st.markdown(
    '<p class="analytics-chart-title">Projects by Ministry</p>',
    unsafe_allow_html=True,
)
        ministry_figure = go.Figure(go.Bar(
            x=ministry_counts.tolist(), y=ministry_counts.index.tolist(), orientation="h",
            marker_color=NAVY, hovertemplate="%{y}<br>%{x:,} projects<extra></extra>",
        ))
        ministry_figure.update_layout(height=composition_height, margin={"l": 20, "r": 30, "t": 15, "b": 40}, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font={"family": "Segoe UI, Arial, sans-serif", "color": "#1F2933"}, showlegend=False)
        ministry_figure.update_xaxes(title="Projects", gridcolor="#E7EAF0", zeroline=False)
        st.plotly_chart(ministry_figure, use_container_width=True, config=PLOT_CONFIG)
    composition_index += 1

else:
    composition_height = max(360, min(620, 24 * len(sector_counts) + 80))
with composition_columns[composition_index]:
    st.markdown("**Projects by Sector**")
    sector_figure = go.Figure(go.Bar(
        x=sector_counts.tolist(), y=sector_counts.index.tolist(), orientation="h",
        marker_color=NAVY, hovertemplate="%{y}<br>%{x:,} projects<extra></extra>",
    ))
    sector_figure.update_layout(height=composition_height, margin={"l": 20, "r": 30, "t": 15, "b": 40}, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font={"family": "Segoe UI, Arial, sans-serif", "color": "#1F2933"}, showlegend=False)
    sector_figure.update_xaxes(title="Projects", gridcolor="#E7EAF0", zeroline=False)
    st.plotly_chart(sector_figure, use_container_width=True, config=PLOT_CONFIG)

_section("Schedule Reporting")
schedule_rows = []
coverage_rows = []
for month in months:
    month_frame = analytics_data.loc[analytics_data["report_month"].eq(month)]
    revised_doc_available = month_frame["revised_doc"].astype("string").str.strip().notna() & month_frame["revised_doc"].astype("string").str.strip().ne("")
    physical_available = int(month_frame["physical_progress_pct"].notna().sum())
    revised_cost_available = int(month_frame["revised_cost_available"].fillna(False).astype(bool).sum())
    schedule_rows.append({"month": month, "available": int(revised_doc_available.sum()), "unavailable": int(len(month_frame) - revised_doc_available.sum())})
    coverage_rows.append({
        "Report Month": _month_label(month),
        "Project Records": int(len(month_frame)),
        "Physical Progress Available": physical_available,
        "Revised Cost Available": revised_cost_available,
        "Revised DoC Available": int(revised_doc_available.sum()),
    })

schedule = pd.DataFrame(schedule_rows)
schedule_figure = go.Figure()
schedule_figure.add_bar(name="Revised DoC Available", x=schedule["month"].map(_month_label), y=schedule["available"], marker_color=NAVY)
schedule_figure.add_bar(name="Revised DoC Unavailable", x=schedule["month"].map(_month_label), y=schedule["unavailable"], marker_color="#AAB7C4")
schedule_figure.update_layout(barmode="stack", height=300, margin={"l": 35, "r": 18, "t": 16, "b": 40}, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font={"family": "Segoe UI, Arial, sans-serif", "color": "#1F2933"}, legend={"orientation": "h", "y": -0.18})
schedule_figure.update_yaxes(title="Projects", gridcolor="#E7EAF0", zeroline=False)
st.plotly_chart(schedule_figure, use_container_width=True, config=PLOT_CONFIG)

_section(
    "Data Coverage Over Time",
    "Availability of reported fields only; missing data is not a performance assessment.",
)
coverage_table = pd.DataFrame(coverage_rows)
styled_coverage = coverage_table.style.set_properties(
    **{"background-color": "#FFFFFF", "color": "#1F2933", "border-color": "#D9DEE5"}
)
st.dataframe(styled_coverage, hide_index=True, use_container_width=True)
