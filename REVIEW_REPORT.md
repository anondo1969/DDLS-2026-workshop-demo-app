# Review report — 6 November 2026

## Scope and outcome

Reviewed the revised ADHD treatment in Sweden Streamlit project against the
**exact user-uploaded CSV**, the [SciLifeLab Serve template's Streamlit
profile](https://github.com/ScilifelabDataCentre/serve-app-template/blob/main/profiles/streamlit/Dockerfile),
its [AGENTS.md](https://github.com/ScilifelabDataCentre/serve-app-template/blob/main/AGENTS.md),
the [Serve Streamlit guide](https://serve.scilifelab.se/docs/application-hosting/streamlit/),
and the [indicator metadata](https://vardenisiffror.se/sv/indikatorer/adhd-behandling-bland-barn-och-unga).

**Result: static data/deployment checks and runnable Python tests pass after fixes.**
The Streamlit UI and an actual Docker container could not be run in this environment.
**No GitHub push, GHCR publication, or Serve deployment occurred.**

## Verified

- The copied CSV is byte-for-byte identical to the uploaded CSV. SHA-256:
  `b914b87721e847a3bb627a494d9a2c18b5c2aca86de481abd93eebb5ccef5377`.
- All 308 rows, 22 areas (Riket and 21 regions), and 14 years (2012–2025) are
  present; no missing values or duplicate area/year observations were found.
- National source observations are **Riket 2012 = 16.32**, **Riket 2025 = 48.80**;
  the absolute change is **+32.48 per 1,000 inhabitants**, not a percentage.
- Filters preserve original observations and year order; the comparison uses
  all 21 regions for the selected year, with **source-supplied** Riket as the
  reference line (never an unweighted mean).
- Chart data/hover and axis labels describe **ADHD medication treatment**
  with rates *per 1,000 inhabitants*. The source describes ages 0–17 and uses
  **Läkemedelsregistret, Socialstyrelsen**. Rates are aggregate observations,
  not estimates of ADHD prevalence or a care-quality ranking.
- Dockerfile is adapted from the referenced Streamlit profile: Python 3.12-slim,
  UID 1000 non-root, Streamlit `app.py` in the work directory,
  `0.0.0.0:8501`, exposed port 8501, health endpoint `/_stcore/health`.
- Build context includes `data/adhd_treatment_sweden_workshop_2012_2025.csv`
  and `COPY --chown=1000:1000 data/ $HOME/data/` places it at
  `/home/appuser/data/`. A test recreates that layout and successfully loads
  all 308 rows without relying on the process working directory.
- Workflow targets `linux/amd64`, uses unique GHCR tags, and only pushes an
  image when **manually dispatched**. Pushes to `main` run checks/build and
  smoke tests but do not publish a container image.

## Issues found and corrected

1. **Potential silent rounding of invalid years:** floating-point parsing
   accepted a fractional year such as `2012.0000000000000001` as 2012.
   Validation now requires an exact whole-number year in 2012–2025;
   corrupted-year tests were added.
2. **Unapproved automatic container publication risk:** GHCR image publishing
   was previously triggered by any `main` push. Publishing now requires a
   manual `workflow_dispatch` and README/deployment steps reflect the gate.
   **Note:** pushing to a *public* GitHub repository still makes code and CSV
   public, so check redistribution permission before pushing.
3. **Ambiguous labeling:** charts and table now explicitly label ADHD
   *medication* treatment; the metric explanation clarifies that a rate
   difference is neither a percentage nor a number of patients.
4. **Limited deployment coverage:** added .dockerignore detection, Docker
   contract tests, a simulated container filesystem test, and stricter
   standard-library preflight checks.

## Commands executed / status

| Check | Result |
| --- | --- |
| `python scripts/preflight.py --strict` | PASS |
| `python -m unittest discover -s tests -v` | PASS — 23 passed, 1 skipped |
| `python -m pytest -q` | PASS — see final test output / equivalent collection |
| `python -m compileall -q app scripts tests` | PASS |
| Real CSV SHA-256 comparison | PASS — hashes match |
| Plotly chart data and serialization checks | PASS |
| `.github/workflows/docker-image-ghcr.yml` YAML syntax | PASS (local YAML parser) |
| Re-created Docker filesystem layout and CSV load | PASS |
| Streamlit `AppTest` UI rerun | NOT VERIFIED — Streamlit not installed here |
| Streamlit pip installation | BLOCKED — package index DNS/network unavailable |
| Docker `build --platform linux/amd64` / container smoke test | NOT VERIFIED — Docker executable unavailable |
| GitHub Actions execution / GHCR and Serve deployment | NOT RUN — requires approval and a GitHub/Serve environment |

Local tests used **Python 3.13.5**, **pandas 2.2.3**, and **Plotly 6.5.2**.
The intended image uses **Python 3.12**, and requirements pin **Plotly 6.3.0**;
that exact installed runtime remains unverified until you run Docker or
install dependencies on Python 3.12.

## Required user-side verification (before any deployment)

From the project root with Docker available:

```bash
docker build --platform linux/amd64 -t adhd-treatment-sweden:review .
docker run -d --rm --name adhd-review -p 8501:8501 adhd-treatment-sweden:review
curl --fail http://127.0.0.1:8501/_stcore/health
docker exec adhd-review python -c "from data import load_data; d=load_data(); print(len(d), d.loc[(d.area=='Riket') & (d.year==2025), 'treated_per_1000'].iloc[0])"
docker stop adhd-review
```

Open <http://localhost:8501> **before** the `docker stop` command. Confirm
that the two charts appear and that selecting areas, adjusting the year range,
and selecting the regional comparison year updates the expected elements.
The GitHub Actions job will repeat the Docker build/health test after an
approved push; a separate **Run workflow** action is required to publish an image.

Confirm the data reuse terms and attribution obligations with the source owner
before making the **CSV or container image public**.
