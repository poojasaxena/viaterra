"""Viaterra's interactive nautical atlas (MapLibre + OpenFreeMap)."""

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import base64
from viaterra.processing.paths import load_config, require_asset
from viaterra.db.queries import get_visited_places
from html import escape

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

/* Main map container */
.frame {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    border: none;
    border-radius: 0;
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



.frame::after {
    content: "";
    position: absolute;
    inset: -3px;
    z-index: 10;
    pointer-events: none;

    border: __FRAME_WIDTH__px solid transparent;

    border-image-source:
        url("data:image/png;base64,__WEATHERED_FRAME__");

    border-image-slice:
        __FRAME_SLICE_VERTICAL__%
        __FRAME_SLICE_HORIZONTAL__%;

    border-image-width: 1;
    border-image-repeat: stretch;

    opacity: __FRAME_OPACITY__;
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

.atlas-search {
    position: absolute;
    top: 16px;
    left: 16px;
    width: min(340px, calc(100% - 85px));
    z-index: 20;
    font: 14px system-ui, sans-serif;
}

.atlas-search-bar {
    display: flex;
    gap: 5px;
}

.atlas-locate {
    flex: 0 0 44px;
    min-height: 44px;
    display: grid;
    place-items: center;
    border: 1px solid #D8CFBE;
    border-radius: 8px;
    background: #FFFCF5;
    color: #254C60;
    cursor: pointer;
    box-shadow: 0 3px 12px rgba(29, 56, 64, 0.15);
}

.atlas-locate:hover:not(:disabled) {
    background: #E2EEEB;
}

.atlas-locate:disabled {
    opacity: 0.65;
    cursor: wait;
}

.atlas-search .atlas-search-bar input {
    min-width: 0;
    width: 100%;
    padding: 13px 16px;
    border: 1px solid #D8CFBE;
    border-radius: 8px;
    background: #FFFCF5;
    color: #254C60;
    box-shadow: 0 3px 12px rgba(29, 56, 64, 0.15);
    outline: none;
}

.atlas-save-popup input {
    width: 100%;
    min-height: 36px;
    margin: 6px 0 2px;
    border: 1px solid #D8CFBE;
    border-radius: 6px;
    padding: 5px 8px;
    background: #FFFCF5;
    color: #254C60;
    font: inherit;
}

.atlas-location-status:not(:empty) {
    margin-top: 4px;
    padding: 8px 12px;
    border-radius: 7px;
    background: #FFFCF5;
    color: #254C60;
}

.atlas-search input:focus {
    border-color: #438FA6;
}

.atlas-search-results {
    display: none;
    margin-top: 4px;
    max-height: 240px;
    overflow-y: auto;
    background: #FFFCF5;
    border-radius: 7px;
    box-shadow: 0 4px 16px rgba(29, 56, 64, 0.18);
}

.atlas-search-results button {
    display: block;
    width: 100%;
    padding: 11px 14px;
    border: 0;
    background: transparent;
    color: #254C60;
    text-align: left;
    cursor: pointer;
}

.atlas-search-results button:hover {
    background: #F1EADC;
}

.atlas-save-popup {
    color: #254C60;
    padding: 2px 8px 2px 2px;
}

.atlas-save-button {
    margin-top: 8px;
    padding: 6px 12px;
    min-height: 36px;
    border: 1px solid #376E80;
    border-radius: 16px;
    background: #FFFCF5;
    color: #254C60;
    cursor: pointer;
    font: inherit;
}

.atlas-save-button:hover:not(:disabled) {
    background: #E2EEEB;
}

.atlas-save-button:disabled {
    opacity: 0.65;
    cursor: default;
}

.atlas-save-status:not(:empty) {
    margin-top: 6px;
}

/* A generic decorative element for the atlas */
.viaterra-decoration {
    position: absolute;
    height: auto;
    z-index: 11;
    pointer-events: none;
    transform-origin: center;
    filter: drop-shadow(3px 5px 4px rgba(45, 35, 24, 0.20));
}

@media (max-width: 640px) {
    .viaterra-decoration {
        display: none;
    }
}

/* Hide fixed-position nautical ornaments on interactive views. */
__INTERACTIVE_ORNAMENT_CSS__

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
    __SEARCH_CONTROL__
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

<!-- Travel memorabilia configured in TOML -->
__DECORATIONS__


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
  features: placeFeatures(points)
};

function placeFeatures(places) {
  return places.map((p, i) => ({
    type: 'Feature', id: i,
    properties: {name: p.name, country: p.country_code || ''},
    geometry: {type: 'Point', coordinates: [p.longitude, p.latitude]}
  }));
}


const MAP_POSITION = __MAP_POSITION__;

const map = new maplibregl.Map({
    container: 'map',
    style: 'https://tiles.openfreemap.org/styles/liberty',
    center: MAP_POSITION.center,
    zoom: MAP_POSITION.zoom,
    minZoom: 1.1,
    maxZoom: __MAX_ZOOM__,
    renderWorldCopies: true,
    attributionControl: false
});

const searchInput = document.getElementById('atlas-search-input');
const searchResults = document.getElementById('atlas-search-results');
const locateButton = document.getElementById('atlas-locate');
const locationStatus = document.getElementById('atlas-location-status');
let searchMarker = null;
let saveToken = null;
let savePopup = null;
let saveRequest = null;
let searchSequence = 0;

function searchPlaceLabel(properties) {
    return [...new Set([properties.name, properties.city, properties.country]
        .filter(Boolean))].join(', ');
}

function updateSavePopup() {
    if (!savePopup) return;
    const {button, status, result, nameInput} = savePopup;
    if (nameInput) {
        nameInput.hidden = !saveToken;
        nameInput.disabled = saveRequest?.popup === savePopup || result?.status === 'saved';
    }
    button.hidden = !saveToken || result?.status === 'saved';
    button.disabled = saveRequest !== null || (nameInput !== null && !nameInput.value.trim());
    button.textContent = saveRequest?.popup === savePopup ? 'Saving…'
        : result?.status === 'nearby' ? 'Save separate flag' : 'Save as visited';
    status.textContent = saveToken ? (result?.message || '') : '';
}

function requestSave(popup) {
    if (!saveToken || saveRequest) return;
    searchResults.style.display = 'none';
    const id = Array.from(crypto.getRandomValues(new Uint32Array(4))).join('-');
    const confirm = popup.result?.status === 'nearby' ? popup.result.id : null;
    saveRequest = {id, popup};
    updateSavePopup();
    window.parent.postMessage({
        type: 'viaterra:save',
        request: {id, place: popup.place, confirm, token: saveToken}
    }, '*');
}

function showSearchPlace(feature, closeResults = false, accuracy = null) {
    const properties = feature.properties || {};
    const [longitude, latitude] = feature.geometry.coordinates;
    const label = searchPlaceLabel(properties);
    const place = {
        name: properties.name || label,
        longitude,
        latitude,
        country: properties.country || '',
        country_alpha2: properties.countrycode || ''
    };

    map.jumpTo({center: [longitude, latitude], zoom: 16});

    if (searchMarker) searchMarker.remove();

    const content = document.createElement('div');
    content.className = 'atlas-save-popup';
    const title = document.createElement('div');
    title.className = 'place-name';
    title.textContent = place.name;
    content.appendChild(title);
    const area = accuracy === null
        ? [...new Set([properties.city, properties.country]
            .filter(value => value && value !== place.name))].join(', ')
        : `Accuracy about ${Math.round(accuracy)} m`;
    if (area) {
        const location = document.createElement('div');
        location.className = 'place-meta';
        location.textContent = area;
        content.appendChild(location);
    }

    const button = document.createElement('button');
    button.type = 'button';
    button.hidden = true;
    button.className = 'atlas-save-button';
    const status = document.createElement('div');
    status.className = 'atlas-save-status';
    status.setAttribute('role', 'status');
    content.append(button, status);
    const popup = {place, button, status, result: null, nameInput: null};
    if (accuracy !== null) {
        const nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.value = place.name;
        nameInput.maxLength = 250;
        nameInput.setAttribute('aria-label', 'Place name');
        nameInput.addEventListener('input', () => {
            popup.place.name = nameInput.value.trim();
            popup.result = null;
            updateSavePopup();
        });
        content.insertBefore(nameInput, button);
        popup.nameInput = nameInput;
    }
    button.addEventListener('click', () => requestSave(popup));
    savePopup = popup;
    updateSavePopup();

    searchMarker = new maplibregl.Marker({color: '#713F70'})
        .setLngLat([longitude, latitude])
        .setPopup(new maplibregl.Popup({offset: 25, maxWidth: '240px'})
            .setDOMContent(content))
        .addTo(map);
    searchMarker.togglePopup();

    if (closeResults) {
        searchInput.value = label;
        searchResults.style.display = 'none';
    }
}

if (__SAVE_COMPONENT__) {
    window.addEventListener('message', event => {
        if (event.source !== window.parent || event.data?.type !== 'viaterra:state') return;

        const {token, result, places} = event.data;
        if (token !== saveToken && savePopup) savePopup.result = null;
        if (token !== saveToken) saveRequest = null;
        saveToken = token;
        if (Array.isArray(places)) {
            geojson.features = placeFeatures(places);
            map.getSource('visited-places')?.setData(geojson);
        }

        if (saveRequest && result?.id === saveRequest.id) {
            saveRequest.popup.result = result;
            if (result.status === 'saved' && saveRequest.popup === savePopup) {
                searchMarker.getElement().style.visibility = 'hidden';
            }
            saveRequest = null;
        }
        updateSavePopup();
    });
    window.parent.postMessage({type: 'viaterra:mapReady'}, '*');
}

if (locateButton && locationStatus) {
    locateButton.addEventListener('click', () => {
        if (!window.isSecureContext || !navigator.geolocation) {
            locationStatus.textContent = 'Use HTTPS or localhost to access your location.';
            return;
        }

        const sequence = ++searchSequence;
        searchResults.style.display = 'none';
        locateButton.disabled = true;
        locationStatus.textContent = 'Finding your location…';

        navigator.geolocation.getCurrentPosition(({coords}) => {
            locateButton.disabled = false;
            if (sequence !== searchSequence) return;
            locationStatus.textContent = '';
            showSearchPlace({
                geometry: {coordinates: [coords.longitude, coords.latitude]},
                properties: {name: 'My location'}
            }, true, coords.accuracy);
        }, error => {
            locateButton.disabled = false;
            if (sequence !== searchSequence) return;
            locationStatus.textContent = {
                1: 'Allow location access in your browser or open Echoes directly.',
                2: 'Your device could not find its location. Try again.',
                3: 'Finding your location timed out. Try again.'
            }[error.code] || 'Could not find your location. Try again.';
        }, {enableHighAccuracy: true, timeout: 12000, maximumAge: 0});
    });
}

if (searchInput && searchResults) {
    searchInput.addEventListener('input', () => {
        searchSequence++;
        searchResults.style.display = 'none';
        if (locationStatus) locationStatus.textContent = '';
    });
    searchInput.addEventListener('keydown', async event => {
        if (event.key !== 'Enter') return;
        event.preventDefault();

        const query = searchInput.value.trim();
        if (query.length < 3) return;

        const sequence = ++searchSequence;
        if (locationStatus) locationStatus.textContent = '';
        searchResults.replaceChildren();
        searchResults.style.display = 'block';
        const message = document.createElement('div');
        message.style.padding = '12px';
        message.textContent = 'Searching...';
        searchResults.appendChild(message);

        try {
            const url = 'https://photon.komoot.io/api/?limit=5&q='
                + encodeURIComponent(query);
            const response = await fetch(url);
            if (!response.ok) throw new Error('Search unavailable');
            const data = await response.json();
            if (sequence !== searchSequence) return;
            const features = (data.features || []).filter(feature => {
                const coords = feature.geometry?.coordinates;
                return feature.geometry?.type === 'Point' && coords?.length >= 2
                    && Number.isFinite(coords[0]) && Number.isFinite(coords[1])
                    && Math.abs(coords[0]) <= 180 && Math.abs(coords[1]) <= 90
                    && searchPlaceLabel(feature.properties || {});
            });
            searchResults.replaceChildren();
            if (!features.length) {
                message.textContent = 'No places found';
                searchResults.appendChild(message);
                return;
            }

            // Enter previews the best match, just as the user expects.
            showSearchPlace(features[0]);
            for (const feature of features) {
                const label = searchPlaceLabel(feature.properties || {});
                const button = document.createElement('button');
                button.type = 'button';
                button.textContent = label;
                button.addEventListener('click', () => showSearchPlace(feature, true));
                searchResults.appendChild(button);
            }
        } catch (error) {
            if (sequence !== searchSequence) return;
            message.textContent = 'Search temporarily unavailable';
            searchResults.replaceChildren(message);
        }
    });
}

/* Homepage stays fixed; functional pages allow zoom and pan. */
if (__INTERACTIVE__) {
    map.addControl(
        new maplibregl.NavigationControl({showCompass: false}),
        'top-right'
    );
} else {
    map.scrollZoom.disable();
    map.boxZoom.disable();
    map.dragPan.disable();
    map.dragRotate.disable();
    map.doubleClickZoom.disable();
    map.touchZoomRotate.disable();
    map.keyboard.disable();
}
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
          // Keep buildings discernible at street zoom in functional pages.
          const isBuilding = /building/.test(id) || src.includes('building');
          map.setPaintProperty(layer.id, 'fill-color',
              __INTERACTIVE__ && isBuilding ? '#E4D9C3' : '#F3E9D5');
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
          if (!__INTERACTIVE__) {
            map.setLayoutProperty(layer.id, 'visibility', 'none');
          } else {
            map.setPaintProperty(layer.id, 'line-color', '#C8BDA9');
            map.setPaintProperty(layer.id, 'line-opacity', 0.9);
          }
        } else {
          map.setPaintProperty(layer.id, 'line-color', '#D4C4AA');
          map.setPaintProperty(layer.id, 'line-opacity', 0.4);
        }
      } else if (layer.type === 'symbol') {
        // Keep country and settlement labels, but not POIs, transit, roads or
        // numerous sea labels. The visited-place flags must remain the focus.
        const geographic = /country|state|city|town|village|settlement/.test(id);
        if (!geographic && !__INTERACTIVE__) {
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

def render_atlas_map(
    *,
    interactive: bool = False,
    decorations: bool | None = None,
    save_enabled: bool | None = None,
    save_token: str | None = None,
    save_result: dict | None = None,
    recently_saved: list[dict] | None = None,
) -> dict | None:
    """Render the nautical atlas, fixed on the homepage or navigable elsewhere.

    The existing no-argument homepage call remains unchanged. Interactive maps
    omit the homepage souvenirs by default. Echoes opts into the pin-saving
    component by passing its owner authorization as save_enabled.
    """
    if decorations is None:
        decorations = not interactive

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

    map_position = {
        "center": [
            float(map_config.get("center_longitude", 13.0)),
            float(map_config.get("center_latitude", 24.0)),
        ],
        "zoom": float(map_config.get("zoom", 1.25)),
    }

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

    use_save_component = interactive and save_enabled is not None
    if not places and not use_save_component:
        st.info("No geolocated places are available in Neon yet.")
        return

    places = list(places or [])
    if use_save_component and recently_saved:
        existing = {
            (place["name"], float(place["latitude"]), float(place["longitude"]))
            for place in places
        }
        for place in recently_saved:
            identity = (place["name"], place["latitude"], place["longitude"])
            if identity not in existing:
                places.append(place)
                existing.add(identity)

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

    frame_config = map_config.get("frame", {})
    frame_asset = frame_config.get("asset", "weathered_frame")
    frame_width = int(frame_config.get("width", 18))
    frame_opacity = float(frame_config.get("opacity", 1.0))
    frame_slice_vertical = float(frame_config.get("slice_vertical", 14))
    frame_slice_horizontal = float(frame_config.get("slice_horizontal", 10))

    frame_base64 = encode_image(
        "illustrations", frame_asset
    )

    # Decorative travel memorabilia
    decoration_config = map_config.get("decorations", {})
    decoration_html = []

    if decorations and decoration_config.get("enabled", True):
        for name, settings in decoration_config.items():
            if name == "enabled" or not isinstance(settings, dict):
                continue

            asset = settings["asset"]
            category = settings["category"]

            image_base64 = encode_image(
                "illustrations", "travel", category, asset
            )

            positioning = "; ".join(
                f"{side}: {settings[side]}"
                for side in ("top", "right", "bottom", "left")
                if side in settings
            )

            width = float(settings.get("width", 120))
            rotation = float(settings.get("rotation", 0))
            opacity = float(settings.get("opacity", 1))

            style = (
                f"{positioning}; "
                f"width: {width}px; "
                f"transform: rotate({rotation}deg); "
                f"opacity: {opacity};"
            )

            decoration_html.append(
                '<img class="viaterra-decoration" '
                f'src="data:image/png;base64,{image_base64}" '
                f'style="{escape(style, quote=True)}" '
                'alt="" aria-hidden="true">'
            )


        # Inject data and configuration into the map template
    html = _MAP_HTML
    search_control = """
    <div class="atlas-search" id="atlas-search">
        <div class="atlas-search-bar">
            <input
                id="atlas-search-input"
                type="search"
                placeholder="Search for a place..."
                aria-label="Search for a place"
                autocomplete="off"
                enterkeyhint="search"
            >
            <button type="button" id="atlas-locate" class="atlas-locate"
                    title="Use my location" aria-label="Use my location">
                <svg width="20" height="20" viewBox="0 0 24 24"
                     fill="none" stroke="currentColor" stroke-width="1.8"
                     stroke-linecap="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="7"/>
                    <circle cx="12" cy="12" r="2.5"/>
                    <path d="M12 2v3m0 14v3M2 12h3m14 0h3"/>
                </svg>
            </button>
        </div>
        <div id="atlas-location-status" class="atlas-location-status" role="status"></div>
        <div id="atlas-search-results" class="atlas-search-results"></div>
    </div>
    """

    html = html.replace(
        "__SEARCH_CONTROL__",
        search_control if interactive else "",
    )

    html = html.replace("__SAVE_COMPONENT__", json.dumps(use_save_component))
    html = html.replace("__INTERACTIVE__", json.dumps(interactive))
    html = html.replace("__MAX_ZOOM__", "19" if interactive else "17")
    html = html.replace(
        "__INTERACTIVE_ORNAMENT_CSS__",
        ".nautical-boat, .nautical-compass { display: none; }" if interactive else "",
    )
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
    html = html.replace("__DECORATIONS__","\n".join(decoration_html),)
    html = html.replace("__MAP_POSITION__",json.dumps(map_position),)
    html = html.replace("__FRAME_WIDTH__", str(frame_width))
    html = html.replace("__FRAME_OPACITY__", str(frame_opacity))
    html = html.replace("__FRAME_SLICE_VERTICAL__", str(frame_slice_vertical))
    html = html.replace("__FRAME_SLICE_HORIZONTAL__", str(frame_slice_horizontal))

    if use_save_component:
        atlas_component = components.declare_component(
            "echoes_atlas", path=str(Path(__file__).with_name("atlas_frontend"))
        )
        return atlas_component(
            map_html=html,
            height=map_height,
            save_token=save_token if save_enabled else None,
            save_result=save_result,
            places=json.loads(safe_json),
            key="viaterra_echoes_atlas",
        )

    components.html(
        html,
        height=map_height,
        scrolling=False,
    )
