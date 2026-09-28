from backend.app.tools import LatLon, get_chlorophyll, get_pfz, get_sst
import httpx

PT = LatLon(lat=15.0, lon=74.0)


def test_get_pfz():
    out = get_pfz("KERALA")
    assert out.sector == "KERALA" and len(out.zones) == 1
    assert out.provenance.mode in ("fixture", "cache")


def test_get_sst_offline(monkeypatch):
    from backend.app.data import openmeteo as om

    def boom(*a, **k):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", boom)
    monkeypatch.setattr(om, "read_cache", lambda *a, **k: None)
    out = get_sst(PT)
    assert out.sst_c == 28.4 and out.lat == 15.0
    assert out.provenance.mode == "fixture"


def test_get_sst_live_shape():
    out = get_sst(PT)
    assert 0 < out.sst_c < 40 and out.provenance.mode in ("live", "cache", "fixture")


def test_get_chlorophyll():
    out = get_chlorophyll(PT)
    assert out.chlorophyll_mg_m3 == 0.42
