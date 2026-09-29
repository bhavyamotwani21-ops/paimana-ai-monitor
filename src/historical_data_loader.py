"""Extract and validate project-month history from official PAIMANA reports."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_REPORT_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "historical_projects.csv"
REPORT_PATTERN = "FlashReport_*.pdf"

OFFICIAL_PROJECT_COUNTS = {
    "2026-06": 1847,
    "2026-07": 1775,
    "2026-08": 1731,
}

MONTH_NUMBERS = {
    "JANUARY": 1,
    "FEBRUARY": 2,
    "MARCH": 3,
    "APRIL": 4,
    "MAY": 5,
    "JUNE": 6,
    "JULY": 7,
    "AUGUST": 8,
    "SEPTEMBER": 9,
    "OCTOBER": 10,
    "NOVEMBER": 11,
    "DECEMBER": 12,
}

NORMALIZED_COLUMNS = [
    "report_month",
    "ministry",
    "sector",
    "project_id",
    "project_name",
    "agency",
    "legacy_ocms_code",
    "pmgid",
    "state",
    "approval_date",
    "start_date",
    "original_target_doc",
    "revised_doc",
    "original_cost_cr",
    "revised_cost_cr",
    "revised_cost_raw",
    "revised_cost_available",
    "cumulative_expenditure_cr",
    "physical_progress_pct",
    "source_report",
]

DATE_PATTERN = re.compile(r"^(0[1-9]|1[0-2])/\d{4}$")
PROJECT_TAIL_PATTERN = re.compile(
    r"\((?P<project_id>\d+)\)\s+"
    r"\((?P<legacy>[^()]*)\)\s+"
    r"\((?P<pmgid>[^()]*)\)"
)


class HistoricalExtractionError(RuntimeError):
    """Raised when a report cannot be parsed and validated safely."""


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _missing_text(value: str) -> str | None:
    normalized = _normalize_space(value)
    if normalized.upper() in {"", "-", "NA", "N/A"}:
        return None
    return normalized


def _parse_number(value: str, field: str, context: str) -> float | None:
    normalized = _normalize_space(value)
    if normalized.upper() in {"", "-", "NA", "N/A"}:
        return None
    try:
        return float(normalized.replace(",", ""))
    except ValueError as exc:
        raise HistoricalExtractionError(
            f"Malformed {field} value {value!r} in {context}."
        ) from exc


def _parse_month_value(value: str, field: str, context: str) -> str | None:
    normalized = _missing_text(value)
    if normalized is None:
        return None
    if not DATE_PATTERN.fullmatch(normalized):
        raise HistoricalExtractionError(
            f"Malformed {field} value {value!r} in {context}; expected MM/YYYY."
        )
    return normalized


def _cluster_lines(words: Iterable[dict[str, Any]], tolerance: float = 2.0) -> list[tuple[float, str]]:
    """Group positioned PDF words into visual text lines."""
    ordered = sorted(words, key=lambda word: (float(word["top"]), float(word["x0"])))
    grouped: list[tuple[float, list[dict[str, Any]]]] = []
    for word in ordered:
        top = float(word["top"])
        if not grouped or abs(top - grouped[-1][0]) > tolerance:
            grouped.append((top, [word]))
        else:
            grouped[-1][1].append(word)

    return [
        (top, _normalize_space(" ".join(word["text"] for word in sorted(line, key=lambda item: item["x0"]))))
        for top, line in grouped
    ]


def _band_words(
    words: list[dict[str, Any]], start: float, end: float, left: float, right: float
) -> list[dict[str, Any]]:
    return [
        word
        for word in words
        if start <= float(word["top"]) < end and left <= float(word["x0"]) < right
    ]


def _band_text(
    words: list[dict[str, Any]], start: float, end: float, left: float, right: float
) -> str:
    return _normalize_space(
        " ".join(text for _, text in _cluster_lines(_band_words(words, start, end, left, right)))
    )


def _split_trailing_parenthesized(value: str, context: str) -> tuple[str, str]:
    """Split ``project name (agency)`` while allowing parentheses inside names."""
    text = value.rstrip()
    if not text.endswith(")"):
        raise HistoricalExtractionError(f"Agency group is missing in {context}: {value!r}")

    depth = 0
    for index in range(len(text) - 1, -1, -1):
        if text[index] == ")":
            depth += 1
        elif text[index] == "(":
            depth -= 1
            if depth == 0:
                project_name = text[:index].strip()
                agency = text[index + 1 : -1].strip()
                if not project_name or not agency:
                    break
                return project_name, agency

    raise HistoricalExtractionError(f"Could not separate project name and agency in {context}.")


def _parse_project_column(
    lines: list[tuple[float, str]], context: str
) -> tuple[list[str], str, str, str, str | None, str | None]:
    flattened = _normalize_space(" ".join(text for _, text in lines))
    tail = PROJECT_TAIL_PATTERN.search(flattened)
    if tail is None:
        raise HistoricalExtractionError(
            f"Could not parse project identifiers from the project column in {context}: {flattened!r}"
        )

    project_id = tail.group("project_id")
    legacy = _missing_text(tail.group("legacy"))
    pmgid = _missing_text(tail.group("pmgid"))

    identifier_line = next(
        (
            index
            for index, (_, text) in enumerate(lines)
            if re.search(rf"\({re.escape(project_id)}\)", text)
        ),
        len(lines),
    )
    project_start = 0
    for index in range(max(0, identifier_line - 1)):
        if lines[index + 1][0] - lines[index][0] > 14:
            project_start = index + 1

    heading_lines = [text for _, text in lines[:project_start]]
    project_text = _normalize_space(" ".join(text for _, text in lines[project_start:]))
    project_tail = PROJECT_TAIL_PATTERN.search(project_text)
    if project_tail is None:
        raise HistoricalExtractionError(
            f"Grouping headings could not be separated safely in {context}: {project_text!r}"
        )

    name_and_agency = project_text[: project_tail.start()].strip()
    project_name, agency = _split_trailing_parenthesized(name_and_agency, context)
    return heading_lines, project_id, project_name, agency, legacy, pmgid


def _project_blocks(words: list[dict[str, Any]]) -> list[list[tuple[float, str]]]:
    """Split a page into project records using the three trailing identifiers."""
    lines = _cluster_lines(
        [
            word
            for word in words
            if float(word["top"]) > 250 and 80 <= float(word["x0"]) < 470
        ]
    )
    blocks: list[list[tuple[float, str]]] = []
    current: list[tuple[float, str]] = []
    for line in lines:
        if not current and re.fullmatch(r"Total\s*\(\d+\)", line[1], re.IGNORECASE):
            continue
        current.append(line)
        if PROJECT_TAIL_PATTERN.search(_normalize_space(" ".join(text for _, text in current))):
            blocks.append(current)
            current = []
    return blocks


def _parse_pair(
    value: str, pattern: re.Pattern[str], field: str, context: str
) -> tuple[str, str]:
    tokens = pattern.findall(value)
    # Some official report rows render a pair of unavailable values as
    # ``NA ()`` rather than ``NA (NA)``. Preserve both fields as unavailable;
    # never infer either member of the pair.
    compact_unavailable_pair = re.fullmatch(
        r"\s*(?:N/?A\s*\(\s*\)|\(\s*-\s*\))\s*", value, re.IGNORECASE
    )
    if len(tokens) == 1 and compact_unavailable_pair:
        return tokens[0], tokens[0]
    if len(tokens) != 2:
        raise HistoricalExtractionError(
            f"Expected two {field} values in {context}, found {tokens!r} from {value!r}."
        )
    return tokens[0], tokens[1]


def _parse_single(
    value: str, pattern: re.Pattern[str], field: str, context: str
) -> str:
    tokens = pattern.findall(value)
    if len(tokens) != 1:
        raise HistoricalExtractionError(
            f"Expected one {field} value in {context}, found {tokens!r} from {value!r}."
        )
    return tokens[0]


DATE_TOKEN_PATTERN = re.compile(
    r"\d{2}/\d{4}|\bN/?A\b|(?<!\w)-(?!\w)", re.IGNORECASE
)
NUMBER_TOKEN_PATTERN = re.compile(
    r"\d[\d,]*(?:\.\d+)?|(?<!\w)-(?!\w)|\bN/?A\b", re.IGNORECASE
)


def _report_month_from_text(text: str, source_report: str) -> str:
    match = re.search(
        r"\b(" + "|".join(MONTH_NUMBERS) + r")\s+(20\d{2})\b",
        text.upper(),
    )
    if match is None:
        raise HistoricalExtractionError(f"Could not determine report month from {source_report}.")
    return f"{int(match.group(2)):04d}-{MONTH_NUMBERS[match.group(1)]:02d}"


def _find_table_pages(pdf: pdfplumber.PDF, source_report: str) -> tuple[str, list[int]]:
    """Locate only the Table 6 title and its following repeated-header pages."""
    title_pages: list[int] = []
    page_texts: list[str] = []
    for index, page in enumerate(pdf.pages):
        text = page.extract_text(x_tolerance=1, y_tolerance=2) or ""
        page_texts.append(text)
        if index > 5 and "Table 6: All Ongoing Projects" in text:
            title_pages.append(index)

    if len(title_pages) != 1:
        raise HistoricalExtractionError(
            f"Expected one Table 6 title in {source_report}, found pages "
            f"{[page + 1 for page in title_pages]}."
        )

    data_pages: list[int] = []
    for index in range(title_pages[0] + 1, len(pdf.pages)):
        text = page_texts[index]
        if "All Ongoing Projects" in text and "Sl.No" in text:
            data_pages.append(index)
        elif data_pages:
            break

    if not data_pages:
        raise HistoricalExtractionError(f"No Table 6 data pages found in {source_report}.")

    return _report_month_from_text(page_texts[data_pages[0]], source_report), data_pages


def _update_grouping(
    headings: list[str], ministry: str | None, sector: str | None, context: str
) -> tuple[str | None, str | None]:
    if not headings:
        return ministry, sector

    if headings[0].startswith(("Ministry of ", "Department of ")):
        if len(headings) < 2:
            raise HistoricalExtractionError(
                f"Ministry heading has no accompanying sector in {context}: {headings!r}"
            )
        ministry = _normalize_space(" ".join(headings[:-1]))
        sector = headings[-1]
    else:
        sector = _normalize_space(" ".join(headings))

    return ministry, sector


def extract_table6_report(pdf_path: str | Path) -> pd.DataFrame:
    """Extract and validate Table 6 from one official monthly Flash Report."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"Historical PAIMANA report not found: {path}")

    rows: list[dict[str, Any]] = []
    serial_numbers: list[int] = []
    ministry: str | None = None
    sector: str | None = None

    with pdfplumber.open(path) as pdf:
        report_month, data_pages = _find_table_pages(pdf, path.name)

        for page_index in data_pages:
            page = pdf.pages[page_index]
            words = page.extract_words(x_tolerance=1, y_tolerance=2, keep_blank_chars=False)
            blocks = _project_blocks(words)

            for block_index, project_lines in enumerate(blocks):
                start = max(250.0, project_lines[0][0] - 3)
                broad_end = (
                    1440.0
                    if block_index == len(blocks) - 1
                    else blocks[block_index + 1][0][0] - 2
                )
                anchors = [
                    word
                    for word in words
                    if start <= float(word["top"]) < broad_end
                    and float(word["x0"]) < 80
                    and re.fullmatch(r"\d+", word["text"])
                ]
                if len(anchors) != 1:
                    raise HistoricalExtractionError(
                        f"Expected one serial number in {path.name}, PDF page "
                        f"{page_index + 1}, project block {block_index + 1}; "
                        f"found {[word['text'] for word in anchors]}."
                    )
                serial_number = int(anchors[0]["text"])
                end = float(anchors[0]["top"]) + 15
                context = f"{path.name}, PDF page {page_index + 1}, serial {serial_number}"

                headings, project_id, project_name, agency, legacy, pmgid = _parse_project_column(
                    project_lines, context
                )
                ministry, sector = _update_grouping(headings, ministry, sector, context)
                if ministry is None or sector is None:
                    raise HistoricalExtractionError(
                        f"Missing carried ministry/sector grouping in {context}."
                    )

                state = _missing_text(_band_text(words, start, end, 470, 560))
                approval_raw, start_raw = _parse_pair(
                    _band_text(words, start, end, 560, 650),
                    DATE_TOKEN_PATTERN,
                    "approval/start date",
                    context,
                )
                target_raw, revised_doc_raw = _parse_pair(
                    _band_text(words, start, end, 650, 750),
                    DATE_TOKEN_PATTERN,
                    "target/revised completion date",
                    context,
                )
                original_cost_raw, revised_cost_raw = _parse_pair(
                    _band_text(words, start, end, 750, 840),
                    NUMBER_TOKEN_PATTERN,
                    "original/revised cost",
                    context,
                )
                expenditure_raw = _parse_single(
                    _band_text(words, start, end, 840, 930),
                    NUMBER_TOKEN_PATTERN,
                    "cumulative expenditure",
                    context,
                )
                progress_raw = _parse_single(
                    _band_text(words, start, end, 930, 1030),
                    NUMBER_TOKEN_PATTERN,
                    "physical progress",
                    context,
                )

                revised_cost_numeric = _parse_number(revised_cost_raw, "revised cost", context)
                revised_cost_available = (
                    revised_cost_numeric is not None and revised_cost_numeric > 0
                )

                rows.append(
                    {
                        "report_month": report_month,
                        "ministry": ministry,
                        "sector": sector,
                        "project_id": str(project_id),
                        "project_name": project_name,
                        "agency": agency,
                        "legacy_ocms_code": legacy,
                        "pmgid": pmgid,
                        "state": state,
                        "approval_date": _parse_month_value(
                            approval_raw, "approval date", context
                        ),
                        "start_date": _parse_month_value(start_raw, "start date", context),
                        "original_target_doc": _parse_month_value(
                            target_raw, "original target DoC", context
                        ),
                        "revised_doc": _parse_month_value(
                            revised_doc_raw, "revised DoC", context
                        ),
                        "original_cost_cr": _parse_number(
                            original_cost_raw, "original cost", context
                        ),
                        "revised_cost_cr": (
                            revised_cost_numeric if revised_cost_available else None
                        ),
                        "revised_cost_raw": revised_cost_raw,
                        "revised_cost_available": revised_cost_available,
                        "cumulative_expenditure_cr": _parse_number(
                            expenditure_raw, "cumulative expenditure", context
                        ),
                        "physical_progress_pct": _parse_number(
                            progress_raw, "physical progress", context
                        ),
                        "source_report": path.name,
                    }
                )
                serial_numbers.append(serial_number)

    extracted = pd.DataFrame(rows, columns=NORMALIZED_COLUMNS)
    expected_serials = list(range(1, len(extracted) + 1))
    if serial_numbers != expected_serials:
        mismatch = next(
            (
                (position, actual, expected)
                for position, (actual, expected) in enumerate(
                    zip(serial_numbers, expected_serials), start=1
                )
                if actual != expected
            ),
            None,
        )
        raise HistoricalExtractionError(
            f"Serial-number validation failed for {path.name}: {mismatch}."
        )
    return extracted


