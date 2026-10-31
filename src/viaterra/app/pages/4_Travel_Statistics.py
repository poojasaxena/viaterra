"""Viaterra — Travel Statistics."""

import streamlit as st

from viaterra.app.ui import render_header
from viaterra.app.navigation import render_navigation


st.set_page_config(
    page_title="Travel Statistics | Viaterra",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_header()
render_navigation(active_page="Travel Statistics")

st.subheader("Travel Statistics")
st.caption("This chapter of Viaterra is taking shape.")
