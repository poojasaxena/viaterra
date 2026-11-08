# Viaterra

**A Personal Travel Atlas** · Project overview and working roadmap  
**Last updated:** 8 November 2026

Viaterra is a personal, map-centred record of travel: the places visited, the paths connecting them, and the memories that make them meaningful. Its public-facing pages are designed for exploration; editing is reserved for the owner. The application is built with Python and Streamlit, backed by Neon PostgreSQL/PostGIS.

> **Project principle:** Record a place once; reuse it everywhere. A new location saved while travelling should appear on the homepage map and become available to future journeys, memories, city views and statistics without editing CSVs or running local scripts.

## 1. Agreed page plan

Six pages are planned. **Titles and responsibilities are agreed at a planning level; the current source code still uses some earlier page names.** The homepage design is deliberately treated as largely settled.

| # | Page / header | Purpose | Status |
|---|---|---|---|
| 1 | **Viaterra** — `viaterra.svg` | Interactive world map displaying individual visited-place flags; maritime visual identity. | **Working.** Visual design to remain largely unchanged. |
| 2 | **Footprints** — `footprints.svg` | Backtrack trips by selecting existing places and arranging stops in travel order; visualize the route. Dates optional. | **Planned.** Earlier `My Journeys` page is a placeholder in the reviewed archive. |
| 3 | **Echoes** — `echoes.svg` | A home for personal recollections and meaningful locations, optionally with notes and photographs. Integrate compact place capture/management here. | **Planned.** Earlier `Places & Memories` page is a placeholder in the reviewed archive. |
| 4 | **The World in Cities** — `the_world_in_cities.svg` *(alternative: `terra_cognita.svg`)* | Second geographical view of the same visited-place data: cities highlighted/filled by boundary instead of displaying every individual flag. | **Planned.** City matching and boundary-processing groundwork exists. |
| 5 | **Travel Statistics** — `travel_statistics.svg` | Statistical views of visited countries, cities, places and geographical distribution. Time-series only when real visit dates exist. | **Planned.** Placeholder page exists. |
| 6 | **About Viaterra** — `about_viaterra.svg` | Story, purpose and philosophy of the atlas. | **Existing page.** |

**Note on city-map semantics:** Highlighting a city means at least one saved place was visited within its relevant boundary; it does **not** imply the entire municipal area was explored. City matches must be checked before coverage statistics are treated as authoritative.

The headers live in `data/assets/headers/`. Other artwork (for example, `finding_my_anchor.svg`, `the_geography_of_belonging.svg`, `a_thousand_shore_one_anchor.svg`) remains available for future editorial uses. Some filenames in the reviewed project archive predate the newer headers listed here; verify the files locally before changing the configuration.

## 2. The immediate priority: practical location capture

A separate **Capture a Place** prototype has already been installed and tested through the user interface:

1. Search by place name and choose the right geographical result.
2. Review its name, coordinates and a map preview.
3. Check for possible nearby duplicates.
4. Save the visited location directly to Neon/PostGIS.
5. Refresh the homepage; the new flag appears.

**Verified manual test:** Sydney Opera House, Australia, was saved and its flag appeared on the homepage. **It is a test record, not an actual visit; it must be removed safely by its exact database identity once a delete workflow exists.**

The prototype also offers **Use my location**, requesting browser GPS permission, but that path still needs end-to-end testing on the phone. The current name search is **search-on-submit**, not live autocomplete; the current review map does not have a draggable pin.

### Agreed product direction

- Integrate the capture functionality into **Echoes**, rather than keeping a permanent seventh navigation item.
- Make the interaction **compact, fast, phone-first and Google Maps-like**: search or GPS → choose/review → save.
- Automatically perform routine duplicate checks where feasible; make extra steps appear only when a genuine conflict or ambiguity needs review.
- Allow searching, editing and deleting existing places, with safeguards and clear feedback that includes the place name.
- Keep optional memories separate from the essential operation of saving a location; no note, date or photo should be mandatory.
- Never rely on the locally mounted dataset directory for interactive saving from Streamlit Cloud.
- Preserve owner-only write access; the atlas can remain publicly viewable.

**Next implementation milestone:** integrate and compact the working capture flow inside Echoes, implement safe record management (especially deletion of the Sydney test flag), and verify GPS on the Pixel 8. Keep the homepage visually unchanged.

## 3. Architecture