def summarize_data_quality(history: pd.DataFrame) -> pd.DataFrame:
    """Return the required month-level extraction and data-quality controls."""
    summaries: list[dict[str, Any]] = []
    for report_month, month_data in history.groupby("report_month", sort=True):
        official_count = OFFICIAL_PROJECT_COUNTS.get(report_month)
        summaries.append(
            {
                "report_month": report_month,
                "extracted_rows": int(len(month_data)),
                "official_rows": official_count,
                "official_count_difference": (
                    None if official_count is None else int(len(month_data) - official_count)
                ),
                "unique_project_ids": int(month_data["project_id"].nunique(dropna=True)),
                "duplicate_project_month_pairs": int(
                    month_data.duplicated(["project_id", "report_month"]).sum()
                ),
                "missing_project_ids": int(month_data["project_id"].isna().sum()),
                "missing_ministry": int(month_data["ministry"].isna().sum()),
                "missing_sector": int(month_data["sector"].isna().sum()),
                "missing_original_cost": int(month_data["original_cost_cr"].isna().sum()),
                "missing_cumulative_expenditure": int(
                    month_data["cumulative_expenditure_cr"].isna().sum()
                ),
                "missing_physical_progress": int(
                    month_data["physical_progress_pct"].isna().sum()
                ),
                "available_revised_cost": int(
                    month_data["revised_cost_available"].sum()
                ),
                "unavailable_revised_cost": int(
                    (~month_data["revised_cost_available"]).sum()
                ),
                "malformed_dates": 0,
            }
        )
    return pd.DataFrame(summaries)


