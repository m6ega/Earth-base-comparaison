
from pathlib import Path
import json
import math

import numpy as np
import rasterio
from rasterio.windows import Window
import matplotlib.pyplot as plt


# ==========================================
# 1. FILES AND SETTINGS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

SOURCE_FILE = BASE_DIR / "megt00n090hb.img"

OUTPUT_DEM = BASE_DIR / "mars-gale-dem.tif"
OUTPUT_METADATA = BASE_DIR / "mars-gale-metadata.json"
OUTPUT_PREVIEW = BASE_DIR / "mars-gale-preview.png"

# Gale Crater centre
GALE_LATITUDE = -5.44
GALE_LONGITUDE = 137.70

# Desired crop size in kilometres
CROP_SIZE_KM = 100

# Mars reference radius from NASA metadata
MARS_RADIUS_METRES = 3396000

# NASA data uses a central meridian of 180 degrees
CENTRAL_MERIDIAN = 180


# ==========================================
# 2. CHECK SOURCE FILE
# ==========================================

if not SOURCE_FILE.exists():
    raise FileNotFoundError(
        f"NASA source file not found: {SOURCE_FILE}"
    )

print("Opening NASA Mars elevation data...")


# ==========================================
# 3. OPEN AND INSPECT SOURCE
# ==========================================

with rasterio.open(SOURCE_FILE) as src:

    print("Source opened successfully.")

    if src.count != 1:
        raise ValueError("Expected a single-band DEM.")

    if src.width != 11520 or src.height != 5632:
        raise ValueError("Unexpected source dimensions.")

    if src.crs is None:
        raise ValueError("Mars coordinate system is missing.")

    if src.nodata != 0:
        raise ValueError(
            f"Unexpected NoData value: {src.nodata}. "
            "Check the NASA header before continuing."
        )

    # Convert Gale coordinates into Mars projected metres.
    center_x = (
        MARS_RADIUS_METRES
        * math.radians(GALE_LONGITUDE - CENTRAL_MERIDIAN)
    )

    center_y = (
        MARS_RADIUS_METRES
        * math.radians(GALE_LATITUDE)
    )

    # Convert projected coordinates into raster pixels.
    center_row, center_col = src.index(center_x, center_y)

    print("Gale centre pixel:", center_row, center_col)

    # Calculate crop dimensions.
    pixel_size_x, pixel_size_y = src.res

    crop_width = round(
        (CROP_SIZE_KM * 1000) / pixel_size_x
    )

    crop_height = round(
        (CROP_SIZE_KM * 1000) / pixel_size_y
    )

    # Centre the crop around Gale Crater.
    col_start = center_col - crop_width // 2
    row_start = center_row - crop_height // 2

    # Make sure the crop stays inside the source raster.
    if (
        col_start < 0
        or row_start < 0
        or col_start + crop_width > src.width
        or row_start + crop_height > src.height
    ):
        raise ValueError(
            "The requested Gale Crater crop is outside "
            "the source raster."
        )

    window = Window(
        col_start,
        row_start,
        crop_width,
        crop_height
    )

    # Read the actual numerical elevation values.
    elevation = src.read(1, window=window)

    # Preserve the original Mars georeferencing.
    crop_transform = src.window_transform(window)

    crop_crs = src.crs
    source_bounds = src.bounds
    source_resolution = src.res
    source_nodata = src.nodata

    print("Crop extracted successfully.")


# ==========================================
# 4. CHECK ELEVATION VALUES
# ==========================================

# The ENVI header identifies zero as its ignore value.
# Keep the original pixel values unchanged.
valid_pixels = elevation[elevation != source_nodata]

if valid_pixels.size == 0:
    raise ValueError("No valid elevation pixels in crop.")

minimum = int(np.min(valid_pixels))
maximum = int(np.max(valid_pixels))
mean = float(np.mean(valid_pixels))

print("\nElevation statistics:")
print("Minimum:", minimum, "metres")
print("Maximum:", maximum, "metres")
print("Mean:", round(mean, 2), "metres")
print("Valid pixels:", valid_pixels.size)


# ==========================================
# 5. CREATE GEOTIFF
# ==========================================

output_profile = {
    "driver": "GTiff",
    "height": elevation.shape[0],
    "width": elevation.shape[1],
    "count": 1,
    "dtype": "int16",
    "crs": crop_crs,
    "transform": crop_transform,
    "nodata": source_nodata,
    "compress": "deflate"
}

