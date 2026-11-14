"""Validate every registered planetary reference (deployment / CI check).

Usage (from the repository root or anywhere):
    python backend/check_references.py

Runs the same validation the API uses (approval record, SHA-256 integrity of
dem.tif / metadata.json / preview.png, metadata, geometry, body model) and
exits non-zero if any registered reference fails or none are available.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import errors  # noqa: E402
import reference  # noqa: E402
import settings  # noqa: E402


def main() -> int:
    registered = sorted(p.parent.name for p in settings.REFERENCES_DIR.glob("*/registration.json"))
    failures = []

    for rid in registered:
        try:
            ref = reference.load_reference(rid)
        except errors.TerraError as exc:
            failures.append(rid)
            print(f"FAIL  {rid}: {exc.code}")
            continue
        info = ref.api_object()
        print(f"OK    {rid:18} body={info['body']:5} {info['name']}")

    print(f"\n{len(registered) - len(failures)}/{len(registered)} registered references valid "
          f"(methodology {settings.METHODOLOGY_VERSION})")
    return 1 if failures or not registered else 0


if __name__ == "__main__":
    sys.exit(main())
