# Terra Analog: single service (FastAPI API + static frontend, same origin).
#
#   docker build -t terra-analog .
#   docker run --rm -p 8000:8000 terra-analog
#   open http://localhost:8000
#
# All geospatial libraries come from prebuilt manylinux wheels: rasterio bundles
# GDAL and pyproj bundles PROJ, so no system GDAL/PROJ packages are required.
# The rasterio wheel links against the system expat library (libexpat.so.1),
# which slim images do not ship.
FROM python:3.14-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    WEB_CONCURRENCY=1

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --only-binary=:all: -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

# Fail the build if any registered reference does not validate byte-for-byte.
RUN python backend/check_references.py \
    && useradd --create-home --uid 10001 terra

USER terra
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=4)"

# Each worker allows TERRA_MAX_CONCURRENT_ANALYSES (default 2) analyses at once.
CMD ["sh", "-c", "exec uvicorn app:app --app-dir backend --host 0.0.0.0 --port \"$PORT\" --workers \"$WEB_CONCURRENCY\" --proxy-headers --timeout-graceful-shutdown 30"]
