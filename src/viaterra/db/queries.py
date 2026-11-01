"""Read-only Neon queries for Viaterra's atlas."""

import streamlit as st
from viaterra.db.connection import connect


@st.cache_data(ttl=600, show_spinner=False)
def get_visited_places() -> list[dict]:
    """Load geolocated places; do not infer city or country memberships."""
    sql = """
        SELECT place_key, name, latitude, longitude, country_code
        FROM places
        WHERE location IS NOT NULL
          AND latitude BETWEEN -90 AND 90
          AND longitude BETWEEN -180 AND 180
        ORDER BY source_index NULLS LAST, place_key
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [
                {
                    "place_key": key,
                    "name": name,
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "country_code": country,
                }
                for key, name, lat, lon, country in cur.fetchall()
            ]
