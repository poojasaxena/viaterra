"""Viaterra's interactive nautical atlas (MapLibre + OpenFreeMap)."""

import json

import streamlit as st
import streamlit.components.v1 as components

from viaterra.db.queries import get_visited_places


_MAP_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<link href="https://unpkg.com/maplibre-gl@6.16.0/dist/maplibre-gl.css" rel="stylesheet" />
<style>

  :root { --sea:#67C7D8; --navy:#214D5B; --ivory:#F5F0E4; --gold:#BC985F; }
  * { box-sizing:border-box; }
  html,body { margin:0;height:100%;background:var(--sea);font-family:Georgia,'Times New Roman',serif; }
  

/* Stable, restrained frame. Decorative ornaments can be added later. */
.frame {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    border: 1px solid #B99459;
    border-radius: 4px;
}



  /* Decorative chart engraving; never intercepts map clicks or gestures. */
  .nautical-boat {
    position: absolute;
    left: 65%;
    bottom: 38px;
    width: clamp(120px, 14vw, 205px);
    height: auto;
    z-index: 2;
    pointer-events: none;
    opacity: .78;
    filter: drop-shadow(0 1px 0 rgba(18,64,78,.08));
  }
  @media (max-width: 640px) {
    .nautical-boat { width: 100px; left: 60%; bottom: 34px; opacity: .68; }
  }
  #map {height:100%;width:100%;}
  .titleplate {position:absolute;top:18px;left:18px;z-index:2;padding:10px 15px;background:rgba(250,247,238,.94);border:1px solid #CBC4B0;border-radius:5px;pointer-events:none;box-shadow:0 1px 6px rgba(21,62,70,.08);}
  .eyebrow {font:10px system-ui,sans-serif;letter-spacing:2.2px;color:#97734B;margin-bottom:5px;}
  .titleplate strong {font-size:20px;color:var(--navy);font-weight:500;}
  .legend {position:absolute;bottom:14px;left:14px;z-index:2;display:flex;align-items:center;gap:7px;background:rgba(250,247,238,.95);border:1px solid #D3C9B4;border-radius:5px;padding:7px 10px;color:#45616A;font:11px system-ui,sans-serif;}
  .legend svg {width:18px;height:18px;flex:none;}
  .maplibregl-popup-content {padding:12px 14px;background:#FBF8F0;color:#254C60;border:1px solid #C6C7B8;border-radius:6px;box-shadow:0 4px 16px rgba(0,0,0,.14);}
  .maplibregl-popup-close-button {font-size:18px;color:#45636B;}
  .place-name {font:600 14px system-ui,sans-serif;margin-right:12px;line-height:1.4;}
  .place-meta {font:11px system-ui,sans-serif;letter-spacing:.05em;margin-top:5px;color:#8A755D;}
  .maplibregl-ctrl-group {border:1px solid #C6CBC0;background:#FAF8F2;}
  .maplibregl-ctrl-attrib {font-size:10px !important;}
  .error {position:absolute;top:45%;left:8%;right:8%;text-align:center;color:#613E3E;background:#FFF9F3;padding:20px;z-index:5;display:none;}
  @media (max-width:640px) {.titleplate{top:10px;left:10px;padding:8px 10px}.titleplate strong{font-size:15px}.eyebrow{font-size:8px}.legend{bottom:8px;left:8px;}}
</style>
</head>
<body>
<div class="frame">
  <div id="map" role="application" aria-label="Interactive maritime atlas of individually marked visited places"></div>
  <!-- Fixed cartographic ornament: not a geographic pin or map feature. -->
  <svg class="nautical-boat" viewBox="0 0 220 136" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">
    <g fill="none" stroke-linecap="round" stroke-linejoin="round">
      <!-- A small hand-inked sailing vessel. -->
      <path d="M111 18 L111 99" stroke="#194E61" stroke-width="1.35"/>
      <path d="M106 22 L110 22 L110 93" stroke="#D6E6DE" stroke-width=".75"/>
      <path d="M108 23 Q76 49 69 89 Q87 94 106 92 Z" fill="#F5EAD8" fill-opacity=".86" stroke="#25596A" stroke-width="1.25"/>
      <path d="M114 31 Q137 50 153 91 L114 94 Z" fill="#E8E4D3" fill-opacity=".84" stroke="#25596A" stroke-width="1.25"/>
      <path d="M107 28 Q88 60 78 86 M120 45 Q138 70 145 89" stroke="#6B99A0" stroke-width=".75" opacity=".65"/>
      <path d="M110 14 L123 17 L110 20" fill="#C2A16F" stroke="#C2A16F" stroke-width=".7"/>
      <path d="M52 97 Q110 107 169 96 L157 108 Q109 121 65 108 Z" fill="#245D70" fill-opacity=".85" stroke="#E5E4D5" stroke-width="1.1"/>
      <path d="M69 104 Q107 113 151 104" stroke="#D3E2DB" stroke-width=".85" opacity=".9"/>
      <path d="M64 97 L159 97" stroke="#D3E2DB" stroke-width="1"/>
      <!-- Loose, non-repeating strokes evoke water rather than a sine wave. -->
      <path d="M4 116 Q19 111 34 115 T66 115 Q82 111 96 116 T128 115 Q146 110 162 116 T207 114" stroke="#E8F0E8" stroke-width="1.6" opacity=".95"/>
      <path d="M24 124 Q43 120 61 124 Q78 128 92 124 M112 125 Q134 120 154 124 T213 124" stroke="#D0E6E5" stroke-width="1.15" opacity=".9"/>
      <path d="M49 132 Q68 129 83 132 M138 132 Q159 129 176 132" stroke="#A9CFD1" stroke-width=".9" opacity=".85"/>
      <path d="M12 107 Q22 103 33 107 M179 106 Q194 101 209 106" stroke="#B9D9D7" stroke-width=".9" opacity=".75"/>
    </g>
  </svg>
  <div class="titleplate"><div class="eyebrow">✦ VIATERRA ✦</div><strong>Where I Have Wandered</strong></div>
  <div class="legend">
    <svg viewBox="0 0 36 36" aria-hidden="true"><circle cx="18" cy="18" r="15" fill="#FCF7EC" stroke="#214D5B" stroke-width="2.4"/><circle cx="18" cy="18" r="12" fill="none" stroke="#B99761" stroke-width="1"/><path d="M14 9 V27" stroke="#214D5B" stroke-width="2.2" stroke-linecap="round"/><path d="M16 10 L26 13.5 L16 18 Z" fill="#B86D59" stroke="#8C4C41" stroke-width="0.8"/><circle cx="14" cy="9" r="1.6" fill="#B99761"/></svg>
    Places visited
  </div>
  <div id="error" class="error">The map couldn't load its base tiles. Check internet access and the browser console.</div>
</div>
<script type="module">
import * as maplibregl from 'https://unpkg.com/maplibre-gl@6.16.0/dist/maplibre-gl.mjs';

const points = __PLACES__;
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

// Circular nautical marker: 36px SVG registered at pixelRatio 2 (18px on screen).
// Each location remains an independent point, without clustering.
const burgeeSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 36 36">
  <circle cx="18" cy="18" r="15" fill="#FCF7EC" stroke="#214D5B" stroke-width="2.4"/>
  <circle cx="18" cy="18" r="12" fill="none" stroke="#B99761" stroke-width="1"/>
  <path d="M14 9 V27" fill="none" stroke="#214D5B" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M16 10 L26 13.5 L16 18 Z" fill="#B86D59" stroke="#8C4C41" stroke-width="0.8" stroke-linejoin="round"/>
  <circle cx="14" cy="9" r="1.6" fill="#B99761"/>
</svg>`;

// One seamless, gently sunlit sea texture. All frequency terms are periodic,
// so the image tiles without seams. Generated locally in the browser; no asset URL.
function createSeaTexture() {
  const size = 256;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas 2D is not available');
  const pixels = ctx.createImageData(size, size);
  const tau = Math.PI * 2;
  const clamp = v => Math.max(0, Math.min(255, Math.round(v)));

  for (let y = 0; y < size; y++) {
    const v = tau * y / size;
    for (let x = 0; x < size; x++) {
      const u = tau * x / size;
      // Broad, gently varying water tones, then fine, wind-stretched ripples.
      const broad = 0.50 * Math.sin(u * 2 + 0.8 * Math.cos(v))
                  + 0.35 * Math.sin(u + 2 * v + 0.45)
                  + 0.25 * Math.cos(3 * v - 2 * u);
      const waviness = Math.sin(13 * u + 1.2 * Math.sin(3 * v))
                      * Math.cos(5 * v + 0.35 * Math.sin(u));
      const glint = Math.pow(Math.max(0, Math.sin(17 * u + 3 * v)
                      * Math.cos(7 * v - 2 * u)), 10);
      const value = broad * 13 + waviness * 4;
      const idx = (y * size + x) * 4;
      pixels.data[idx] = clamp(103 + value + glint * 7);
      pixels.data[idx + 1] = clamp(199 + value * .72 + glint * 10);
      pixels.data[idx + 2] = clamp(216 + value * .65 + glint * 10);
      pixels.data[idx + 3] = 255;
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
        map.setPaintProperty(layer.id, 'background-color', '#F5F0E4');
      } else if (layer.type === 'hillshade' || layer.type === 'raster' || layer.type === 'color-relief' || layer.type === 'fill-extrusion') {
        map.setLayoutProperty(layer.id, 'visibility', 'none');
      } else if (layer.type === 'fill') {
        if (id.includes('water') || src === 'water') {
          map.setPaintProperty(layer.id, 'fill-color', '#67C7D8');
          if (map.hasImage('viaterra-sea-texture')) {
            map.setPaintProperty(layer.id, 'fill-pattern', 'viaterra-sea-texture');
          }
          map.setPaintProperty(layer.id, 'fill-opacity', 1);
        } else {
          // Eliminate landcover, park, woodland and other textured shading.
          map.setPaintProperty(layer.id, 'fill-color', '#F5F0E4');
          map.setPaintProperty(layer.id, 'fill-opacity', 1);
        }
      } else if (layer.type === 'line') {
        if (id.includes('water') || src.includes('water')) {
          map.setPaintProperty(layer.id, 'line-color', '#67C7D8');
        } else if (/boundary|admin|border|coast/.test(id)) {
          map.setPaintProperty(layer.id, 'line-color', '#C4B8A0');
          map.setPaintProperty(layer.id, 'line-opacity', 0.65);
        } else if (/road|street|highway|rail|bridge|tunnel/.test(id)) {
          map.setLayoutProperty(layer.id, 'visibility', 'none');
        } else {
          map.setPaintProperty(layer.id, 'line-color', '#CEC8B8');
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
          map.setPaintProperty(layer.id, 'text-halo-color', '#F5F0E4');
          map.setPaintProperty(layer.id, 'text-halo-width', 1);
        }
      }
    } catch (e) { /* Tolerate style-specific layer differences. */ }
  }
}

function addBurgeeLayer(image) {
  map.addImage('viaterra-burgee', image, {pixelRatio: 2});
  // No clustering: every one of the 1,467 saved positions is its own feature.
  map.addSource('visited-places', {type: 'geojson', data: geojson, cluster: false});
  map.addLayer({
    id: 'burgee-pins', type: 'symbol', source: 'visited-places',
    layout: {
      'icon-image': 'viaterra-burgee',
      'icon-size': ['interpolate', ['linear'], ['zoom'], 1, 0.83, 5, 0.93, 10, 1.05, 15, 1.13],
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
  // Register before assigning fill-pattern to water layers.
  try {
    map.addImage('viaterra-sea-texture', createSeaTexture(), {pixelRatio: 1});
  } catch (e) {
    console.warn('Sea texture unavailable; retaining flat sea color.', e);
  }
  applyMaritimeStyle();
  const image = new Image();
  image.onload = () => addBurgeeLayer(image);
  image.onerror = () => {error.textContent = 'The map marker could not be loaded.'; error.style.display = 'block';};
  image.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(burgeeSvg);
});
</script>
</body>
</html>
"""


def render_atlas_map() -> None:
    """Render a wide nautical map of places already imported into Neon."""
    try:
        places = get_visited_places()
    except Exception:
        st.error("Viaterra couldn't load visited places from Neon. Check the database connection.")
        return

    if not places:
        st.info("No geolocated places are available in Neon yet.")
        return

    # JSON is embedded only as a JavaScript literal; escape HTML-sensitive characters.
    safe_json = json.dumps(places, ensure_ascii=True, separators=(",", ":"))
    safe_json = safe_json.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = _MAP_HTML.replace("__PLACES__", safe_json)
    components.html(html, height=660, scrolling=False)