```text
Google Maps Takeout and external reference data
              │
              ▼
    Local processing / review
    country + city matching
              │
              ▼
     Neon PostgreSQL / PostGIS  ◄──── Owner-only place capture/editing
              │
              ▼
         Streamlit views
    Homepage · Footprints · Echoes
    Cities · Statistics · About
```

- **Application:** Python ≥ 3.11, Streamlit (`src/viaterra/app/`).
- **Database:** Neon PostgreSQL with PostGIS (`src/viaterra/db/`).
- **Core tables:** `countries`, `cities`, `places`, `journeys`, `journey_places`, `memories` (defined in `src/viaterra/db/schema.sql`).
- **Presentation:** current homepage map is rendered by `app/components/atlas_map.py`, invoked from `app/main.py`.
- **Homepage query:** `db/queries.py::get_visited_places()` retrieves records with valid geolocated points. Its cache TTL is 600 seconds; the capture prototype clears that cache after saving.
- **Python CLI:** `viaterra` invokes `viaterra.app.cli:main`.

The current import schema has no separate **visited-versus-wishlist** field because the original import deliberately included *visited* Google Maps locations only. Importing *Want to go* is deferred. Do not mix wishlist records into the existing homepage query without an explicit visit-status model.

The `journeys` and `journey_places` tables allow a journey title, optional start/end dates and ordered stops. The `memories` table supports notes tied to a place or journey. These are **schema capabilities**, not completed interfaces.

**Visit-date caveat:** `created_at` is a database record timestamp, **not proof of travel date**. The Google Maps export has not been verified as a source of actual visit dates. Footprints should therefore support manually ordered stops *without* requiring dates, and should never fabricate an exact historical route.

## 4. Repository organization

The reviewed project ZIP (before the Capture a Place addition) contains:

```text
viaterra/
├── pyproject.toml
├── config.toml
├── .streamlit/config.toml
├── data/
│   ├── assets/         # Headers, branding, illustrations
│   ├── gallary/        # Existing spelling in project
│   └── references/
├── src/viaterra/
│   ├── app/
│   │   ├── main.py
│   │   ├── cli.py
│   │   ├── navigation.py
│   │   ├── ui.py
│   │   ├── components/atlas_map.py
│   │   └── pages/     # Current, older page structure
│   ├── db/
│   │   ├── connection.py
│   │   ├── schema.sql
│   │   ├── queries.py
│   │   ├── repository.py
│   │   └── import_places.py
│   ├── pipeline/import_google_maps.py
│   └── processing/
│       ├── country_matching.py
│       ├── city_matching.py
│       └── paths.py
└── tests/
```

The installed prototype additionally provides:

```text
src/viaterra/app/pages/6_Capture_a_Place.py
src/viaterra/db/capture.py
src/viaterra/places/search.py
```

The current navigation names in the older archive were `The Atlas`, `My Journeys`, `Places & Memories`, `Travel Statistics` and `About Viaterra`; these need **planned, coordinated renaming**, not an assumed already-completed migration.

## 5. External dataset organization

The geographical and Google Maps datasets are maintained **outside the repository** under `$GLOBAL_DATASETS_DIR/Personal/Travel/` (a local Workbench/Datasets directory). The structure shared in November 2026 is:

```text
Personal/Travel/
├── processed/
│   ├── google_maps_visited.csv
│   ├── google_maps_visited_backup.csv
│   ├── country_review.csv
│   ├── country_overrides.csv
│   ├── city_matches.csv
│   ├── city_review.csv
│   ├── city_candidates.csv
│   ├── city_overrides.csv
│   └── city_boundaries.geojson
└── raw/
    ├── google_maps/google_maps_2026-10-31.zip
    ├── geography/
    │   ├── ne_10m_admin_0_countries.geojson
    │   └── overture/
    │       ├── tiles/
    │       ├── wismar.geojson
    │       └── wismar.geojson.state
    └── travel_history/
```

### Processing responsibilities

- **`country_matching.py`:** Uses Natural Earth country polygons to identify the country of each visited point; produces review and override files, preserving manual corrections. Writes enriched columns back to the processed visited CSV.
- **`city_matching.py`:** Uses Overture `division_area` and `division` data, cached by 0.5-degree geographic tiles, to propose/review city matches and export selected city boundaries. Deliberately conservative about city identification; it does not write to Neon or the master places CSV.
- **`.partial.geojson.state` files:** Appear to be download/checkpoint artifacts; do not delete without checking whether incomplete downloads still need them.
- **`db/import_places.py`:** Imports the country-enriched visited CSV to Neon. **Dry-run by default**, with `--apply` for writes. Its upsert may replace fields for matching source identities; avoid overwriting future user-edited fields during re-imports.

