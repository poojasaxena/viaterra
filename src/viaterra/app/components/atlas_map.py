"""Viaterra's interactive nautical atlas (MapLibre + OpenFreeMap)."""

import json

import streamlit as st
import streamlit.components.v1 as components
import base64
from viaterra.processing.paths import load_config, require_asset
from viaterra.db.queries import get_visited_places


_MAP_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<link href="https://unpkg.com/maplibre-gl@6.16.0/dist/maplibre-gl.css" rel="stylesheet" />
<style>
/* ============================================================
   VIATERRA — MAP STYLES
   Keep all map CSS inside this <style> element.
   ============================================================ */

/* 1. Palette and basic layout */
:root {
    --sea: __SEA_COLOR__;
    --navy: #F5F0E4;
    --ivory: #F3E9D5;
    --gold: #BC985F;
}

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    height: 100%;
    background: var(--sea);
    font-family: Georgia, "Times New Roman", serif;
}

/* 2. Interactive map and its simple, stable frame */
.frame {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    border: 1px solid #B99459;
    border-radius: 4px;
}

#map {
    width: 100%;
    height: 100%;
}

/* 3. Sailing boat: decorative only, does not intercept map input */
.nautical-boat {
    position: absolute;
    left: 65%;
    bottom: 38px;
    width: clamp(120px, 14vw, 205px);
    height: auto;
    z-index: 2;
    pointer-events: none;
    opacity: 0.78;
    filter: drop-shadow(0 1px 0 rgba(18, 64, 78, 0.08));
}


/* Soft depth beneath the weathered parchment */
.frame::before {
    content: "";
    position: absolute;
    inset: 0;
    z-index: 9;
    pointer-events: none;

    box-shadow:
        inset 0 0 12px rgba(92, 64, 37, 0.16),
        inset 0 0 28px rgba(110, 78, 46, 0.10);

    background:
        radial-gradient(
            ellipse at top left,
            rgba(121, 86, 49, 0.12),
            transparent 23%
        ),
        radial-gradient(
            ellipse at bottom right,
            rgba(121, 86, 49, 0.12),
            transparent 23%
        );
}



/* Weathered parchment frame */
.frame::after {
    content: "";
    position: absolute;
    inset: -8px;
    z-index: 10;
    pointer-events: none;

    background:
        url("data:image/png;base64,__WEATHERED_FRAME__")
        center / 100% 100% no-repeat;
}

/* Decorative compass rose */
.nautical-compass {
    position: absolute;
    left: 2%;
    top: 30%;
    width: 150px;
    height: auto;
    opacity: 0.78;
    z-index: 2;
    pointer-events: none;
}


/* 4. Bottom-right legend: above MapLibre's attribution */
.legend {
    position: absolute;
    right: 14px;
    bottom: 38px;
    z-index: 2;
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 7px 10px;
    background: rgba(250, 247, 238, 0.95);
    border: 1px solid #D3C9B4;
    border-radius: 5px;
    color: #45616A;
    font: 11px system-ui, sans-serif;
    white-space: nowrap;
}

.legend svg {
    width: 18px;
    height: 18px;
    flex: none;
}

/* 5. MapLibre popup and built-in controls */
.maplibregl-popup-content {
    padding: 12px 14px;
    background: #FBF8F0;
    color: #254C60;
    border: 1px solid #C6C7B8;
    border-radius: 6px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.14);
}

.maplibregl-popup-close-button {
    font-size: 18px;
    color: #45636B;
}

.place-name {
    font: 600 14px system-ui, sans-serif;
    margin-right: 12px;
    line-height: 1.4;
}

.place-meta {
    font: 11px system-ui, sans-serif;
    letter-spacing: 0.05em;
    margin-top: 5px;
    color: #8A755D;
}

.maplibregl-ctrl-group {
    border: 1px solid #C6CBC0;
    background: #FAF8F2;
}

.maplibregl-ctrl-attrib {
    font-size: 10px !important;
}

/* 6. Visible only when the map fails to load */
.error {
    position: absolute;
    top: 45%;
    left: 8%;
    right: 8%;
    z-index: 5;
    display: none;
    padding: 20px;
    text-align: center;
    color: #613E3E;
    background: #FFF9F3;
}

