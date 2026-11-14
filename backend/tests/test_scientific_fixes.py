"""Synthetic controls for methodology 0.3; not scientific analog ground truth."""
import math
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
import errors
import settings
import similarity
import terrain_features as tf
from analysis import METRICS, compute_features, information_warnings, analyze
from preprocessing import HarmonizedGrid, harmonize, _read_footprint
from validation import open_earth_dem
from conftest import write_dem


def encoded(path, data, scale, offset, units="metre", mask=None):
    write_dem(path, data, dtype="float64", units=units, nodata=-9999,
              transform=from_origin(500000,4500000,500,500))
    with rasterio.open(path, "r+") as dst:
        dst.scales = (scale,)
        dst.offsets = (offset,)
        if mask is not None:
            dst.write_mask(mask.astype("uint8") * 255)
    return open_earth_dem(path)[0]


@pytest.mark.parametrize("units,factor", [("metre",1.),("feet",.3048),("US survey foot",1200/3937)])
def test_decode_before_unit_conversion(tmp_path, units, factor):
    src=encoded(tmp_path/"encoded.tif",np.full((64,64),1000.),.5,10.,units)
    for r in (src.native_spacing_m,src.native_spacing_m*2):
        grid=harmonize(src,r,32)
        assert grid.valid.all()
        assert np.allclose(grid.elevation_m,510*factor,atol=1e-10)


@pytest.mark.parametrize("scale,offset", [(0.5,10.),(-0.5,1200.),(0.,12.),(1.,0.)])
def test_encoded_matches_physical_with_raw_nodata_and_internal_mask(tmp_path,scale,offset):
    y,x=np.indices((64,64));raw=(1000+2*x+4*y).astype(float)
    raw[12:16,12:16]=-9999
    mask=np.ones(raw.shape,bool);mask[30:35,30:35]=False
    src=encoded(tmp_path/"raw.tif",raw,scale,offset,mask=mask)
    # Internal dataset mask takes precedence over the raw NoData sentinel in GDAL.
    # The actual GDAL valid-data mask is the source of truth for both encodings.
    with rasterio.open(src.path) as d:
        valid=~np.ma.getmaskarray(d.read(1,masked=True))
    physical=raw*scale+offset
    other=encoded(tmp_path/"physical.tif",physical,1.,0.,mask=valid)
    for r in (src.native_spacing_m,src.native_spacing_m*2):
        a,b=harmonize(src,r,32),harmonize(other,r,32)
        assert np.array_equal(a.valid,b.valid)
        assert np.allclose(a.elevation_m,b.elevation_m,equal_nan=True,atol=1e-10)


def test_nodata_masked_before_decoding_and_zero_remains_valid(tmp_path):
    raw=np.full((64,64),1000.);raw[31,31]=-9999
    src=encoded(tmp_path/"raw.tif",raw,1.,-1000.)
    data,_=_read_footprint(src,16000,0)
    assert np.isnan(data).sum()==1
    assert np.all(data[np.isfinite(data)]==0.)


@pytest.mark.parametrize("scale,offset",[(float("nan"),0),(float("inf"),0),(1,float("inf"))])
def test_nonfinite_encoding_rejected(tmp_path,scale,offset):
    with pytest.raises(errors.TerraError) as exc:
        encoded(tmp_path/"bad.tif",np.ones((64,64)),scale,offset)
    assert exc.value.code==errors.INVALID_DEM[0]


def test_overflow_rejected_not_silently_masked(tmp_path):
    src=encoded(tmp_path/"overflow.tif",np.full((64,64),1000.),1e308,0)
    with pytest.raises(errors.TerraError,match="non-finite"):
        harmonize(src,src.native_spacing_m,32)


def test_plausibility_applies_to_decoded_elevation(tmp_path):
    src=encoded(tmp_path/"valid.tif",np.full((64,64),20000.),.1,0)
    assert np.nanmedian(harmonize(src,src.native_spacing_m,32).elevation_m)==pytest.approx(2000)
    src=encoded(tmp_path/"invalid.tif",np.full((64,64),1000.),10.,0)
    with pytest.raises(errors.TerraError):
        harmonize(src,src.native_spacing_m,32)


def features(z,r=500.):
    return compute_features(HarmonizedGrid(z,np.isfinite(z),r,z.shape[0]),"synthetic")


def scores(a,b):
    return {k:similarity.distribution_similarity(a.scoring_histograms[k],b.scoring_histograms[k]) for k in METRICS}


def plane(angle):
    return np.tile(np.arange(64)*500*math.tan(math.radians(angle)),(64,1))