**Separation of responsibilities:** raw exports are retained, processed outputs are reviewable and reproducible, and Neon is the operational source of truth for the deployed app. Interactive captured records use a separate source marker (`source_list='viaterra_capture'`) and distinct place keys.

## 6. Visual direction

**Mediterranean Antique:** luminous Aegean blue, sun-faded turquoise, warm shell white, dusty coral, muted olive and old gold. Nautical details include the signature anchor, compasses, sea motifs and carefully chosen travel ephemera. The wave symbol 🌊 is welcome, but the app should not become visually busy.

- Homepage: refined wordmark/header and map; no further broad redesign planned.
- Map: current **individual orange visited-place flags** with a maritime frame and selected decorations.
- Interior pages: visually coordinated but more restrained; **compact functionality over ornamental cards or oversized forms**.
- Mobile usability: a first-class concern, particularly for saving places while travelling.

Main app styling and asset paths are configured in `config.toml` and `.streamlit/config.toml`. The header artwork resides in `data/assets/headers/`.

## 7. Local development and configuration

From the project root, with the intended virtual environment active:

```bash
pip install -e .
viaterra
```

For optional development tools:

```bash
pip install -e '.[dev]'
pytest
ruff check .
```

Database connection uses `VIATERRA_DATABASE_URL` from the environment or an untracked `.streamlit/secrets.toml` file. The capture prototype additionally requires `VIATERRA_EDITOR_PASSWORD` to enable owner-only saving. The GPS component requires permission and a secure browser context (HTTPS or localhost). **Never commit credentials, production database URLs, or `.env` files.**

The prototype uses Photon/OpenStreetMap for submitted place-name searches and a browser geolocation component for GPS; third-party service availability, terms and rate limits require consideration before larger-scale use. Some local processing modules depend on additional tools/libraries (for example, GeoPandas and the Overture CLI); these should be documented in their own processing setup rather than presumed installed by the minimal app dependencies.

## 8. Roadmap and open decisions

### Now — practical capture and management

- [x] Show geolocated visited-place flags on the homepage.
- [x] Search for a place, select it, check duplicates and save to PostgreSQL in the separate prototype.
- [x] Confirm the Sydney Opera House test flag appeared on the homepage.
- [ ] Integrate compact capture into **Echoes** and remove the temporary navigation item once migrated.
- [ ] Verify GPS capture end-to-end on a phone.
- [ ] Implement safe find/edit/delete; remove the Australian test record after exact identification.
- [ ] Improve search selection and reduce unnecessary steps while keeping duplicate protection.
- [ ] Confirm deployed owner authentication and privacy model before public editing use.

### Later — reflective and analytical pages

- [ ] **Footprints:** create trips, link saved places, reorder stops, draw routes; do not assume accurate visit dates or transport paths.
- [ ] **Echoes:** optional place/journey memories and photographs; decide photo storage approach before implementing uploads.
- [ ] **The World in Cities:** finish/verify city matching; show filled visited-city boundaries using the same source places as the homepage.
- [ ] **Travel Statistics:** real counts by country/city/region, geographical distribution and carefully grounded derived metrics.
- [ ] **Navigation:** consolidate to the six agreed pages and connect the new headers.

### Explicitly deferred

- Importing the Google Maps *Want to go* list or implementing wishlist semantics.
- Comprehensive historical journey reconstruction and mandatory visit-date entry.
- Major homepage visual redesign.

## 9. Decisions to preserve

1. **One saved place, many uses.** Do not duplicate place records across page-specific datasets.
2. **No mandatory journaling.** Notes, photos, trip dates and narratives are optional.
3. **No invented travel chronology.** Journey order can be curated manually; distinguish a straight-line connection from a historically verified travel route.
4. **No needless extra management page.** The tested Capture page is temporary; integrate its functions into Echoes.
5. **No automatic mass import of Overture localities.** Geographic reference tiles are not personal visited places.
6. **No secret leakage or unrestricted public writes.** Public exploration and owner-only editing are different permissions.
7. **A calm, personal atlas.** Functional pages should feel as effortless as possible, while the homepage retains Viaterra's expressive maritime identity.

---

*This README describes the reviewed source archive, the subsequently tested Capture a Place prototype, the shared external-data directory tree and the six-page plan agreed on 8 November 2026. It is a project guide, not a claim that every planned feature is implemented.*
