"""Small, transaction-safe write operation for a manually captured place."""

import hashlib
import uuid

import pycountry

from viaterra.db.connection import connect
from viaterra.db.queries import get_visited_places


def country_iso3(alpha2: str | None) -> str | None:
    if not alpha2:
        return None
    match = pycountry.countries.get(alpha_2=alpha2.upper())
    return match.alpha_3 if match else None


def find_nearby(latitude: float, longitude: float) -> list[tuple]:
    """Return existing places within 35 metres for duplicate review."""
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Invalid coordinates.")

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT place_key, name, round(ST_Distance(location::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography))::int
                FROM places
                WHERE location IS NOT NULL
                  AND ST_DWithin(location::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 35)
                ORDER BY 3 LIMIT 5
            """, (longitude, latitude, longitude, latitude))
            nearby = cur.fetchall()
    return nearby


def insert_visited_place(*, name: str, latitude: float, longitude: float,
                         country_alpha2: str | None, country_name: str | None) -> str:
    clean = name.strip()
    if not clean or len(clean) > 250 or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Name or coordinates are invalid.")
    iso3 = country_iso3(country_alpha2)
    key = hashlib.sha256(("viaterra:manual:" + uuid.uuid4().hex).encode()).hexdigest()[:24]
    with connect() as conn:
        with conn.cursor() as cur:
            if iso3:
                cur.execute("""
                    INSERT INTO countries(code, name, code_source)
                    VALUES (%s, %s, 'photon') ON CONFLICT (code) DO NOTHING
                """, (iso3, country_name or iso3))
            cur.execute("""
                INSERT INTO places (place_key, name, source_list, latitude, longitude,
                                    location, country_code, country_status, country_method)
                VALUES (%s, %s, 'viaterra_capture', %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)
            """, (key, clean, latitude, longitude, longitude, latitude,
                  iso3, 'matched' if iso3 else 'unresolved',
                  'photon' if iso3 else None))
    get_visited_places.clear()
    return key
