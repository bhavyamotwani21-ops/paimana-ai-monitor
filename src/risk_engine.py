"""Transparent rule-based monitoring indicators for PAIMANA project history.

The indicators in this module are screening signals for monitoring officers.
They are not predictions, risk scores, or proof of delay, inefficiency, fraud,
or project failure.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "historical_projects.csv"

REQUIRED_COLUMNS = {
    "report_month",
    "project_id",
    "project_name",
    "ministry",
    "sector",
    "original_cost_cr",
    "revised_cost_cr",
    "revised_cost_available",
    "revised_doc",
    "cumulative_expenditure_cr",
    "physical_progress_pct",
    "source_report",
}

NUMERIC_COLUMNS = (
    "original_cost_cr",
    "revised_cost_cr",
    "cumulative_expenditure_cr",
    "physical_progress_pct",
)

INDICATOR_COLUMNS = [
    "report_month",
    "project_id",
    "project_name",
    "ministry",
    "sector",
    "indicator_code",
    "indicator_category",
    "indicator_title",
    "explanation",
    "current_value",
    "previous_value",
    "change_value",
    "change_percent",
    "previous_report_month",
    "source_report",
    "original_cost_cr",
    "revised_cost_cr",
    "cost_change_cr",
    "cost_change_pct",
    "previous_revised_doc",
    "current_revised_doc",
    "extension_months",
    "previous_expenditure_cr",
    "current_expenditure_cr",
    "expenditure_change_cr",
    "previous_physical_progress_pct",
    "current_physical_progress_pct",
    "physical_progress_change_pct_points",
]

INDICATOR_CODES = [
    "COST_REVIEW",
    "SCHEDULE_REVIEW",
    "PROGRESS_STAGNATION_REVIEW",
    "EXPENDITURE_PROGRESS_REVIEW",
    "REVISED_COST_UNAVAILABLE",
    "REVISED_DOC_UNAVAILABLE",
    "PHYSICAL_PROGRESS_UNAVAILABLE",
]

SUBSTANTIVE_INDICATOR_CODES = [
    "COST_REVIEW",
    "SCHEDULE_REVIEW",
    "PROGRESS_STAGNATION_REVIEW",
    "EXPENDITURE_PROGRESS_REVIEW",
]

DATA_QUALITY_INDICATOR_CODES = [
    "REVISED_COST_UNAVAILABLE",
    "REVISED_DOC_UNAVAILABLE",
    "PHYSICAL_PROGRESS_UNAVAILABLE",
]

PRIORITY_COLUMNS = [
    "report_month",
    "project_id",
    "project_name",
    "ministry",
    "sector",
    "review_priority",
    "substantive_indicator_count",
    "triggered_substantive_indicators",
    "data_quality_indicator_count",
    "triggered_data_quality_indicators",
    "priority_explanation",
    "review_priority_disclaimer",
    "source_report",
]

REVIEW_PRIORITY_DISCLAIMER = (
    "Review Priority is a prototype prioritization aid based on triggered "
    "monitoring indicators. It is not an official MoSPI risk classification."
)

EARLY_WARNING_COLUMNS = [
    "report_month", "project_id", "warning_code", "warning_name", "explanation",
    "previous_report_month", "earliest_report_month", "source_indicator_code",
    "earliest_physical_progress_pct", "previous_physical_progress_pct",
    "current_physical_progress_pct", "previous_progress_gain_pct_points",
    "current_progress_gain_pct_points", "previous_expenditure_cr",
    "current_expenditure_cr", "expenditure_change_cr", "previous_revised_doc",
    "current_revised_doc", "extension_months", "source_report",
]

EARLY_WARNING_CODES = [
    "PROGRESS_SLOWDOWN", "REPEATED_STAGNATION", "PROGRESS_STAGNATION_REVIEW",
    "EXPENDITURE_PROGRESS_DIVERGENCE", "SCHEDULE_DETERIORATION",
]

EARLY_WARNING_DISCLAIMER = (
    "Early Warning Status is a prototype screening status based on transparent "
    "rules. It is not a prediction or an official MoSPI classification."
)

MONTH_VALUE_PATTERN = re.compile(r"^(0[1-9]|1[0-2])/\d{4}$")


class RiskEngineDataError(ValueError):
    """Raised when historical data is unsafe to evaluate."""


def _format_number(value: float, decimals: int = 2) -> str:
    text = f"{float(value):,.{decimals}f}"
    return text.rstrip("0").rstrip(".")


def _coerce_revised_cost_available(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values.dtype):
        return values.astype("boolean")

    normalized = values.astype("string").str.strip().str.lower()
    mapping = {"true": True, "false": False}
    invalid = normalized.notna() & ~normalized.isin(mapping)
    if invalid.any():
        examples = sorted(normalized.loc[invalid].dropna().unique().tolist())[:5]
        raise RiskEngineDataError(
            "revised_cost_available contains values other than true/false: "
            f"{examples}"
        )
    return normalized.map(mapping).astype("boolean")


def _validate_month_values(values: pd.Series, column: str) -> None:
    present = values.dropna().astype("string").str.strip()
    invalid = ~present.str.fullmatch(MONTH_VALUE_PATTERN)
    if invalid.any():
        examples = sorted(present.loc[invalid].unique().tolist())[:5]
        raise RiskEngineDataError(
            f"{column} contains values outside MM/YYYY format: {examples}"
        )


def _prepare_history(history: pd.DataFrame) -> pd.DataFrame:
    missing_columns = sorted(REQUIRED_COLUMNS - set(history.columns))
    if missing_columns:
        raise RiskEngineDataError(
            f"Historical data is missing required columns: {missing_columns}"
        )

    prepared = history.copy()
    prepared["project_id"] = prepared["project_id"].astype("string").str.strip()
    if prepared["project_id"].isna().any() or prepared["project_id"].eq("").any():
        raise RiskEngineDataError("Historical data contains a missing project_id.")

    try:
        prepared["_report_period"] = pd.PeriodIndex(
            prepared["report_month"].astype("string"), freq="M"
        )
    except (TypeError, ValueError) as exc:
        raise RiskEngineDataError(
            "report_month must contain valid monthly values in YYYY-MM format."
        ) from exc

    for column in NUMERIC_COLUMNS:
        try:
            prepared[column] = pd.to_numeric(prepared[column], errors="raise")
        except (TypeError, ValueError) as exc:
            raise RiskEngineDataError(f"{column} contains a non-numeric value.") from exc

    prepared["revised_cost_available"] = _coerce_revised_cost_available(
        prepared["revised_cost_available"]
    )
    inconsistent_cost = (
        prepared["revised_cost_available"].fillna(False)
        & prepared["revised_cost_cr"].isna()
    )
    if inconsistent_cost.any():
        raise RiskEngineDataError(
            "A revised cost is marked available but revised_cost_cr is missing."
        )

    _validate_month_values(prepared["revised_doc"], "revised_doc")

    duplicates = prepared.duplicated(["project_id", "report_month"], keep=False)
    if duplicates.any():
        sample = prepared.loc[duplicates, ["project_id", "report_month"]].head(5)
        raise RiskEngineDataError(
            "Historical data contains duplicate project-month observations: "
            f"{sample.to_dict('records')}"
        )

    return prepared.sort_values(
        ["project_id", "_report_period"], kind="stable"
    ).reset_index(drop=True)


def load_historical_projects(
    csv_path: str | Path = HISTORICAL_DATA_PATH,
) -> pd.DataFrame:
    """Load the validated historical CSV without changing the source file."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Historical project data not found: {path}")

    history = pd.read_csv(
        path,
        dtype={
            "project_id": "string",
            "legacy_ocms_code": "string",
            "pmgid": "string",
        },
    )
    return _prepare_history(history).drop(columns="_report_period")