def test_audit_slope_boundary_and_far_negative_control():
    a,b=features(plane(.999999)),features(plane(1.000001))
    assert similarity.distribution_similarity(a.histograms["slope_distribution"],b.histograms["slope_distribution"])==0
    assert scores(a,b)["slope_distribution"]>0.99999
    assert scores(a,features(plane(25)))["slope_distribution"]==0


@pytest.mark.parametrize("edges",[settings.SLOPE_BIN_EDGES_DEG,settings.RELIEF_BIN_EDGES_M,settings.ROUGHNESS_BIN_EDGES_M])
def test_soft_mass_and_continuity_at_all_edges_and_centers(edges):
    centers=(np.array(edges[:-1])+edges[1:])/2
    for value in [*edges,*centers]:
        eps=1e-9
        p,n=tf.soft_histogram_fractions([value-eps,np.nan],edges)
        q,_=tf.soft_histogram_fractions([value+eps],edges)
        assert n==1 and p.sum()==pytest.approx(1) and np.all(p>=0)
        assert similarity.distribution_similarity(p,q)>0.9999
    p,_=tf.soft_histogram_fractions([-1e9,1e9],edges)
    assert p[0]==p[-1]==.5


def test_soft_assignment_independent_linear_oracle_and_not_blanket_score_inflation():
    # Centers 0.5, 1.5, 3.0: x=1.0 splits mass equally between the first two.
    p,n=tf.soft_histogram_fractions([1.0,3.0,np.nan],[0,1,2,4])
    assert n==2 and p==pytest.approx([.25,.25,.5])
    edges=[0,1,2,4]
    hard=[tf.histogram_fractions([v],edges)[0] for v in (.6,.9)]
    soft=[tf.soft_histogram_fractions([v],edges)[0] for v in (.6,.9)]
    assert similarity.distribution_similarity(*hard)==1
    assert similarity.distribution_similarity(*soft)<1


def test_soft_empty_single_bin_and_invalid_edges():
    p,n=tf.soft_histogram_fractions([np.nan],[0,1]);assert n==0 and p.tolist()==[0]
    p,n=tf.soft_histogram_fractions([-100,100],[0,1]);assert n==2 and p.tolist()==[1]
    for edges in ([0,0,1],[0,float("inf")],[1,0]):
        with pytest.raises(ValueError):tf.soft_histogram_fractions([1],edges)


def test_identity_offset_inversion_and_flat_limits_are_explicit():
    y,x=np.indices((64,64));z=100*np.sin(x/3.4)+40*np.cos(y/4.6)
    a=features(z)
    for other in (z,z+1000,-z):
        assert all(s==pytest.approx(1,abs=1e-6) for s in scores(a,features(other)).values())
    flat=features(np.ones((64,64))*500)
    assert all(s==1 for s in scores(flat,flat).values())
    warnings=information_warnings(flat,flat)
    assert {w["code"] for w in warnings}=={"FLAT_TERRAIN","REFERENCE_FLAT_TERRAIN","LOW_INFORMATION_TERRAIN"}
    assert sum(w["code"]=="LOW_INFORMATION_TERRAIN" for w in warnings)==2
    assert not information_warnings(a,a)


def test_api_scoring_uses_soft_mass_and_preserves_chart_counts(tmp_path,monkeypatch):
    import analysis
    from reference import load_reference
    from preprocessing import plan_common_grid
    p=tmp_path/"earth.tif"
    src=encoded(p,np.tile(np.arange(64)*3.,(64,1))+1000,.5,10)
    ref=load_reference("mars-gale")
    resolution,cells=plan_common_grid(src,ref.source);resolution=round(resolution,6)
    ef=features(harmonize(src,resolution,cells).elevation_m,resolution)
    rf=features(np.zeros((cells,cells)),resolution)
    monkeypatch.setattr(analysis,"reference_features",lambda *args:rf)
    out=analyze(p,"mars-gale")
    assert out["scores"]==pytest.approx(scores(ef,rf))
    assert out["charts"]["slope_distribution"]["earth"]==list(ef.histograms["slope_distribution"])
    codes={w["code"] for w in out["warnings"]}
    assert {"REFERENCE_FLAT_TERRAIN","LOW_INFORMATION_TERRAIN","DESCRIPTOR_SIMILARITY_ONLY",
            "CROSS_REFERENCE_SCALE_CAUTION","SOFT_HISTOGRAM_SCORING","ELEVATION_ENCODING_APPLIED"}<=codes


def test_js_roundoff_near_equal_vectors_stays_finite():
    p=[0.10304156820886091,0.23661197181533114,0.5393095228793129,0.12103693709649457]
    q=[0.10304156820886086,0.2366119718153316,0.5393095228793129,0.12103693709649468]
    assert similarity.js_distance(p,q)==pytest.approx(0.,abs=2e-8)
    assert similarity.js_distance(q,p)==pytest.approx(0.,abs=2e-8)
