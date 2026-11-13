"""Footprints, the ordered journeys in Viaterra."""

import hmac
import logging
import secrets

import streamlit as st

from viaterra.app.components.atlas_map import render_atlas_map
from viaterra.app.components.echoes_page import owner_password, selected_place
from viaterra.app.navigation import render_navigation
from viaterra.app.ui import render_header
from viaterra.db.capture import find_nearby, insert_visited_place
from viaterra.db.queries import get_visited_places
from viaterra.db.footprints import available_stops, journey_stops, list_journeys, save_journey

_LOGGER = logging.getLogger(__name__)
_DRAFT = "footprints_draft"
_SELECTION = "footprints_journey"
_SELECT_SAVED = "footprints_select_saved"


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
            st.session_state[_DRAFT] = {"id": None, "keys": [], "token": secrets.token_urlsafe(24)}
        if edit.button("Edit journey", disabled=journey_id is None):
            st.session_state["footprints_title"] = journeys[journey_id]
            st.session_state[_DRAFT] = {
                "id": journey_id, "keys": [place["place_key"] for place in stops],
                "token": secrets.token_urlsafe(24),
                "country": stops[0].get("country_code") if stops else None,
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
        draft.setdefault("token", secrets.token_urlsafe(24))
        request = render_atlas_map(
            interactive=True, decorations=False, journey=True,
            places_loader=list,
            journey_editor={
                "token": draft["token"],
                "title": st.session_state.get("footprints_title", ""),
                "keys": [key for key in draft["keys"] if key in places],
                "places": list(places.values()),
                "country": draft.get("country"),
            },
            save_result=draft.get("result"),
        )
        handle_journey_action(request, draft, places)
        return

    render_atlas_map(interactive=True, decorations=False, journey=True,
                     places_loader=lambda: stops)
    if not journeys:
        st.info("No journeys yet.")


def handle_journey_action(request: object, draft: dict, places: dict[str, dict]) -> None:
    if not isinstance(request, dict) or request.get("token") != draft["token"]:
        return
    request_id = request.get("id")
    if not isinstance(request_id, str) or not request_id or request_id == draft.get("request_id"):
        return
    draft["request_id"] = request_id
    if request.get("action") == "cancel":
        st.session_state.pop(_DRAFT, None)
        st.rerun()
        return
    if request.get("action") == "pick_place":
        draft["result"] = pick_journey_place(request, draft, places)
        st.rerun()
        return
    if request.get("action") != "save_journey":
        return

    title, keys = request.get("title"), request.get("keys")
    if (
        not isinstance(title, str) or not title.strip() or len(title) > 120
        or not isinstance(keys, list) or not keys
        or any(not isinstance(key, str) or key not in places for key in keys)
    ):
        draft["result"] = {"id": request_id, "message": "Enter a title and select saved stops."}
        st.rerun()
        return

    try:
        journey_id = save_journey(title, keys, draft["id"])
    except Exception:
        _LOGGER.exception("Could not save journey")
        draft["result"] = {"id": request_id, "message": "Could not save. Your route is still here."}
    else:
        st.session_state[_SELECT_SAVED] = journey_id
        st.session_state.pop(_DRAFT, None)
    st.rerun()


def pick_journey_place(request: dict, draft: dict, places: dict[str, dict]) -> dict:
    """Reuse a nearby saved pin or capture the selected search result."""
    result = {"id": request["id"]}
    try:
        place = selected_place(request.get("place"))
    except ValueError as exc:
        return {**result, "message": str(exc)}

    confirmation = draft.pop("place_confirmation", None)
    try:
        latitude, longitude = place["latitude"], place["longitude"]
        nearby = list(find_nearby(latitude, longitude))
        nearby_ids = {key for key, _, _ in nearby}
        reuse_key = request.get("reuse_key")
        confirmed = (
            confirmation is not None
            and request.get("confirm") == confirmation["id"]
            and place == confirmation["place"]
        )
        if isinstance(reuse_key, str):
            if confirmed and reuse_key in nearby_ids and reuse_key in places:
                return {**result, "picked_place": places[reuse_key]}
            return {**result, "message": "That saved pin is unavailable. Search again."}

        if nearby and not (confirmed and nearby_ids <= confirmation["keys"]):
            options = [
                {"key": key, "name": name, "distance": distance}
                for key, name, distance in nearby if key in places
            ]
            draft["place_confirmation"] = {
                "id": request["id"], "place": place, "keys": nearby_ids,
            }
            return {**result, "nearby": options}

        created = insert_visited_place(
            name=place["name"], latitude=latitude, longitude=longitude,
            country_alpha2=place["country_alpha2"], country_name=place["country"],
        )
        clear_cache = getattr(get_visited_places, "clear", None)
        if callable(clear_cache):
            clear_cache()
        updated = available_stops()
        if isinstance(created, str) and created in updated and created not in places:
            return {**result, "picked_place": updated[created]}

        # Older capture helpers may return no key. Match the new row by place and position.
        matches = [
            item for key, item in updated.items()
            if key not in places and item["name"] == place["name"]
            and abs(item["latitude"] - latitude) < 0.000001
            and abs(item["longitude"] - longitude) < 0.000001
        ]
        if len(matches) == 1:
            return {**result, "picked_place": matches[0]}
        return {**result, "message": "Pin saved. Search again to select it from nearby pins."}
    except Exception:
        _LOGGER.exception("Could not pick a place for the journey")
        return {**result, "message": "Could not add this place. Your route is still here."}
