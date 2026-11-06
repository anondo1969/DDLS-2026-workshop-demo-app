# ADHD treatment in Sweden: explore the data

A small, public, educational Streamlit dashboard for a DDLS workshop. It shows
annual ADHD medication treatment rates for children and young people aged 0-17
across Sweden ("Riket") and all 21 regions, with two interactive Plotly charts,
summary metrics, a filtered table, and a filtered CSV download.

**Unit:** treated children and young people per 1,000 inhabitants. It is not an
ADHD prevalence estimate, a clinical recommendation, or a care quality ranking.

**Data source:** the single bundled workshop CSV, an export of the Varden i
siffror indicator ["ADHD-behandling bland barn och unga"](https://vardenisiffror.se/sv/indikatorer/adhd-behandling-bland-barn-och-unga).
The indicator attributes its source to Läkemedelsregistret, Socialstyrelsen.
The source webpage defines the age group as 0-17 years. The full input is **308
aggregate rows: 22 areas x 14 years (2012-2025)**. It is not individual-level
patient data. Original uploaded CSV SHA-256:
`b914b87721e847a3bb627a494d9a2c18b5c2aca86de481abd93eebb5ccef5377`.

**Important for public deployment:** check the Vården i siffror data reuse
terms, any attribution obligations, and your institution's publication
requirements **before** publishing this dataset or image publicly. No data
license is asserted by this repository; choose a code license separately if
publishing your source. No user data or tracking is collected.

## Project layout

```text
adhd-treatment-sweden/
|-- .github/workflows/docker-image-ghcr.yml
|-- .streamlit/config.toml
|-- .dockerignore
|-- .gitignore
|-- AGENTS.md
|-- DEPLOY.md
|-- Dockerfile
|-- README.md
|-- REVIEW_REPORT.md
|-- app/
|   |-- __init__.py
|   |-- app.py
|   |-- charts.py
|   |-- data.py
|   `-- requirements.txt
|-- data/
|   `-- adhd_treatment_sweden_workshop_2012_2025.csv
|-- scripts/
|   `-- preflight.py
`-- tests/
    |-- test_charts.py
    |-- test_data.py
    |-- test_deployment.py
    `-- test_streamlit.py
```

## 1. Run locally (Python 3.12 recommended)

From the directory containing this README, on macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r app/requirements.txt
python scripts/preflight.py --strict
python -m unittest discover -s tests -v
streamlit run app/app.py --server.port=8501 --browser.gatherUsageStats=false
```

Visit **http://localhost:8501**. Stop with `Ctrl+C`.

If `python3.12` is not installed, install Python 3.12, then repeat these
commands. The equivalent Windows PowerShell activation command is
`.venv\Scripts\Activate.ps1` (using `py -3.12 -m venv .venv`).

### Data file and validation

The supplied CSV is already in `data/` in this project. If working from code
without the CSV, **do not** generate dummy data: place the exact original file
at `data/adhd_treatment_sweden_workshop_2012_2025.csv` and rerun the app.
The app prints an actionable error if the file is missing or invalid.

The validator fails on missing/unexpected columns, missing or invalid numeric
values, noninteger or out-of-range years (including values that float parsing
could incorrectly round), negative or nonfinite rates, duplicate area-year combinations,
area-type mismatches, incomplete years/areas, and incorrect source national
values. It explicitly requires **Riket 2012 = 16.32** and **Riket 2025 = 48.80**.
There is no imputation or averaging of regional values into Riket.

The tests cover data integrity, corrupted inputs, filtered rate-change
calculations, Plotly charts, static Docker file inclusion and port checks,
a simulated in-container CSV loading path, and (when Streamlit is installed)
actual UI widget reruns via `streamlit.testing.v1.AppTest`.

See [REVIEW_REPORT.md](REVIEW_REPORT.md) for the validation run, findings, and
what remains unverified without Docker or a Streamlit runtime.

## 2. Build and smoke-test Docker locally

Install and start Docker Desktop (or another Docker Engine). From the project
root, run exactly:

```bash
docker build --platform linux/amd64 -t adhd-treatment-sweden:local .
docker run -d --rm --name adhd-treatment-sweden -p 8501:8501 adhd-treatment-sweden:local
curl --fail http://127.0.0.1:8501/_stcore/health
docker exec adhd-treatment-sweden python -c "from data import load_data; d=load_data(); print(len(d), d.query('area == \"Riket\" and year == 2025').iloc[0].treated_per_1000)"
docker stop adhd-treatment-sweden
```

Open **http://localhost:8501** *before stopping* to confirm both charts render
and that changing the area/year filters updates the charts and table. If the
health check fails on the first attempt while Streamlit starts, retry it.

The Dockerfile is adapted from the
[Serve template's Streamlit profile](https://github.com/ScilifelabDataCentre/serve-app-template/blob/main/profiles/streamlit/Dockerfile):
Python **3.12-slim**, non-root user **UID 1000**, in-container `app.py` in the
WORKDIR, bind **0.0.0.0:8501**, a standard Streamlit health check, and
telemetry disabled. Docker copies the real CSV to `/home/appuser/data/`, which
is exactly where `app/data.py` resolves `../data/` at runtime.

## 3. Deploy through GitHub to SciLifeLab Serve (only after approval)

**Nothing has been pushed or deployed for you.** After reviewing your data
reuse rights, create an **empty public GitHub repository** under an account or
organization you control. Replace `YOUR_OWNER` and `YOUR_REPO` below; from this
project root:

```bash
git init
git add .
git commit -m "Initial Streamlit research dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_OWNER/YOUR_REPO.git
git push -u origin main
```

**The final `git push` makes the source and bundled CSV public in your GitHub
repository, so confirm redistribution rights first.** A push to `main` triggers
GitHub Actions to install the pinned dependencies, validate the CSV, run tests,
build for `linux/amd64`, and smoke-test the container. **It does not publish a
container image.**

**After separate approval to publish the image**, open your GitHub repository:
**Actions > Validate Streamlit app (manual approval to publish image) > Run
workflow > Run workflow** on `main`. This explicit `workflow_dispatch` run
performs the same validations and Docker health test, then publishes a uniquely
tagged image to GHCR. The workflow uses the built-in `GITHUB_TOKEN`; no extra
secret is required. Merely pushing to `main` never publishes an image.

When the manually triggered publishing run succeeds, open its **Deployment image reference** job summary.
Copy the full immutable GHCR image URL, for example:

```text
ghcr.io/YOUR_OWNER/YOUR_REPO:20261106-121530-a1b2c3d-1-1
```

This is just an example tag: use the **actual** tag from your workflow summary.
In your GitHub repository, open **Packages > package settings** and set the
container package to **Public**; Serve must pull it without authentication.
Each new version uses a newly generated tag (do not deploy `latest`).

Then visit [SciLifeLab Serve](https://serve.scilifelab.se/), sign in/create an
account, create or choose a project, and create a new **Streamlit app**. Use:

| Serve field | Value |
| --- | --- |
| Title | ADHD treatment in Sweden: explore the data |
| Description | Educational dashboard of Swedish ADHD medication treatment rates, ages 0-17, 2012-2025 |
| Image | Exact public `ghcr.io/...:<unique-tag>` from the Action |
| Port | `8501` |
| Storage / mount path | `None` (CSV is bundled and read-only) |
| Hardware | Default allocation |
| Subdomain | Choose an available name, or let Serve assign one |
| Permissions | `Link` for initial review, then `Public` after approvals |
| Source URL | The public GitHub repository you created |
| Subjects / creators | Enter your actual workshop metadata and authors |

Create the app, wait for it to become available, open its URL, and repeat the
filter/chart checks. Do not copy a local file path into the image field. To
update a deployment, commit and push changes, **manually trigger the GitHub
Actions publishing workflow again**, locate the **new** unique GHCR tag from
that run, then change the image reference in Serve app settings and press
**Update**. Leave the GHCR image publicly available for Serve to pull.

See [DEPLOY.md](DEPLOY.md) for a short deployment checklist and the official
[Streamlit hosting guide](https://serve.scilifelab.se/docs/application-hosting/streamlit/)
for evolving Serve requirements.

## Limitations and scientific care

The observations are aggregates, not records about individuals. A changing
rate does **not** establish causation, ADHD prevalence, suitability of
medication, care quality, or risk to an individual. A high/low regional rate
is not intrinsically better/worse. The bar chart uses the independent
**Riket** national observation, not the unweighted average of regional rates.
The regional comparison year is independent of the trend filter by design.

No passwords, databases, uploaded patient data, accounts, or user tracking.
