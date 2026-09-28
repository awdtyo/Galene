from backend.app.tools import LatLon, check_geofence, plan_route


def test_geofence_inside_eez_outside_mpa():
    out = check_geofence(LatLon(lat=15.0, lon=74.0))
    assert out.inside_eez is True and out.inside_mpa is False
    assert "NOT for navigation" in out.note


def test_geofence_inside_mpa():
    # Verified centroid inside Sundarbans MPA polygon (real WDPA geometry).
    out = check_geofence(LatLon(lat=21.965, lon=88.91))
    assert out.inside_mpa is True
    assert out.mpa_name is not None and "Sundarban" in out.mpa_name


def test_route_detours_around_mpa():
    a, b = LatLon(lat=21.9, lon=88.0), LatLon(lat=21.9, lon=89.4)
    out = plan_route(a, b)
    assert out.detoured is True and len(out.waypoints) == 3 and out.distance_km > 0


def test_route_direct_when_clear():
    a, b = LatLon(lat=15.0, lon=74.0), LatLon(lat=15.5, lon=74.5)
    out = plan_route(a, b)
    assert out.detoured is False and len(out.waypoints) == 2
