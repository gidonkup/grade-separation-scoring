FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY . .

# Bakes backend/data/*.geojson into the image from data_sources/raw/ at build
# time, so the container doesn't redo this (spatial joins, validity fixes on
# the built-up-area layer, etc.) on every cold start.
RUN python backend/scripts/build_reference_data.py

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
