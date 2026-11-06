# Agent notes for this Streamlit project

Reference: https://github.com/ScilifelabDataCentre/serve-app-template

- Use the SciLifeLab Serve **Streamlit** profile, not a generic web container.
- Keep `app/app.py` as the source entry point and `app.py` inside the container WORKDIR.
- Run on port **8501**, bound to **0.0.0.0**; retain UID **1000** and the health check.
- Build and publish with `--platform linux/amd64`, via a unique, immutable GHCR image tag.
- The source dataset is **only** `data/adhd_treatment_sweden_workshop_2012_2025.csv`.
  Include it in Docker builds and repository commits after checking reuse rights.
- Validate the CSV strictly. Never impute, fetch, synthesize, or drop invalid observations.
- `Riket` is its own source observation; never derive it from regional averages.
- The dashboard is descriptive and educational, not an interpretation of care quality.
- No auth, secrets, sensitive data uploads, tracking, or database.
- Run `python scripts/preflight.py --strict` and `python -m unittest discover -s tests -v` before changes.
- Pushes to `main` only validate/build/smoke-test. Publication to GHCR requires explicit manual `workflow_dispatch`; no automatic image publication on push.
- Before public deployment, review the data reuse terms and the current Serve docs.