/* 7. Small screens */
@media (max-width: 640px) {
    .nautical-boat {
        left: 60%;
        bottom: 34px;
        width: 100px;
        opacity: 0.68;
    }

    .legend {
        right: 8px;
        bottom: 36px;
    }
}
</style>
</head>
<body>
<!-- Map layout. The legend and boat float over the interactive map. -->
<div class="frame">
    <div id="map" role="application" aria-label="Interactive maritime atlas of individually marked visited places"></div>
  <!-- Fixed cartographic ornament: not a geographic pin or map feature. -->

<img
    class="nautical-boat"
    src="data:image/png;base64,__SAILBOAT__"
    alt=""
    aria-hidden="true"
>

<img
    class="nautical-compass"
    src="data:image/png;base64,__COMPASS__"
    alt=""
    aria-hidden="true"
>


    <!-- This marker key is intentionally positioned at bottom-right via .legend. -->
    <div class="legend">
        <svg viewBox="0 0 40 40" aria-hidden="true">
            <circle cx="20" cy="20" r="18"
                    fill="__MARKER_FILL__" stroke="__MARKER_BORDER__" stroke-width="3" />
            <path d="M15 11 V29" fill="none" stroke="__MARKER_FLAG__"
                  stroke-width="2.8" stroke-linecap="round" />
            <path d="M17.5 12 L29 15.5 L17.5 20 Z" fill="__MARKER_FLAG__" />
        </svg>
        Where I Have Wandered
    </div>
  <div id="error" class="error">The map couldn't load its base tiles. Check internet access and the browser console.</div>
</div>
<script type="module">
import * as maplibregl from 'https://unpkg.com/maplibre-gl@6.16.0/dist/maplibre-gl.mjs';

const points = __PLACES__;

const SEA_CONFIG = __SEA_SETTINGS__;

const SEA_RGB = [
    parseInt(SEA_CONFIG.color.slice(1, 3), 16),
    parseInt(SEA_CONFIG.color.slice(3, 5), 16),
    parseInt(SEA_CONFIG.color.slice(5, 7), 16),
];

const geojson = {
  type: 'FeatureCollection',
  features: points.map((p, i) => ({
    type: 'Feature', id: i,
    properties: {name: p.name, country: p.country_code || ''},
    geometry: {type: 'Point', coordinates: [p.longitude, p.latitude]}
  }))
};

const map = new maplibregl.Map({
  container: 'map',
  style: 'https://tiles.openfreemap.org/styles/liberty',
  center: [13, 17], zoom: 1.25, minZoom: 1.1, maxZoom: 17,
  renderWorldCopies: false,
  attributionControl: false
});
map.addControl(new maplibregl.NavigationControl({showCompass: false}), 'top-right');
map.addControl(new maplibregl.AttributionControl({compact: true}), 'bottom-right');

const error = document.getElementById('error');
map.on('error', e => { if (!map.isStyleLoaded() && e.error) error.style.display = 'block'; });

// Circular nautical marker: 40px SVG registered at pixelRatio 2 (20px before icon-size).
// Each location remains an independent point, without clustering.

const burgeeSvg = `<svg xmlns="http://www.w3.org/2000/svg"
    width="40" height="40" viewBox="0 0 40 40">

    <circle cx="20" cy="20" r="18"
        fill="__MARKER_FILL__"
        stroke="__MARKER_BORDER__"
        stroke-width="3"/>

    <path d="M15 11 V29"
        fill="none"
        stroke="__MARKER_FLAG__"
        stroke-width="2.8"
        stroke-linecap="round"/>

    <path d="M17.5 12 L29 15.5 L17.5 20 Z"
        fill="__MARKER_FLAG__"/>
  </svg>`;



/*
 * VIATERRA — Organic watercolor sea
 *
 * Soft pigment variation rather than repeated wave marks.
 * Uses the sea palette from config.toml.
 * Texture is seamless and repeats without hard tile edges.
 */
