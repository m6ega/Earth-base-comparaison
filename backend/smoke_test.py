"""End-to-end HTTP smoke test against a running Terra Analog service.

Usage:
    python backend/smoke_test.py http://127.0.0.1:8000 path/to/earth.tif

Standard library only. Checks: /health, /references (each with a body),
same-origin frontend delivery and every local asset it references, and a
real POST /analyze against every registered reference (is_mock=false,
matching reference id, soft-histogram scoring warning present). Exits non-zero on
the first failure. It never fakes or caches a response.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

METHODOLOGY_MARKER = "SOFT_HISTOGRAM_SCORING"  # emitted by every analysis since 0.3


def get(base: str, path: str) -> tuple[int, bytes, str]:
    try:
        with urllib.request.urlopen(base + path, timeout=60) as r:
            return r.status, r.read(), r.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("content-type", "")


def post_analyze(base: str, dem: Path, reference_id: str) -> tuple[int, dict]:
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in (("reference_id", reference_id), ("vertical_unit_fallback", "metre")):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="earth.tif"\r\n'
        "Content-Type: image/tiff\r\n\r\n".encode() + dem.read_bytes() + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        base + "/analyze", data=b"".join(parts), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check(ok: bool, message: str) -> None:
    print(("PASS  " if ok else "FAIL  ") + message)
    if not ok:
        sys.exit(1)


def main() -> None:
    base, dem = sys.argv[1].rstrip("/"), Path(sys.argv[2])

    status, body, _ = get(base, "/health")
    check(status == 200 and json.loads(body).get("status") == "ok", "GET /health")

    status, body, _ = get(base, "/references")
    data = json.loads(body)
    refs = data.get("references", [])
    check(status == 200 and data.get("is_mock") is False and refs, f"GET /references ({len(refs)} references)")
    check(all(r.get("body") and r.get("preview_url") for r in refs), "every reference has body and preview_url")
    for r in refs:
        s, img, ctype = get(base, r["preview_url"])
        check(s == 200 and ctype.startswith("image/png") and img[:4] == b"\x89PNG", f"preview {r['id']}")

    status, html, ctype = get(base, "/")
    check(status == 200 and "text/html" in ctype, "frontend served at /")
    page = html.decode("utf-8", "replace")
    assets = set(re.findall(r'(?:src|href)="(?![a-zA-Z][a-zA-Z0-9+.-]*:|#)([^"]+)"', page))
    css_status, css, _ = get(base, "/style.css")
    assets |= {u.strip("'\"") for u in re.findall(r"url\(([^)]+)\)", css.decode("utf-8", "replace"))
               if not u.strip("'\"").startswith(("http", "data:", "#"))}
    for asset in sorted(assets):
        s, _, _ = get(base, "/" + asset.lstrip("./"))
        check(s == 200, f"asset {asset}")

    for r in refs:
        status, result = post_analyze(base, dem, r["id"])
        codes = {w.get("code") for w in result.get("warnings", [])}
        check(
            status == 200 and result.get("status") == "success" and result.get("is_mock") is False
            and result.get("reference", {}).get("id") == r["id"] and METHODOLOGY_MARKER in codes,
            f"POST /analyze {r['id']}: total={result.get('total_similarity')} is_mock={result.get('is_mock')}",
        )

    print(f"\nSmoke test passed: {len(refs)} references analysed at {base}")


if __name__ == "__main__":
    main()
