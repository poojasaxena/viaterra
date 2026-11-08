"""Small, on-demand OpenStreetMap/Photon lookup for Viaterra's capture page.

Prototype only: public Photon servers are best-effort and not an SLA-backed geocoder.
No request is sent on every keystroke; all requests require an explicit action.
"""

from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PHOTON = "https://photon.komoot.io"


def _get(path: str, params: dict) -> dict:
    url = f"{PHOTON}{path}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "ViaterraPersonalAtlas/0.1 (personal travel capture prototype)", "Accept": "application/json"})
    with urlopen(request, timeout=12) as response:
        return json.load(response)


def _parse(feature: dict) -> dict | None:
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or []
    if len(coords) < 2:
        return None
    props = feature.get("properties") or {}
    name = props.get("name") or props.get("city") or props.get("street") or props.get("country") or "Unnamed location"
    location_bits = [props.get(k) for k in ("city", "state", "country")]
    area = ", ".join(x for x in location_bits if x and x != name)
    return {"name": name, "area": area, "latitude": float(coords[1]), "longitude": float(coords[0]),
            "country": props.get("country"), "country_alpha2": (props.get("countrycode") or "").upper(),
            "osm_type": props.get("osm_type"), "osm_id": props.get("osm_id")}


def search_places(query: str) -> list[dict]:
    query = query.strip()
    if len(query) < 3:
        return []
    data = _get("/api/", {"q": query, "limit": 6, "lang": "en"})
    return [p for f in data.get("features", []) if (p := _parse(f))]


def nearest_place(latitude: float, longitude: float) -> dict | None:
    data = _get("/reverse", {"lat": latitude, "lon": longitude, "limit": 1, "lang": "en"})
    for feature in data.get("features", []):
        result = _parse(feature)
        if result:
            return result
    return None
