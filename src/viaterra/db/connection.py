"""Neon connection and schema initialization for Viaterra only."""

import argparse
import os
import tomllib
from pathlib import Path

import psycopg


def connect():
    """Connect to Viaterra's Neon PostgreSQL database."""

    url = os.environ.get("VIATERRA_DATABASE_URL")

    if not url:
        project_root = Path(__file__).resolve().parents[3]
        secrets_file = project_root / ".streamlit" / "secrets.toml"

        if secrets_file.exists():
            with secrets_file.open("rb") as f:
                secrets = tomllib.load(f)

            url = secrets.get("VIATERRA_DATABASE_URL")

    if not url:
        raise RuntimeError(
            "VIATERRA_DATABASE_URL not found in environment "
            "or .streamlit/secrets.toml"
        )

    return psycopg.connect(url, connect_timeout=15)


def init_schema():
    sql = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with connect() as conn:
        conn.execute(sql)
        count = conn.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' "
            "AND table_name IN ('countries', 'cities', 'places', 'journeys', 'journey_places', 'memories')"
        ).fetchone()[0]
    print(f"Viaterra schema initialized: {count}/6 core tables found.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init", action="store_true", help="Create schema (idempotent)")
    args = parser.parse_args()
    if args.init:
        init_schema()
    else:
        with connect() as conn:
            row = conn.execute("SELECT current_database(), PostGIS_Version()").fetchone()
            print(f"Connected to {row[0]} (PostGIS {row[1]})")


if __name__ == "__main__":
    main()
