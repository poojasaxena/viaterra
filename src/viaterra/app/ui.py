
"""Shared presentation components for Viaterra."""

import streamlit as st

from viaterra.processing.paths import VIATERRA_HEADER




def render_header() -> None:
    """Render the compact Viaterra homepage header."""

    import base64

    svg_base64 = base64.b64encode(
        VIATERRA_HEADER.read_bytes()
    ).decode("ascii")

    st.html(
        f"""
        <style>
            /* Streamlit page chrome */
            [data-testid="stToolbar"],
            [data-testid="stDecoration"],
            [data-testid="stHeader"] {{
                display: none !important;
            }}

            [data-testid="stMainBlockContainer"] {{
                padding-top: 0.5rem !important;
            }}

            /* Viaterra header */
            .viaterra-header {{
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                width: 100%;
                padding: 0;
                margin: 0;
            }}

            .viaterra-eyebrow {{
                color: #899371;
                font-size: 0.65rem;
                font-weight: 500;
                letter-spacing: 0.25em;
                text-transform: uppercase;
                line-height: 1.2;
                margin: 0 0 0.1rem;
            }}

            .viaterra-svg {{
                display: block;
                width: min(100%, 340px);
                height: auto;
                margin: 0;
            }}

            .viaterra-ornament {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.6rem;
                margin: 0.1rem auto 0.3rem;
                color: #C7A165;
            }}

            .viaterra-ornament::before,
            .viaterra-ornament::after {{
                content: "";
                width: 55px;
                height: 1px;
                background: #C7A165;
            }}

            .viaterra-symbol {{
                font-size: 1.1rem;
                line-height: 1;
            }}

            .viaterra-subtitle {{
                font-family: Georgia, "Times New Roman", serif;
                font-size: 0.85rem;
                font-style: italic;
                color: #557786;
                line-height: 1.4;
                margin: 0;
                white-space: nowrap;
            }}

            @media (max-width: 640px) {{
                .viaterra-svg {{
                    width: min(100%, 300px);
                }}

                .viaterra-subtitle {{
                    white-space: normal;
                    font-size: 0.8rem;
                }}
            }}
        </style>

        <header class="viaterra-header">
            <div class="viaterra-eyebrow">
               ✦ A Personal Travel Atlas ✦
            </div>
            <img
                class="viaterra-svg"
                src="data:image/svg+xml;base64,{svg_base64}"
                alt="Viaterra"
            >

            <div class="viaterra-ornament">
                <span class="viaterra-symbol">⚓</span>
            </div>

            <p class="viaterra-subtitle">
                Journeys across the world, places that stay,
                and memories gathered along the way.
            </p>
        </header>
        """
    )



def render_welcome() -> None:
    """Render the homepage introduction."""

    st.subheader("A world of journeys")

    st.write(
        "An atlas of places explored, roads travelled, "
        "oceans crossed, and moments remembered."
    )


def render_theme_preview() -> None:
    """Preview basic Streamlit components and their theme."""

    st.subheader("Discover Viaterra")

    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        with st.container(border=True):
            st.markdown("#### The Atlas")
            st.write("Explore the world through the places visited.")

    with col2:
        with st.container(border=True):
            st.markdown("#### My Journeys")
            st.write("Rediscover trips, routes, and destinations.")

    with col3:
        with st.container(border=True):
            st.markdown("#### Memories")
            st.write("Collect moments and places worth remembering.")
