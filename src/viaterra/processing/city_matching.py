"""Reviewable city-area matching for Viaterra using Overture divisions.

Save as src/viaterra/processing/city_matching.py.
Run from Viaterra project root:
    python -m viaterra.processing.city_matching --max-tiles 3
    python -m viaterra.processing.city_matching --max-tiles 10
    python -m viaterra.processing.city_matching --max-tiles 0

Existing area downloads are reused. Each processed tile needs BOTH cached
`division_area` polygons and `division` hierarchy records. Only the first N
incomplete tiles are downloaded per run. No Neon or master places CSV changes.

Automatic matches are deliberately conservative. Review overlapping areas in
city_candidates.csv and record any accepted choice in city_overrides.csv.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

DATA_ROOT = Path(os.environ["GLOBAL_DATASETS_DIR"]).expanduser().resolve() / "Personal" / "Travel"
SOURCE = DATA_ROOT / "processed" / "google_maps_visited.csv"
CACHE = DATA_ROOT / "raw" / "geography" / "overture" / "tiles"
MATCHES_OUT = DATA_ROOT / "processed" / "city_matches.csv"
REVIEW_OUT = DATA_ROOT / "processed" / "city_review.csv"
CANDIDATES_OUT = DATA_ROOT / "processed" / "city_candidates.csv"
OVERRIDES_OUT = DATA_ROOT / "processed" / "city_overrides.csv"
BOUNDARIES_OUT = DATA_ROOT / "processed" / "city_boundaries.geojson"

TILE_SIZE = 0.5
PAD = 0.035
# A county and a neighborhood are not automatically cities. A 'region' can
# nevertheless be a city-level authority (Taipei). We keep it for review.
CANDIDATE_SUBTYPES = {"locality", "localadmin", "region", "county", "borough", "macrohood"}
STRONG_SUBTYPES = {"locality", "localadmin"}
OVERRIDE_FIELDS = ["place_key", "chosen_overture_area_id", "comment"]


def tile_key(lat: float, lon: float) -> tuple[int, int]:
    return (math.floor(lat / TILE_SIZE), math.floor(lon / TILE_SIZE))


def tile_path(key: tuple[int, int]) -> Path:
    # Preserve compatibility with files already downloaded by first version.
    return CACHE / f"localities_{key[0]}_{key[1]}.geojson"


def division_path(key: tuple[int, int]) -> Path:
    return CACHE / f"divisions_{key[0]}_{key[1]}.geojson"


def tile_bbox(key: tuple[int, int]) -> tuple[float, float, float, float]:
    lat0, lon0 = key[0] * TILE_SIZE, key[1] * TILE_SIZE
    return (max(-180., lon0 - PAD), max(-90., lat0 - PAD),
            min(180., lon0 + TILE_SIZE + PAD), min(90., lat0 + TILE_SIZE + PAD))


def load_points() -> gpd.GeoDataFrame:
    df = pd.read_csv(SOURCE, dtype={"place_key": "string", "google_maps_id": "string"})
    required = {"place_key", "name", "latitude", "longitude"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")
    if df.place_key.isna().any() or df.place_key.duplicated().any():
        raise ValueError("Each place must have a unique, non-null place_key")
    for field in ("latitude", "longitude"):
        df[field] = pd.to_numeric(df[field], errors="coerce")
    valid = df.latitude.between(-90, 90) & df.longitude.between(-180, 180)
    df["tile"] = [tile_key(lat, lon) if ok else None
                  for lat, lon, ok in zip(df.latitude, df.longitude, valid)]
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs="EPSG:4326")


def download(key: tuple[int, int], kind: str) -> bool:
    """Download the given Overture type, atomically, into our tile cache."""
    target = tile_path(key) if kind == "division_area" else division_path(key)
    if target.exists():
        return True
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".partial.geojson")
    bbox = ",".join(f"{x:.5f}" for x in tile_bbox(key))
    command = ["overturemaps", "download", "--bbox", bbox,
               "--type", kind, "-f", "geojson", "-o", str(tmp)]
    print(f"Downloading {target.name} ({bbox})", flush=True)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not tmp.exists() or not tmp.stat().st_size:
        print(f"WARNING: {kind} download failed: {result.stderr[-400:]}", file=sys.stderr)
        tmp.unlink(missing_ok=True)
        return False
    try:
        # GeoJSON is usually a FeatureCollection; validate before caching.
        parsed = json.loads(tmp.read_text(encoding="utf-8"))
        if parsed.get("type") != "FeatureCollection":
            raise ValueError("Expected GeoJSON FeatureCollection")
    except (ValueError, UnicodeError) as exc:
        print(f"WARNING: invalid download {target.name}: {exc}", file=sys.stderr)
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(target)
    return True


def get_primary(value) -> str:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return value
    if isinstance(value, dict):
        return str(value.get("primary") or "")
    return ""


def parse_nested(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return None
    return value


def load_areas(keys: list[tuple[int, int]]) -> gpd.GeoDataFrame:
    frames = []
    for key in keys:
        if not tile_path(key).exists():
            continue
        frame = gpd.read_file(tile_path(key)).to_crs("EPSG:4326")
        if frame.empty:
            continue
        needed = {"id", "subtype", "names", "geometry"}
        if not needed.issubset(frame.columns):
            raise ValueError(f"Missing area fields in {tile_path(key)}: {needed - set(frame.columns)}")
        frame = frame[frame.subtype.isin(CANDIDATE_SUBTYPES) & frame.geometry.notna()].copy()
        frame["city_name"] = frame.names.apply(get_primary)
        cols = [x for x in ("id", "division_id", "city_name", "subtype", "country", "region", "admin_level", "geometry") if x in frame]
        frames.append(frame[cols])
    if not frames:
        return gpd.GeoDataFrame(columns=["id", "division_id", "city_name", "subtype", "geometry"],
                                geometry="geometry", crs="EPSG:4326")
    combined = pd.concat(frames, ignore_index=True)
    return gpd.GeoDataFrame(combined.drop_duplicates("id"), geometry="geometry", crs="EPSG:4326")


def load_divisions(keys: list[tuple[int, int]]) -> dict[str, dict]:
    """Index nearby Overture division point records by division ID.

    Parent division centers may lie outside downloaded bounding boxes, so
    missing ancestor records are normal and must NOT imply no parent exists.
    """
    divisions = {}
    for key in keys:
        if not division_path(key).exists():
            continue
        frame = gpd.read_file(division_path(key))
        for _, record in frame.iterrows():
            identifier = record.get("id")
            if pd.isna(identifier):
                continue
            divisions[str(identifier)] = {
                "parent_id": record.get("parent_division_id"),
                "local_type": parse_nested(record.get("local_type")),
                "hierarchies": parse_nested(record.get("hierarchies")),
                "name": get_primary(record.get("names")),
                "subtype": record.get("subtype"),
            }
    return divisions


def hierarchy_details(division_id, divisions: dict) -> tuple[str, str, str]:
    """Return parent ID, local type, and default hierarchy in readable form."""
    if pd.isna(division_id) or str(division_id) not in divisions:
        return "", "", ""  # division metadata not in the current local cache
    division = divisions[str(division_id)]
    parent = division.get("parent_id")
    parent = "" if pd.isna(parent) else str(parent or "")
    local_type = division.get("local_type")
    if isinstance(local_type, dict):
        local_type = local_type.get("en") or next(iter(local_type.values()), "")
    elif isinstance(local_type, list):
        # Overture stores local_type as language/value pairs, e.g. [["en", "city"]].
        pairs = [p for p in local_type if isinstance(p, (list, tuple)) and len(p) >= 2]
        local_type = next((p[1] for p in pairs if p[0] == "en"), pairs[0][1] if pairs else "")
    elif local_type is None:
        local_type = ""
    hierarchies = division.get("hierarchies")
    default = hierarchies[0] if isinstance(hierarchies, list) and hierarchies else []
    labels = []
    for part in default:
        if isinstance(part, dict):
            labels.append(f"{part.get('name', '')} ({part.get('subtype', '')})")
    return parent, str(local_type), " > ".join(labels)


def load_overrides() -> pd.DataFrame:
    if not OVERRIDES_OUT.exists():
        pd.DataFrame(columns=OVERRIDE_FIELDS).to_csv(OVERRIDES_OUT, index=False)
    overrides = pd.read_csv(OVERRIDES_OUT, dtype="string").fillna("")
    if not set(OVERRIDE_FIELDS).issubset(overrides.columns):
        raise ValueError(f"city_overrides.csv requires {OVERRIDE_FIELDS}")
    if overrides.place_key.duplicated().any():
        raise ValueError("Duplicate place_key in city_overrides.csv")
    return overrides


def run(max_tiles: int) -> None:
    points = load_points()
    counts = points.loc[points.tile.notna(), "tile"].value_counts()
    all_keys = list(counts.index)
    incomplete = [k for k in all_keys if not (tile_path(k).exists() and division_path(k).exists())]
    # Download hierarchies for existing cached tiles FIRST, rather than
    # extending geographic coverage before verifying the new approach.
    incomplete.sort(key=lambda k: (not tile_path(k).exists(), -int(counts[k])))
    for key in incomplete[:max_tiles]:
        if not tile_path(key).exists() and not download(key, "division_area"):
            continue
        download(key, "division")
    cached = [k for k in all_keys if tile_path(k).exists() and division_path(k).exists()]
    print(f"Complete tiles: {len(cached)} / {len(all_keys)}; {len(all_keys) - len(cached)} remain")

    points["city_status"] = "not_processed"
    points.loc[points.tile.isin(cached), "city_status"] = "no_city_candidate"
    points.loc[points.tile.isna(), "city_status"] = "missing_coordinates"
    points["overture_city_id"] = pd.NA
    points["city_name"] = pd.NA

    areas = load_areas(cached)
    divisions = load_divisions(cached)
    candidate_records = []
    hits = None
    if not areas.empty:
        available = points.loc[points.tile.isin(cached), ["place_key", "geometry"]]
        hits = gpd.sjoin(available, areas, how="inner", predicate="intersects")
        hits = hits.drop_duplicates(["place_key", "id"])
        for _, hit in hits.iterrows():
            parent, local_type, hierarchy = hierarchy_details(hit.get("division_id"), divisions)
            candidate_records.append({
                "place_key": hit.place_key,
                "overture_area_id": hit.id,
                "division_id": hit.get("division_id", ""),
                "area_name": hit.city_name,
                "subtype": hit.subtype,
                "country_alpha2": hit.get("country", ""),
                "region": hit.get("region", ""),
                "admin_level": hit.get("admin_level", ""),
                "local_type": local_type,
                "parent_division_id": parent,
                "default_hierarchy": hierarchy,
            })
    candidates = pd.DataFrame(candidate_records, columns=[
        "place_key", "overture_area_id", "division_id", "area_name", "subtype",
        "country_alpha2", "region", "admin_level", "local_type",
        "parent_division_id", "default_hierarchy",
    ])

    if not candidates.empty:
        # Choose a city-level polygon only when exactly one candidate has
        # an explicit settlement/municipality classification. Overture can
        # classify an actual city as a "region" (e.g., Taipei), while also
        # labeling its wards/villages as localities.
        by_key = candidates.groupby("place_key")
        for place_key, group in by_key:
            types = group.local_type.fillna("").astype(str).str.strip().str.casefold()
            settlement = (
                group.subtype.isin({"locality", "localadmin"})
                & types.isin({"city", "town", "municipality", "village"})
            )
            city_region = (
                group.subtype.eq("region")
                & types.isin({"city", "municipality"})
            )
            eligible = group.loc[settlement | city_region]
            if len(eligible) == 1:
                chosen = eligible.iloc[0]
                mask = points.place_key.eq(place_key)
                points.loc[mask, "city_status"] = "matched"
                points.loc[mask, "overture_city_id"] = chosen.overture_area_id
                points.loc[mask, "city_name"] = chosen.area_name
            else:
                points.loc[points.place_key.eq(place_key), "city_status"] = "review"

    overrides = load_overrides()
    selections = overrides.loc[overrides.chosen_overture_area_id.str.strip().ne("")]
    candidate_pairs = set(zip(candidates.place_key.astype(str), candidates.overture_area_id.astype(str)))
    for _, manual in selections.iterrows():
        pair = (str(manual.place_key), str(manual.chosen_overture_area_id))
        # A manual choice is accepted only when the containing area is loaded
        # and verified for that specific point; prevents stale/mistyped IDs.
        if pair not in candidate_pairs:
            print(f"WARNING: override not applied (not a containing cached polygon): {pair}", file=sys.stderr)
            continue
        chosen = candidates.loc[(candidates.place_key == pair[0]) &
                                (candidates.overture_area_id == pair[1])].iloc[0]
        mask = points.place_key.eq(pair[0])
        points.loc[mask, "city_status"] = "verified"
        points.loc[mask, "overture_city_id"] = pair[1]
        points.loc[mask, "city_name"] = chosen.area_name

    columns = ["place_key", "source_index", "name", "latitude", "longitude",
               "country", "country_iso3", "overture_city_id", "city_name", "city_status"]
    columns = [c for c in columns if c in points]
    results = pd.DataFrame(points[columns].copy())
    results.to_csv(MATCHES_OUT, index=False)
    results.loc[~results.city_status.isin(["matched", "verified"])].to_csv(REVIEW_OUT, index=False)
    candidates.to_csv(CANDIDATES_OUT, index=False)

    used_ids = set(results.overture_city_id.dropna().astype(str))
    if used_ids:
        selected_areas = areas.loc[areas.id.astype(str).isin(used_ids)].copy()
        selected_areas = selected_areas.rename(columns={"id": "overture_city_id"})
        selected_areas.to_file(BOUNDARIES_OUT, driver="GeoJSON")
    else:
        BOUNDARIES_OUT.unlink(missing_ok=True)

    print("\nCITY MATCHING")
    print(results.city_status.value_counts().to_string())
    print("Distinct selected areas:", results.overture_city_id.nunique())
    print("Candidate rows:", len(candidates))
    print("Matches:", MATCHES_OUT)
    print("Review:", REVIEW_OUT)
    print("Candidates:", CANDIDATES_OUT)
    print("Manual selections:", OVERRIDES_OUT)
    print("Boundaries:", BOUNDARIES_OUT if BOUNDARIES_OUT.exists() else "none yet")
    print("\nReview candidate hierarchy before processing further tiles.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-tiles", type=int, default=3,
                        help="Maximum additional tiles to COMPLETE (default 3)")
    args = parser.parse_args()
    if not 0 <= args.max_tiles <= 50:
        parser.error("--max-tiles must be between 0 and 50")
    run(args.max_tiles)


if __name__ == "__main__":
    main()
