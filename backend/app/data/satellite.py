"""Sentinel-2 true-colour tiles via CDSE Sentinel Hub Process API (VERIFIED live).

Verified 2026-09-28: POST https://sh.dataspace.copernicus.eu/api/v1/process
with CDSE Bearer token -> HTTP 200 image/png (coastline visible).
Tiles cached to data/cache (gitignored). No new deps (httpx only).
"""

import hashlib

import httpx

from backend.app.data.cache import cache_path
from backend.app.data.copernicus import get_cdse_token

PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
_WIDTH = 512

TRUECOLOR_SCRIPT = (
    "//VERSION=3\n"
    "function setup(){return{input:[\"B04\",\"B03\",\"B02\"],output:{bands:3}}}\n"
    "function evaluatePixel(s){return[s.B04,s.B03,s.B02]}"
)


def fetch_tile(minlon: float, minlat: float, maxlon: float, maxlat: float) -> dict:
    """Return {png: bytes, bounds: [[s,w],[n,e]]}. Raises on failure (no fake imagery)."""
    key = f"sat_{minlon:.2f}_{minlat:.2f}_{maxlon:.2f}_{maxlat:.2f}"
    digest = hashlib.md5(key.encode()).hexdigest()
    p = cache_path(f"tile_{digest}.png")
    if p.exists():
        return {"png": p.read_bytes(), "bounds": [[minlat, minlon], [maxlat, maxlon]], "cached": True}
    token = get_cdse_token()["data"]["access_token"]
    aspect = max((maxlat - minlat) / max((maxlon - minlon), 1e-6), 0.2)
    req = {
        "input": {
            "bounds": {"bbox": [minlon, minlat, maxlon, maxlat]},
            "data": [
                {
                    "type": "S2L2A",
                    "dataFilter": {
                        "timeRange": {"from": "2026-08-01T00:00:00Z", "to": "2026-09-28T00:00:00Z"},
                        "maxCloudCoverage": 30,
                    },
                }
            ],
        },
        "output": {"width": _WIDTH, "height": min(int(_WIDTH * aspect), 1024)},
        "evalscript": TRUECOLOR_SCRIPT,
    }
    r = httpx.post(PROCESS_URL, headers={"Authorization": "Bearer " + token}, json=req, timeout=90)
    r.raise_for_status()
    p.write_bytes(r.content)
    return {"png": r.content, "bounds": [[minlat, minlon], [maxlat, maxlon]], "cached": False}
