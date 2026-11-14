"""Upload handling and strict validation of uploaded Earth GeoTIFFs.

Nothing is assumed: a file without a horizontal CRS, without a usable affine
transform or without declared vertical units is rejected.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import BinaryIO

import pyproj
import rasterio

import errors
import settings
from preprocessing import GDAL_ENV, DemSource, describe_source

TIFF_MAGIC = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")  # classic and BigTIFF

_METRE_NAMES = {"m", "metre", "metres", "meter", "meters"}
_FOOT_NAMES = {"ft", "foot", "feet", "international foot"}
_US_FOOT_NAMES = {"us survey foot", "us survey feet", "us-ft", "ftus", "foot_us", "us_survey_foot"}
_ANGULAR_UNITS = {"degree", "degrees", "radian", "radians", "grad", "gon", "arc-second", "arc-minute"}


def check_extension(filename: str | None) -> None:
    name = (filename or "").lower()
    if not name.endswith(settings.ALLOWED_EXTENSIONS):
        raise errors.fail(
            errors.UNSUPPORTED_FORMAT,
            "Only single-band elevation GeoTIFF files with a .tif or .tiff extension are supported.",
        )


def save_upload(stream: BinaryIO, destination: Path) -> int:
    """Copy an upload to disk in chunks, enforcing the size limit."""
    written = 0
    with destination.open("wb") as out:
        while True:
            chunk = stream.read(settings.UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            written += len(chunk)
            if written > settings.MAX_UPLOAD_BYTES:
                raise errors.fail(
                    errors.FILE_TOO_LARGE,
                    f"The uploaded file exceeds the {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
                )
            out.write(chunk)
    if written == 0:
        raise errors.fail(errors.INVALID_DEM, "The uploaded file is empty.")
    return written


def check_tiff_signature(path: Path) -> None:
    with path.open("rb") as fh:
        head = fh.read(4)
    if head not in TIFF_MAGIC:
        raise errors.fail(
            errors.UNSUPPORTED_FORMAT,
            "The uploaded file is not a TIFF file, despite its extension.",
        )


def unit_name_to_metres(name: str | None) -> float | None:
    if not name:
        return None
    key = name.strip().lower()
    if key in _METRE_NAMES:
        return 1.0
    if key in _FOOT_NAMES:
        return 0.3048
    if key in _US_FOOT_NAMES:
        return 1200.0 / 3937.0
    return None


def _split_crs(crs: pyproj.CRS) -> tuple[pyproj.CRS, pyproj.CRS | None]:
    if crs.is_compound:
        horizontal = next((c for c in crs.sub_crs_list if not c.is_vertical), None)
        vertical = next((c for c in crs.sub_crs_list if c.is_vertical), None)
        if horizontal is None:
            raise errors.fail(errors.UNSUPPORTED_CRS, "The compound CRS has no horizontal component.")
        return horizontal, vertical
    return crs, None


def _check_horizontal(crs: pyproj.CRS) -> None:
    if not (crs.is_geographic or crs.is_projected):
        raise errors.fail(
            errors.UNSUPPORTED_CRS,
            "The horizontal CRS must be a geographic or projected CRS; local or engineering "
            "coordinate systems are not supported.",
        )
    ellipsoid = crs.ellipsoid
    semi_major = ellipsoid.semi_major_metre if ellipsoid is not None else float("nan")
    lo, hi = settings.EARTH_SEMI_MAJOR_RANGE_M
    if not (math.isfinite(semi_major) and lo <= semi_major <= hi):
        raise errors.fail(
            errors.UNSUPPORTED_CRS,
            "The CRS is not defined on an Earth ellipsoid "
            f"(semi-major axis {semi_major:.0f} m). Upload an Earth DEM.",
        )
    if crs.is_projected:
        for axis in crs.axis_info[:2]:
            unit = (axis.unit_name or "").lower()
            factor = axis.unit_conversion_factor
            if unit in _ANGULAR_UNITS or not (factor and math.isfinite(factor) and factor > 0):
                raise errors.fail(
                    errors.UNSUPPORTED_CRS,
                    f"The projected CRS axis unit '{axis.unit_name}' is not a physical length unit.",
                )


def _vertical_factor(vertical_crs: pyproj.CRS | None, band_unit: str | None) -> tuple[float, str]:
    from_crs = None
    if vertical_crs is not None and vertical_crs.axis_info:
        axis = vertical_crs.axis_info[0]
        named = unit_name_to_metres(axis.unit_name)
        factor = axis.unit_conversion_factor
        from_crs = named if named is not None else (factor if factor and math.isfinite(factor) else None)
    from_band = unit_name_to_metres(band_unit)

    if band_unit and from_band is None:
        raise errors.fail(
            errors.UNKNOWN_VERTICAL_UNITS,
            f"The elevation band declares an unsupported unit '{band_unit}'. Use metres or feet.",
        )
    if from_crs is not None and from_band is not None and not math.isclose(from_crs, from_band, rel_tol=1e-6):
        raise errors.fail(
            errors.INVALID_DEM,
            "The vertical CRS and the elevation band declare conflicting vertical units.",
        )
    factor = from_band if from_band is not None else from_crs
    if factor is None:
        raise errors.fail(
            errors.UNKNOWN_VERTICAL_UNITS,
            "The GeoTIFF does not declare its elevation units. Set the band unit (for example "
            "'metre', via gdal_edit.py -units metre) or include a vertical CRS. Units are never assumed.",
        )
    source = "band unit" if from_band is not None else "vertical CRS"
    return factor, source


def open_earth_dem(path: Path) -> tuple[DemSource, dict]:
    """Validate an uploaded GeoTIFF and return its measured geometry.

    Returns the DemSource and a dict of facts used for warnings.
    """
    check_tiff_signature(path)
    try:
        with rasterio.Env(**GDAL_ENV), rasterio.open(path) as ds:
            if ds.driver != "GTiff":
                raise errors.fail(errors.UNSUPPORTED_FORMAT, "The uploaded file is not a GeoTIFF.")
            if ds.count != 1:
                raise errors.fail(
                    errors.INVALID_DEM,
                    f"The GeoTIFF has {ds.count} bands; exactly one elevation band is required.",
                )
            dtype = ds.dtypes[0]
            if dtype not in settings.ALLOWED_DTYPES:
                raise errors.fail(errors.INVALID_DEM, f"Unsupported elevation data type '{dtype}'.")
            if min(ds.width, ds.height) < settings.MIN_RASTER_SIDE_PIXELS:
                raise errors.fail(errors.INVALID_DEM, "The raster is too small to contain terrain.")
            if ds.width * ds.height > settings.MAX_RASTER_PIXELS:
                raise errors.fail(
                    errors.RASTER_TOO_LARGE,
                    f"The raster declares {ds.width} x {ds.height} pixels, above the limit of "
                    f"{settings.MAX_RASTER_PIXELS:,} pixels.",
                )
            if ds.crs is None:
                raise errors.fail(
                    errors.MISSING_CRS,
                    "The GeoTIFF has no coordinate reference system. Georeferencing cannot be assumed.",
                )
            transform = ds.transform
            det = transform.a * transform.e - transform.b * transform.d
            if transform.is_identity or not math.isfinite(det) or det == 0:
                raise errors.fail(
                    errors.INVALID_DEM,
                    "The GeoTIFF has no valid affine geotransform (ground-control-point-only "
                    "georeferencing is not supported).",
                )
            try:
                full_crs = pyproj.CRS.from_wkt(ds.crs.to_wkt())
            except pyproj.exceptions.CRSError as exc:
                raise errors.fail(errors.UNSUPPORTED_CRS, "The GeoTIFF CRS could not be interpreted.") from exc
            horizontal, vertical = _split_crs(full_crs)
            _check_horizontal(horizontal)
            factor, unit_source = _vertical_factor(vertical, ds.units[0] if ds.units else None)
            width, height = ds.width, ds.height
    except errors.TerraError:
        raise
    except rasterio.errors.RasterioError as exc:
        raise errors.fail(errors.INVALID_DEM, "The uploaded file is not a readable GeoTIFF.") from exc

    source = describe_source(path, "earth", horizontal, transform, width, height, factor)
    facts = {"vertical_to_metres": factor, "vertical_unit_source": unit_source, "crs_name": horizontal.name}
    return source, facts
