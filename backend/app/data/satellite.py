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

# S3 OLCI red-green ratio -> colour ramp (VERIFIED live 2026-09-28: collection
# SENTINEL-3-OLCI with bands B08/B06 accepted, HTTP 200 PNG). Relative scale
# only — NOT calibrated chlorophyll; land is not masked. Indicative overlay.
CHL_SCRIPT = (
    "//VERSION=3\n"
    "function setup(){return{input:[\"B08\",\"B06\"],output:{bands:3}}}\n"
    "function evaluatePixel(s){"
    "let r=s.B08/(s.B06+0.001);"
    "if(r<0.4)return[0.05,0.2,0.6];"
    "if(r<0.7)return[0.05,0.6,0.5];"
    "if(r<1.0)return[0.9,0.8,0.2];"
    "return[0.85,0.25,0.1];}"
)


def _process(collection: str, data_filter: dict, script: str, prefix: str,
             minlon: float, minlat: float, maxlon: float, maxlat: float) -> dict:
    key = f"{prefix}_{minlon:.2f}_{minlat:.2f}_{maxlon:.2f}_{maxlat:.2f}"
    digest = hashlib.md5(key.encode()).hexdigest()
    p = cache_path(f"tile_{digest}.png")
    if p.exists():
        return {"png": p.read_bytes(), "bounds": [[minlat, minlon], [maxlat, maxlon]], "cached": True}
    token = get_cdse_token()["data"]["access_token"]
    aspect = max((maxlat - minlat) / max((maxlon - minlon), 1e-6), 0.2)
    req = {
        "input": {"bounds": {"bbox": [minlon, minlat, maxlon, maxlat]},
                  "data": [{"type": collection, "dataFilter": data_filter}]},
        "output": {"width": _WIDTH, "height": min(int(_WIDTH * aspect), 1024)},
        "evalscript": script,
    }
    r = httpx.post(PROCESS_URL, headers={"Authorization": "Bearer " + token}, json=req, timeout=90)
    r.raise_for_status()
    p.write_bytes(r.content)
    return {"png": r.content, "bounds": [[minlat, minlon], [maxlat, maxlon]], "cached": False}


def fetch_tile(minlon: float, minlat: float, maxlon: float, maxlat: float) -> dict:
    """Return {png: bytes, bounds: [[s,w],[n,e]]}. Raises on failure (no fake imagery)."""
    return _process(
        "S2L2A",
        {"timeRange": {"from": "2026-08-01T00:00:00Z", "to": "2026-09-28T00:00:00Z"}, "maxCloudCoverage": 30},
        TRUECOLOR_SCRIPT, "sat", minlon, minlat, maxlon, maxlat,
    )


def fetch_chl(minlon: float, minlat: float, maxlon: float, maxlat: float) -> dict:
    """Chlorophyll-proxy overlay (S3 OLCI red-green ratio, relative scale)."""
    return _process(
        "SENTINEL-3-OLCI",
        {"timeRange": {"from": "2026-09-01T00:00:00Z", "to": "2026-09-28T00:00:00Z"}},
        CHL_SCRIPT, "chl", minlon, minlat, maxlon, maxlat,
    )
