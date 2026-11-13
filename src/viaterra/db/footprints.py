"""Store ordered journeys using the existing Viaterra places."""

from viaterra.db.connection import connect


def list_journeys() -> dict[int, str]:
    with connect() as conn:
        return dict(conn.execute("""
            SELECT journey_id, title FROM journeys ORDER BY created_at DESC, journey_id DESC
        """).fetchall())


def journey_stops(journey_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("""
            SELECT p.place_key, p.name, p.latitude, p.longitude, p.country_code
            FROM journey_places jp
            JOIN places p ON p.place_key = jp.place_key
            WHERE jp.journey_id = %s
            ORDER BY jp.visit_order NULLS LAST, jp.place_key
        """, (journey_id,)).fetchall()
    return [dict(place_key=key, name=name, latitude=lat, longitude=lon, country_code=code)
            for key, name, lat, lon, code in rows]


def available_stops() -> dict[str, dict]:
    with connect() as conn:
        rows = conn.execute("""
            SELECT p.place_key, p.name, p.latitude, p.longitude, p.country_code,
                   c.name, city.name
            FROM places p
            LEFT JOIN countries c ON c.code = p.country_code
            LEFT JOIN cities city ON city.city_id = p.city_id
            WHERE p.latitude BETWEEN -90 AND 90 AND p.longitude BETWEEN -180 AND 180
            ORDER BY p.name, p.place_key
        """).fetchall()
    return {
        key: dict(place_key=key, name=name, latitude=lat, longitude=lon,
                  country_code=code, country=country, city=city)
        for key, name, lat, lon, code, country, city in rows
    }


def save_journey(title: str, keys: list[str], journey_id: int | None = None) -> int:
    title = title.strip()
    if not title or not keys or len(keys) != len(set(keys)):
        raise ValueError("Enter a title and add at least one distinct saved place.")

    with connect() as conn:
        if journey_id is None:
            journey_id = conn.execute(
                "INSERT INTO journeys (title) VALUES (%s) RETURNING journey_id", (title,)
            ).fetchone()[0]
        else:
            updated = conn.execute(
                "UPDATE journeys SET title = %s WHERE journey_id = %s RETURNING journey_id",
                (title, journey_id),
            ).fetchone()
            if updated is None:
                raise ValueError("This journey is no longer available.")
            conn.execute("DELETE FROM journey_places WHERE journey_id = %s", (journey_id,))

        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO journey_places (journey_id, place_key, visit_order) VALUES (%s, %s, %s)",
                [(journey_id, key, order) for order, key in enumerate(keys, start=1)],
            )
    return journey_id