function createSeaTexture() {
    const size = 256;
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;

    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas 2D unavailable');

    const pixels = ctx.createImageData(size, size);

    const clamp = (v, min = 0, max = 255) =>
        Math.max(min, Math.min(max, v));

    const rgb = hex => [
        parseInt(hex.slice(1, 3), 16),
        parseInt(hex.slice(3, 5), 16),
        parseInt(hex.slice(5, 7), 16)
    ];

    const deep = rgb(SEA_CONFIG.deep_color);
    const base = rgb(SEA_CONFIG.color);
    const light = rgb(SEA_CONFIG.light_color);

    const lerp = (a, b, t) => a + (b - a) * t;
    const smooth = t => t * t * (3 - 2 * t);

    // Deterministic, tileable noise.
    function hash(x, y) {
        const n = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
        return n - Math.floor(n);
    }

    function noise(x, y, fx, fy) {
        const px = x * fx / size;
        const py = y * fy / size;

        const ix = Math.floor(px);
        const iy = Math.floor(py);

        const sx = smooth(px - ix);
        const sy = smooth(py - iy);

        const sample = (dx, dy) => {
            const nx = ((ix + dx) % fx + fx) % fx;
            const ny = ((iy + dy) % fy + fy);
            return hash(nx, ny);
        };

        const top = lerp(sample(0, 0), sample(1, 0), sx);
        const bottom = lerp(sample(0, 1), sample(1, 1), sx);

        return lerp(top, bottom, sy);
    }

    for (let y = 0; y < size; y++) {
        for (let x = 0; x < size; x++) {

            // Gently distort the pigment shapes so they
            // don't resemble a regular geometric pattern.
            const warp = (
                noise(x, y, 2, 2) - 0.5
            ) * 28;

            // Broad watercolor washes at multiple scales.
            const broad =
                (noise(x + warp, y, 3, 3) - 0.5) * 0.70 +
                (noise(x, y + warp, 7, 5) - 0.5) * 0.30;

            // Very fine irregular pigment variation.
            const fine =
                noise(x, y, 17, 13) - 0.5;

            // Color variation: no bright repeated glints.

            const tone = clamp(
                0.5 +
                broad * SEA_CONFIG.broad_strength / 7 +
                fine * SEA_CONFIG.ripple_strength / 100,
                0,
                1
            );


            const from = tone < 0.5 ? deep : base;
            const to = tone < 0.5 ? base : light;

            const blend = tone < 0.5
                ? tone * 2
                : (tone - 0.5) * 2;

            const i = (y * size + x) * 4;

            for (let channel = 0; channel < 3; channel++) {
                pixels.data[i + channel] = Math.round(
                    lerp(from[channel], to[channel], blend)
                );
            }

            pixels.data[i + 3] = 255;
        }
    }

    return pixels;
}


// Overlay paints suppress the stock physical-atlas textures and draw our sea
// and land as calm, solid nautical colors. Keep only restrained geographic labels.
function applyMaritimeStyle() {
  for (const layer of map.getStyle().layers || []) {
    const id = (layer.id || '').toLowerCase();
    const src = (layer['source-layer'] || '').toLowerCase();
    try {
      if (layer.type === 'background') {
        map.setPaintProperty(layer.id, 'background-color', '#F3E9D5');

        if (map.hasImage('viaterra-land-wash')) {
            map.setPaintProperty(
                layer.id,
                'background-pattern',
                'viaterra-land-wash'
            );
        }

      } else if (layer.type === 'hillshade' || layer.type === 'raster' || layer.type === 'color-relief' || layer.type === 'fill-extrusion') {
        map.setLayoutProperty(layer.id, 'visibility', 'none');
      } else if (layer.type === 'fill') {
        if (id.includes('water') || src === 'water') {
          map.setPaintProperty(layer.id, 'fill-color', SEA_CONFIG.color);
          if (map.hasImage('viaterra-sea-texture')) {
            map.setPaintProperty(layer.id, 'fill-pattern', 'viaterra-sea-texture');
          }
          map.setPaintProperty(layer.id, 'fill-opacity', 1);
        } else {
          // Eliminate landcover, park, woodland and other textured shading.
          map.setPaintProperty(layer.id, 'fill-color', '#F3E9D5');
          if (map.hasImage('viaterra-land-wash')) {
            map.setPaintProperty(
                layer.id,
                'fill-pattern',
                'viaterra-land-wash'
            );
        }
          map.setPaintProperty(layer.id, 'fill-opacity', 1);
        }
      } else if (layer.type === 'line') {
        if (id.includes('water') || src.includes('water')) {
          map.setPaintProperty(layer.id, 'line-color', SEA_CONFIG.color);
        } else if (/boundary|admin|border|coast/.test(id)) {
          map.setPaintProperty(layer.id, 'line-color', '#BCA788');
          map.setPaintProperty(layer.id, 'line-opacity', 0.65);
        } else if (/road|street|highway|rail|bridge|tunnel/.test(id)) {
          map.setLayoutProperty(layer.id, 'visibility', 'none');
        } else {
          map.setPaintProperty(layer.id, 'line-color', '#D4C4AA');
          map.setPaintProperty(layer.id, 'line-opacity', 0.4);
        }
      } else if (layer.type === 'symbol') {
        // Keep country and settlement labels, but not POIs, transit, roads or
        // numerous sea labels. The visited-place flags must remain the focus.
        const geographic = /country|state|city|town|village|settlement/.test(id);
        if (!geographic) {
          map.setLayoutProperty(layer.id, 'visibility', 'none');
        } else {
          map.setPaintProperty(layer.id, 'text-color', '#365E67');
          map.setPaintProperty(layer.id, 'text-halo-color', '#F3E9D5');
          map.setPaintProperty(layer.id, 'text-halo-width', 1);
        }
      }
    } catch (e) { /* Tolerate style-specific layer differences. */ }
  }
}

