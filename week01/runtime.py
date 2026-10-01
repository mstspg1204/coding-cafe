"""
api.py
------
FastAPI service for the accessibility scorer.

    GET /health
    GET /amenities?lat=&lon=&radius=
    GET /isochrones?lat=&lon=            -> GeoJSON walking shapes to draw
    GET /score?lat=&lon=&method=auto     -> the 0-100 score

Start it with:
    uvicorn api:app --reload

Then open http://127.0.0.1:8000/docs to click through the endpoints.

Two ways of measuring are supported:
    isochrone  real walking shapes from OpenRouteService (needs a free key)
    distance   street distance from OSRM's demo server, divided by walk speed
method=auto picks isochrone when a key is available, distance otherwise.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

from overpass_amenities import fetch_amenities
import ors_isochrones as iso

OSRM_URL = "https://router.project-osrm.org"

# The public OSRM demo server only has the car profile loaded, so we ask it for
# network DISTANCE along real streets and convert to walking time ourselves.
WALK_SPEED_MS = 1.33
TABLE_CHUNK = 90

BANDS = iso.BANDS
CATEGORIES = ["grocery", "health", "school", "park", "transit"]

app = FastAPI(title="Accessibility scorer", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Measuring by street distance (OSRM)
# ---------------------------------------------------------------------------

def _table_chunk(origin: tuple[float, float], targets: list[dict]) -> list:
    coords = f"{origin[1]},{origin[0]}"
    for t in targets:
        coords += f";{t['lon']},{t['lat']}"
    destinations = ";".join(str(i) for i in range(1, len(targets) + 1))

    response = requests.get(
        f"{OSRM_URL}/table/v1/driving/{coords}",
        params={"sources": "0", "destinations": destinations, "annotations": "distance"},
        timeout=30,
        headers={"User-Agent": "walkshed-hackathon/1.0"},
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok":
        raise RuntimeError(data.get("message", "OSRM refused the request"))
    return data["distances"][0][1:]


def measure_by_distance(lat: float, lon: float, places: list[dict]) -> str:
    """Add walk_m and walk_s to every place. Returns the method actually used."""
    try:
        distances = []
        for i in range(0, len(places), TABLE_CHUNK):
            distances += _table_chunk((lat, lon), places[i : i + TABLE_CHUNK])
        for place, metres in zip(places, distances):
            metres = metres if metres is not None else place["distance_m"] * 1.4
            place["walk_m"] = round(metres)
            place["walk_s"] = round(metres / WALK_SPEED_MS)
            place["band"] = band_of_seconds(place["walk_s"])
        return "distance"
    except (requests.RequestException, RuntimeError, KeyError, IndexError):
        # A detour factor of 1.4 turns straight-line distance into a usable
        # estimate of street distance when the demo server is unavailable.
        for place in places:
            metres = place["distance_m"] * 1.4
            place["walk_m"] = round(metres)
            place["walk_s"] = round(metres / WALK_SPEED_MS)
            place["band"] = band_of_seconds(place["walk_s"])
        return "straight-line"


# ---------------------------------------------------------------------------
# Measuring by isochrone (OpenRouteService)
# ---------------------------------------------------------------------------

def measure_by_isochrone(lat: float, lon: float, places: list[dict], key: str | None) -> tuple[str, list[dict]]:
    """Put every place in a time band using the walking shapes. Returns (method, bands)."""
    bands, mode = iso.fetch_isochrones(lat, lon, api_key=key)
    for place in places:
        band = iso.band_index(place["lat"], place["lon"], bands)
        place["band"] = band
        place["walk_s"] = bands[band]["value"] if band != -1 else None
        place["walk_m"] = None
    return ("isochrone" if mode == "ors" else "circle"), bands


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def band_of_seconds(seconds: int) -> int:
    """0 = within 5 min, 1 = within 10, 2 = within 15, -1 = beyond."""
    for i, limit in enumerate(BANDS):
        if seconds <= limit:
            return i
    return -1


def build_score(places: list[dict]) -> dict:
    rows = []
    for category in CATEGORIES:
        hits = [p for p in places if p["category"] == category and p["band"] != -1]
        nearest = min((p["band"] for p in hits), default=-1)
        base = {0: 70, 1: 50, 2: 30}.get(nearest, 0)
        points = 0 if nearest == -1 else min(100, base + min(len(hits), 3) * 10)
        closest = min(hits, key=lambda p: p["band"], default=None)
        rows.append({
            "category": category,
            "count": len(hits),
            "nearest_band": nearest,
            "nearest_minutes": BANDS[nearest] // 60 if nearest != -1 else None,
            "nearest_name": closest["name"] if closest else None,
            "points": points,
        })

    total = round(sum(r["points"] for r in rows) / len(rows))
    return {
        "total": total,
        "verdict": verdict(total),
        "categories": rows,
        "missing": [r["category"] for r in rows if r["count"] == 0],
    }


def verdict(n: int) -> str:
    if n >= 80:
        return "Everyday needs are on your doorstep."
    if n >= 60:
        return "Most needs are walkable; one or two are a trek."
    if n >= 40:
        return "Walkable for some things, a vehicle for the rest."
    if n > 0:
        return "Daily life here needs a vehicle."
    return "Nothing mapped within a 15-minute walk."


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "ors_key_loaded": bool(os.environ.get("ORS_API_KEY"))}


@app.get("/amenities")
def amenities(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius: int = Query(1200, ge=100, le=5000),
):
    """Every mapped amenity within the radius, nearest first."""
    try:
        places = fetch_amenities(lat, lon, radius)
    except RuntimeError as err:
        raise HTTPException(status_code=503, detail=str(err))
    return {"count": len(places), "places": places}


@app.get("/isochrones")
def isochrones(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    key: str | None = Query(None, description="OpenRouteService key; falls back to ORS_API_KEY"),
):
    """The 5, 10 and 15 minute walking shapes, as GeoJSON ready to draw."""
    try:
        bands, mode = iso.fetch_isochrones(lat, lon, api_key=key)
    except iso.IsochroneError as err:
        raise HTTPException(status_code=502, detail=str(err))
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Could not reach OpenRouteService.")

    collection = iso.as_feature_collection(bands)
    collection["properties"] = {"mode": mode, "origin": {"lat": lat, "lon": lon}}
    return collection


@app.get("/score")
def score(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius: int = Query(1200, ge=100, le=5000),
    method: str = Query("auto", pattern="^(auto|isochrone|distance)$"),
    key: str | None = Query(None, description="OpenRouteService key; falls back to ORS_API_KEY"),
    include_shapes: bool = Query(True, description="Return the walking shapes too"),
):
    """The accessibility score for one coordinate."""
    try:
        places = fetch_amenities(lat, lon, radius)
    except RuntimeError as err:
        raise HTTPException(status_code=503, detail=str(err))

    have_key = bool(key or os.environ.get("ORS_API_KEY"))
    use_isochrone = method == "isochrone" or (method == "auto" and have_key)

    bands = None
    if use_isochrone:
        try:
            used, bands = measure_by_isochrone(lat, lon, places, key)
        except (iso.IsochroneError, requests.RequestException):
            used = measure_by_distance(lat, lon, places)   # keep answering
    else:
        used = measure_by_distance(lat, lon, places)

    result = build_score(places)
    result["method"] = used
    result["origin"] = {"lat": lat, "lon": lon, "radius_m": radius}
    result["places"] = [p for p in places if p["band"] != -1]
    if bands is not None and include_shapes:
        result["shapes"] = iso.as_feature_collection(bands)
    return result