
"""Viaterra — Personal Travel Atlas."""

import streamlit as st

from viaterra.app.ui import (
    render_header,
    render_theme_preview,
    render_welcome,
)
from viaterra.app.navigation import render_navigation


st.set_page_config(
    page_title="Viaterra | Personal Travel Atlas",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_header()

render_navigation(active_page="Viaterra")

render_welcome()
render_theme_preview()


st.write("")
