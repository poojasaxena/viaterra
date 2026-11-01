"""Import the country-enriched CSV into Neon; preview by default."""

import argparse
import os
from pathlib import Path

import pandas as pd

from viaterra.db.connection import connect


def csv_path() -> Path:
    root = os.environ.get("GLOBAL_DATASETS_DIR")
    if not root:
        raise RuntimeError("GLOBAL_DATASETS_DIR is not set")
    return Path(root).expanduser().resolve() / "Personal/Travel/processed/google_maps_visited.csv"


def optional(row, field):
    value = row.get(field)
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def load_rows():
    path = csv_path()
    df = pd.read_csv(path, dtype={
        "place_key": "string", "country_iso3": "string",
        "google_maps_id": "string", "google_maps_url": "string",
    })
    needed = {"place_key", "name", "latitude", "longitude", "country_status"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"CSV lacks required columns: {sorted(missing)}")
    if df["place_key"].isna().any() or df["place_key"].duplicated().any():
        raise ValueError("place_key must be non-null and unique")
    if df["name"].isna().any():
        raise ValueError("Every place must have a name")
    valid_status = {"matched", "proposed", "verified", "unresolved"}
    if not set(df["country_status"]).issubset(valid_status):
        raise ValueError("Unexpected country_status")
    for field in ("latitude", "longitude"):
        df[field] = pd.to_numeric(df[field], errors="coerce")
    coords_ok = (
        (df.latitude.isna() & df.longitude.isna()) |
        (df.latitude.between(-90, 90) & df.longitude.between(-180, 180))
    )
    if not coords_ok.all():
        raise ValueError("Invalid or incomplete latitude/longitude pair")
    rows = df.to_dict("records")
    countries = {}
    for row in rows:
        status = row["country_status"]
        code = optional(row, "country_iso3") if status in ("matched", "verified") else None
        name = optional(row, "country") if code else None
        if code:
            if not isinstance(code, str) or len(code) != 3 or not name:
                raise ValueError(f"Bad country on {row['name']!r}: {code!r} / {name!r}")
            if code in countries and countries[code] != name:
                raise ValueError(f"Conflicting names for country code {code}")
            countries[code] = name
    return path, rows, countries


UPSERT_PLACE = """
INSERT INTO places (
    place_key, name, source_index, source_list, google_maps_id, google_maps_url,
    latitude, longitude, location, country_code, country_status, country_method,
    nearest_country, nearest_iso3, distance_km_approx
) VALUES (
    %(place_key)s, %(name)s, %(source_index)s, %(source_list)s,
    %(google_maps_id)s, %(google_maps_url)s,
    %(latitude)s, %(longitude)s,
    ST_SetSRID(
        ST_MakePoint(
            %(longitude)s::double precision,
            %(latitude)s::double precision
        ),
        4326
    ),
    %(country_code)s, %(country_status)s, %(country_method)s,
    %(nearest_country)s, %(nearest_iso3)s, %(distance_km_approx)s
)
ON CONFLICT (place_key) DO UPDATE SET
    name = EXCLUDED.name,
    source_index = EXCLUDED.source_index,
    source_list = EXCLUDED.source_list,
    google_maps_id = EXCLUDED.google_maps_id,
    google_maps_url = EXCLUDED.google_maps_url,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    location = EXCLUDED.location,
    country_code = EXCLUDED.country_code,
    country_status = EXCLUDED.country_status,
    country_method = EXCLUDED.country_method,
    nearest_country = EXCLUDED.nearest_country,
    nearest_iso3 = EXCLUDED.nearest_iso3,
    distance_km_approx = EXCLUDED.distance_km_approx,
    updated_at = now()
"""


def import_data(rows, countries):
    with connect() as conn:
        with conn.cursor() as cur:
            for code, name in sorted(countries.items()):
                cur.execute(
                    "INSERT INTO countries(code, name) VALUES (%s, %s) "
                    "ON CONFLICT (code) DO NOTHING",
                    (code, name),
                )
            for row in rows:
                status = row["country_status"]
                code = optional(row, "country_iso3") if status in ("matched", "verified") else None
                lat = optional(row, "latitude")
                lon = optional(row, "longitude")
                payload = {
                    "place_key": str(row["place_key"]),
                    "name": str(row["name"]),
                    "source_index": optional(row, "source_index"),
                    "source_list": optional(row, "source_list"),
                    "google_maps_id": optional(row, "google_maps_id"),
                    "google_maps_url": optional(row, "google_maps_url"),
                    "latitude": lat, "longitude": lon,
                    "country_code": code,
                    "country_status": status,
                    "country_method": optional(row, "country_method"),
                    "nearest_country": optional(row, "nearest_country"),
                    "nearest_iso3": optional(row, "nearest_iso3"),
                    "distance_km_approx": optional(row, "distance_km_approx"),
                }
                cur.execute(UPSERT_PLACE, payload)
        count = conn.execute("SELECT count(*) FROM places").fetchone()[0]
    print(f"Import committed. Database now contains {count} places.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write to Neon (default: dry-run)")
    args = parser.parse_args()
    path, rows, countries = load_rows()
    statuses = pd.Series([r["country_status"] for r in rows]).value_counts()
    print(f"CSV: {path}")
    print(f"Records: {len(rows)} | Countries to ensure: {len(countries)}")
    print(statuses.to_string())
    if not args.apply:
        print("DRY RUN: No database changes. Add --apply to import.")
        return
    import_data(rows, countries)


if __name__ == "__main__":
    main()
