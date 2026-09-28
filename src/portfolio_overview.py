"""Reusable transformations for the Home portfolio overview."""

from __future__ import annotations

import re

import pandas as pd


# Geographic reference points used only to position state totals on the India map.
STATE_CENTROIDS = {
    "Andaman and Nicobar Islands": (11.74, 92.66), "Andhra Pradesh": (15.91, 79.74),
    "Arunachal Pradesh": (28.22, 94.73), "Assam": (26.20, 92.94),
    "Bihar": (25.10, 85.31), "Chandigarh": (30.73, 76.78),
    "Chhattisgarh": (21.28, 81.87), "Dadra and Nagar Haveli and Daman and Diu": (20.18, 73.02),
    "Delhi": (28.61, 77.21), "Goa": (15.30, 74.12), "Gujarat": (22.26, 71.19),
    "Haryana": (29.06, 76.09), "Himachal Pradesh": (31.10, 77.17),
    "Jammu and Kashmir": (33.78, 76.58), "Jharkhand": (23.61, 85.28),
    "Karnataka": (15.32, 75.71), "Kerala": (10.85, 76.27), "Ladakh": (34.23, 77.56),
    "Lakshadweep": (10.57, 72.64), "Madhya Pradesh": (22.97, 78.66),
    "Maharashtra": (19.75, 75.71), "Manipur": (24.66, 93.91),
    "Meghalaya": (25.47, 91.37), "Mizoram": (23.16, 92.94),
    "Nagaland": (26.16, 94.56), "Odisha": (20.95, 85.10),
    "Puducherry": (11.94, 79.81), "Punjab": (31.15, 75.34),
    "Rajasthan": (27.02, 74.22), "Sikkim": (27.53, 88.51),
    "Tamil Nadu": (11.13, 78.66), "Telangana": (18.11, 79.02),
    "Tripura": (23.94, 91.99), "Uttar Pradesh": (26.85, 80.95),
    "Uttarakhand": (30.07, 79.02), "West Bengal": (22.99, 87.85),
}

STATE_ALIASES = {
    "andaman & nicobar": "Andaman and Nicobar Islands",
    "andaman and nicobar islands": "Andaman and Nicobar Islands",
    "dadra & nagar haveli and daman & diu": "Dadra and Nagar Haveli and Daman and Diu",
    "nct of delhi": "Delhi", "new delhi": "Delhi", "orissa": "Odisha",
    "pondicherry": "Puducherry", "uttaranchal": "Uttarakhand",
    "jammu & kashmir": "Jammu and Kashmir",
}


def latest_unique_snapshot(history: pd.DataFrame, report_month: str) -> pd.DataFrame:
    """Return one auditable row per project for a report month."""
    snapshot = history.loc[history["report_month"].eq(report_month)].copy()
    with_id = snapshot.loc[snapshot["project_id"].notna()].drop_duplicates(
        "project_id", keep="last"
    )
    without_id = snapshot.loc[snapshot["project_id"].isna()]
    return pd.concat([with_id, without_id]).sort_index().reset_index(drop=True)


def normalize_state(value: object) -> str | None:
    """Map a single-state label to its canonical name; never split multi-state work."""
    if pd.isna(value):
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    lowered = text.casefold()
    if not text or lowered in {"pan india", "offshore"} or lowered.startswith("multi-state"):
        return None
    canonical = STATE_ALIASES.get(lowered, text)
    return canonical if canonical in STATE_CENTROIDS else None


def aggregate_states(snapshot: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Aggregate project and financial values for reliably single-state projects."""
    work = snapshot.copy()
    work["mapped_state"] = work["state"].map(normalize_state)
    excluded = int(work["mapped_state"].isna().sum())
    work = work.dropna(subset=["mapped_state"])
    result = work.groupby("mapped_state", as_index=False).agg(
        project_count=("project_id", "nunique"),
        original_cost_cr=("original_cost_cr", "sum"),
        revised_cost_cr=("revised_cost_cr", lambda values: values.sum(min_count=1)),
        cumulative_expenditure_cr=("cumulative_expenditure_cr", "sum"),
    ).rename(columns={"mapped_state": "state"})
    result["lat"] = result["state"].map(lambda name: STATE_CENTROIDS[name][0])
    result["lon"] = result["state"].map(lambda name: STATE_CENTROIDS[name][1])
    return result, excluded


def _group_small_categories(frame: pd.DataFrame, value_column: str, max_slices: int = 10) -> pd.DataFrame:
    """Keep the largest dynamic categories and combine the remainder as Others."""
    ordered = frame.sort_values(value_column, ascending=False).reset_index(drop=True)
    if len(ordered) <= max_slices:
        return ordered
    major = ordered.iloc[: max_slices - 1].copy()
    remainder = ordered.iloc[max_slices - 1 :]
    other = {"ministry": "Others", value_column: remainder[value_column].sum(),
             "project_count": remainder["project_count"].sum()}
    return pd.concat([major, pd.DataFrame([other])], ignore_index=True)


def ministry_project_distribution(snapshot: pd.DataFrame) -> pd.DataFrame:
    counts = snapshot.dropna(subset=["ministry"]).groupby("ministry")["project_id"].nunique()
    frame = counts.rename("project_count").reset_index()
    return _group_small_categories(frame, "project_count")


def ministry_cost_distribution(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Use revised cost when reported, otherwise original cost, once per project."""
    work = snapshot.dropna(subset=["ministry"]).copy()
    revised = pd.to_numeric(work["revised_cost_cr"], errors="coerce")
    original = pd.to_numeric(work["original_cost_cr"], errors="coerce")
    work["portfolio_cost_cr"] = revised.where(revised.gt(0), original)
    frame = work.groupby("ministry", as_index=False).agg(
        total_cost_cr=("portfolio_cost_cr", lambda values: values.sum(min_count=1)),
        project_count=("project_id", "nunique"),
    ).dropna(subset=["total_cost_cr"])
    return _group_small_categories(frame, "total_cost_cr")
