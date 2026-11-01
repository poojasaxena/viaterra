
"""Identify countries for Viaterra places, preserving manual corrections."""

import hashlib
import os
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DATA_ROOT = (
    Path(os.environ["GLOBAL_DATASETS_DIR"]).expanduser().resolve()
    / "Personal"
    / "Travel"
)

PROCESSED = DATA_ROOT / "processed"
SOURCE = PROCESSED / "google_maps_visited.csv"
REVIEW = PROCESSED / "country_review.csv"
OVERRIDES = PROCESSED / "country_overrides.csv"

BOUNDARIES = (
    DATA_ROOT / "raw/geography/ne_10m_admin_0_countries.geojson"
)

BOUNDARIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/"
    "natural-earth-vector/master/geojson/"
    "ne_10m_admin_0_countries.geojson"
)

COUNTRY_CONVENTIONS = {
    "Western Sahara": ("Morocco", "MAR"),
    "Somaliland": ("Somalia", "SOM"),
    "Kosovo": ("Kosovo", "XKX"),
}

OVERRIDE_COLUMNS = [
    "place_key",
    "name",
    "suggested_country",
    "suggested_iso3",
    "distance_km_approx",
    "manual_country",
    "manual_iso3",
    "comment",
]

GENERATED_COLUMNS = [
    "place_key",
    "country",
    "country_iso3",
    "country_status",
    "country_method",
    "nearest_country",
    "nearest_iso3",
    "distance_km_approx",
]


# --------------------------------------------------
# Source identity
# --------------------------------------------------


def make_place_key(row: pd.Series) -> str:
    """Create a stable key independent of CSV row ordering."""

    place_id = row.get("google_maps_id")
    url = row.get("google_maps_url")

    place_id = str(place_id).strip() if pd.notna(place_id) else ""
    url = str(url).strip() if pd.notna(url) else ""

    if place_id:
        identity = f"id:{place_id}"

    elif url:
        identity = f"url:{url}"

    elif pd.notna(row["latitude"]) and pd.notna(row["longitude"]):
        identity = (
            f"coordinate:{row['latitude']:.8f},"
            f"{row['longitude']:.8f}"
        )

    else:
        identity = (
            f"missing:{row['source_index']}:{row['name']}"
        )

    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return digest[:24]



# --------------------------------------------------
# Load data
# --------------------------------------------------

