# Terra Analog — Mars Data Sources

**Status:** Phase 0 research note  
**Primary reference:** Gale Crater, Mars  
**Research date:** 14 November 2026

## 1. Selected source

**Dataset:** Mars Global Surveyor (MGS), Mars Orbiter Laser Altimeter (MOLA), Mission Experiment Gridded Data Record (MEGDR), topography product.

**Maintaining archive:** NASA Planetary Data System (PDS) Geosciences Node, Washington University in St. Louis.

Official documentation:
- https://pds-geosciences.wustl.edu/missions/mgs/megdr.html
- https://pds-geosciences.wustl.edu/missions/mgs/mola.html

Maintained PDS4 bundle:
- https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/

The PDS Geosciences documentation says the MEGDR products are global Mars topographic maps made by binning MOLA altimetry observations. It identifies the topography product as the difference between planetary radius and the areoid where an areoid product is supplied. At 128 pixels/degree, the archive divides the global grid into tiles.

## 2. Gale Crater reference

**Priority:** Required

- Planet: Mars
- Approximate centre: 5.44°S, 137.70°E
- Suggested reference name: `gale_crater_mola_128ppd`

## 3. Candidate source tile

The official PDS MEGDR directory table lists the following 128-pixel/degree topography tile:

- File: `megt00n090hb.img`
- PDS4 label: `megt00n090hb.xml`
- ENVI header: `megt00n090hb.hdr`
- Product family: `T` = topography
- Latitude coverage: 0° to 44°S
- Longitude coverage: 90°E to 180°E
- Nominal grid resolution: 128 pixels per degree

Official directory:
https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg128/

Direct file URLs:
- IMG: https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg128/megt00n090hb.img
- XML: https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg128/megt00n090hb.xml
- HDR: https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg128/megt00n090hb.hdr

**Coverage check:** Gale (about 5.44°S, 137.70°E) lies inside this tile. The optional Gusev reference (about 14.53°S, 175.52°E) also lies inside it.

### Verification status

- [x] Official PDS MOLA MEGDR documentation located.
- [x] PDS4 bundle directory located.
- [x] `meg128` directory identified.
- [x] Exact `megt00n090hb.img` and matching `.xml` filenames listed by the official archive.
- [x] Tile geographic coverage checked against Gale and Gusev coordinates.
- [ ] Binary IMG successfully downloaded and opened locally.
- [ ] XML inspected for exact dimensions, byte order, data type, scaling/offset, units, special constants/NoData, map projection and coordinate-system details.
- [ ] Exact IMG file size recorded.
- [ ] Conversion tested in GDAL/QGIS and GeoTIFF output checked.

The browser index lists the IMG and XML entries, but the binary and XML endpoints did not return inspectable content in the research session. Therefore file size and label-level raster properties are **not yet verified**. Do not mark the data as downloaded until the team has downloaded and opened it.

## 4. Resolution and spatial reference

The `H` code in the MEGDR filename denotes 128 pixels per degree. This is an angular grid resolution, not a constant ground distance everywhere.

- Angular cell spacing: 1/128 degree = 0.0078125° = 28.125 arcseconds.
- A rough linear scale near Gale is on the order of 0.46 km per pixel, but the exact ground spacing depends on latitude and the planet's reference model.
- Do not describe the grid as a universally fixed 463 m resolution without qualifying the approximation.
- The PDS MOLA page states the final MEGDR products were generated from the final PEDR data using the IAU 2000 coordinate system.
- The precise map projection, coordinate convention, raster dimensions, vertical reference, units, byte order and NoData/special constants must be read from this tile's own XML/label and header before conversion.

**Important:** Do not assign an Earth CRS to the Mars raster. Preserve and document the Mars spatial reference independently. The frontend must not place the Mars preview on an Earth OpenStreetMap layer.

## 5. Product selection

Use the `megt...` topography product for elevation.

Do not substitute:
- `megr...` — planetary radius
- `megc...` — observation counts
- `mega...` — areoid, where present

The PDS MEGDR documentation explains these as separate map products. The 128-pixel/degree topography tile is the requested numerical topography raster, not a rendered JPEG/PNG map.

## 6. Expected preparation and conversion

The backend developer should own the actual data preparation. Suggested high-level workflow:

1. Download the IMG, matching XML and HDR from the official PDS4 `meg128` directory.
2. Verify file size/checksum where available and keep the original source files unchanged.
3. Read the XML and HDR. Confirm array dimensions, storage type, byte order, image offset, scale/offset, units, coordinate system, map projection and special constants.
4. Open the raster with a compatible GDAL workflow or import it into QGIS using the supplied metadata/header. Do not guess import parameters.
5. Crop a documented area around Gale using Mars coordinates and an agreed extent.
6. Export the cropped numeric raster as GeoTIFF while preserving the Mars coordinate reference and NoData handling. Avoid exporting only a color-rendered image.
7. Re-open the GeoTIFF and compare its dimensions, pixel values, georeferencing and NoData mask against the source crop.
8. Generate a separate preview PNG for the frontend. The PNG is for display only; numerical analysis must use the GeoTIFF/raster values.

The exact GDAL driver/command and whether a small metadata-assisted import step is required should be confirmed after inspecting the PDS4 XML/HDR. Do not assume the raw `.img` is self-describing.

## 7. Scientific comparison cautions

- Compare relative terrain geometry, not absolute Earth and Mars elevation values.
- Earth and Mars use different planetary reference surfaces and spatial reference systems. Do not subtract raw elevations across planets or pretend they share a vertical datum.
- Agree with the backend developer on common comparison-area dimensions and effective sampling resolution.
- Resampling must be documented because it changes the terrain signal and derived slope/roughness.
- MOLA is a gridded altimetry product; its effective detail is limited by the product resolution and source observations. Avoid implying rover-scale detail.
- Surface roughness depends on the scale/window used; record the method and scale.
- A terrain similarity score describes similarity under the selected metrics and preprocessing. It does not establish habitability, geological identity or a real-world analogue in every scientific sense.

## 8. Optional Gusev reference

- Approximate centre: 14.53°S, 175.52°E.
- It falls inside the same candidate `megt00n090hb` tile.
- Treat Gusev as optional and do not spend Phase 0 time building a second reference unless Gale is already working.

## 9. Sources

1. PDS Geosciences Node, MGS MOLA MEGDR documentation: https://pds-geosciences.wustl.edu/missions/mgs/megdr.html
2. PDS4 MGS MOLA Topography Derived bundle: https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/
3. PDS Geosciences Node, MGS MOLA overview: https://pds-geosciences.wustl.edu/missions/mgs/mola.html
4. PDS MOLA MEGDR data set profile: https://pds.nasa.gov/ds-view/pds/viewProfile.jsp?dsid=MGS-M-MOLA-5-MEGDR-L3-V1.0
