"""Universal registry and polar regressions; all Earth inputs are synthetic."""
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
import pyproj
import pytest
import rasterio
from rasterio.transform import from_origin
from fastapi.testclient import TestClient
import errors
import settings
import reference
from app import app
from analysis import analyze
from preprocessing import describe_source, harmonize, plan_common_grid
from validation import open_earth_dem

IDS = ['mars-gale','moon-mons-mouton','moon-shackleton']
client = TestClient(app)

@pytest.fixture
def catalog(tmp_path,monkeypatch):
    directory=tmp_path/'references';directory.mkdir()
    shutil.copytree(settings.REFERENCES_DIR/'moon-shackleton',directory/'moon-shackleton')
    monkeypatch.setattr(settings,'REFERENCES_DIR',directory)
    reference.load_reference.cache_clear()
    return directory

def approve(directory):
    p=directory/'registration.json';d=json.loads(p.read_text())
    d['sha256']={n:hashlib.sha256((directory/n).read_bytes()).hexdigest() for n in d['sha256']}
    p.write_text(json.dumps(d))

@pytest.mark.parametrize('rid',IDS)
def test_registry_asset_identity_and_masks(rid):
    r=reference.load_reference(rid)
    assert r.dem_sha256==hashlib.sha256(r.source.path.read_bytes()).hexdigest()
    assert r.source.path.parent.name==rid
    assert r.source.horizontal_crs.ellipsoid.semi_major_metre == (3396000 if r.source.body=='mars' else 1737400)
    with rasterio.open(r.source.path) as ds:
        z=ds.read(1,masked=True)
        assert z.count()==r.metadata['raster']['valid_pixels']
        assert int(np.ma.count_masked(z))==r.metadata['raster']['nodata_pixels']
    preview=client.get(r.preview_url)
    assert preview.status_code==200 and preview.content==r.preview_path.read_bytes()

@pytest.mark.parametrize('lat',[-85.0,-89.0,-89.67,-89.9999,-90.0])
def test_polar_ground_distances_and_harmonization(tmp_path,lat):
    crs=reference.load_reference('moon-shackleton').source.horizontal_crs
    xy=pyproj.Transformer.from_crs(crs.geodetic_crs,crs,always_xy=True)
    x,y=xy.transform(129.78,lat)
    t=from_origin(x-8000,y+8000,80,80)
    p=tmp_path/'polar.tif'
    yy,xx=np.indices((200,200));z=(100+0.2*xx+0.3*yy).astype('float32')
    with rasterio.open(p,'w',driver='GTiff',width=200,height=200,count=1,dtype='float32',crs=crs.to_wkt(),transform=t,nodata=-9999) as d:d.write(z,1)
    source=describe_source(p,'moon',crs,t,200,200,1.0)
    from dataclasses import replace
    source=replace(source,elevation_range_m=(100,200))
    # Spherical polar stereographic scale: ground spacing = map spacing*cos(colatitude/2)^2.
    expected=80*np.cos(np.radians(90+lat)/2)**2
    assert source.spacing_xy_m==pytest.approx((expected,expected),rel=2e-5)
    grid=harmonize(source,160,64)
    assert grid.valid_fraction==1 and np.isfinite(grid.elevation_m).all()
    assert grid.footprint_m==10240
    assert grid.elevation_m.min()>=100 and grid.elevation_m.max()<=200

@pytest.mark.parametrize('rid',IDS)
def test_equal_physical_grids(synthetic_dem,rid):
    earth,_=open_earth_dem(synthetic_dem);ref=reference.load_reference(rid)
    res,n=plan_common_grid(earth,ref.source)
    assert res>=earth.native_spacing_m and res>=ref.source.native_spacing_m
    eg=harmonize(earth,res,n);rg=harmonize(ref.source,res,n)
    assert eg.footprint_m==rg.footprint_m and eg.elevation_m.shape==rg.elevation_m.shape

@pytest.mark.parametrize('rid',IDS)
def test_actual_selected_analysis(synthetic_dem,rid):
    with synthetic_dem.open('rb') as f:r=client.post('/analyze',files={'file':('earth.tif',f)},data={'reference_id':rid})
    assert r.status_code==200,r.text
    data=r.json();ref=reference.load_reference(rid)
    assert data['is_mock'] is False and data['reference']['id']==rid
    assert data['reference']['dem_sha256']==hashlib.sha256(ref.source.path.read_bytes()).hexdigest()
    assert data['reference']['preview_url']==ref.preview_url
    assert all(np.isfinite(v) and 0<=v<=1 for v in [data['total_similarity'],*data['scores'].values()])
    assert data['charts']['slope_distribution']['reference']==data['charts']['slope_distribution']['mars']
    assert any(w['code']=='COMPARISON_SCALE' for w in data['warnings'])
    assert {'DESCRIPTOR_SIMILARITY_ONLY','CROSS_REFERENCE_SCALE_CAUTION','SOFT_HISTOGRAM_SCORING'} <= {w['code'] for w in data['warnings']}
    if rid=='mars-gale':
        # Methodology 0.3 golden value; 0.2 hard assignment was 0.3584422608885516.
        # Bins/weights were not fitted to this synthetic fixture.
        assert settings.METHODOLOGY_VERSION=='0.3-proposal'
        assert data['total_similarity']==pytest.approx(0.3962021713268066,abs=1e-12)

