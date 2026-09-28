import importlib
import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import src.auth as auth
import src.ui as ui
from src.risk_engine import HISTORICAL_DATA_PATH, load_historical_projects
from src.portfolio_overview import (
    aggregate_states,
    latest_unique_snapshot,
    ministry_cost_distribution,
    ministry_project_distribution,
)


# Streamlit reruns app.py without always re-importing changed helper modules.
# Reload shared modules so every rerun uses their current implementations.
auth = importlib.reload(auth)
ui = importlib.reload(ui)


st.set_page_config(
    page_title="PAIMANA",
    layout="wide",
    initial_sidebar_state="expanded",
)


LOGIN_CSS = """
<style>
    :root {
        --login-background: #F7F8FA;
        --login-card: #FFFFFF;
        --login-primary: #17365D;
        --login-primary-dark: #102A43;
        --login-accent: #D99024;
        --login-text: #1F2933;
        --login-secondary: #66727F;
        --login-border: #D9DEE5;
        --login-secondary-surface: #F2F4F7;
    }

    html, body, .stApp {
        font-family: "Segoe UI", Arial, sans-serif;
    }

    .stApp {
        background: var(--login-background);
        color: var(--login-text);
    }

    [data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    [data-testid="stToolbar"],
    #MainMenu,
    footer:not(.login-footer) {
        display: none !important;
    }

    [data-testid="stHeader"] {
        background: transparent;
        height: 0;
    }

    .block-container {
        max-width: none;
        padding: 0 0 0.8rem !important;
    }

    .login-identity {
        margin: 1rem auto 0.8rem;
        text-align: center;
    }

    .login-wordmark {
        border-bottom: 2px solid var(--login-accent);
        color: var(--login-primary);
        display: inline-block;
        font-size: 1.85rem;
        font-weight: 750;
        letter-spacing: 0.08em;
        line-height: 1.1;
        margin: 0;
        padding-bottom: 0.12rem;
    }

    .login-system-name {
        color: var(--login-text);
        font-size: 0.96rem;
        font-weight: 600;
        margin: 0.3rem 0 0;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--login-card);
        border: 1px solid var(--login-border) !important;
        border-radius: 7px;
        box-shadow: 0 4px 14px rgba(31, 41, 51, 0.06);
    }

    [data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 1.35rem 1.6rem 1.2rem;
    }

    .login-title {
        color: var(--login-primary-dark);
        font-size: 1.4rem !important;
        font-weight: 700;
        line-height: 1.2 !important;
        margin: 0 0 0.25rem !important;
        padding: 0 !important;
        text-align: center;
    }

    .login-supporting-text {
        color: var(--login-secondary);
        font-size: 0.88rem;
        margin: 0 0 1rem;
        text-align: center;
    }

    .stTextInput label,
    .stTextInput [data-testid="stWidgetLabel"] p,
    .stCheckbox label,
    .stCheckbox [data-testid="stWidgetLabel"] p {
        color: var(--login-text) !important;
        font-size: 0.9rem;
        font-weight: 650;
    }

    .stTextInput input {
        background: #FFFFFF;
        border: 1px solid var(--login-border);
        border-radius: 4px;
        color: var(--login-text);
        min-height: 2.65rem;
    }

    .stTextInput input:focus {
        border-color: var(--login-primary);
        box-shadow: 0 0 0 1px var(--login-primary);
    }

    .stTextInput button {
        display: none !important;
    }

    .stCheckbox {
        margin-top: -0.25rem;
    }

    .stButton > button[kind="primary"] {
        background: var(--login-primary);
        border: 1px solid var(--login-primary);
        border-radius: 4px;
        color: #FFFFFF;
        font-weight: 700;
        min-height: 2.65rem;
    }

    .stButton > button[kind="primary"]:hover {
        background: var(--login-primary-dark);
        border-color: var(--login-primary-dark);
        color: #FFFFFF;
    }

    .authorization-note {
        color: var(--login-secondary);
        font-size: 0.78rem;
        margin: 0.75rem 0 0;
        text-align: center;
    }

    .login-footer {
        border-top: 1px solid var(--login-border);
        color: var(--login-secondary);
        font-size: 0.74rem;
        margin: 0.9rem auto 0;
        max-width: 460px;
        padding-top: 0.65rem;
        text-align: center;
    }

</style>
"""


