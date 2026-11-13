"""Echoes: search the atlas and save a visited flag at the selected point."""

from __future__ import annotations

import hmac
import logging
import os
import re
import secrets

import streamlit as st

from viaterra.app.components.atlas_map import render_atlas_map
from viaterra.app.navigation import render_navigation
from viaterra.app.ui import render_header
from viaterra.db.capture import find_nearby, insert_visited_place
from viaterra.db.queries import get_visited_places

_AUTHORIZED = "viaterra_capture_authorized"
_SAVE_TOKEN = "echoes_save_token"
_LAST_REQUEST = "echoes_last_save_request"
_RESULT = "echoes_save_result"
_CONFIRMATION = "echoes_save_confirmation"
_RECENTLY_SAVED = "echoes_recently_saved"
_LOGGER = logging.getLogger(__name__)


def owner_password() -> str | None:
    value = os.environ.get("VIATERRA_EDITOR_PASSWORD")
    if value:
        return value
    try:
        return st.secrets.get("VIATERRA_EDITOR_PASSWORD")
    except (FileNotFoundError, KeyError):
        return None


def selected_place(value: object) -> dict:
    """Validate the selected Photon result before using it with the database."""
    if not isinstance(value, dict):
        raise ValueError("Select a search result again.")

    name = value.get("name")
    latitude = value.get("latitude")
    longitude = value.get("longitude")
    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name) > 250
        or type(latitude) not in (int, float)
        or type(longitude) not in (int, float)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        raise ValueError("Select a valid search result again.")

    country = value.get("country")
    alpha2 = value.get("country_alpha2")
    return {
        "name": name.strip(),
        "latitude": float(latitude),
        "longitude": float(longitude),
        "country": country.strip()[:250] if isinstance(country, str) else "",
        "country_alpha2": (
            alpha2.upper()
            if isinstance(alpha2, str) and re.fullmatch(r"[a-zA-Z]{2}", alpha2)
            else ""
        ),
    }


def save_selected_place(request: dict, *, authorized: bool) -> None:
    """Handle one owner request and return the outcome to the map on rerun."""
    if not authorized or not isinstance(request, dict):
        return

    token = request.get("token")
    if not isinstance(token, str) or token != st.session_state.get(_SAVE_TOKEN):
        return

    request_id = request.get("id")
    if (
        not isinstance(request_id, str)
        or not re.fullmatch(r"[0-9]{1,10}(?:-[0-9]{1,10}){3}", request_id)
        or request_id == st.session_state.get(_LAST_REQUEST)
    ):
        return

    st.session_state[_LAST_REQUEST] = request_id
    confirmation = st.session_state.pop(_CONFIRMATION, None)
    result = {"id": request_id, "status": "error"}

    try:
        place = selected_place(request.get("place"))
    except ValueError as exc:
        result["message"] = str(exc)
    else:
        try:
            nearby = list(find_nearby(place["latitude"], place["longitude"]))
            nearby_ids = {place_id for place_id, _, _ in nearby}
            confirmed = (
                confirmation is not None
                and request.get("confirm") == confirmation["id"]
                and place == confirmation["place"]
                and nearby_ids <= confirmation["nearby_ids"]
            )

            if nearby and not confirmed:
                _, name, distance = min(nearby, key=lambda row: row[2])
                st.session_state[_CONFIRMATION] = {
                    "id": request_id,
                    "place": place,
                    "nearby_ids": nearby_ids,
                }
                result.update(
                    status="nearby",
                    message=f"Nearby flag: {name} ({distance} m).",
                )
            else:
                insert_visited_place(
                    name=place["name"],
                    latitude=place["latitude"],
                    longitude=place["longitude"],
                    country_alpha2=place["country_alpha2"],
                    country_name=place["country"],
                )
                result.update(status="saved", message="Saved to Viaterra")
                st.session_state.setdefault(_RECENTLY_SAVED, []).append(
                    {
                        "name": place["name"],
                        "latitude": place["latitude"],
                        "longitude": place["longitude"],
                        "country_code": place["country_alpha2"],
                    }
                )
                clear_cache = getattr(get_visited_places, "clear", None)
                if callable(clear_cache):
                    clear_cache()
        except Exception:
            _LOGGER.exception("Echoes could not complete the save request")
            if result["status"] != "saved":
                result["message"] = "Could not save this flag. Try again."

    st.session_state[_RESULT] = result
    st.rerun()


def render_echoes() -> None:
    st.set_page_config(
        page_title="Echoes | Viaterra",
        page_icon="⚓",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    render_header(header_key="echoes", subtitle="Every place holds a memory")
    render_navigation(active_page="Echoes")

    password = owner_password()
    authorized = bool(password and st.session_state.get(_AUTHORIZED, False))
    if not authorized:
        st.session_state.pop(_SAVE_TOKEN, None)

    if authorized:
        if _SAVE_TOKEN not in st.session_state:
            st.session_state[_SAVE_TOKEN] = secrets.token_urlsafe(24)
        if st.button("Lock editing", type="tertiary"):
            st.session_state[_AUTHORIZED] = False
            st.session_state.pop(_SAVE_TOKEN, None)
            st.session_state.pop(_CONFIRMATION, None)
            st.session_state.pop(_RESULT, None)
            st.rerun()
    elif password:
        with st.popover("Unlock editing"):
            with st.form("echoes_login", clear_on_submit=True):
                supplied = st.text_input("Owner password", type="password")
                login = st.form_submit_button("Unlock")
            if login:
                if hmac.compare_digest(supplied.encode(), password.encode()):
                    st.session_state[_AUTHORIZED] = True
                    st.rerun()
                st.error("Incorrect password.")

    request = render_atlas_map(
        interactive=True,
        decorations=False,
        save_enabled=authorized,
        save_token=st.session_state.get(_SAVE_TOKEN),
        save_result=st.session_state.get(_RESULT) if authorized else None,
        recently_saved=st.session_state.get(_RECENTLY_SAVED),
    )
    if request is not None:
        save_selected_place(request, authorized=authorized)

    st.caption("Place search data © OpenStreetMap contributors, delivered by Photon.")
