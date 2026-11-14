"""Discover explicitly approved, content-verified planetary references.

Legacy metadata is adapted without changing original scientific assets.
"""
from __future__ import annotations
import hashlib
import json
import logging
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np
import pyproj
import rasterio
from pydantic import BaseModel, ConfigDict, Field
import errors
import settings
from preprocessing import GDAL_ENV, DemSource, describe_source
from validation import unit_name_to_metres

ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
logger = logging.getLogger(__name__)

class Approval(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    schema_version: Literal[1]
    reference_id: str
    enabled: bool
    approved: bool
    body: str
    name: str = Field(min_length=1)
    category: str | None
    description: str
    effective_resolution_m: float | None = Field(gt=0)
    effective_resolution_evidence: str | None
    sha256: dict[str, str]
    limitations: list[str]

class BodyModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    name: str = Field(min_length=1)
    semi_major_m: float = Field(gt=0)
    semi_minor_m: float = Field(gt=0)

class ScientificModel(BaseModel):
    model_config = ConfigDict(extra='allow', strict=True, allow_inf_nan=False)

class Center(ScientificModel):
    latitude_planetocentric: float = Field(ge=-90,le=90)
    longitude_positive_east: float = Field(ge=-180,le=360)

class Elevation(ScientificModel):
    unit: str
    reference: str = Field(min_length=1)
    minimum: float
    maximum: float
    mean: float

class RasterMetadata(ScientificModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    resolution_metres: list[float] = Field(min_length=2,max_length=2)
    nodata: float
    valid_pixels: int = Field(gt=0)
    nodata_pixels: int = Field(ge=0)

class Coordinates(ScientificModel):
    crs_wkt: str = Field(min_length=1)
    projection: str = Field(min_length=1)

class Metadata(ScientificModel):
    planet: str
    region: str = Field(min_length=1)
    source: str = Field(min_length=1)
    center: Center
    elevation: Elevation
    raster: RasterMetadata
    coordinate_system: Coordinates


def _json(path):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out: raise ValueError('duplicate JSON key')
            out[k] = v
        return out
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('non-finite JSON')))

def _digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def _directories():
    root = settings.REFERENCES_DIR.resolve()
    return {p.name:p for p in root.iterdir() if p.is_dir() and not p.is_symlink()
            and p.resolve().parent == root and ID.fullmatch(p.name)
            and (p/'registration.json').is_file()}

class ReferenceDirectories(Mapping):
    """Compatibility mapping; discovery is refreshed on every access."""
    def __iter__(self): return iter(_directories())
    def __len__(self): return len(_directories())
    def __getitem__(self, key): return _directories()[key]
REFERENCE_DIRS = ReferenceDirectories()

@dataclass(frozen=True)
class PlanetaryReference:
    id: str
    name: str
    dataset: str
    preview_path: Path
    source: DemSource
    metadata: dict
    approval: Approval
    fingerprint: str
    dem_sha256: str
    @property
    def preview_url(self): return f'/static/references/{self.id}/preview.png'
    def api_object(self):
        return dict(id=self.id,name=self.name,dataset=self.dataset,
                    effective_resolution_m=self.approval.effective_resolution_m,preview_url=self.preview_url,
                    body=self.approval.body,category=self.approval.category,description=self.approval.description,
                    center=dict(latitude_planetocentric=self.source.center_lat,longitude_positive_east=self.source.center_lon),
                    grid_spacing_m=list(self.source.spacing_xy_m),
                    elevation_unit='metres',elevation_datum=self.metadata['elevation']['reference'],
                    limitations=list(self.approval.limitations),
                    dem_sha256=self.dem_sha256,version=self.fingerprint)
MarsReference = PlanetaryReference  # compatibility for existing Python callers

def _unavailable(rid, detail):
    return errors.fail(errors.REFERENCE_UNAVAILABLE, f"Reference '{rid}' is unavailable: {detail}")

def load_reference(reference_id):
    if not isinstance(reference_id,str) or not ID.fullmatch(reference_id):
        raise errors.fail(errors.UNKNOWN_REFERENCE, 'Unknown reference identifier.')
    directory = _directories().get(reference_id)
    if directory is None:
        raise errors.fail(errors.UNKNOWN_REFERENCE, 'Unknown reference identifier.')
    try:
        paths = [directory/name for name in ('registration.json','metadata.json','dem.tif','preview.png')]
        if any(p.is_symlink() or not p.is_file() or p.resolve().parent != directory.resolve() for p in paths):
            raise ValueError('missing or unsafe runtime asset')
        approval = Approval.model_validate(_json(paths[0]))
        if approval.reference_id != reference_id: raise ValueError('registration ID mismatch')
        if not approval.enabled or not approval.approved: raise ValueError('reference is disabled or unapproved')
        if set(approval.sha256) != {'dem.tif','metadata.json','preview.png'}: raise ValueError('incomplete integrity manifest')
        digests = {p.name:_digest(p) for p in paths}
        if any(not re.fullmatch('[0-9a-f]{64}',h) or digests[n] != h for n,h in approval.sha256.items()):
            raise ValueError('asset checksum mismatch; revalidation and approval required')
        body_path = settings.BACKEND_DIR/'reference-bodies.json'
        body_config = body_path.read_text(encoding='utf-8')
        fingerprint = hashlib.sha256((json.dumps(digests,sort_keys=True)+body_config).encode()).hexdigest()
        return _load_validated(str(directory),reference_id,fingerprint,body_config)
    except errors.TerraError: raise
    except Exception as exc:
        logger.warning('Reference %s validation failed: %s',reference_id,exc)
        raise _unavailable(reference_id, 'metadata or asset validation failed; consult server diagnostics.') from exc

