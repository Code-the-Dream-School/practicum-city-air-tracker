FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY pyproject.toml /app/pyproject.toml
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY services/pipeline /app/services/pipeline
COPY configs /app/configs
RUN pip install --no-cache-dir --no-build-isolation --no-deps /app

ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "pipeline.cli", "--source", "openweather", "--history-hours", "72"]
