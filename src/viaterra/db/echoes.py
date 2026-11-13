"""Queries for the visited places and personal notes in Echoes."""

from viaterra.db.connection import connect


def get_echoes_places() -> list[dict]:
    """Load each map flag with its persistent database key."""
    with connect() as conn:
        rows = conn.execute("""
            SELECT place_key, name, latitude, longitude, country_code
            FROM places
            WHERE latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180
            ORDER BY place_key
        """).fetchall()
    return [
        dict(place_key=key, name=name, latitude=lat, longitude=lon, country_code=country)
        for key, name, lat, lon, country in rows
    ]


def get_place_memories(place_key: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("""
            SELECT memory_id, title, story
            FROM memories
            WHERE place_key = %s AND journey_id IS NULL
            ORDER BY created_at DESC, memory_id DESC
        """, (place_key,)).fetchall()
    return [
        dict(id=str(memory_id), title=title, story=story or "")
        for memory_id, title, story in rows
    ]


def save_place_memory(
    place_key: str, title: str, story: str, memory_id: int | None = None,
) -> None:
    """Insert a note or update an existing note belonging to this place."""
    with connect() as conn:
        if memory_id is None:
            conn.execute("""
                INSERT INTO memories (place_key, title, story)
                VALUES (%s, %s, %s)
            """, (place_key, title, story))
        else:
            updated = conn.execute("""
                UPDATE memories SET title = %s, story = %s
                WHERE memory_id = %s AND place_key = %s AND journey_id IS NULL
                RETURNING memory_id
            """, (title, story, memory_id, place_key)).fetchone()
            if updated is None:
                raise ValueError("This memory is no longer available for this place.")