def add_monitoring_comparisons(history: pd.DataFrame) -> pd.DataFrame:
    """Add neutral changes for truly consecutive months of the same project."""
    compared = _prepare_history(history)
    grouped = compared.groupby("project_id", sort=False)

    compared["previous_report_month"] = grouped["report_month"].shift(1)
    previous_period = grouped["_report_period"].shift(1)
    current_number = compared["_report_period"].map(lambda value: value.ordinal)
    previous_number = previous_period.map(
        lambda value: value.ordinal if pd.notna(value) else np.nan
    )
    compared["_is_consecutive_month"] = (current_number - previous_number).eq(1)

    change_specs = {
        "cumulative_expenditure_cr": "expenditure_change_cr",
        "physical_progress_pct": "physical_progress_change_pct_points",
    }
    for source_column, change_column in change_specs.items():
        previous_column = f"previous_{source_column}"
        compared[previous_column] = grouped[source_column].shift(1)
        valid = (
            compared["_is_consecutive_month"]
            & compared[source_column].notna()
            & compared[previous_column].notna()
        )
        compared[change_column] = np.where(
            valid,
            compared[source_column] - compared[previous_column],
            np.nan,
        )

    compared["previous_revised_doc"] = grouped["revised_doc"].shift(1)
    current_doc = pd.to_datetime(
        compared["revised_doc"], format="%m/%Y", errors="coerce"
    ).dt.to_period("M")
    previous_doc = pd.to_datetime(
        compared["previous_revised_doc"], format="%m/%Y", errors="coerce"
    ).dt.to_period("M")
    valid_doc = (
        compared["_is_consecutive_month"]
        & current_doc.notna()
        & previous_doc.notna()
    )
    current_doc_number = current_doc.map(
        lambda value: value.ordinal if pd.notna(value) else np.nan
    )
    previous_doc_number = previous_doc.map(
        lambda value: value.ordinal if pd.notna(value) else np.nan
    )
    compared["revised_doc_extension_months"] = np.where(
        valid_doc,
        current_doc_number - previous_doc_number,
        np.nan,
    )

    return compared.drop(columns="_report_period")


