"""Viaterra — private, mobile-friendly capture of a visited place."""

from __future__ import annotations

import hmac
import os

import pandas as pd
import streamlit as st
from streamlit_geolocation import streamlit_geolocation

from viaterra.app.components.atlas_map import render_atlas_map

from viaterra.app.navigation import render_navigation
from viaterra.app.ui import render_header
from viaterra.db.capture import find_nearby, insert_visited_place
from viaterra.places.search import nearest_place, search_places

st.set_page_config(page_title="Capture a Place | Viaterra", page_icon="⚓", layout="wide",
                   initial_sidebar_state="collapsed")
render_header(
    header_key="echoes",
    subtitle="Every place holds a memory",
)
render_navigation(active_page="Echoes")
render_atlas_map(
    interactive=True,
    decorations=False,
)


def owner_password() -> str | None:
    value = os.environ.get("VIATERRA_EDITOR_PASSWORD")
    if value:
        return value
    try:
        return st.secrets.get("VIATERRA_EDITOR_PASSWORD")
    except Exception:
        return None


password = owner_password()
if not password:
    st.warning("Editing is disabled until VIATERRA_EDITOR_PASSWORD is configured. No database writes are possible.")
    st.stop()

if not st.session_state.get("viaterra_capture_authorized", False):
    with st.form("capture_login"):
        supplied = st.text_input("Owner password", type="password")
        login = st.form_submit_button("Unlock place capture")
    if login:
        if hmac.compare_digest(supplied.encode(), password.encode()):
            st.session_state["viaterra_capture_authorized"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

if st.button("Lock editing", type="tertiary"):
    st.session_state["viaterra_capture_authorized"] = False
    st.rerun()


def choose(place: dict) -> None:
    st.session_state["capture_selected"] = place
    st.session_state["capture_name"] = place["name"]
    st.session_state["capture_lat"] = float(place["latitude"])
    st.session_state["capture_lon"] = float(place["longitude"])
    st.session_state["capture_country"] = place.get("country") or ""
    st.session_state["capture_alpha2"] = place.get("country_alpha2") or ""
    st.session_state["capture_nearby_checked"] = None
    st.session_state["capture_saved"] = None


search_tab, gps_tab = st.tabs(["🔎 Search by name", "◎ Use my location"])
with search_tab:
    with st.form("lookup_place"):
        query = st.text_input("Search for a place", placeholder="e.g. Cape Point, South Africa")
        submitted = st.form_submit_button("Find places")
    if submitted:
        if len(query.strip()) < 3:
            st.info("Enter at least three characters.")
        else:
            try:
                st.session_state["capture_results"] = search_places(query)
            except Exception as exc:
                st.session_state["capture_results"] = []
                st.error(f"Location search unavailable: {exc}")
    results = st.session_state.get("capture_results", [])
    if results:
        options = [f"{p['name']} — {p['area']} ({p['latitude']:.4f}, {p['longitude']:.4f})"
                   for p in results]
        with st.form("choose_place"):
            index = st.radio("Select the right place", range(len(options)), format_func=lambda i: options[i])
            selected = st.form_submit_button("Use this location")
        if selected:
            choose(results[index])
            st.rerun()
    elif submitted:
        st.info("No matches found. Try a nearby town or a more specific name.")

with gps_tab:
    st.write("Tap the button below and allow location access on your phone. Requires HTTPS or localhost.")
    position = streamlit_geolocation()
    if isinstance(position, dict) and position.get("latitude") is not None and position.get("longitude") is not None:
        lat = float(position["latitude"])
        lon = float(position["longitude"])
        accuracy = position.get("accuracy")
        if accuracy is not None:
            st.caption(f"Reported GPS accuracy: approximately {float(accuracy):.0f} metres.")
        if st.button("Use these coordinates", key=f"gps_use_{lat:.6f}_{lon:.6f}"):
            place = {"name": "My visited place", "latitude": lat, "longitude": lon,
                     "country": "", "country_alpha2": ""}
            try:
                nearby = nearest_place(lat, lon)
                if nearby:
                    place["name"] = nearby["name"]
                    place["country"] = nearby.get("country") or ""
                    place["country_alpha2"] = nearby.get("country_alpha2") or ""
            except Exception:
                st.info("We couldn't identify a nearby name, but your coordinates are usable.")
            choose(place)
            st.rerun()

if "capture_selected" in st.session_state:
    st.divider()
    st.markdown("#### Review your flag")
    st.text_input("Place name", key="capture_name", help="You can replace a nearby suggestion with your own name.")
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Latitude", min_value=-90.0, max_value=90.0,
                        format="%.7f", step=0.0001, key="capture_lat")
    with c2:
        st.number_input("Longitude", min_value=-180.0, max_value=180.0,
                        format="%.7f", step=0.0001, key="capture_lon")
    lat = float(st.session_state["capture_lat"])
    lon = float(st.session_state["capture_lon"])
    st.map(pd.DataFrame([{"lat": lat, "lon": lon}]), zoom=13)
    if st.session_state.get("capture_country"):
        st.caption(f"Suggested country: {st.session_state['capture_country']}")
    st.caption("The pin shows the chosen coordinates. Adjust latitude/longitude above if necessary. If you move to a different country, search for the place again to refresh the country suggestion.")

    # The confirmation is tied to the exact proposed data: changing anything requires another review.
    identity = (st.session_state["capture_name"].strip(), lat, lon,
                st.session_state.get("capture_alpha2", ""))
    if not identity[0]:
        st.warning("A place name is required.")
    elif st.session_state.get("capture_saved") == identity:
        st.success("Flag saved to Viaterra. The homepage map will load the new flag when refreshed.")
    elif st.session_state.get("capture_nearby_checked") != identity:
        if st.button("Check for duplicates", type="primary"):
            try:
                nearby = find_nearby(lat, lon)
                st.session_state["capture_nearby"] = nearby
                st.session_state["capture_nearby_checked"] = identity
                st.rerun()
            except Exception as exc:
                st.error(f"Could not check database: {exc}")
    else:
        nearby = st.session_state.get("capture_nearby", [])
        if nearby:
            st.warning("Existing flag(s) within 35 metres: " + "; ".join(
                f"{name} ({distance} m)" for _, name, distance in nearby))
            confirm = st.checkbox("This is a different place; save a separate flag anyway", key="capture_confirm_duplicate")
        else:
            st.success("No existing flags found within 35 metres.")
            confirm = True
        if st.button("Save visited flag", type="primary", disabled=not confirm):
            try:
                # Repeat the duplicate check immediately before writing; new nearby places
                # require the same explicit duplicate acknowledgement.
                latest = find_nearby(lat, lon)
                if latest and not st.session_state.get("capture_confirm_duplicate", False):
                    st.session_state["capture_nearby"] = latest
                    st.warning("A nearby flag was found. Review it before saving.")
                else:
                    insert_visited_place(name=identity[0], latitude=lat, longitude=lon,
                                         country_alpha2=st.session_state.get("capture_alpha2"),
                                         country_name=st.session_state.get("capture_country"))
                    st.session_state["capture_saved"] = identity
                    st.rerun()
            except Exception as exc:
                st.error(f"Could not save place: {exc}")

st.caption("Place search data © OpenStreetMap contributors, delivered by Photon. GPS runs only when you request it.")