with rasterio.open(
    OUTPUT_DEM,
    "w",
    **output_profile
) as dst:

    dst.write(elevation, 1)

    dst.update_tags(
        TITLE="MOLA Mars Gale Crater Elevation Model",
        SOURCE="NASA MGS MOLA MEGDR MEG128",
        UNITS="metres",
        REFERENCE="GMM3 Mars areoid",
        REGION="Gale Crater"
    )

print("\nCreated:", OUTPUT_DEM.name)


# ==========================================
# 6. CREATE METADATA JSON
# ==========================================

metadata = {
    "dataset": "MOLA Gale Crater DEM",
    "source": "NASA MGS MOLA MEGDR MEG128",
    "source_file": SOURCE_FILE.name,
    "source_label": "megt00n090hb.xml",
    "planet": "Mars",
    "region": "Gale Crater",

    "center": {
        "latitude_planetocentric": GALE_LATITUDE,
        "longitude_positive_east": GALE_LONGITUDE
    },

    "elevation": {
        "unit": "metres",
        "reference": "GMM3 Mars areoid",
        "minimum": minimum,
        "maximum": maximum,
        "mean": mean,
        "source_data_type": "Signed 16-bit integer",
        "byte_order": "Big-endian",
        "scale_factor": 1
    },

    "raster": {
        "width": int(elevation.shape[1]),
        "height": int(elevation.shape[0]),
        "resolution_metres": list(source_resolution),
        "crop_size_requested_km": CROP_SIZE_KM,
        "nodata": source_nodata,
        "valid_pixels": int(valid_pixels.size),
        "nodata_pixels": int(
            np.count_nonzero(elevation == source_nodata)
        )
    },

    "coordinate_system": {
        "projection": "Mars Equirectangular",
        "central_meridian_degrees": CENTRAL_MERIDIAN,
        "mars_radius_metres": MARS_RADIUS_METRES,
        "crs_wkt": crop_crs.to_wkt()
    },

    "processing": [
        "Read original NASA MOLA elevation raster",
        "Converted Gale Crater coordinates to projected metres",
        "Extracted a centred approximately 100 km crop",
        "Preserved original elevation values",
        "Preserved Mars coordinate reference system",
        "Exported numerical GeoTIFF"
    ],

    "data_quality_notes": [
        "NASA describes the grid values as median observed topography, "
        "with interpolated values supplied where observations are absent.",
        "Zero values are treated as NoData according to the ENVI header.",
        "The source does not provide a separate per-pixel observation mask."
    ]
}

with open(OUTPUT_METADATA, "w", encoding="utf-8") as file:
    json.dump(metadata, file, indent=4)

print("Created:", OUTPUT_METADATA.name)


# ==========================================
# 7. CREATE TERRAIN PREVIEW
# ==========================================

masked_elevation = np.ma.masked_equal(
    elevation,
    source_nodata
)

# Display clipping only; original DEM values remain unchanged.
display_min, display_max = np.percentile(
    valid_pixels,
    [2, 98]
)

left = crop_transform.c
top = crop_transform.f
right = left + elevation.shape[1] * crop_transform.a
bottom = top + elevation.shape[0] * crop_transform.e

extent = [
    (left - center_x) / 1000,
    (right - center_x) / 1000,
    (bottom - center_y) / 1000,
    (top - center_y) / 1000
]

plt.figure(figsize=(10, 8))

image = plt.imshow(
    masked_elevation,
    cmap="terrain",
    origin="upper",
    extent=extent,
    vmin=display_min,
    vmax=display_max
)

plt.colorbar(image, label="Elevation (metres)")
plt.title("Mars - Gale Crater MOLA Elevation")
plt.xlabel("Distance from Gale centre (km)")
plt.ylabel("Distance from Gale centre (km)")
plt.tight_layout()

plt.savefig(
    OUTPUT_PREVIEW,
    dpi=200,
    bbox_inches="tight"
)

plt.close()

print("Created:", OUTPUT_PREVIEW.name)


# ==========================================
# 8. VALIDATE OUTPUT
# ==========================================

print("\nValidating generated GeoTIFF...")

with rasterio.open(OUTPUT_DEM) as check:

    saved_elevation = check.read(1)

    assert saved_elevation.shape == elevation.shape
    assert check.crs == crop_crs
    assert check.nodata == source_nodata
    assert np.array_equal(saved_elevation, elevation)

    print("Dimensions:", check.width, "x", check.height)
    print("CRS:", check.crs)
    print("Resolution:", check.res)
    print("Elevation values preserved: YES")

print("\n================================")
print("MARS DATA PROCESSING COMPLETE")
print("================================")
print("Generated files:")
print(OUTPUT_DEM.name)
print(OUTPUT_METADATA.name)
print(OUTPUT_PREVIEW.name)
