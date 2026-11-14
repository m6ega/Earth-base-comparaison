# Deploying Terra Analog

Terra Analog runs as **one service**: FastAPI serves the API (`/health`,
`/references`, `/analyze`, reference previews) and the static website from the
same origin. No database, queue, object storage or secrets are required.

## Requirements

- x86-64 Linux host or container platform (any provider that runs a Dockerfile,
  or a Python 3.14 runtime). Python 3.12 also works; all dependencies ship
  prebuilt manylinux wheels, and `rasterio`/`pyproj` bundle GDAL and PROJ.
- Memory: plan **≥ 1 GB per concurrent analysis** (2 analyses per worker by
  default). Large uploads decode up to 40 million cells per DEM.
- Disk: about 10 MB for the application and references, plus temporary space for
  uploads (≤ 50 MB each, deleted after every request).
- A reverse proxy or platform router that allows **request bodies of at least
  52 MB** and **request timeouts of at least 120 s** (large DEMs take longer).

## Option A: Docker (recommended)

```bash
docker build -t terra-analog .
docker run --rm -p 8000:8000 terra-analog
# open http://localhost:8000
```

The build **fails** if any registered reference does not validate byte-for-byte
(`backend/check_references.py`). The image runs as a non-root user, exposes
`PORT` (default 8000) and defines a `HEALTHCHECK` on `/health`.

## Option B: plain Python host

From a clean checkout of `frontend--dev`:

```bash
python -m venv .venv && . .venv/bin/activate
pip install --only-binary=:all: -r backend/requirements.txt
python backend/check_references.py
uvicorn app:app --app-dir backend --host 0.0.0.0 --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-1}" --proxy-headers --timeout-graceful-shutdown 30
```

Do not use `--reload` in production. The service does not depend on the
working directory, VS Code or Live Server.

## Configuration

All variables are optional (see [.env.example](.env.example)):

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | Listening port |
| `WEB_CONCURRENCY` | `1` | Uvicorn worker processes |
| `TERRA_MAX_CONCURRENT_ANALYSES` | `2` | Analyses running at once per worker |
| `TERRA_ANALYSIS_QUEUE_TIMEOUT_S` | `60` | Wait for a free slot before `503 SERVER_BUSY` |
| `TERRA_SERVE_FRONTEND` | `1` | Serve the website from the API |
| `TERRA_FRONTEND_DIR` | `frontend/` | Website directory |
| `TERRA_CORS_ORIGINS` | local dev origins | Only needed if the website is hosted on another origin |

Built-in limits: uploads ≤ 50 MB (checked while streaming), raster ≤ 200 million
declared pixels, ≤ 40 million decoded pixels per window, `.tif`/`.tiff` only.

## Verifying a deployment

```bash
curl -fs https://YOUR-HOST/health                      # {"status":"ok"}
curl -fs https://YOUR-HOST/references                  # four references, each with "body"
python backend/smoke_test.py https://YOUR-HOST path/to/earth.tif
```

`smoke_test.py` (standard library only) checks health, references and previews,
the website and every asset it references, and runs a real analysis against
every reference, asserting `is_mock: false`, the requested `reference_id` and the
methodology 0.3 warning `SOFT_HISTOGRAM_SCORING`.

Then open the site and check that the four reference cards load, an analysis
completes, and the browser console shows no errors.

## Operational notes

- **Logs** contain error codes and server-side exception details only; uploaded
  file names and contents are never logged.
- **Caching:** website files are served with `Cache-Control: no-cache` (ETag
  revalidation), so browsers pick up a new release on the next load.
- **Scaling:** each worker holds its own in-memory reference feature cache.
  Increase `WEB_CONCURRENCY` with memory, not beyond the host's CPU count.
- **Shutdown:** SIGTERM drains in-flight requests for up to 30 s; temporary upload
  files are removed by their request context.
- **References** are part of the image. To add one, commit its validated assets
  and `registration.json`; nothing is downloaded at runtime.

## Continuous integration

`.github/workflows/ci.yml` runs on every push to `frontend--dev` and `main`:
backend tests and reference validation on Ubuntu, then a Docker build followed by
`smoke_test.py` against the running container.