def validate_history(history: pd.DataFrame) -> pd.DataFrame:
    """Fail rather than save data that violates critical extraction controls."""
    if list(history.columns) != NORMALIZED_COLUMNS:
        raise HistoricalExtractionError("Historical data does not match the normalized schema.")

    quality = summarize_data_quality(history)
    critical_failures: list[str] = []
    for row in quality.to_dict("records"):
        month = row["report_month"]
        if pd.notna(row["official_rows"]) and row["official_count_difference"] != 0:
            critical_failures.append(
                f"{month}: extracted {row['extracted_rows']} vs official {row['official_rows']}"
            )
        for field in (
            "duplicate_project_month_pairs",
            "missing_project_ids",
            "missing_ministry",
            "missing_sector",
            "malformed_dates",
        ):
            if row[field]:
                critical_failures.append(f"{month}: {field}={row[field]}")

    if critical_failures:
        raise HistoricalExtractionError(
            "Historical extraction failed validation: " + "; ".join(critical_failures)
        )
    return quality


def add_historical_changes(history: pd.DataFrame) -> pd.DataFrame:
    """Add neutral consecutive-month changes for each project."""
    result = history.copy()
    result["_month_period"] = pd.PeriodIndex(result["report_month"], freq="M")
    result = result.sort_values(["project_id", "_month_period"]).reset_index(drop=True)
    grouped = result.groupby("project_id", sort=False)
    previous_period = grouped["_month_period"].shift(1)
    month_number = result["_month_period"].map(lambda value: value.ordinal)
    previous_month_number = previous_period.map(
        lambda value: value.ordinal if pd.notna(value) else np.nan
    )
    consecutive = (month_number - previous_month_number) == 1

    change_specs = {
        "expenditure_change_cr": "cumulative_expenditure_cr",
        "physical_progress_change_pct_points": "physical_progress_pct",
        "revised_cost_change_cr": "revised_cost_cr",
    }
    for output_column, source_column in change_specs.items():
        previous = grouped[source_column].shift(1)
        valid = consecutive & result[source_column].notna() & previous.notna()
        result[output_column] = np.where(valid, result[source_column] - previous, np.nan)

    previous_doc = grouped["revised_doc"].shift(1)
    valid_doc = consecutive & result["revised_doc"].notna() & previous_doc.notna()
    result["revised_doc_changed"] = pd.Series(pd.NA, index=result.index, dtype="boolean")
    result.loc[valid_doc, "revised_doc_changed"] = (
        result.loc[valid_doc, "revised_doc"] != previous_doc.loc[valid_doc]
    )
    return result.drop(columns="_month_period")


