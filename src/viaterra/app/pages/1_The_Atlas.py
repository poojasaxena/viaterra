"""Viaterra — The Atlas."""

import streamlit as st

from viaterra.app.ui import render_header
from viaterra.app.navigation import render_navigation


st.set_page_config(
    page_title="The Atlas | Viaterra",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_header()
render_navigation(active_page="The Atlas")

st.subheader("The Atlas")
st.caption("This chapter of Viaterra is taking shape.")
