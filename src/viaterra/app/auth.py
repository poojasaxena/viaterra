"""Owner-only access to the travel atlas."""

import streamlit as st


def require_owner() -> None:
    """Stop the page before it loads data unless the Google account is the owner."""
    try:
        owner_email = str(st.secrets.get("VIATERRA_OWNER_EMAIL", "")).strip().casefold()
        auth = st.secrets.get("auth", {})
    except FileNotFoundError:
        owner_email, auth = "", {}

    if not owner_email or not auth:
        st.error("Viaterra sign-in is not configured.")
        st.stop()

    if not st.user.is_logged_in:
        st.title("Viaterra")
        st.caption("A private travel atlas.")
        st.button("Sign in with Google", on_click=st.login)
        st.stop()

    email = str(st.user.get("email", "")).strip().casefold()
    if st.user.get("email_verified") is not True or email != owner_email:
        st.error("This Google account does not have access to Viaterra.")
        st.button("Sign out", on_click=st.logout)
        st.stop()

    with st.sidebar:
        st.button("Sign out", on_click=st.logout)