def build_historical_dataset(
    raw_report_dir: str | Path = RAW_REPORT_DIR,
    output_path: str | Path = PROCESSED_CSV_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract all discovered monthly reports, validate, and save one CSV."""
    raw_dir = Path(raw_report_dir)
    reports = sorted(raw_dir.glob(REPORT_PATTERN))
    if not reports:
        raise FileNotFoundError(f"No PAIMANA Flash Reports found in {raw_dir}.")

    history = pd.concat(
        [extract_table6_report(report) for report in reports], ignore_index=True
    )
    history = history.sort_values(["report_month", "project_id"]).reset_index(drop=True)
    quality = validate_history(history)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(destination, index=False, encoding="utf-8")
    return history, quality


def _print_verification() -> None:
    reports = sorted(RAW_REPORT_DIR.glob(REPORT_PATTERN))
    print("Reports discovered:")
    for report in reports:
        print(f"  {report.name}")

    history, quality = build_historical_dataset()
    print(f"\nMonths loaded: {', '.join(sorted(history['report_month'].unique()))}")
    print(f"Normalized columns: {list(history.columns)}")
    print("\nData-quality summary:")
    print(quality.to_string(index=False))

    example = history.loc[history["project_id"].eq("612786")].sort_values("report_month")
    print("\nProject 612786 history:")
    print(
        example[
            [
                "report_month",
                "original_cost_cr",
                "revised_cost_cr",
                "cumulative_expenditure_cr",
                "physical_progress_pct",
                "revised_doc",
            ]
        ].to_string(index=False)
    )

    changes = add_historical_changes(example)
    print("\nProject 612786 month-to-month changes:")
    print(
        changes[
            [
                "report_month",
                "expenditure_change_cr",
                "physical_progress_change_pct_points",
                "revised_cost_change_cr",
                "revised_doc_changed",
            ]
        ].to_string(index=False)
    )
    print(f"\nProcessed CSV: {PROCESSED_CSV_PATH}")


if __name__ == "__main__":
    _print_verification()
