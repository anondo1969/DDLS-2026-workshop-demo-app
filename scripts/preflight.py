"""Zero-dependency preflight checks for the SciLifeLab Serve Streamlit project."""

import argparse
import csv
import fnmatch
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = ROOT / "data" / "adhd_treatment_sweden_workshop_2012_2025.csv"
REQUIRED_COLUMNS = ["year", "area", "area_type", "treated_per_1000"]


def dockerignore_excludes_csv(ignore_text: str) -> bool:
    """Check common .dockerignore exclusions of the required CSV.

    This is a static best-effort check, not a replacement for a Docker build;
    patterns are applied in order, including later !exceptions.
    """
    csv_path = f"data/{CSV_FILE.name}"
    ignored = False
    for raw in ignore_text.splitlines():
        pattern = raw.strip()
        if not pattern or pattern.startswith("#"):
            continue
        keep = pattern.startswith("!")
        if keep:
            pattern = pattern[1:]
        pattern = pattern.lstrip("/").rstrip("/")
        if not pattern:
            continue
        if (
            fnmatch.fnmatchcase(csv_path, pattern)
            or fnmatch.fnmatchcase(CSV_FILE.name, pattern)
            or fnmatch.fnmatchcase("data", pattern)
            or csv_path.startswith(pattern + "/")
        ):
            ignored = not keep
    return ignored


def run(strict: bool) -> list[str]:
    problems: list[str] = []
    required_files = [
        "app/app.py", "app/data.py", "app/charts.py", "app/requirements.txt",
        "Dockerfile", ".dockerignore", ".streamlit/config.toml",
        ".github/workflows/docker-image-ghcr.yml", "README.md", "DEPLOY.md",
    ]
    for item in required_files:
        if not (ROOT / item).is_file():
            problems.append(f"Missing required project file: {item}")
    if not CSV_FILE.is_file():
        problems.append(f"Missing source CSV: data/{CSV_FILE.name}")
        return problems

    with CSV_FILE.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != REQUIRED_COLUMNS:
            problems.append(f"Unexpected CSV columns: {reader.fieldnames}")
            return problems
        rows = list(reader)

    if len(rows) != 308:
        problems.append(f"CSV must have 308 rows, found {len(rows)}")
    pairs = []
    years = []
    area_types = {}
    national = {}
    for number, row in enumerate(rows, start=2):
        try:
            if not re.fullmatch(r"(?:201[2-9]|202[0-5])", row["year"] or ""):
                raise ValueError("year must be an integer from 2012 to 2025")
            year = int(row["year"])
            value = Decimal(row["treated_per_1000"])
            if not value.is_finite() or value < 0:
                raise ValueError("nonfinite/negative rate")
            if not row["area"] or not row["area_type"]:
                raise ValueError("empty area or area_type")
            if row["area_type"] not in ("National", "Region"):
                raise ValueError("area_type must be National or Region")
            if (row["area"] == "Riket") != (row["area_type"] == "National"):
                raise ValueError("Riket must be National; regions must be Region")
        except (ValueError, InvalidOperation, TypeError) as exc:
            problems.append(f"CSV row {number} has invalid values: {exc}")
            continue
        years.append(year)
        pairs.append((row["area"], year))
        area_types[row["area"]] = row["area_type"]
        if row["area"] == "Riket":
            national[year] = value
    if len(set(pairs)) != len(pairs):
        problems.append("Duplicate area-year pair(s) in CSV")
    if set(years) != set(range(2012, 2026)):
        problems.append("CSV must contain every year from 2012 through 2025")
    if len(area_types) != 22:
        problems.append(f"CSV must contain 22 areas, found {len(area_types)}")
    if Counter(area_types.values()) != Counter({"Region": 21, "National": 1}):
        problems.append("CSV must contain 21 regions and one national area")
    if area_types.get("Riket") != "National":
        problems.append("Riket must be National")
    if national.get(2012) != Decimal("16.32") or national.get(2025) != Decimal("48.80"):
        problems.append("National endpoint check failed: 2012=16.32, 2025=48.80")
    if len(pairs) == 308:
        counts = Counter(area for area, _ in pairs)
        if any(count != 14 for count in counts.values()):
            problems.append("Every area must have 14 annual observations")
        missing_pairs = {(area, year) for area in area_types for year in range(2012, 2026)} - set(pairs)
        if missing_pairs:
            problems.append(f"Incomplete area-year panel; {len(missing_pairs)} observation(s) missing")

    if strict:
        if any(not (ROOT / item).is_file() for item in required_files):
            return problems
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        requirements = (ROOT / "app" / "requirements.txt").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/docker-image-ghcr.yml").read_text(encoding="utf-8") if (ROOT / ".github/workflows/docker-image-ghcr.yml").exists() else ""
        required_docker = [
            'FROM python:3.12-slim', 'WORKDIR $HOME/app', 'useradd -m -u 1000',
            'COPY --chown=1000:1000 app/ ./',
            'COPY --chown=1000:1000 data/ $HOME/data/',
            'USER appuser', 'EXPOSE 8501', '0.0.0.0', '_stcore/health',
            '"streamlit", "run", "app.py"', '--browser.gatherUsageStats=false',
        ]
        for item in required_docker:
            if item not in dockerfile:
                problems.append(f"Dockerfile is missing Streamlit profile contract: {item}")
        if dockerignore_excludes_csv((ROOT / ".dockerignore").read_text(encoding="utf-8")):
            problems.append(f"Docker build context excludes required CSV: data/{CSV_FILE.name}")
        for dependency in ("streamlit", "pandas", "plotly"):
            if not re.search(rf"(?m)^{dependency}==[0-9]", requirements):
                problems.append(f"Dependency {dependency} must be pinned with ==")
        for term in ("linux/amd64", "ghcr.io", "GITHUB_SHA", "docker push", "_stcore/health", "workflow_dispatch"):
            if term not in workflow:
                problems.append(f"GitHub workflow missing required term: {term}")
        if workflow.count("if: github.event_name == 'workflow_dispatch'") < 3:
            problems.append("GHCR login, image push, and image summary must be manual-dispatch only")

    return problems


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Also verify Docker/CI setup")
    args = parser.parse_args()
    issues = run(args.strict)
    if issues:
        for issue in issues:
            print("FAIL:", issue, file=sys.stderr)
        sys.exit(1)
    print("PASS: 308 original rows, 22 areas, 14 years, national endpoints, and expected project files")
    if args.strict:
        print("PASS: Static Streamlit Dockerfile, CSV COPY/build-context paths, version pins, and gated GHCR workflow (image not built)")
