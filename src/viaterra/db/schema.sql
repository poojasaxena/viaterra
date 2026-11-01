-- Viaterra v1: additive schema, no DROP statements.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS countries (
    code VARCHAR(3) PRIMARY KEY,
    name TEXT NOT NULL,
    code_source TEXT NOT NULL DEFAULT 'natural_earth',
    visited_override BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cities (
    city_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    country_code VARCHAR(3) REFERENCES countries(code),
    name TEXT NOT NULL,
    center geometry(Point, 4326),
    boundary geometry(MultiPolygon, 4326),
    visited_override BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS cities_boundary_gix ON cities USING GIST(boundary);
CREATE INDEX IF NOT EXISTS cities_center_gix ON cities USING GIST(center);
CREATE INDEX IF NOT EXISTS cities_country_idx ON cities(country_code);

CREATE TABLE IF NOT EXISTS places (
    place_key VARCHAR(24) PRIMARY KEY,
    name TEXT NOT NULL,
    source_index INTEGER,
    source_list TEXT,
    google_maps_id TEXT,
    google_maps_url TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location geometry(Point, 4326),
    country_code VARCHAR(3) REFERENCES countries(code),
    city_id BIGINT REFERENCES cities(city_id),
    country_status TEXT NOT NULL CHECK (country_status IN ('matched','proposed','verified','unresolved')),
    country_method TEXT,
    nearest_country TEXT,
    nearest_iso3 TEXT,
    distance_km_approx DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT valid_coordinates CHECK (
        (latitude IS NULL AND longitude IS NULL AND location IS NULL)
        OR (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180 AND location IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS places_location_gix ON places USING GIST(location);
CREATE INDEX IF NOT EXISTS places_country_idx ON places(country_code);
CREATE INDEX IF NOT EXISTS places_city_idx ON places(city_id);

CREATE TABLE IF NOT EXISTS journeys (
    journey_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT valid_journey_dates CHECK (
        start_date IS NULL OR end_date IS NULL OR start_date <= end_date
    )
);

CREATE TABLE IF NOT EXISTS journey_places (
    journey_id BIGINT NOT NULL REFERENCES journeys(journey_id) ON DELETE CASCADE,
    place_key VARCHAR(24) NOT NULL REFERENCES places(place_key),
    visit_order INTEGER,
    PRIMARY KEY (journey_id, place_key)
);
CREATE INDEX IF NOT EXISTS journey_places_place_idx ON journey_places(place_key);

CREATE TABLE IF NOT EXISTS memories (
    memory_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    place_key VARCHAR(24) REFERENCES places(place_key),
    journey_id BIGINT REFERENCES journeys(journey_id),
    title TEXT NOT NULL,
    story TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT memory_has_subject CHECK (place_key IS NOT NULL OR journey_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS memories_place_idx ON memories(place_key);
CREATE INDEX IF NOT EXISTS memories_journey_idx ON memories(journey_id);

-- Pins imply a visit; explicit overrides can correct or supplement that inference.
CREATE OR REPLACE VIEW country_visit_status AS
SELECT c.code, c.name,
       COALESCE(c.visited_override, EXISTS (
           SELECT 1 FROM places p WHERE p.country_code = c.code
       )) AS visited,
       (SELECT count(*) FROM places p WHERE p.country_code = c.code) AS pin_count
FROM countries c;
