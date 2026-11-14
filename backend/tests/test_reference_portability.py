"""Reference integrity must survive any checkout on any platform.

Registration records pin SHA-256 hashes of the exact approved bytes. These
tests guard against Git line-ending conversion (core.autocrlf / text=auto)
silently changing metadata.json bytes on Linux/macOS deployments.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import errors
import reference
import settings

REFS = settings.REFERENCES_DIR
REPO = settings.BACKEND_DIR.parent
REGISTERED = sorted(p.parent.name for p in REFS.glob("*/registration.json"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(*args: str) -> subprocess.CompletedProcess | None:
    if shutil.which("git") is None or not (REPO / ".git").exists():
        return None
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)


def test_all_four_references_registered_and_loadable():
    assert REGISTERED == ["mars-amazonis", "mars-gale", "moon-mons-mouton", "moon-shackleton"]
    reference.load_reference.cache_clear()
    assert [r.id for r in reference.list_references()] == REGISTERED


@pytest.mark.parametrize("rid", REGISTERED)
def test_files_on_disk_match_registration(rid):
    approval = json.loads((REFS / rid / "registration.json").read_bytes())
    for name, expected in approval["sha256"].items():
        assert _sha((REFS / rid / name).read_bytes()) == expected, f"{rid}/{name}"


@pytest.mark.parametrize("rid", REGISTERED)
def test_git_stores_approved_bytes_verbatim(rid):
    """What Git stores is what every clean checkout delivers (attribute -text)."""
    if _git("rev-parse", "--git-dir") is None:
        pytest.skip("not running inside a Git checkout (e.g. container image)")
    approval = json.loads((REFS / rid / "registration.json").read_bytes())
    for name, expected in approval["sha256"].items():
        rel = f"backend/references/{rid}/{name}"
        blob = _git("cat-file", "blob", f":{rel}")
        assert blob.returncode == 0, f"{rel} is not tracked"
        assert _sha(blob.stdout) == expected, f"Git blob for {rel} differs from the approved bytes"
        attr = _git("check-attr", "text", "--", rel).stdout.decode()
        assert attr.strip().endswith("unset"), f"{rel} must not be subject to text conversion: {attr}"


def test_line_ending_conversion_is_detected_not_ignored(tmp_path, monkeypatch):
    """A CRLF->LF rewrite of metadata.json must make the reference unavailable."""
    directory = tmp_path / "references"
    shutil.copytree(REFS / "mars-gale", directory / "mars-gale")
    meta = directory / "mars-gale" / "metadata.json"
    original = meta.read_bytes()
    converted = original.replace(b"\r\n", b"\n") if b"\r\n" in original else original.replace(b"\n", b"\r\n")
    assert converted != original
    meta.write_bytes(converted)

    monkeypatch.setattr(settings, "REFERENCES_DIR", directory)
    reference.load_reference.cache_clear()
    try:
        assert reference.list_references() == []
        with pytest.raises(errors.TerraError) as exc:
            reference.load_reference("mars-gale")
        assert exc.value.code == "REFERENCE_UNAVAILABLE"
    finally:
        reference.load_reference.cache_clear()
