"""Prepared Mars references owned by the backend.

The reference raster and its verified metadata.json are cross-checked before
use. Provenance values are read from metadata.json, never assumed.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pyproj
import rasterio

import errors
import settings
from preprocessing import GDAL_ENV, DemSource, describe_source
from validation import unit_name_to_metres

# Only identifiers in this registry are accepted; paths and URLs never are.
REFERENCE_DIRS = {"mars-gale": settings.REFERENCES_DIR / "mars-gale"}
MARS_SEMI_MAJOR_RANGE_M = (3_380_000.0, 3_410_000.0)
CENTER_TOLERANCE_DEG = 0.01


@dataclass(frozen=True)
class MarsReference:
    id: str
    name: str
    dataset: str
    preview_path: Path
    source: DemSource
    metadata: dict

    @property
    def preview_url(self) -> str:
        return f"/static/references/{self.id}/preview.png"

    def api_object(self) -> dict:
        # effective_resolution_m stays null: metadata.json verifies the grid
        # spacing (resolution_metres) but not the effective resolution of the
        # MOLA product, and the contract says null until verified.
        return {
            "id": self.id,
            "name": self.name,
            "dataset": self.dataset,
            "effective_resolution_m": None,
            "preview_url": self.preview_url,
        }


def _unavailable(reference_id: str, detail: str) -> errors.TerraError:
    return errors.fail(
        errors.REFERENCE_UNAVAILABLE,
        f"The Mars reference '{reference_id}' failed its integrity check: {detail}",
    )


@lru_cache(maxsize=None)
def load_reference(reference_id: str) -> MarsReference:
    directory = REFERENCE_DIRS.get(reference_id)
    if directory is None:
        raise errors.fail(errors.UNKNOWN_REFERENCE, f"Unknown reference_id '{reference_id}'.")
    dem_path, meta_path, preview_path = directory / "dem.tif", directory / "metadata.json", directory / "preview.png"
    for p in (dem_path, meta_path, preview_path):
        if not p.is_file():
            raise _unavailable(reference_id, f"missing {p.name}.")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        raster_meta, elev_meta, crs_meta = meta["raster"], meta["elevation"], meta["coordinate_system"]
        name, dataset = str(meta["region"]), str(meta["source"])
    except (ValueError, KeyError) as exc:
        raise _unavailable(reference_id, "metadata.json is malformed.") from exc

    with rasterio.Env(**GDAL_ENV), rasterio.open(dem_path) as ds:
        checks = {
            "band count": ds.count == 1,
            "width": ds.width == raster_meta["width"],
            "height": ds.height == raster_meta["height"],
            "pixel size": all(
                math.isclose(a, b, rel_tol=1e-9)
                for a, b in zip((abs(ds.transform.a), abs(ds.transform.e)), raster_meta["resolution_metres"])
            ),
            "nodata": ds.nodata is not None and float(ds.nodata) == float(raster_meta["nodata"]),
            "crs present": ds.crs is not None,
        }
        failed = [k for k, ok in checks.items() if not ok]
        if failed:
            raise _unavailable(reference_id, "raster does not match metadata.json (" + ", ".join(failed) + ").")
        crs = pyproj.CRS.from_wkt(ds.crs.to_wkt())
        semi_major = crs.ellipsoid.semi_major_metre
        lo, hi = MARS_SEMI_MAJOR_RANGE_M
        if not (lo <= semi_major <= hi) or not math.isclose(semi_major, crs_meta["mars_radius_metres"]):
            raise _unavailable(reference_id, "the CRS is not the documented Mars sphere.")
        if not crs.is_projected:
            raise _unavailable(reference_id, "the CRS is not projected.")
        tag_unit = unit_name_to_metres(ds.tags().get("UNITS"))
        meta_unit = unit_name_to_metres(elev_meta.get("unit"))
        if tag_unit is None or meta_unit is None or tag_unit != meta_unit:
            raise _unavailable(reference_id, "vertical units are not consistently declared.")
        transform, width, height = ds.transform, ds.width, ds.height

    source = describe_source(dem_path, "mars", crs, transform, width, height, meta_unit)
    center = meta.get("center", {})
    if (
        abs(source.center_lat - center.get("latitude_planetocentric", float("nan"))) > CENTER_TOLERANCE_DEG
        or abs(source.center_lon - center.get("longitude_positive_east", float("nan"))) > CENTER_TOLERANCE_DEG
    ):
        raise _unavailable(reference_id, "the raster centre does not match metadata.json.")

    return MarsReference(
        id=reference_id,
        name=name,
        dataset=dataset,
        preview_path=preview_path,
        source=source,
        metadata=meta,
    )


def list_references() -> list[MarsReference]:
    return [load_reference(rid) for rid in REFERENCE_DIRS]
