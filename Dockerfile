FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

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

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5001", "main:app"]
