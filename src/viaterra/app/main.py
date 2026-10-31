
"""Viaterra — Personal Travel Atlas."""

import streamlit as st

from viaterra.app.ui import (
    render_header,
    render_theme_preview,
    render_welcome,
)


st.set_page_config(
    page_title="Viaterra | Personal Travel Atlas",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_header()

render_welcome()

st.write("")

render_theme_preview()
