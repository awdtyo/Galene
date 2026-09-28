"""Read-only geo endpoints for the Leaflet frontend (real fixtures)."""

from fastapi import APIRouter

from backend.app.data.static_geo import fetch_eez, fetch_mpas
from backend.app.tools import get_pfz

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/eez")
def eez():
    return fetch_eez()["data"]


@router.get("/mpas")
def mpas():
    return fetch_mpas()["data"]


@router.get("/pfz")
def pfz(sector: str = "KERALA"):
    return get_pfz(sector).model_dump()
