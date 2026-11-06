# Adapted from ScilifelabDataCentre/serve-app-template/profiles/streamlit/Dockerfile.
# Build with: docker build --platform linux/amd64 -t adhd-treatment-sweden:local .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    USER=appuser \
    HOME=/home/appuser

RUN useradd -m -u 1000 "$USER"
WORKDIR $HOME/app

COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Preserve the project's relative paths: app/data.py resolves ../data/.
COPY --chown=1000:1000 app/ ./
COPY --chown=1000:1000 data/ $HOME/data/
COPY --chown=1000:1000 .streamlit/ $HOME/.streamlit/

USER appuser
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)" || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
