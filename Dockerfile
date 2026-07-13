FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agents ./agents

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /tmp/jesse \
    && chown -R appuser:appuser /tmp/jesse

USER appuser

CMD ["sh", "-c", "uvicorn agents.jessie.api.main:app --host 0.0.0.0 --port ${PORT}"]