HOME_CSS = """
<style>
    .block-container > [data-testid="stVerticalBlock"] {
        gap: 0.6rem;
    }

    .page-heading {
        line-height: 1.15;
        margin-bottom: 0.45rem;
    }

    .page-introduction {
        line-height: 1.35;
        margin-bottom: 0.35rem;
    }

    .page-heading-rule {
        display: none;
    }

    .home-overview-label {
        color: #17365D;
        font-size: 1.05rem;
        font-weight: 700;
        margin: 0.55rem 0 0.15rem;
    }

    .home-overview-copy {
        color: #66727F;
        font-size: 0.94rem;
        line-height: 1.4;
        margin: 0.15rem 0 1rem;
    }

    .home-section-title {
        color: #17365D;
        font-size: 1.18rem;
        font-weight: 700;
        line-height: 1.3;
        margin: 0 0 0.45rem;
        padding-top: 1rem;
    }

    .home-subsection-title,
    .home-chart-title {
        color: #102A43;
        font-size: 1rem;
        font-weight: 700;
        line-height: 1.35;
    }

    .home-subsection-title {
        margin: 0 0 0.35rem;
        padding-top: 0.65rem;
    }

    .home-chart-title {
        margin: 0.05rem 0 0.35rem;
    }

    .home-filter-title {
        color: #17365D;
        font-size: 0.9rem;
        font-weight: 700;
        letter-spacing: 0.025em;
        margin: 0 0 0.55rem;
        text-transform: uppercase;
    }

    .home-kpi-card {
        background: #FFFFFF;
        border: 1px solid #D9DEE5;
        border-top: 3px solid #17365D;
        border-radius: 5px;
        box-sizing: border-box;
        height: 150px;
        padding: 0.8rem 1rem;
    }

    .home-kpi-label {
        color: #66727F;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.035em;
        margin: 0;
        text-transform: uppercase;
    }

    .home-kpi-value {
        color: #17365D;
        font-size: 1.48rem;
        font-weight: 750;
        line-height: 1.2;
        margin: 0.48rem 0 0;
    }

    .home-kpi-note {
        color: #66727F;
        font-size: 0.78rem;
        line-height: 1.35;
        margin: 0.3rem 0 0;
    }

    .home-ratio-panel {
        align-items: center;
        background: #FFFFFF;
        border: 1px solid #D9DEE5;
        border-left: 4px solid #D99024;
        border-radius: 5px;
        display: grid;
        gap: 0.3rem 1rem;
        grid-template-columns: minmax(150px, auto) 1fr;
        padding: 0.9rem 1rem;
    }

    .home-ratio-value {
        color: #17365D;
        font-size: 1.65rem;
        font-weight: 750;
        margin: 0;
    }

    .home-ratio-note,
    .home-chart-note {
        color: #66727F;
        font-size: 0.84rem;
        line-height: 1.45;
        margin: 0;
    }

    .home-chart-panel {
        background: #FFFFFF;
        border: 1px solid #D9DEE5;
        border-radius: 5px;
        padding: 0.25rem 0.7rem 0.55rem;
    }

    .home-coverage-grid {
        display: grid;
        gap: 0;
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .home-coverage-item {
        background: #FFFFFF;
        border: 1px solid #D9DEE5;
        margin: -1px 0 0 -1px;
        min-height: 80px;
        padding: 0.75rem 0.85rem;
    }

    .home-coverage-label {
        color: #66727F;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.025em;
        line-height: 1.35;
        margin: 0;
        text-transform: uppercase;
    }

    .home-coverage-value {
        color: #17365D;
        font-size: 1.3rem;
        font-weight: 750;
        margin: 0.35rem 0 0;
    }

    .home-source {
        border-top: 1px solid #D9DEE5;
        color: #66727F;
        font-size: 0.8rem;
        margin-top: 0.9rem;
        padding-top: 0.6rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF !important;
        border-color: #D9DEE5 !important;
        box-shadow: none !important;
    }

    [data-testid="stSelectbox"] div[role="group"],
    div[data-baseweb="select"] > div {
        background: #FFFFFF !important;
        border-color: #D9DEE5 !important;
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
        color: #17365D !important;
        fill: #17365D !important;
    }

    [data-testid="stSelectbox"] label p,
    .stSelectbox label p {
        color: #1F2933 !important;
        font-weight: 650;
    }

    div[role="listbox"],
    div[role="option"] {
        background: #FFFFFF !important;
        color: #1F2933 !important;
    }

    div[role="option"]:hover,
    div[role="option"][aria-selected="true"] {
        background: #F2F4F7 !important;
        color: #102A43 !important;
    }

    @media (max-width: 900px) {
        .home-coverage-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .home-ratio-panel {
            grid-template-columns: 1fr;
        }
    }
</style>
"""


