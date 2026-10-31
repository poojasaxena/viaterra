"""Viaterra — My Journeys."""

import streamlit as st

from viaterra.app.ui import render_header
from viaterra.app.navigation import render_navigation


st.set_page_config(
    page_title="My Journeys | Viaterra",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_header()
render_navigation(active_page="My Journeys")

st.subheader("My Journeys")
st.caption("This chapter of Viaterra is taking shape.")