def _indicator(
    row: pd.Series,
    *,
    code: str,
    category: str,
    title: str,
    explanation: str,
    current_value: Any = None,
    previous_value: Any = None,
    change_value: Any = None,
    change_percent: Any = None,
    previous_report_month: Any = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    indicator = {
        "report_month": row["report_month"],
        "project_id": row["project_id"],
        "project_name": row["project_name"],
        "ministry": row["ministry"],
        "sector": row["sector"],
        "indicator_code": code,
        "indicator_category": category,
        "indicator_title": title,
        "explanation": explanation,
        "current_value": current_value,
        "previous_value": previous_value,
        "change_value": change_value,
        "change_percent": change_percent,
        "previous_report_month": previous_report_month,
        "source_report": row["source_report"],
    }
    indicator.update({column: None for column in INDICATOR_COLUMNS if column not in indicator})
    if evidence:
        indicator.update(evidence)
    return indicator


def generate_monitoring_indicators(history: pd.DataFrame) -> pd.DataFrame:
    """Evaluate transparent monitoring rules and return one row per indicator."""
    compared = add_monitoring_comparisons(history)
    indicators: list[dict[str, Any]] = []

    for _, row in compared.iterrows():
        original_cost = row["original_cost_cr"]
        revised_cost = row["revised_cost_cr"]
        revised_available = pd.notna(row["revised_cost_available"]) and bool(
            row["revised_cost_available"]
        )

        if (
            revised_available
            and pd.notna(original_cost)
            and pd.notna(revised_cost)
            and revised_cost > original_cost
        ):
            cost_change = float(revised_cost - original_cost)
            cost_change_pct = (
                float(cost_change / original_cost * 100)
                if original_cost != 0
                else np.nan
            )
            percentage_text = (
                f"{_format_number(cost_change_pct)}%"
                if pd.notna(cost_change_pct)
                else "not calculable because the original cost is zero"
            )
            indicators.append(
                _indicator(
                    row,
                    code="COST_REVIEW",
                    category="Cost Review",
                    title="Revised cost exceeds original cost",
                    explanation=(
                        f"Original cost is ₹{_format_number(original_cost)} crore and "
                        f"revised cost is ₹{_format_number(revised_cost)} crore. "
                        f"The reported increase is ₹{_format_number(cost_change)} crore "
                        f"({percentage_text})."
                    ),
                    current_value=float(revised_cost),
                    previous_value=float(original_cost),
                    change_value=cost_change,
                    change_percent=cost_change_pct,
                    evidence={
                        "original_cost_cr": float(original_cost),
                        "revised_cost_cr": float(revised_cost),
                        "cost_change_cr": cost_change,
                        "cost_change_pct": cost_change_pct,
                    },
                )
            )

        extension_months = row["revised_doc_extension_months"]
        if pd.notna(extension_months) and extension_months > 0:
            indicators.append(
                _indicator(
                    row,
                    code="SCHEDULE_REVIEW",
                    category="Schedule Review",
                    title="Revised completion date moved later",
                    explanation=(
                        f"Revised DoC moved from {row['previous_revised_doc']} to "
                        f"{row['revised_doc']}, an extension of "
                        f"{int(extension_months)} month(s) between consecutive reports."
                    ),
                    current_value=row["revised_doc"],
                    previous_value=row["previous_revised_doc"],
                    change_value=int(extension_months),
                    previous_report_month=row["previous_report_month"],
                    evidence={
                        "previous_revised_doc": row["previous_revised_doc"],
                        "current_revised_doc": row["revised_doc"],
                        "extension_months": int(extension_months),
                    },
                )
            )

        progress_change = row["physical_progress_change_pct_points"]
        if pd.notna(progress_change) and progress_change == 0:
            previous_progress = row["previous_physical_progress_pct"]
            current_progress = row["physical_progress_pct"]
            indicators.append(
                _indicator(
                    row,
                    code="PROGRESS_STAGNATION_REVIEW",
                    category="Progress Review",
                    title="Reported physical progress unchanged",
                    explanation=(
                        f"Reported physical progress remained at "
                        f"{_format_number(current_progress)}% from "
                        f"{row['previous_report_month']} to {row['report_month']}."
                    ),
                    current_value=float(current_progress),
                    previous_value=float(previous_progress),
                    change_value=float(progress_change),
                    previous_report_month=row["previous_report_month"],
                    evidence={
                        "previous_physical_progress_pct": float(previous_progress),
                        "current_physical_progress_pct": float(current_progress),
                        "physical_progress_change_pct_points": float(progress_change),
                    },
                )
            )

        expenditure_change = row["expenditure_change_cr"]
        if (
            pd.notna(expenditure_change)
            and expenditure_change > 0
            and pd.notna(progress_change)
            and progress_change == 0
        ):
            previous_expenditure = row["previous_cumulative_expenditure_cr"]
            current_expenditure = row["cumulative_expenditure_cr"]
            indicators.append(
                _indicator(
                    row,
                    code="EXPENDITURE_PROGRESS_REVIEW",
                    category="Expenditure-Progress Review",
                    title=(
                        "Expenditure increased while reported physical progress "
                        "was unchanged"
                    ),
                    explanation=(
                        f"Cumulative expenditure increased from "
                        f"₹{_format_number(previous_expenditure)} crore to "
                        f"₹{_format_number(current_expenditure)} crore, an increase of "
                        f"₹{_format_number(expenditure_change)} crore. Reported physical "
                        f"progress remained at {_format_number(row['physical_progress_pct'])}%."
                    ),
                    current_value=float(current_expenditure),
                    previous_value=float(previous_expenditure),
                    change_value=float(expenditure_change),
                    previous_report_month=row["previous_report_month"],
                    evidence={
                        "previous_expenditure_cr": float(previous_expenditure),
                        "current_expenditure_cr": float(current_expenditure),
                        "expenditure_change_cr": float(expenditure_change),
                        "previous_physical_progress_pct": float(
                            row["previous_physical_progress_pct"]
                        ),
                        "current_physical_progress_pct": float(
                            row["physical_progress_pct"]
                        ),
                        "physical_progress_change_pct_points": float(progress_change),
                    },
                )
            )

        if not revised_available or pd.isna(revised_cost):
            indicators.append(
                _indicator(
                    row,
                    code="REVISED_COST_UNAVAILABLE",
                    category="Data Quality Review",
                    title="Revised cost unavailable",
                    explanation=(
                        "A meaningful revised cost is unavailable in this monthly "
                        "snapshot, so cost increase is not assessed."
                    ),
                )
            )

        if pd.isna(row["revised_doc"]):
            indicators.append(
                _indicator(
                    row,
                    code="REVISED_DOC_UNAVAILABLE",
                    category="Data Quality Review",
                    title="Revised completion date unavailable",
                    explanation=(
                        "Revised DoC is unavailable in this monthly snapshot, so a "
                        "schedule revision cannot be assessed for this observation."
                    ),
                )
            )

        if pd.isna(row["physical_progress_pct"]):
            indicators.append(
                _indicator(
                    row,
                    code="PHYSICAL_PROGRESS_UNAVAILABLE",
                    category="Data Quality Review",
                    title="Physical progress unavailable",
                    explanation=(
                        "Reported physical progress is unavailable in this monthly "
                        "snapshot, so progress-change rules cannot use this observation."
                    ),
                )
            )

    return pd.DataFrame(indicators, columns=INDICATOR_COLUMNS)


def _ordered_indicator_text(values: pd.Series, allowed_codes: list[str]) -> str:
    present = set(values.dropna().astype(str))
    return ", ".join(code for code in allowed_codes if code in present)


def _priority_explanation(row: pd.Series) -> str:
    count = int(row["substantive_indicator_count"])
    if count == 0:
        return (
            "No substantive monitoring indicators triggered under the current "
            "prototype monitoring rules for this reporting snapshot."
        )
    noun = "indicator" if count == 1 else "indicators"
    return (
        f"{count} substantive monitoring {noun} triggered for this reporting "
        f"snapshot: {row['triggered_substantive_indicators']}."
    )


def generate_review_priorities(
    history: pd.DataFrame,
    indicators: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return one transparent prototype review priority per project-month.

    Priorities are calculated from substantive monitoring indicators only.
    Data-quality indicators remain attached separately and never increase the
    substantive count or priority.
    """
    prepared = _prepare_history(history)
    base_columns = [
        "report_month",
        "project_id",
        "project_name",
        "ministry",
        "sector",
        "source_report",
    ]
    base = prepared[base_columns].copy()

    indicator_data = (
        generate_monitoring_indicators(history)
        if indicators is None
        else indicators.copy()
    )
    required_indicator_columns = {"report_month", "project_id", "indicator_code"}
    missing_columns = sorted(required_indicator_columns - set(indicator_data.columns))
    if missing_columns:
        raise RiskEngineDataError(
            f"Indicator data is missing required columns: {missing_columns}"
        )

    indicator_data["project_id"] = (
        indicator_data["project_id"].astype("string").str.strip()
    )
    unknown_codes = sorted(
        set(indicator_data["indicator_code"].dropna()) - set(INDICATOR_CODES)
    )
    if unknown_codes:
        raise RiskEngineDataError(
            f"Indicator data contains unsupported indicator codes: {unknown_codes}"
        )

    indicator_duplicates = indicator_data.duplicated(
        ["project_id", "report_month", "indicator_code"], keep=False
    )
    if indicator_duplicates.any():
        sample = indicator_data.loc[
            indicator_duplicates,
            ["project_id", "report_month", "indicator_code"],
        ].head(5)
        raise RiskEngineDataError(
            "Indicator data contains duplicate project-month rules: "
            f"{sample.to_dict('records')}"
        )

    base_keys = pd.MultiIndex.from_frame(base[["project_id", "report_month"]])
    indicator_keys = pd.MultiIndex.from_frame(
        indicator_data[["project_id", "report_month"]]
    )
    unknown_keys = indicator_keys.difference(base_keys)
    if len(unknown_keys):
        raise RiskEngineDataError(
            "Indicator data contains project-months absent from historical data: "
            f"{list(unknown_keys[:5])}"
        )

    key_columns = ["project_id", "report_month"]
    substantive = indicator_data.loc[
        indicator_data["indicator_code"].isin(SUBSTANTIVE_INDICATOR_CODES)
    ]
    substantive_summary = (
        substantive.groupby(key_columns, sort=False)["indicator_code"]
        .agg(
            substantive_indicator_count="nunique",
            triggered_substantive_indicators=lambda values: _ordered_indicator_text(
                values, SUBSTANTIVE_INDICATOR_CODES
            ),
        )
        .reset_index()
    )

    data_quality = indicator_data.loc[
        indicator_data["indicator_code"].isin(DATA_QUALITY_INDICATOR_CODES)
    ]
    data_quality_summary = (
        data_quality.groupby(key_columns, sort=False)["indicator_code"]
        .agg(
            data_quality_indicator_count="nunique",
            triggered_data_quality_indicators=lambda values: _ordered_indicator_text(
                values, DATA_QUALITY_INDICATOR_CODES
            ),
        )
        .reset_index()
    )

    priorities = base.merge(
        substantive_summary,
        how="left",
        on=key_columns,
        validate="one_to_one",
    ).merge(
        data_quality_summary,
        how="left",
        on=key_columns,
        validate="one_to_one",
    )
    priorities["substantive_indicator_count"] = (
        priorities["substantive_indicator_count"].fillna(0).astype(int)
    )
    priorities["data_quality_indicator_count"] = (
        priorities["data_quality_indicator_count"].fillna(0).astype(int)
    )
    priorities["triggered_substantive_indicators"] = priorities[
        "triggered_substantive_indicators"
    ].fillna("")
    priorities["triggered_data_quality_indicators"] = priorities[
        "triggered_data_quality_indicators"
    ].fillna("")

    priorities["review_priority"] = np.select(
        [
            priorities["substantive_indicator_count"].ge(2),
            priorities["substantive_indicator_count"].eq(1),
        ],
        ["HIGH", "MEDIUM"],
        default="NORMAL",
    )
    priorities["priority_explanation"] = priorities.apply(
        _priority_explanation, axis=1
    )
    priorities["review_priority_disclaimer"] = REVIEW_PRIORITY_DISCLAIMER

    if len(priorities) != len(base):
        raise RiskEngineDataError(
            "Priority coverage does not match the historical project-month population."
        )
    if priorities.duplicated(key_columns).any():
        raise RiskEngineDataError("A project-month received multiple priority rows.")
    if int(priorities["substantive_indicator_count"].sum()) != len(substantive):
        raise RiskEngineDataError(
            "Substantive indicators were lost or double-counted during aggregation."
        )
    if int(priorities["data_quality_indicator_count"].sum()) != len(data_quality):
        raise RiskEngineDataError(
            "Data-quality indicators were lost or double-counted during aggregation."
        )
    data_quality_only = priorities["substantive_indicator_count"].eq(0) & priorities[
        "data_quality_indicator_count"
    ].gt(0)
    if not priorities.loc[data_quality_only, "review_priority"].eq("NORMAL").all():
        raise RiskEngineDataError(
            "A data-quality-only project-month received MEDIUM or HIGH priority."
        )

    return priorities[PRIORITY_COLUMNS].sort_values(
        ["report_month", "project_id"], kind="stable"
    ).reset_index(drop=True)


def generate_early_warnings(
    history: pd.DataFrame,
    indicators: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return distinct, evidence-bearing early warnings per project-month."""
    del indicators  # Existing equivalent rule codes are retained in source_indicator_code.
    compared = add_monitoring_comparisons(history)
    grouped = compared.groupby("project_id", sort=False)
    compared["_earliest_report_month"] = grouped["report_month"].shift(2)
    compared["_earliest_physical_progress_pct"] = grouped[
        "physical_progress_pct"
    ].shift(2)
    compared["_previous_progress_gain"] = grouped[
        "physical_progress_change_pct_points"
    ].shift(1)
    warnings: list[dict[str, Any]] = []

    def append_warning(row: pd.Series, code: str, name: str, explanation: str,
                       source_code: str | None = None, **evidence: Any) -> None:
        record = {column: None for column in EARLY_WARNING_COLUMNS}
        record.update({
            "report_month": row["report_month"], "project_id": row["project_id"],
            "warning_code": code, "warning_name": name, "explanation": explanation,
            "previous_report_month": row.get("previous_report_month"),
            "source_indicator_code": source_code, "source_report": row["source_report"],
        })
        record.update(evidence)
        warnings.append(record)

    for _, row in compared.iterrows():
        previous_gain = row["_previous_progress_gain"]
        current_gain = row["physical_progress_change_pct_points"]
        has_three_progress = (
            pd.notna(row["_earliest_report_month"])
            and pd.notna(row["_earliest_physical_progress_pct"])
            and pd.notna(row["previous_physical_progress_pct"])
            and pd.notna(row["physical_progress_pct"])
            and pd.notna(previous_gain) and pd.notna(current_gain)
        )
        common_progress_evidence = {
            "earliest_report_month": row["_earliest_report_month"],
            "earliest_physical_progress_pct": row["_earliest_physical_progress_pct"],
            "previous_physical_progress_pct": row["previous_physical_progress_pct"],
            "current_physical_progress_pct": row["physical_progress_pct"],
            "previous_progress_gain_pct_points": previous_gain,
            "current_progress_gain_pct_points": current_gain,
        }
        if has_three_progress and previous_gain > 0 and 0 <= current_gain < previous_gain:
            append_warning(
                row, "PROGRESS_SLOWDOWN", "Progress Slowdown",
                "Reported monthly physical-progress gain decreased from "
                f"+{_format_number(previous_gain)} pp to +{_format_number(current_gain)} pp.",
                **common_progress_evidence,
            )
        if has_three_progress and previous_gain == 0 and current_gain == 0:
            append_warning(
                row, "REPEATED_STAGNATION", "Repeated Stagnation",
                "Reported physical progress remained at "
                f"{_format_number(row['physical_progress_pct'])}% across three consecutive reports.",
                **common_progress_evidence,
            )

        if pd.notna(current_gain) and current_gain == 0:
            append_warning(
                row, "PROGRESS_STAGNATION_REVIEW", "Progress Stagnation",
                f"Reported physical progress remained at {_format_number(row['physical_progress_pct'])}% "
                f"from {row['previous_report_month']} to {row['report_month']}.",
                source_code="PROGRESS_STAGNATION_REVIEW",
                previous_physical_progress_pct=row["previous_physical_progress_pct"],
                current_physical_progress_pct=row["physical_progress_pct"],
                current_progress_gain_pct_points=current_gain,
            )

        expenditure_gain = row["expenditure_change_cr"]
        if pd.notna(expenditure_gain) and expenditure_gain > 0 and pd.notna(current_gain) and current_gain <= 0:
            progress_text = (
                "remained unchanged"
                if current_gain == 0
                else f"declined/corrected by {_format_number(abs(current_gain))} pp"
            )
            append_warning(
                row, "EXPENDITURE_PROGRESS_DIVERGENCE", "Expenditure–Progress Divergence",
                f"Cumulative expenditure increased by ₹{_format_number(expenditure_gain)} crore while "
                f"reported physical progress {progress_text} ({_format_number(current_gain)} pp).",
                source_code=("EXPENDITURE_PROGRESS_REVIEW" if current_gain == 0 else None),
                previous_expenditure_cr=row["previous_cumulative_expenditure_cr"],
                current_expenditure_cr=row["cumulative_expenditure_cr"],
                expenditure_change_cr=expenditure_gain,
                previous_physical_progress_pct=row["previous_physical_progress_pct"],
                current_physical_progress_pct=row["physical_progress_pct"],
                current_progress_gain_pct_points=current_gain,
            )

        extension = row["revised_doc_extension_months"]
        if pd.notna(extension) and extension > 0:
            append_warning(
                row, "SCHEDULE_DETERIORATION", "Schedule Deterioration",
                f"Revised DoC moved from {row['previous_revised_doc']} to {row['revised_doc']} "
                f"(+{int(extension)} months).",
                source_code="SCHEDULE_REVIEW",
                previous_revised_doc=row["previous_revised_doc"],
                current_revised_doc=row["revised_doc"], extension_months=int(extension),
            )

    result = pd.DataFrame(warnings, columns=EARLY_WARNING_COLUMNS)
    if result.empty:
        return result
    duplicates = result.duplicated(["project_id", "report_month", "warning_code"])
    if duplicates.any():
        raise RiskEngineDataError("Early-warning generation produced duplicate conditions.")
    return result.sort_values(["report_month", "project_id", "warning_code"], kind="stable").reset_index(drop=True)


def generate_early_warning_status(
    history: pd.DataFrame,
    warnings: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Summarize distinct warning conditions without producing a numeric risk score."""
    prepared = _prepare_history(history)
    base = prepared[["report_month", "project_id"]].copy()
    warning_data = generate_early_warnings(history) if warnings is None else warnings.copy()
    if warning_data.empty:
        summary = pd.DataFrame(columns=["project_id", "report_month", "active_warning_count", "active_warning_names"])
    else:
        summary = warning_data.groupby(["project_id", "report_month"], as_index=False).agg(
            active_warning_count=("warning_code", "nunique"),
            active_warning_names=("warning_name", lambda values: ", ".join(dict.fromkeys(values))),
        )
    status = base.merge(summary, how="left", on=["project_id", "report_month"], validate="one_to_one")
    status["active_warning_count"] = status["active_warning_count"].fillna(0).astype(int)
    status["active_warning_names"] = status["active_warning_names"].fillna("")
    status["early_warning_status"] = np.select(
        [status["active_warning_count"].ge(3), status["active_warning_count"].eq(2), status["active_warning_count"].eq(1)],
        ["HIGH ATTENTION", "ELEVATED", "WATCH"], default="NO CURRENT WARNING",
    )
    status["early_warning_disclaimer"] = EARLY_WARNING_DISCLAIMER
    return status.sort_values(["report_month", "project_id"], kind="stable").reset_index(drop=True)


def _print_verification() -> None:
    history = load_historical_projects()
    indicators = generate_monitoring_indicators(history)
    indicator_counts_before = indicators["indicator_code"].value_counts().sort_index()
    priorities = generate_review_priorities(history, indicators)
    indicator_counts_after = indicators["indicator_code"].value_counts().sort_index()
    if not indicator_counts_before.equals(indicator_counts_after):
        raise RiskEngineDataError(
            "Existing monitoring indicator counts changed during priority generation."
        )

    print(f"Historical rows loaded: {len(history):,}")
    print(f"Projects evaluated: {history['project_id'].nunique():,}")
    print(f"Indicators generated: {len(indicators):,}")

    print("\nCount by indicator code:")
    code_counts = (
        indicators["indicator_code"]
        .value_counts()
        .reindex(INDICATOR_CODES, fill_value=0)
        .astype(int)
    )
    print(code_counts.to_string())

    print("\nCount by indicator category:")
    print(indicators["indicator_category"].value_counts().sort_index().to_string())

    print("\nSample triggered indicators:")
    sample_columns = [
        "report_month",
        "project_id",
        "indicator_code",
        "explanation",
    ]
    print(indicators[sample_columns].head(10).to_string(index=False))

    print("\nData-quality indicator counts:")
    data_quality = indicators.loc[
        indicators["indicator_category"].eq("Data Quality Review"),
        "indicator_code",
    ].value_counts().reindex(
        [
            "REVISED_COST_UNAVAILABLE",
            "REVISED_DOC_UNAVAILABLE",
            "PHYSICAL_PROGRESS_UNAVAILABLE",
        ],
        fill_value=0,
    ).astype(int)
    print(data_quality.to_string())

    priority_counts = (
        priorities["review_priority"]
        .value_counts()
        .reindex(["HIGH", "MEDIUM", "NORMAL"], fill_value=0)
        .astype(int)
    )
    priority_total = int(priority_counts.sum())
    if priority_total != len(priorities) or len(priorities) != len(history):
        raise RiskEngineDataError(
            "HIGH + MEDIUM + NORMAL does not match the historical row count."
        )

    print("\nReview Priority summary:")
    print(f"Total project-month priority rows: {len(priorities):,}")
    print(priority_counts.to_string())
    print(
        "Priority count reconciliation: PASS - HIGH + MEDIUM + NORMAL = "
        f"{priority_total:,} historical project-month rows."
    )
    print("Existing monitoring indicator counts unchanged: PASS")

    priority_sample_columns = [
        "report_month",
        "project_id",
        "project_name",
        "substantive_indicator_count",
        "triggered_substantive_indicators",
    ]
    for priority in ("HIGH", "MEDIUM", "NORMAL"):
        sample = priorities.loc[
            priorities["review_priority"].eq(priority), priority_sample_columns
        ].head(5)
        print(f"\nSample {priority} project-months:")
        print(sample.to_string(index=False))

    project_id = "612786"
    example_history = history.loc[history["project_id"].eq(project_id)]
    example_comparisons = add_monitoring_comparisons(example_history)
    print(f"\nProject {project_id} calculations:")
    calculation_columns = [
        "report_month",
        "cumulative_expenditure_cr",
        "expenditure_change_cr",
        "physical_progress_pct",
        "physical_progress_change_pct_points",
        "revised_doc",
        "previous_revised_doc",
        "revised_doc_extension_months",
    ]
    print(example_comparisons[calculation_columns].to_string(index=False))

    print(f"\nProject {project_id} indicators:")
    example_indicators = indicators.loc[indicators["project_id"].eq(project_id)]
    print(
        example_indicators[
            ["report_month", "indicator_code", "explanation"]
        ].to_string(index=False)
    )

    example_priorities = priorities.loc[priorities["project_id"].eq(project_id)]
    print(f"\nProject {project_id} monthly Review Priority:")
    print(
        example_priorities[
            [
                "report_month",
                "review_priority",
                "substantive_indicator_count",
                "triggered_substantive_indicators",
                "data_quality_indicator_count",
                "triggered_data_quality_indicators",
                "priority_explanation",
            ]
        ].to_string(index=False)
    )

    prohibited = {
        "PROGRESS_STAGNATION_REVIEW",
        "EXPENDITURE_PROGRESS_REVIEW",
    }
    actual_codes = set(example_indicators["indicator_code"])
    if actual_codes & prohibited:
        raise RiskEngineDataError(
            f"Project {project_id} unexpectedly triggered {actual_codes & prohibited}."
        )
    july_schedule = example_indicators.loc[
        example_indicators["report_month"].eq("2026-07")
        & example_indicators["indicator_code"].eq("SCHEDULE_REVIEW")
    ]
    if len(july_schedule) != 1 or july_schedule.iloc[0]["change_value"] != 2:
        raise RiskEngineDataError(
            f"Project {project_id} did not produce the expected July schedule review."
        )
    expected_priorities = {
        "2026-06": "NORMAL",
        "2026-07": "MEDIUM",
        "2026-08": "NORMAL",
    }
    actual_priorities = example_priorities.set_index("report_month")[
        "review_priority"
    ].to_dict()
    if actual_priorities != expected_priorities:
        raise RiskEngineDataError(
            f"Project {project_id} priority check failed: {actual_priorities}."
        )
    print(
        f"\nProject {project_id} verification: PASS - July schedule extension detected; "
        "no progress-stagnation or expenditure-progress indicator detected; "
        "monthly priorities are NORMAL, MEDIUM, NORMAL."
    )


if __name__ == "__main__":
    _print_verification()
