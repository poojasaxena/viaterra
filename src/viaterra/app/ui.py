
"""Shared presentation components for Viaterra."""

import streamlit as st

from viaterra.processing.paths import (
    VIATERRA_HEADER,
    LEFT_HEADER_IMAGE,
    AUTHOR_LOGO,
    load_config,
)

def render_header() -> None:
    """Render the compact Viaterra homepage header."""

    config = load_config()
    author_logo_color = config["branding"].get(
        "author_logo_color", "#315B70"
    )

    viaterra_wordmark_color = config["branding"].get(
        "viaterra_wordmark_color", "#5F7482"
    )

    import base64

    svg_base64 = base64.b64encode(
        VIATERRA_HEADER.read_bytes()
    ).decode("ascii")

    left_base64 = base64.b64encode(
        LEFT_HEADER_IMAGE.read_bytes()
    ).decode("ascii")

    author_base64 = base64.b64encode(
        AUTHOR_LOGO.read_bytes()
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
                font-size: 0.60rem;
                font-family: Georgia, serif;
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

            .viaterra-svg {{
                display: block;
                width: min(100%, 340px);
                height: 90px;
                margin: 0;

                background-color: {viaterra_wordmark_color};

                -webkit-mask-image: url("data:image/svg+xml;base64,{svg_base64}");
                mask-image: url("data:image/svg+xml;base64,{svg_base64}");

                -webkit-mask-size: contain;
                mask-size: contain;

                -webkit-mask-position: center;
                mask-position: center;

                -webkit-mask-repeat: no-repeat;
                mask-repeat: no-repeat;
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


            .viaterra-author-logo {{
                position: absolute;
                top: -10px;
                right: 0;
                width: 175px;
                height: 175px;
                pointer-events: none;

                background-color: {author_logo_color};

                -webkit-mask-image: url("data:image/svg+xml;base64,{author_base64}");
                mask-image: url("data:image/svg+xml;base64,{author_base64}");

                -webkit-mask-size: contain;
                mask-size: contain;

                -webkit-mask-position: center;
                mask-position: center;

                -webkit-mask-repeat: no-repeat;
                mask-repeat: no-repeat;
            }}


            @media (max-width: 640px) {{
                .viaterra-author-logo {{
                    display: none;
                }}
            }}

            .viaterra-subtitle {{
                font-family: Georgia, "Times New Roman", serif;
                font-size: 0.85rem;
                font-style: italic;
                color: #557786;
                line-height: 1.4;
                margin: 0 0 30px;
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

            .viaterra-header {{
                position: relative;
            }}

            .viaterra-left-illustration {{
                position: absolute;
                top: -26px;
                left: 0;
                width: 215px;
                height: 215px;
                object-fit: contain;
                pointer-events: none;
                filter: saturate(1.15);
            }}

            [data-testid="stHeaderActionElements"] {{
                display: none !important;
            }}

            a.anchor-link {{
                display: none !important;
            }}

            @media (max-width: 900px) {{
                .viaterra-left-illustration {{
                    width: 110px;
                    height: 110px;
                    top: 5px;
                }}
            }}

            @media (max-width: 640px) {{
                .viaterra-left-illustration {{
                    display: none;
                }}
            }}

        </style>

        <header class="viaterra-header">
            <img
                class="viaterra-left-illustration"
                src="data:image/png;base64,{left_base64}"
                alt="Antique maritime illustration"
            >
            <div
                class="viaterra-author-logo"
                role="img"
                aria-label="Personal signature"
            ></div>
            <div class="viaterra-eyebrow">
               ✦ A Personal Travel Atlas ✦
            </div>
            <div
                class="viaterra-svg"
                role="img"
                aria-label="Viaterra"
            ></div>

            <div class="viaterra-ornament">
                <span class="viaterra-symbol">⚓</span>
            </div>

            <p class="viaterra-subtitle">
                Finding my anchor across the world
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