@lru_cache(maxsize=32)
def _load_validated(directory, rid, fingerprint, body_config):
    directory = Path(directory)
    approval = Approval.model_validate(_json(directory/'registration.json'))
    body = BodyModel.model_validate(json.loads(body_config)[approval.body])
    meta = _json(directory/'metadata.json')
    Metadata.model_validate(meta)
    if meta['planet'].lower()!=approval.body or meta['region']!=approval.name: raise ValueError('body/name mismatch')
    if meta.get('reference_id',rid)!=rid: raise ValueError('metadata ID mismatch')
    if not isinstance(meta['source'],str) or not meta['source'].strip(): raise ValueError('missing source')
    r,e,c = meta['raster'],meta['elevation'],meta['coordinate_system']
    if not isinstance(e['reference'],str) or not e['reference'].strip(): raise ValueError('missing vertical datum')
    for key in ('mars_radius_metres', 'lunar_radius_metres'):
        if c.get(key) is not None and not math.isclose(c[key], body.semi_major_m, rel_tol=1e-10):
            raise ValueError('documented radius mismatch')
    units=unit_name_to_metres(e['unit'])
    if units != 1: raise ValueError('runtime references must contain metre elevations')
    if approval.effective_resolution_m is not None and not approval.effective_resolution_evidence:
        raise ValueError('effective resolution needs scientific evidence')
    notes=meta.get('data_quality_notes',meta.get('limitations',[]))
    if not isinstance(notes,list) or not all(isinstance(v,str) for v in notes): raise ValueError('invalid limitations')
    with rasterio.Env(**GDAL_ENV),rasterio.open(directory/'dem.tif') as ds:
        if ds.driver!='GTiff' or ds.count!=1 or ds.crs is None: raise ValueError('invalid DEM')
        if ds.width!=r['width'] or ds.height!=r['height']: raise ValueError('dimensions mismatch')
        if ds.width*ds.height > settings.MAX_READ_WINDOW_PIXELS: raise ValueError('runtime reference too large')
        if not np.allclose(ds.res,r['resolution_metres'],rtol=1e-9,atol=0): raise ValueError('spacing mismatch')
        if ds.nodata is None or ds.nodata!=r['nodata']: raise ValueError('NoData mismatch')
        if ds.scales!=(1.0,) or ds.offsets!=(0.0,): raise ValueError('unapplied raster scaling')
        if unit_name_to_metres(ds.tags().get('UNITS'))!=units: raise ValueError('vertical unit mismatch')
        crs=pyproj.CRS(ds.crs)
        if not crs.is_projected or not crs.equals(pyproj.CRS(c['crs_wkt'])): raise ValueError('CRS mismatch')
        if not all(math.isclose(x,y,rel_tol=1e-10) for x,y in [(crs.ellipsoid.semi_major_metre,body.semi_major_m),(crs.ellipsoid.semi_minor_metre,body.semi_minor_m)]): raise ValueError('wrong planetary geodetic model')
        if any(not math.isclose(axis.unit_conversion_factor,1) for axis in crs.axis_info): raise ValueError('horizontal CRS must use metres')
        band=ds.read(1,masked=True);values=band.compressed()
        if not values.size or not np.isfinite(values).all(): raise ValueError('no valid finite elevations')
        if values.size!=r['valid_pixels'] or ds.width*ds.height-values.size!=r['nodata_pixels']: raise ValueError('coverage mismatch')
        if not math.isclose(float(values.min()),e['minimum'],abs_tol=1e-5) or not math.isclose(float(values.max()),e['maximum'],abs_tol=1e-5): raise ValueError('elevation statistics mismatch')
        if not math.isclose(float(np.mean(values,dtype=np.float64)),e['mean'],rel_tol=1e-8,abs_tol=1e-5): raise ValueError('mean elevation mismatch')
        source=describe_source(directory/'dem.tif',approval.body,crs,ds.transform,ds.width,ds.height,units)
        from dataclasses import replace
        source=replace(source,elevation_range_m=(float(values.min()),float(values.max())),effective_resolution_m=approval.effective_resolution_m)
    center=meta['center']
    # Longitude is circular; compare centres by geodesic distance, including near poles.
    distance=crs.get_geod().inv(source.center_lon,source.center_lat,center['longitude_positive_east'],center['latitude_planetocentric'])[2]
    if not math.isfinite(distance) or abs(distance)>max(source.native_spacing_m,1): raise ValueError('centre mismatch')
    with rasterio.open(directory/'preview.png') as preview:
        if preview.driver!='PNG' or preview.width<1 or preview.height<1: raise ValueError('invalid preview')
        preview.read()
    return PlanetaryReference(rid,approval.name,meta['source'],directory/'preview.png',source,meta,approval,fingerprint,approval.sha256['dem.tif'])

def list_references():
    result=[]
    for rid in sorted(_directories()):
        try: result.append(load_reference(rid))
        except errors.TerraError as exc: logger.warning('%s',exc.message)
    return result

load_reference.cache_clear = _load_validated.cache_clear