/* Warm, softly mottled watercolor wash for the land */
function createLandTexture() {
    const size = 256;
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;

    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas 2D unavailable');

    const image = ctx.createImageData(size, size);
    const clamp = v => Math.max(0, Math.min(255, Math.round(v)));

    // Repeatable noise with matching edges, so the wash tiles.
    function hash(x, y) {
        const n = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
        return n - Math.floor(n);
    }

    function noise(x, y, frequency) {
        const px = x * frequency / size;
        const py = y * frequency / size;

        const ix = Math.floor(px);
        const iy = Math.floor(py);

        const fx = px - ix;
        const fy = py - iy;

        const sx = fx * fx * (3 - 2 * fx);
        const sy = fy * fy * (3 - 2 * fy);

        const sample = (dx, dy) => hash(
            (ix + dx) % frequency,
            (iy + dy) % frequency
        );

        const top = sample(0, 0) * (1 - sx) + sample(1, 0) * sx;
        const bottom = sample(0, 1) * (1 - sx) + sample(1, 1) * sx;

        return top * (1 - sy) + bottom * sy;
    }

    for (let y = 0; y < size; y++) {
        for (let x = 0; x < size; x++) {

            // Broad pigment clouds, fine washes, paper grain.
            const wash =
                (noise(x, y, 4) - 0.5) * 36 +
                (noise(x, y, 11) - 0.5) * 20 +
                (noise(x, y, 27) - 0.5) * 8;

            const grain = (hash(x + 73, y + 19) - 0.5) * 9;
            const i = (y * size + x) * 4;

            image.data[i]     = clamp(243 + wash * 0.7 + grain);
            image.data[i + 1] = clamp(233 + wash * 0.95 + grain);
            image.data[i + 2] = clamp(213 + wash * 1.1 + grain);
            image.data[i + 3] = 255;
        }
    }

    return image;
}


function addBurgeeLayer(image) {
  map.addImage('viaterra-burgee', image, {pixelRatio: 2});
  // No clustering: each saved position remains its own feature.
  map.addSource('visited-places', {type: 'geojson', data: geojson, cluster: false});
  map.addLayer({
    id: 'burgee-pins', type: 'symbol', source: 'visited-places',
    layout: {
      'icon-image': 'viaterra-burgee',
      'icon-size': ['interpolate', ['linear'], ['zoom'], 1, 0.85, 5, 0.95, 10, 1.1, 15, 1.2],
      'icon-anchor': 'center',
      'icon-allow-overlap': true,
      'icon-ignore-placement': true,
      'icon-rotation-alignment': 'viewport',
      'icon-pitch-alignment': 'viewport'
    }
  });
  map.on('click', 'burgee-pins', e => {
    if (!e.features?.length) return;
    const f = e.features[0];
    const popup = document.createElement('div');
    const name = document.createElement('div');
    name.className = 'place-name';
    name.textContent = f.properties.name || 'Visited place';
    popup.appendChild(name);
    if (f.properties.country) {
      const meta = document.createElement('div');
      meta.className = 'place-meta';
      meta.textContent = f.properties.country;
      popup.appendChild(meta);
    }
    new maplibregl.Popup({offset: 13, maxWidth: '260px'})
      .setLngLat(f.geometry.coordinates).setDOMContent(popup).addTo(map);
  });
  map.on('mouseenter', 'burgee-pins', () => {map.getCanvas().style.cursor = 'pointer';});
  map.on('mouseleave', 'burgee-pins', () => {map.getCanvas().style.cursor = '';});
}

