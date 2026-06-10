FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY rubrics/ ./rubrics/

WORKDIR /app/backend

ENV CHROMA_PERSIST_DIR=/app/data/chroma
ENV WORK_DIR=/app/data/work
ENV LOCAL_STORAGE_DIR=/app/data/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["sh", "-c", "python ingest_rubrics.py && uvicorn main:app --host 0.0.0.0 --port 8000"]