PLOT_CONFIG = {"displayModeBar": False, "responsive": True}


@st.cache_data(show_spinner=False)
def _load_home_history(historical_file_modified_ns: int) -> pd.DataFrame:
    del historical_file_modified_ns
    return load_historical_projects()


def _month_label(report_month: str) -> str:
    return pd.Period(report_month, freq="M").strftime("%B %Y")


def _format_crore(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"₹{float(value):,.2f} crore"


def _render_home_kpi(label: str, value: str, note: str | None = None) -> None:
    note_html = (
        f'<p class="home-kpi-note">{html.escape(note)}</p>' if note else ""
    )
    st.markdown(
        f"""
        <section class="home-kpi-card">
            <p class="home-kpi-label">{html.escape(label)}</p>
            <p class="home-kpi-value">{html.escape(value)}</p>
            {note_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def _progress_band_counts(values: pd.Series) -> pd.Series:
    available = pd.to_numeric(values, errors="coerce").dropna()
    labels = ["0–25%", "26–50%", "51–75%", "76–99%", "100%"]
    counts = pd.Series(0, index=labels, dtype="int64")
    counts["0–25%"] = int(available.between(0, 25, inclusive="both").sum())
    counts["26–50%"] = int((available.gt(25) & available.le(50)).sum())
    counts["51–75%"] = int((available.gt(50) & available.le(75)).sum())
    counts["76–99%"] = int((available.gt(75) & available.lt(100)).sum())
    counts["100%"] = int(available.eq(100).sum())
    return counts


def _base_chart_layout(height: int = 270) -> dict[str, object]:
    return {
        "height": height,
        "margin": {"l": 30, "r": 20, "t": 12, "b": 38},
        "paper_bgcolor": "#FFFFFF",
        "plot_bgcolor": "#FFFFFF",
        "font": {"family": "Segoe UI, Arial, sans-serif", "color": "#1F2933"},
        "showlegend": False,
    }


def apply_login_styles() -> None:
    st.html(LOGIN_CSS)


def render_login_identity() -> None:
    st.markdown(
        """
        <section class="login-identity">
            <p class="login-wordmark">PAIMANA</p>
            <p class="login-system-name">Infrastructure Project Monitoring System</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_login_footer() -> None:
    st.markdown(
        """
        <footer class="login-footer">
            PAIMANA | Ministry of Statistics and Programme Implementation
        </footer>
        """,
        unsafe_allow_html=True,
    )


def login_page() -> None:
    apply_login_styles()
    render_login_identity()

    _, login_column, _ = st.columns([1, 0.8, 1])
    with login_column:
        with st.container(border=True):
            st.markdown('<h2 class="login-title">Monitoring Officer Login</h2>', unsafe_allow_html=True)
            st.markdown(
                '<p class="login-supporting-text">Sign in to access the monitoring portal</p>',
                unsafe_allow_html=True,
            )

            officer_id = st.text_input("Officer ID / Email")
            password = st.text_input(
                "Password",
                type=(
                    "default"
                    if st.session_state.get("paimana_show_password", False)
                    else "password"
                ),
                key="paimana_password",
            )
            st.checkbox("Show password", key="paimana_show_password")

            if st.button("Login", type="primary", use_container_width=True):
                if auth.authenticate(officer_id, password):
                    st.session_state.pop("paimana_password", None)
                    st.rerun()
                else:
                    st.error(
                        "Enter a valid email address and a password with at least "
                        "8 characters, including uppercase, lowercase, a number, "
                        "and a special character."
                    )

            st.markdown(
                '<p class="authorization-note">Authorized access for monitoring officers only.</p>',
                unsafe_allow_html=True,
            )

    render_login_footer()


def home_page() -> None:
    ui.apply_shared_styles()
    st.html(HOME_CSS)
    ui.render_page_header("Home", "Portfolio Overview")
    st.markdown(
        """
        <p class="home-overview-copy">
            Overall snapshot of reported PAIMANA project data.
        </p>
        """,
        unsafe_allow_html=True,
    )

    try:
        history = _load_home_history(HISTORICAL_DATA_PATH.stat().st_mtime_ns)
    except (FileNotFoundError, ValueError) as exc:
        st.error(f"Historical project data could not be loaded: {exc}")
        st.stop()

    available_months = sorted(history["report_month"].dropna().unique().tolist())
    if not available_months:
        st.warning("No historical project snapshots are currently available.")
        st.stop()

    st.markdown('<p class="home-filter-title">Filters</p>', unsafe_allow_html=True)
    with st.container(border=True):
        month_column, ministry_column = st.columns([1, 2])
        with month_column:
            selected_month = st.selectbox(
                "Report Month",
                available_months,
                index=len(available_months) - 1,
                format_func=_month_label,
            )

        month_data = latest_unique_snapshot(history, selected_month)
        month_ministries = sorted(
            month_data["ministry"].dropna().unique().tolist()
        )
        with ministry_column:
            selected_ministry = st.selectbox(
                "Ministry", ["All Ministries", *month_ministries]
            )

    snapshot = month_data
    if selected_ministry != "All Ministries":
        snapshot = snapshot.loc[snapshot["ministry"].eq(selected_ministry)].copy()

    project_count = int(snapshot["project_id"].nunique(dropna=True))
    original_cost_total = snapshot["original_cost_cr"].sum(min_count=1)
    expenditure_total = snapshot["cumulative_expenditure_cr"].sum(min_count=1)

    revised_available_mask = snapshot["revised_cost_available"].fillna(False).astype(bool)
    revised_available_count = int(revised_available_mask.sum())
    revised_unavailable_count = int(project_count - revised_available_count)
    revised_cost_total = (
        snapshot.loc[revised_available_mask, "revised_cost_cr"].sum(min_count=1)
        if revised_available_count
        else None
    )

    physical_available_count = int(snapshot["physical_progress_pct"].notna().sum())
    physical_unavailable_count = int(project_count - physical_available_count)
    revised_doc_available_mask = (
        snapshot["revised_doc"].astype("string").str.strip().notna()
        & snapshot["revised_doc"].astype("string").str.strip().ne("")
    )
    revised_doc_available_count = int(revised_doc_available_mask.sum())
    revised_doc_unavailable_count = int(project_count - revised_doc_available_count)

    st.markdown(
        '<p class="home-section-title">Portfolio Snapshot</p>',
        unsafe_allow_html=True,
    )
    kpi_columns = st.columns(4)
    with kpi_columns[0]:
        _render_home_kpi("Ongoing Projects", f"{project_count:,}")
    with kpi_columns[1]:
        _render_home_kpi("Original Cost", _format_crore(original_cost_total))
    with kpi_columns[2]:
        _render_home_kpi(
            "Latest Revised Cost",
            _format_crore(revised_cost_total),
            f"Available for {revised_available_count:,} of {project_count:,} projects",
        )
    with kpi_columns[3]:
        _render_home_kpi(
            "Cumulative Expenditure", _format_crore(expenditure_total)
        )

    st.markdown(
        '<p class="home-section-title">State-wise Project Monitoring</p>',
        unsafe_allow_html=True,
    )
    map_filter_columns = st.columns(2)
    with map_filter_columns[0]:
        map_ministry = st.selectbox(
            "Ministry", ["All Ministries", *month_ministries], key="home_map_ministry"
        )
    sector_options = sorted(month_data["sector"].dropna().unique().tolist())
    with map_filter_columns[1]:
        map_sector = st.selectbox(
            "Sector", ["All Sectors", *sector_options], key="home_map_sector"
        )
    map_snapshot = month_data
    if map_ministry != "All Ministries":
        map_snapshot = map_snapshot.loc[map_snapshot["ministry"].eq(map_ministry)]
    if map_sector != "All Sectors":
        map_snapshot = map_snapshot.loc[map_snapshot["sector"].eq(map_sector)]
    state_summary, excluded_state_projects = aggregate_states(map_snapshot)
    if state_summary.empty:
        st.info("No reliably single-state projects match the selected map filters.")
    else:
        map_figure = go.Figure(go.Scattergeo(
            lat=state_summary["lat"], lon=state_summary["lon"],
            text=state_summary["state"],
            customdata=state_summary[["project_count", "original_cost_cr", "revised_cost_cr", "cumulative_expenditure_cr"]],
            marker={"size": state_summary["project_count"], "sizemode": "area", "sizeref": max(state_summary["project_count"].max() / 42, 1),
                    "sizemin": 7, "color": state_summary["project_count"], "colorscale": [[0, "#B8C7D9"], [1, "#17365D"]],
                    "colorbar": {"title": "Projects", "thickness": 12}, "line": {"color": "#FFFFFF", "width": 0.8}},
            hovertemplate=("<b>%{text}</b><br>Projects: %{customdata[0]:,}<br>Original Cost: ₹%{customdata[1]:,.2f} crore"
                           "<br>Revised Cost (where reported): ₹%{customdata[2]:,.2f} crore"
                           "<br>Expenditure: ₹%{customdata[3]:,.2f} crore<extra></extra>"),
        ))
        map_figure.update_geos(scope="asia", projection_type="mercator", center={"lat": 22.5, "lon": 80.0},
                               lataxis_range=[6, 38], lonaxis_range=[67, 98], showland=True,
                               landcolor="#F2F4F7", showcountries=True, countrycolor="#AEB8C4",
                               showcoastlines=True, coastlinecolor="#AEB8C4")
        map_figure.update_layout(height=560, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                                 paper_bgcolor="#FFFFFF", font={"family": "Segoe UI, Arial, sans-serif"})
        with st.container(border=True):
            st.plotly_chart(map_figure, use_container_width=True, config=PLOT_CONFIG)
            st.caption(
                f"Map includes {int(state_summary['project_count'].sum()):,} reliably single-state project(s). "
                f"{excluded_state_projects:,} PAN-India, offshore, multi-state, missing, or unmappable project(s) are excluded to avoid incorrect allocation."
            )

    st.markdown('<p class="home-section-title">Ministry Overview</p>', unsafe_allow_html=True)
    projects_by_ministry = ministry_project_distribution(month_data)
    cost_by_ministry = ministry_cost_distribution(month_data)
    ministry_columns = st.columns(2)
    pie_colors = ["#17365D", "#D99024", "#416A8C", "#73899F", "#A65F3C", "#496B5D", "#8B7A4A", "#6D5B7B", "#9AA7B3", "#C2C8CE"]
    with ministry_columns[0]:
        st.markdown('<p class="home-chart-title">Projects by Ministry</p>', unsafe_allow_html=True)
        project_pie = go.Figure(go.Pie(
            labels=projects_by_ministry["ministry"], values=projects_by_ministry["project_count"], hole=0.42,
            marker={"colors": pie_colors}, sort=False,
            hovertemplate="<b>%{label}</b><br>Projects: %{value:,}<br>Share: %{percent}<extra></extra>",
        ))
        project_pie.update_layout(height=430, margin={"l": 10, "r": 10, "t": 10, "b": 10}, legend={"orientation": "h", "y": -0.08},
                                  paper_bgcolor="#FFFFFF", font={"family": "Segoe UI, Arial, sans-serif", "color": "#1F2933"})
        with st.container(border=True):
            st.plotly_chart(project_pie, use_container_width=True, config=PLOT_CONFIG)
            st.caption("Distribution of unique projects across ministries; smaller categories are grouped dynamically as Others.")
    with ministry_columns[1]:
        st.markdown('<p class="home-chart-title">Cost by Ministry</p>', unsafe_allow_html=True)
        cost_pie = go.Figure(go.Pie(
            labels=cost_by_ministry["ministry"], values=cost_by_ministry["total_cost_cr"],
            customdata=cost_by_ministry[["project_count"]], hole=0.42, marker={"colors": pie_colors}, sort=False,
            hovertemplate="<b>%{label}</b><br>Total Cost: ₹%{value:,.2f} crore<br>Share: %{percent}<br>Projects: %{customdata[0]:,}<extra></extra>",
        ))
        cost_pie.update_layout(height=430, margin={"l": 10, "r": 10, "t": 10, "b": 10}, legend={"orientation": "h", "y": -0.08},
                               paper_bgcolor="#FFFFFF", font={"family": "Segoe UI, Arial, sans-serif", "color": "#1F2933"})
        with st.container(border=True):
            st.plotly_chart(cost_pie, use_container_width=True, config=PLOT_CONFIG)
            st.caption("Latest reported project cost: revised cost where available, otherwise original cost. Smaller categories are grouped as Others.")

    st.markdown(
        '<p class="home-section-title">Financial Overview</p>',
        unsafe_allow_html=True,
    )
    financial_labels = ["Original Cost"]
    financial_values = [float(original_cost_total)]
    financial_colors = ["#17365D"]
    if revised_available_count and revised_cost_total is not None:
        financial_labels.append("Available Revised Cost")
        financial_values.append(float(revised_cost_total))
        financial_colors.append("#D99024")
    financial_labels.append("Cumulative Expenditure")
    financial_values.append(float(expenditure_total))
    financial_colors.append("#66727F")

    financial_figure = go.Figure(
        go.Bar(
            x=financial_labels,
            y=financial_values,
            marker_color=financial_colors,
            text=[f"₹{value:,.2f}" for value in financial_values],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}<br>₹%{y:,.2f} crore<extra></extra>",
        )
    )
    financial_figure.update_layout(**_base_chart_layout())
    financial_figure.update_yaxes(
        title="₹ crore", gridcolor="#E7EAF0", rangemode="tozero", zeroline=False
    )
    financial_figure.update_xaxes(tickfont={"color": "#1F2933"})
    with st.container(border=True):
        st.plotly_chart(
            financial_figure,
            use_container_width=True,
            config=PLOT_CONFIG,
        )
        if not revised_available_count:
            st.caption(
                "Project-level revised cost is unavailable for this reporting snapshot; "
                "no revised-cost bar is shown."
            )

    st.markdown(
        '<p class="home-subsection-title">Financial Expenditure Ratio</p>',
        unsafe_allow_html=True,
    )
    ratio = (
        float(expenditure_total) / float(original_cost_total) * 100
        if pd.notna(original_cost_total)
        and float(original_cost_total) > 0
        and pd.notna(expenditure_total)
        else None
    )
    ratio_value = "Not available" if ratio is None else f"{ratio:,.2f}%"
    st.markdown(
        f"""
        <section class="home-ratio-panel">
            <p class="home-ratio-value">{html.escape(ratio_value)}</p>
            <p class="home-ratio-note">
                Cumulative expenditure as a percentage of original project cost.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="home-section-title">Portfolio Distribution</p>',
        unsafe_allow_html=True,
    )
    progress_column, sector_column = st.columns(2)
    progress_counts = _progress_band_counts(snapshot["physical_progress_pct"])
    with progress_column:
        st.markdown(
            '<p class="home-chart-title">Physical Progress Distribution</p>',
            unsafe_allow_html=True,
        )
        progress_figure = go.Figure(
            go.Bar(
                x=progress_counts.index.tolist(),
                y=progress_counts.tolist(),
                marker_color="#17365D",
                text=progress_counts.tolist(),
                textposition="outside",
                cliponaxis=False,
                hovertemplate="%{x}<br>%{y:,} projects<extra></extra>",
            )
        )
        progress_figure.update_layout(**_base_chart_layout(height=420))
        progress_figure.update_yaxes(
            title="Projects", gridcolor="#E7EAF0", rangemode="tozero", zeroline=False
        )
        with st.container(border=True):
            st.plotly_chart(
                progress_figure,
                use_container_width=True,
                config=PLOT_CONFIG,
            )
            if physical_unavailable_count:
                st.caption(
                    f"Physical progress is unavailable for "
                    f"{physical_unavailable_count:,} project(s); missing values are not "
                    "included in the bands."
                )

    with sector_column:
        st.markdown(
            '<p class="home-chart-title">Sector Breakdown</p>',
            unsafe_allow_html=True,
        )
        sector_counts = snapshot["sector"].dropna().value_counts().sort_values()
        sector_height = 420
        sector_figure = go.Figure(
            go.Bar(
                x=sector_counts.tolist(),
                y=sector_counts.index.tolist(),
                orientation="h",
                marker_color="#17365D",
                text=sector_counts.tolist(),
                textposition="outside",
                cliponaxis=False,
                hovertemplate="%{y}<br>%{x:,} projects<extra></extra>",
            )
        )
        sector_figure.update_layout(**_base_chart_layout(height=sector_height))
        sector_figure.update_xaxes(
            title="Projects", gridcolor="#E7EAF0", rangemode="tozero", zeroline=False
        )
        sector_figure.update_yaxes(tickfont={"size": 11})
        with st.container(border=True):
            st.plotly_chart(
                sector_figure,
                use_container_width=True,
                config=PLOT_CONFIG,
            )

    st.markdown(
        '<p class="home-section-title">Data Coverage</p>',
        unsafe_allow_html=True,
    )
    coverage = [
        ("Projects in Selected Snapshot", project_count),
        ("Revised Cost Available", revised_available_count),
        ("Revised Cost Unavailable", revised_unavailable_count),
        ("Physical Progress Available", physical_available_count),
        ("Physical Progress Unavailable", physical_unavailable_count),
        ("Revised DoC Available", revised_doc_available_count),
        ("Revised DoC Unavailable", revised_doc_unavailable_count),
    ]
    coverage_html = "".join(
        f"""
        <div class="home-coverage-item">
            <p class="home-coverage-label">{html.escape(label)}</p>
            <p class="home-coverage-value">{value:,}</p>
        </div>
        """
        for label, value in coverage
    )
    st.html(f'<section class="home-coverage-grid">{coverage_html}</section>')

    source_reports = sorted(snapshot["source_report"].dropna().unique().tolist())
    source_text = ", ".join(source_reports) if source_reports else "Not available"
    st.markdown(
        f'<p class="home-source"><strong>Source:</strong> '
        f'{html.escape(source_text)}</p>',
        unsafe_allow_html=True,
    )


if not auth.is_authenticated():
    login = st.navigation([st.Page(login_page, title="Login")], position="hidden")
    login.run()
    st.stop()


ui.apply_shared_styles()

navigation = st.navigation(
    {
        "PAIMANA": [
            st.Page(home_page, title="Home", default=True),
            st.Page("pages/1_Projects.py", title="Projects"),
            st.Page("pages/2_Risk_Alerts.py", title="Risk & Alerts"),
            st.Page("pages/3_Analytics.py", title="Analytics"),
            st.Page("pages/4_Reports.py", title="Reports"),
        ]
    }
)

navigation.run()

if ui.render_sidebar_account():
    auth.logout()
    st.rerun()
