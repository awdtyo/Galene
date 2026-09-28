# Galene on Hugging Face Spaces (Docker SDK, free CPU).
# Space listens on $PORT (7860). Secrets via Space Variables, never baked in.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY backend/ backend/
COPY frontend/ frontend/
COPY data/fixtures/ data/fixtures/
COPY docs/ docs/

RUN pip install --no-cache-dir --upgrade pip setuptools \
 && pip install --no-cache-dir .

EXPOSE 7860
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
