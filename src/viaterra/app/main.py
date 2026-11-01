"""Viaterra — Personal Travel Atlas."""

import streamlit as st

from viaterra.app.ui import render_header
from viaterra.app.navigation import render_navigation
from viaterra.app.components.atlas_map import render_atlas_map


st.set_page_config(
    page_title="Viaterra | Personal Travel Atlas",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_header()
render_navigation(active_page="Viaterra")
render_atlas_map()
