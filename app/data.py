"""Validated loading and simple selection of the workshop's aggregate CSV.

The CSV is the sole data source. No population-weighted or unweighted
national rates are computed from regional rates.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


CSV_NAME = "adhd_treatment_sweden_workshop_2012_2025.csv"
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / CSV_NAME
COLUMNS = ("year", "area", "area_type", "treated_per_1000")
YEARS = tuple(range(2012, 2026))
EXPECTED_ROWS = 308
EXPECTED_AREAS = 22
EXPECTED_REGIONS = 21
NATIONAL_CHECKS = {2012: 16.32, 2025: 48.80}


class DataValidationError(ValueError):
    """One or more clear, user-facing data quality problems."""

    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("; ".join(issues))


@dataclass(frozen=True)
class AreaSummary:
    area: str
    first_year: int
    latest_year: int
    first_rate: float
    latest_rate: float
    absolute_change: float


def load_data(path: Path | str = DATA_PATH) -> pd.DataFrame:
    """Load and strictly validate a complete 22-area x 14-year indicator panel.

    Invalid input raises DataValidationError instead of dropping observations.
    """
    csv_path = Path(path)
    if not csv_path.is_file():
        raise DataValidationError([
            f"Data file not found: {csv_path}. Put the original CSV at "
            f"data/{CSV_NAME} (relative to the project root), then restart the app."
        ])

    try:
        raw = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise DataValidationError([f"Could not read CSV at {csv_path}: {exc}"]) from exc

    issues: list[str] = []
    missing_columns = sorted(set(COLUMNS) - set(raw.columns))
    unexpected_columns = sorted(set(raw.columns) - set(COLUMNS))
    if missing_columns:
        issues.append("Missing required columns: " + ", ".join(missing_columns))
    if unexpected_columns:
        issues.append("Unexpected columns: " + ", ".join(unexpected_columns))
    if issues:
        raise DataValidationError(issues)

    frame = raw.loc[:, list(COLUMNS)].copy()
    for column in ("year", "area", "area_type", "treated_per_1000"):
        frame[column] = frame[column].astype("string").str.strip()

    missing_area = frame["area"].isna() | frame["area"].eq("")
    missing_type = frame["area_type"].isna() | frame["area_type"].eq("")
    if missing_area.any():
        issues.append(f"Missing area values in {int(missing_area.sum())} row(s).")
    if missing_type.any():
        issues.append(f"Missing area_type values in {int(missing_type.sum())} row(s).")

    # Require a literal integer year. Float parsing alone can silently round
    # strings such as "2012.0000000000000001" down to 2012.
    years = pd.to_numeric(frame["year"], errors="coerce")
    year_text_is_valid = frame["year"].str.fullmatch(r"(?:201[2-9]|202[0-5])", na=False)
    rates = pd.to_numeric(frame["treated_per_1000"], errors="coerce")
    bad_year = years.isna() | ~year_text_is_valid
    bad_rate = rates.isna() | ~np.isfinite(rates)
    if bad_year.any():
        issues.append(
            f"Missing, nonnumeric, or noninteger year (expected integer 2012-2025) "
            f"in {int(bad_year.sum())} row(s)."
        )
    if bad_rate.any():
        issues.append(f"Missing, nonnumeric, or nonfinite treated_per_1000 in {int(bad_rate.sum())} row(s).")
    if (rates < 0).any():
        issues.append("Negative treated_per_1000 values are not valid.")
    if issues:
        raise DataValidationError(issues)

    frame["year"] = years.astype(int)
    frame["treated_per_1000"] = rates.astype(float)

    if len(frame) != EXPECTED_ROWS:
        issues.append(f"Expected {EXPECTED_ROWS} rows; found {len(frame)}.")
    area_count = frame["area"].nunique()
    if area_count != EXPECTED_AREAS:
        issues.append(f"Expected {EXPECTED_AREAS} areas (Riket + 21 regions); found {area_count}.")
    actual_years = set(frame["year"].tolist())
    expected_years = set(YEARS)
    if actual_years != expected_years:
        issues.append(
            "Expected all years 2012-2025; "
            f"missing={sorted(expected_years - actual_years)}, "
            f"unexpected={sorted(actual_years - expected_years)}."
        )

    duplicates = frame.duplicated(subset=["area", "year"], keep=False)
    if duplicates.any():
        pairs = frame.loc[duplicates, ["area", "year"]].drop_duplicates().head(4)
        examples = ", ".join(f"{row.area} {row.year}" for row in pairs.itertuples())
        issues.append(f"Repeated area-year pair(s): {examples}.")

    invalid_types = frame[~frame["area_type"].isin(["National", "Region"])]
    if not invalid_types.empty:
        issues.append("area_type must be National or Region (invalid values found).")
    mismatched = frame[
        ((frame["area"] == "Riket") & (frame["area_type"] != "National"))
        | ((frame["area"] != "Riket") & (frame["area_type"] != "Region"))
    ]
    if not mismatched.empty:
        issues.append("area_type mismatch: only Riket may be National; all other areas must be Region.")
    regions = frame.loc[frame["area_type"] == "Region", "area"].nunique()
    if regions != EXPECTED_REGIONS:
        issues.append(f"Expected {EXPECTED_REGIONS} regions; found {regions}.")

    seen_pairs = set(zip(frame["area"], frame["year"]))
    required_pairs = {(area, year) for area in frame["area"].unique() for year in YEARS}
    missing_pairs = required_pairs - seen_pairs
    if missing_pairs:
        preview = ", ".join(f"{a} {y}" for a, y in sorted(missing_pairs)[:4])
        issues.append(f"Missing area-year observations: {preview}.")

    for year, expected_value in NATIONAL_CHECKS.items():
        result = frame.loc[(frame["area"] == "Riket") & (frame["year"] == year), "treated_per_1000"]
        if len(result) != 1 or not np.isclose(float(result.iloc[0]), expected_value, atol=1e-8, rtol=0):
            issues.append(f"Riket {year} must be {expected_value:.2f} per 1,000 in this CSV.")

    if issues:
        raise DataValidationError(issues)
    return frame.sort_values(["year", "area"], kind="stable").reset_index(drop=True)


def filter_trends(data: pd.DataFrame, areas: list[str], year_range: tuple[int, int]) -> pd.DataFrame:
    """Return exactly the selected area-year observations, sorted for plotting."""
    start, end = year_range
    if start > end:
        raise ValueError("The start year cannot be after the end year.")
    return (
        data.loc[data["area"].isin(areas) & data["year"].between(start, end)]
        .sort_values(["area", "year"], kind="stable")
        .reset_index(drop=True)
    )


def summarize_area(filtered: pd.DataFrame, area: str) -> AreaSummary:
    """Absolute difference of rates, not a percent or population change."""
    area_rows = filtered.loc[filtered["area"] == area].sort_values("year")
    if area_rows.empty:
        raise ValueError(f"No observations for selected area {area} in this range.")
    first = area_rows.iloc[0]
    last = area_rows.iloc[-1]
    return AreaSummary(
        area=area,
        first_year=int(first["year"]),
        latest_year=int(last["year"]),
        first_rate=float(first["treated_per_1000"]),
        latest_rate=float(last["treated_per_1000"]),
        absolute_change=float(last["treated_per_1000"] - first["treated_per_1000"]),
    )


def comparison_for_year(data: pd.DataFrame, year: int) -> tuple[pd.DataFrame, float]:
    """Return all 21 regional observations and the source-supplied Riket value."""
    year_data = data.loc[data["year"] == year]
    regions = (
        year_data.loc[year_data["area_type"] == "Region"]
        .sort_values(["treated_per_1000", "area"], kind="stable")
        .reset_index(drop=True)
    )
    national = year_data.loc[year_data["area"] == "Riket", "treated_per_1000"]
    if len(national) != 1 or len(regions) != EXPECTED_REGIONS:
        raise ValueError(f"Incomplete regional/national comparison for {year}.")
    return regions, float(national.iloc[0])
