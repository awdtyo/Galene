"""Phase 1 data tests. Offline-first: fixture fallback + provenance + cache."""

import json

import httpx

from backend.app.data import cache as cache_mod
from backend.app.data import copernicus, imd, incois, openmeteo, static_geo


def test_fixture_fallback_on_network_error(monkeypatch, tmp_path):
    monkeypatch.setattr(cache_mod.settings, "DATA_CACHE_DIR", str(tmp_path / "c"))
    monkeypatch.setattr(cache_mod.settings, "DATA_FIXTURES_DIR", "data/fixtures")

    def boom(*a, **k):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", boom)
    out = openmeteo.fetch_marine(15.0, 74.0, use_cache=False)
    assert out["provenance"]["mode"] == "fixture"
    assert "hourly" in out["data"]


def test_live_parse_shape_with_mock(monkeypatch, tmp_path):
    monkeypatch.setattr(cache_mod.settings, "DATA_CACHE_DIR", str(tmp_path / "c"))
    sample = json.loads(open("data/fixtures/openmeteo_marine.json").read())

    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return sample

    monkeypatch.setattr(httpx, "get", lambda *a, **k: R())
    out = openmeteo.fetch_marine(15.0, 74.0, use_cache=False)
    assert out["provenance"]["mode"] == "live"
    assert out["data"]["hourly"]["wave_height"][0] == 1.2


def test_fixture_only_fetchers_return_provenance():
    for fn in (
        lambda: imd.fetch_imd_warning(use_cache=False),
        lambda: incois.fetch_pfz(use_cache=False),
        lambda: copernicus.fetch_ocean_colour(15.0, 74.0, use_cache=False),
        lambda: static_geo.fetch_depth(15.0, 74.0),
        lambda: static_geo.fetch_eez(),
        lambda: static_geo.fetch_mpas(),
        lambda: static_geo.fetch_tides(15.0, 74.0),
    ):
        out = fn()
        assert out["provenance"]["mode"] == "fixture"
        assert "fetched_at" in out["provenance"]


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod.settings, "DATA_CACHE_DIR", str(tmp_path / "c"))
    cache_mod.write_cache("probe", {"a": 1})
    assert cache_mod.read_cache("probe") == {"a": 1}
