# Serve deployment checklist

Reference: [SciLifeLab Serve app template](https://github.com/ScilifelabDataCentre/serve-app-template),
[Streamlit hosting guide](https://serve.scilifelab.se/docs/application-hosting/streamlit/).

1. Review public reuse terms for the *original* Vården i siffror export,
   source attribution, code license, and institute approvals. Do not publish
   sensitive data; this workshop file is aggregate-only.
2. From the project root: `python scripts/preflight.py --strict` and
   `python -m unittest discover -s tests -v`.
3. `docker build --platform linux/amd64 -t adhd-treatment-sweden:local .`
4. `docker run --rm -p 8501:8501 adhd-treatment-sweden:local`, then open
   `http://localhost:8501` and check both charts, filters, and table.
5. With explicit approval to publish **code and CSV**, push to a **public
   GitHub repository**. A push to `main` triggers validation and a Docker
   build/health smoke test, but **does not publish** the container image.
6. After separate approval to publish a container, go to **GitHub Actions >
   Validate Streamlit app (manual approval to publish image) > Run workflow**
   on `main`. A successful manual run validates, builds, smoke-tests and
   publishes to GHCR. Make the GHCR package **Public** and copy its exact
   unique image tag from the workflow summary. Do not use `latest`.
7. In SciLifeLab Serve, create a project and a **Streamlit** application:
   - Image: exact `ghcr.io/owner/repo:<new-tag>` (public).
   - Port: `8501`; storage/mount path: **None**.
   - Hardware: default. Source code URL: your public repo.
   - Provide title/description, authors, keywords, subdomain.
   - Use **Link** for review, then **Public** when ready.
8. For future updates: push -> manual GitHub Actions **Run workflow** ->
   new image tag -> change image field in the Serve app settings -> **Update**. Keep referenced images available.

## Container contract

- Profile: Streamlit; Python 3.12-slim; non-root UID 1000.
- Entry point: `streamlit run app.py`, `app.py` in `WORKDIR /home/appuser/app`.
- Listening address: `0.0.0.0`; port `8501`.
- Health path: `/_stcore/health`.
- Data path: `/home/appuser/data/adhd_treatment_sweden_workshop_2012_2025.csv`.
- Architecture: `linux/amd64`. Image tags: unique/immutable.
- No secrets, persistent storage, user tracking, or login.