@pytest.mark.parametrize('rid',['../moon-shackleton','/tmp/evil','MOON','moon-unknown','moon-shackleton/..'])
def test_safe_identifiers(rid):
    with pytest.raises(errors.TerraError) as e:reference.load_reference(rid)
    assert e.value.code=='UNKNOWN_REFERENCE'

def test_discovery_requires_approval_and_detects_new_directory(catalog):
    shutil.copytree(catalog/'moon-shackleton',catalog/'moon-new')
    assert [r.id for r in reference.list_references()]==['moon-shackleton']
    p=catalog/'moon-new'/'registration.json';d=json.loads(p.read_text());d['reference_id']='moon-new';p.write_text(json.dumps(d))
    p=catalog/'moon-new'/'metadata.json';m=json.loads(p.read_text());m['reference_id']='moon-new';p.write_text(json.dumps(m));approve(p.parent)
    assert [r.id for r in reference.list_references()]==['moon-new','moon-shackleton']
    d=json.loads((p.parent/'registration.json').read_text());d['approved']=False;(p.parent/'registration.json').write_text(json.dumps(d))
    assert [r.id for r in reference.list_references()]==['moon-shackleton']

@pytest.mark.parametrize('change',['unit','body','crs','nodata','width','mean','center','nan','unknown_field','disabled','approval_type'])
def test_malformed_metadata_and_approval(catalog,change):
    directory=catalog/'moon-shackleton';p=directory/'metadata.json';m=json.loads(p.read_text())
    if change=='unit':m['elevation']['unit']='feet'
    elif change=='body':m['planet']='Mars'
    elif change=='crs':m['coordinate_system']['crs_wkt']='EPSG:32643'
    elif change=='nodata':m['raster']['nodata']=0
    elif change=='width':m['raster']['width']=True
    elif change=='mean':m['elevation']['mean']=123456
    elif change=='center':m['center']['latitude_planetocentric']=-80
    elif change=='nan':m['elevation']['minimum']=float('nan')
    p.write_text(json.dumps(m));approve(directory)
    p=directory/'registration.json';d=json.loads(p.read_text())
    if change=='unknown_field':d['arbitrary_path']='../outside'
    if change=='disabled':d['enabled']=False
    if change=='approval_type':d['approved']='true'
    p.write_text(json.dumps(d))
    with pytest.raises(errors.TerraError) as e:reference.load_reference('moon-shackleton')
    assert e.value.code=='REFERENCE_UNAVAILABLE'
    assert reference.list_references()==[]
    response=client.post('/analyze',files={'file':('earth.tif',b'not read')},data={'reference_id':'moon-shackleton'})
    assert response.status_code==500 and response.json()['error']['code']=='REFERENCE_UNAVAILABLE'

def test_changed_assets_not_served_from_cache(catalog):
    first=reference.load_reference('moon-shackleton')
    p=catalog/'moon-shackleton'/'dem.tif'
    with rasterio.open(p,'r+') as d:
        z=d.read(1);z[0,0]+=1;d.write(z,1)
    with pytest.raises(errors.TerraError):reference.load_reference('moon-shackleton')
    assert first.dem_sha256!=hashlib.sha256(p.read_bytes()).hexdigest()

def test_switching_references_is_reproducible(synthetic_dem):
    a=analyze(synthetic_dem,'mars-gale')
    b=analyze(synthetic_dem,'moon-shackleton')
    c=analyze(synthetic_dem,'mars-gale')
    assert a==c and a['reference']['dem_sha256']!=b['reference']['dem_sha256']

def test_effective_resolution_uses_verified_scale(synthetic_dem):
    from dataclasses import replace
    earth,_=open_earth_dem(synthetic_dem)
    moon=replace(reference.load_reference('moon-shackleton').source,effective_resolution_m=200.0)
    resolution,_=plan_common_grid(earth,moon)
    assert resolution==200

def test_invalid_geometry_rejected(tmp_path):
    from affine import Affine
    crs=reference.load_reference('moon-shackleton').source.horizontal_crs
    for transform in [Affine(0,0,0,0,0,0),Affine(float('nan'),0,0,0,-80,0)]:
        with pytest.raises(errors.TerraError):describe_source(tmp_path/'unused.tif','moon',crs,transform,10,10,1)

def test_approved_revision_invalidates_features(catalog,synthetic_dem):
    first=analyze(synthetic_dem,'moon-shackleton')
    directory=catalog/'moon-shackleton'
    with rasterio.open(directory/'dem.tif','r+') as d:
        z=d.read(1);mask=d.read_masks(1)>0;z[mask]*=0.5;d.write(z,1)
    p=directory/'metadata.json';m=json.loads(p.read_text())
    m['elevation'].update(minimum=float(z[mask].min()),maximum=float(z[mask].max()),mean=float(np.mean(z[mask],dtype=np.float64)))
    p.write_text(json.dumps(m));approve(directory)
    second=analyze(synthetic_dem,'moon-shackleton')
    assert first['reference']['version']!=second['reference']['version']
    assert first['reference']['dem_sha256']!=second['reference']['dem_sha256']
    assert first['scores']!=second['scores']
    assert second==analyze(synthetic_dem,'moon-shackleton')
