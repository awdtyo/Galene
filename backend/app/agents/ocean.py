"""Ocean Analytics agent: SST, chlorophyll, PFZ correlation note. Wraps ocean tools."""

from backend.app.api.schemas import now_iso
from backend.app.tools import LatLon, get_chlorophyll, get_pfz, get_sst


def analyze(point: LatLon, sector: str, trace: list) -> dict:
    sst = get_sst(point)
    trace.append({"agent": "ocean", "tool": "get_sst", "timestamp": now_iso()})
    chl = get_chlorophyll(point)
    trace.append({"agent": "ocean", "tool": "get_chlorophyll", "timestamp": now_iso()})
    pfz = get_pfz(sector)
    trace.append({"agent": "ocean", "tool": "get_pfz", "timestamp": now_iso()})
    favourable = sst.sst_c >= 27.0 and chl.chlorophyll_mg_m3 >= 0.3
    return {
        "sst_c": sst.sst_c,
        "chlorophyll_mg_m3": chl.chlorophyll_mg_m3,
        "pfz_zones": [z.model_dump() for z in pfz.zones],
        "favourable": favourable,
        "note": "PFZ correlation baseline: warm SST + elevated chlorophyll suggest productivity.",
    }