map.on('load', () => {
    error.style.display = 'none';

    // -------------------------------------------------
    // 1. Register the sea texture
    // -------------------------------------------------
    try {
        map.addImage(
            'viaterra-sea-texture',
            createSeaTexture(),
            { pixelRatio: 1 }
        );
    } catch (e) {
        console.warn(
            'Sea texture unavailable; retaining flat sea color.',
            e
        );
    }

    // -------------------------------------------------
    // 2. Register the watercolor land texture
    // -------------------------------------------------
    try {
        map.addImage(
            'viaterra-land-wash',
            createLandTexture(),
            { pixelRatio: 1 }
        );
    } catch (e) {
        console.warn(
            'Land watercolor texture unavailable; retaining flat land color.',
            e
        );
    }

    // -------------------------------------------------
    // 3. Apply maritime styling
    // Both textures must be registered first.
    // -------------------------------------------------
    applyMaritimeStyle();

    // -------------------------------------------------
    // 4. Load and display visited-place markers
    // -------------------------------------------------
    const image = new Image();

    image.onload = () => {
        addBurgeeLayer(image);
    };

    image.onerror = () => {
        error.textContent = 'The map marker could not be loaded.';
        error.style.display = 'block';
    };

    image.src =
        'data:image/svg+xml;charset=utf-8,'
        + encodeURIComponent(burgeeSvg);
});
</script>
</body>
</html>
"""

def render_atlas_map() -> None:
    """Render the nautical atlas using centralized configuration."""

    # Application configuration
    config = load_config()
    map_config = config.get("map", {})
    sea_config = map_config.get("sea", {})

    marker_config = map_config.get("markers", {})

    marker_settings = {
        "fill": marker_config.get("fill", "#A67C43"),
        "border": marker_config.get("border", "#FFFCF5"),
        "flag": marker_config.get("flag", "#FFFFFF"),
    }
    map_height = int(map_config.get("height", 560))

    sea_settings = {
        "color": sea_config.get("color", "#69C7C8"),
        "deep_color": sea_config.get("deep_color", "#4FAEB4"),
        "light_color": sea_config.get("light_color", "#9EDDD8"),
        "broad_strength": sea_config.get("broad_strength", 22.0),
        "ripple_strength": sea_config.get("ripple_strength", 3.0),
        "glint_red": sea_config.get("glint_red", 3.0),
        "glint_green_blue": sea_config.get("glint_green_blue", 4.0),
    }

    # Load visited locations
    try:
        places = get_visited_places()
    except Exception:
        st.error(
            "Viaterra couldn't load visited places from Neon. "
            "Check the database connection."
        )
        return

    if not places:
        st.info("No geolocated places are available in Neon yet.")
        return

    # Prepare location data
    safe_json = json.dumps(
        places,
        ensure_ascii=True,
        separators=(",", ":"),
    )

    safe_json = (
        safe_json
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


    # -------------------------------------------------
    # Decorative illustrations — configured in TOML
    # -------------------------------------------------

    def encode_image(*keys: str) -> str:
        path = require_asset(*keys)
        return base64.b64encode(path.read_bytes()).decode("ascii")

    boat_base64 = encode_image(
        "illustrations", "sailboat_vintage"
    )

    compass_base64 = encode_image(
        "illustrations", "compass"
    )

    frame_base64 = encode_image(
        "illustrations", "weathered_frame"
    )

    # Inject data and configuration into the map template
    html = _MAP_HTML

    html = html.replace("__COMPASS__", compass_base64)
    html = html.replace("__PLACES__", safe_json)
    html = html.replace("__SEA_SETTINGS__", json.dumps(sea_settings), )
    html = html.replace("__SEA_COLOR__", sea_settings["color"],)
    html = html.replace("__SAILBOAT__", boat_base64,)
    html = html.replace("__MARKER_SETTINGS__", json.dumps(marker_settings),)
    html = html.replace("__MARKER_FILL__", marker_settings["fill"])
    html = html.replace("__MARKER_BORDER__", marker_settings["border"])
    html = html.replace("__MARKER_FLAG__", marker_settings["flag"])
    html = html.replace("__WEATHERED_FRAME__", frame_base64)

    # Render the map
    components.html(
        html,
        height=map_height,
        scrolling=False,
    )
