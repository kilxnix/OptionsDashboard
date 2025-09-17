FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5001 \
    GUNICORN_TIMEOUT=300 \
    GUNICORN_GRACEFUL_TIMEOUT=60 \
    WEB_CONCURRENCY=2

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/logs /app/output /app/TradingPlans && \
    chown -R appuser:appuser /app

WORKDIR /app

COPY --chown=appuser:appuser requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

COPY --chown=appuser:appuser . /app/

USER appuser
EXPOSE 5000 5001

CMD ["/bin/sh", "-lc", "gunicorn --access-logfile - --error-logfile - --workers ${WEB_CONCURRENCY:-2} --bind 0.0.0.0:${PORT:-5001} --timeout ${GUNICORN_TIMEOUT:-300} --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT:-60} main:app"]
