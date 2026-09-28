from backend.app.tools import LatLon, get_alerts, get_forecast, get_tides

PT = LatLon(lat=15.0, lon=74.0)


def test_get_forecast_shape():
    out = get_forecast(PT, hours=2)
    assert len(out.hours) == 2
    assert out.hours[0].wind_kmh is not None


def test_get_tides():
    out = get_tides(PT)
    assert out.high_tide is not None and out.provenance.mode == "fixture"


def test_get_alerts_raw_no_verdict():
    out = get_alerts(PT)
    assert isinstance(out.warnings, list) and out.wind_kmh is not None
    assert not hasattr(out, "verdict")
