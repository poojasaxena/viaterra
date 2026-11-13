"""Footprints, the ordered journeys in Viaterra."""

import hmac
import logging

import streamlit as st

from viaterra.app.components.atlas_map import render_atlas_map
from viaterra.app.components.echoes_page import owner_password
from viaterra.app.navigation import render_navigation
from viaterra.app.ui import render_header
from viaterra.db.footprints import available_stops, journey_stops, list_journeys, save_journey

_LOGGER = logging.getLogger(__name__)
_DRAFT = "footprints_draft"
_SELECTION = "footprints_journey"
_SELECT_SAVED = "footprints_select_saved"


def move_stop(keys: list[str], index: int, direction: int) -> None:
    target = index + direction
    if 0 <= index < len(keys) and 0 <= target < len(keys):
        keys[index], keys[target] = keys[target], keys[index]


def render_footprints() -> None:
    st.set_page_config(page_title="Footprints | Viaterra", page_icon="⚓",
                       layout="wide", initial_sidebar_state="collapsed")
    render_header(header_key="footprints", subtitle="Journeys in the order I travelled")
    render_navigation(active_page="Footprints")

    password = owner_password()
    authorized = bool(password and st.session_state.get("viaterra_capture_authorized"))
    if password and not authorized:
        with st.popover("Unlock editing"):
            with st.form("footprints_login", clear_on_submit=True):
                supplied = st.text_input("Owner password", type="password")
                if st.form_submit_button("Unlock"):
                    if hmac.compare_digest(supplied.encode(), password.encode()):
                        st.session_state["viaterra_capture_authorized"] = True
                        st.rerun()
                    st.error("Incorrect password.")
    elif authorized and st.button("Lock editing", type="tertiary"):
        st.session_state["viaterra_capture_authorized"] = False
        st.session_state.pop(_DRAFT, None)
        st.rerun()

    try:
        journeys = list_journeys()
        if _SELECT_SAVED in st.session_state:
            st.session_state[_SELECTION] = st.session_state.pop(_SELECT_SAVED)
        if st.session_state.get(_SELECTION) not in journeys:
            st.session_state[_SELECTION] = next(iter(journeys), None)
        journey_id = st.selectbox(
            "Journey", list(journeys), format_func=journeys.__getitem__, key=_SELECTION,
        ) if journeys else None
        stops = journey_stops(journey_id) if journey_id is not None else []
    except Exception:
        _LOGGER.exception("Could not load journeys")
        st.error("Viaterra couldn't load journeys from Neon.")
        return

    if authorized:
        new, edit = st.columns(2)
        if new.button("New journey"):
            st.session_state["footprints_title"] = ""
            st.session_state[_DRAFT] = {"id": None, "keys": []}
        if edit.button("Edit journey", disabled=journey_id is None):
            st.session_state["footprints_title"] = journeys[journey_id]
            st.session_state[_DRAFT] = {
                "id": journey_id, "keys": [place["place_key"] for place in stops],
            }

    draft = st.session_state.get(_DRAFT) if authorized else None
    if draft is not None:
        try:
            places = available_stops()
            # Keep previously saved stops in the draft even if their coordinates were removed.
            if draft["id"] is not None:
                for place in journey_stops(draft["id"]):
                    places.setdefault(place["place_key"], place)
        except Exception:
            _LOGGER.exception("Could not load saved places for Footprints")
            st.error("Viaterra couldn't load your saved places.")
            return
        stops = [places[key] for key in draft["keys"] if key in places]
        render_atlas_map(interactive=True, decorations=False, journey=True,
                         places_loader=lambda: stops)
        edit_journey(draft, places)
        return

    render_atlas_map(interactive=True, decorations=False, journey=True,
                     places_loader=lambda: stops)
    if stops:
        for order, place in enumerate(stops, start=1):
            st.write(f"{order}. {place['name']}")
    elif not journeys:
        st.info("No journeys yet.")


def edit_journey(draft: dict, places: dict[str, dict]) -> None:
    title = st.text_input("Journey title", key="footprints_title", max_chars=120)
    keys = draft["keys"]
    countries = sorted({place["country"] for place in places.values() if place.get("country")})
    country = st.selectbox("Filter saved places by country", [None, *countries],
                           format_func=lambda value: value or "All countries")

    def label(key: str) -> str:
        place = places[key]
        return " · ".join(dict.fromkeys(filter(None, (
            place["name"], place.get("city"), place.get("country"),
        ))))

    choices = [key for key, place in places.items() if key not in keys
               and place["latitude"] is not None and place["longitude"] is not None
               and (country is None or place.get("country") == country)]
    picker, add = st.columns([4, 1])
    candidate = picker.selectbox("Find a saved place", choices, index=None, format_func=label)
    if add.button("Add stop", disabled=candidate is None):
        keys.append(candidate)
        st.rerun()

    for index, key in enumerate(keys):
        name, up, down, remove = st.columns([6, 1, 1, 2])
        name.write(f"{index + 1}. {label(key) if key in places else 'Unavailable place'}")
        if up.button("↑", key=f"footprints_up_{key}", help="Move up", disabled=index == 0):
            move_stop(keys, index, -1)
            st.rerun()
        if down.button("↓", key=f"footprints_down_{key}", help="Move down",
                       disabled=index == len(keys) - 1):
            move_stop(keys, index, 1)
            st.rerun()
        if remove.button("Remove", key=f"footprints_remove_{key}"):
            keys.pop(index)
            st.rerun()

    save, cancel = st.columns(2)
    if save.button("Save journey", type="primary",
                   disabled=not title.strip() or not keys or any(key not in places for key in keys)):
        try:
            journey_id = save_journey(title, keys, draft["id"])
        except Exception:
            _LOGGER.exception("Could not save journey")
            st.error("Viaterra couldn't save this journey. Your draft is still here.")
        else:
            st.session_state[_SELECT_SAVED] = journey_id
            st.session_state.pop(_DRAFT, None)
            st.rerun()
    if cancel.button("Cancel"):
        st.session_state.pop(_DRAFT, None)
        st.rerun()