def load_places() -> pd.DataFrame:
    """Load places and discard previously generated country fields."""

    df = pd.read_csv(
        SOURCE,
        dtype={
            "google_maps_id": "string",
            "google_maps_url": "string",
        },
    )

    required = {"source_index", "name", "latitude", "longitude"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if df["source_index"].isna().any():
        raise ValueError("Missing source_index")

    if df["source_index"].duplicated().any():
        raise ValueError("Duplicate source_index")

    df["latitude"] = pd.to_numeric(
        df["latitude"], errors="coerce"
    )
    df["longitude"] = pd.to_numeric(
        df["longitude"], errors="coerce"
    )

    df = df.drop(columns=GENERATED_COLUMNS, errors="ignore")

    df["place_key"] = df.apply(make_place_key, axis=1)

    if df["place_key"].duplicated().any():
        duplicates = df.loc[
            df["place_key"].duplicated(keep=False),
            ["source_index", "name", "place_key"],
        ]
        raise ValueError(
            f"Duplicate place identities:\n{duplicates.to_string(index=False)}"
        )

    return df


def load_countries() -> gpd.GeoDataFrame:
    """Download Natural Earth boundaries once, then use cached data."""

    BOUNDARIES.parent.mkdir(parents=True, exist_ok=True)

    if not BOUNDARIES.exists():
        response = requests.get(BOUNDARIES_URL, timeout=120)
        response.raise_for_status()
        BOUNDARIES.write_bytes(response.content)

    countries = gpd.read_file(BOUNDARIES).to_crs("EPSG:4326")

    required = {"ADMIN", "ADM0_A3", "geometry"}
    if not required.issubset(countries.columns):
        raise ValueError("Unexpected Natural Earth column structure")

    return countries[
        ["ADMIN", "ADM0_A3", "geometry"]
    ].rename(columns={
        "ADMIN": "country",
        "ADM0_A3": "country_iso3",
    })


def normalize_country(name, iso3):
    """Apply Viaterra's country naming conventions."""

    if pd.isna(name):
        return pd.NA, pd.NA

    if name in COUNTRY_CONVENTIONS:
        return COUNTRY_CONVENTIONS[name]

    return name, iso3


# --------------------------------------------------
# Automatic polygon matching
# --------------------------------------------------

def match_polygons(df, countries):
    """Assign countries only when a point has one polygon match."""

    valid = (
        df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
    )

    points = gpd.GeoDataFrame(
        df.loc[valid].copy(),
        geometry=gpd.points_from_xy(
            df.loc[valid, "longitude"],
            df.loc[valid, "latitude"],
        ),
        crs="EPSG:4326",
    )

    matches = gpd.sjoin(
        points[["place_key", "geometry"]],
        countries,
        how="left",
        predicate="intersects",
    )

    counts = matches.groupby("place_key")["country"].count()

    unique_keys = counts[counts == 1].index
    ambiguous_keys = counts[counts > 1].index

    matched = (
        matches[matches["place_key"].isin(unique_keys)]
        .drop_duplicates("place_key")
        .set_index("place_key")
    )

    df["country"] = df["place_key"].map(matched["country"])
    df["country_iso3"] = df["place_key"].map(
        matched["country_iso3"]
    )

    df["country_status"] = "proposed"
    df["country_method"] = "nearest"

    df.loc[df["country"].notna(), "country_status"] = "matched"
    df.loc[df["country"].notna(), "country_method"] = "polygon"

    df.loc[
        df["place_key"].isin(ambiguous_keys),
        ["country_status", "country_method"],
    ] = ["unresolved", ""]

    df.loc[
        ~valid,
        ["country_status", "country_method"],
    ] = ["unresolved", ""]

    for original, (name, iso3) in COUNTRY_CONVENTIONS.items():
        mask = df["country"] == original
        df.loc[mask, "country"] = name
        df.loc[mask, "country_iso3"] = iso3

    return df, points


# --------------------------------------------------
# Nearest-country suggestions
# --------------------------------------------------

def add_nearest_candidates(df, points, countries):
    """Suggest a nearby country without automatically assigning it."""

    df["nearest_country"] = pd.NA
    df["nearest_iso3"] = pd.NA
    df["distance_km_approx"] = float("nan")

    proposed = points[
        points["place_key"].isin(
            df.loc[
                df["country_status"] == "proposed",
                "place_key",
            ]
        )
    ]

    if proposed.empty:
        return df

    nearest = gpd.sjoin_nearest(
        proposed[["place_key", "geometry"]].to_crs("EPSG:3857"),
        countries.to_crs("EPSG:3857"),
        how="left",
        distance_col="distance_m",
    )

    # Equal-distance candidates in different countries
    # should not be silently resolved by arbitrary row order.
    distinct = nearest.groupby("place_key")["country_iso3"].nunique()
    tied_keys = set(distinct[distinct > 1].index)

    nearest = (
        nearest.sort_values(
            ["place_key", "distance_m", "country"]
        )
        .drop_duplicates("place_key")
        .set_index("place_key")
    )

    names = {}
    codes = {}

    for key, row in nearest.iterrows():
        if key in tied_keys:
            continue

        name, iso3 = normalize_country(
            row["country"],
            row["country_iso3"],
        )

        names[key] = name
        codes[key] = iso3

    df["nearest_country"] = df["place_key"].map(names)
    df["nearest_iso3"] = df["place_key"].map(codes)
    df["distance_km_approx"] = (
        df["place_key"].map(nearest["distance_m"]) / 1000
    )

    if tied_keys:
        mask = df["place_key"].isin(tied_keys)
        df.loc[mask, "country_status"] = "unresolved"
        df.loc[mask, "country_method"] = ""
        df.loc[mask, "distance_km_approx"] = float("nan")

    return df


# --------------------------------------------------
# Persistent manual corrections
# --------------------------------------------------

def update_override_template(df):
    """Create or extend the corrections sheet; never erase edits."""

    candidates = df[
        df["country_status"].isin(["proposed", "unresolved"])
    ]

    if OVERRIDES.exists():
        overrides = pd.read_csv(
            OVERRIDES,
            dtype="string",
            keep_default_na=False,
        )

        if not set(OVERRIDE_COLUMNS).issubset(overrides.columns):
            raise ValueError(
                "Existing country_overrides.csv has missing columns"
            )

        if overrides["place_key"].duplicated().any():
            raise ValueError("Duplicate place_key in overrides file")

        overrides = overrides[OVERRIDE_COLUMNS].copy()

    else:
        overrides = pd.DataFrame(columns=OVERRIDE_COLUMNS)

    existing = set(overrides["place_key"])

    new_rows = []

    for _, row in candidates.iterrows():
        if row["place_key"] in existing:
            continue

        new_rows.append({
            "place_key": row["place_key"],
            "name": row["name"],
            "suggested_country": (
                row["nearest_country"]
                if pd.notna(row["nearest_country"]) else ""
            ),
            "suggested_iso3": (
                row["nearest_iso3"]
                if pd.notna(row["nearest_iso3"]) else ""
            ),
            "distance_km_approx": (
                round(row["distance_km_approx"], 3)
                if pd.notna(row["distance_km_approx"]) else ""
            ),
            "manual_country": "",
            "manual_iso3": "",
            "comment": "",
        })

    if new_rows:
        overrides = pd.concat(
            [overrides, pd.DataFrame(new_rows)],
            ignore_index=True,
        )

    # Existing rows, including manual edits, are unchanged.
    if not OVERRIDES.exists() or new_rows:
        overrides.to_csv(OVERRIDES, index=False)

    return overrides


def apply_manual_overrides(df, overrides):
    """Apply only complete, explicitly entered manual corrections."""

    changes = {}

    for _, row in overrides.iterrows():
        country = row["manual_country"].strip()
        iso3 = row["manual_iso3"].strip().upper()

        if not country and not iso3:
            continue

        if not country or not re.fullmatch(r"[A-Z]{3}", iso3):
            raise ValueError(
                f"Incomplete or invalid override for {row['name']}: "
                "provide a country name and a three-letter code"
            )

        changes[row["place_key"]] = (country, iso3)

    for key, (country, iso3) in changes.items():
        mask = df["place_key"] == key

        if not mask.any():
            continue

        df.loc[mask, "country"] = country
        df.loc[mask, "country_iso3"] = iso3
        df.loc[mask, "country_status"] = "verified"
        df.loc[mask, "country_method"] = "manual"

    return df


# --------------------------------------------------
# Save and summarize
# --------------------------------------------------

def main():
    """Run the reproducible country identification workflow."""

    countries = load_countries()
    df = load_places()

    df, points = match_polygons(df, countries)
    df = add_nearest_candidates(df, points, countries)

    overrides = update_override_template(df)
    df = apply_manual_overrides(df, overrides)

    review = df[
        df["country_status"].isin(["proposed", "unresolved"])
    ].copy()

    review = review.sort_values(
        ["distance_km_approx", "name"],
        na_position="last",
    )

    PROCESSED.mkdir(parents=True, exist_ok=True)

    df.to_csv(SOURCE, index=False, float_format="%.8f")
    review.to_csv(REVIEW, index=False, float_format="%.3f")

    print("\nVIATERRA — COUNTRY IDENTIFICATION")
    print("-" * 50)

    print("Total places:", len(df))

    for status in ("matched", "proposed", "verified", "unresolved"):
        count = (df["country_status"] == status).sum()
        print(f"{status.capitalize()}: {count}")

    print("Countries assigned:", df["country_iso3"].nunique())

    print("\nTOP 20 COUNTRIES")
    print("-" * 50)
    print(df["country"].value_counts().head(20).to_string())

    print("\nFILES")
    print("-" * 50)
    print("Enriched:", SOURCE)
    print("Review:", REVIEW)
    print("Manual corrections:", OVERRIDES)


if __name__ == "__main__":
    main()
