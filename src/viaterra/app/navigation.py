"""Navigation for Viaterra."""

import base64
import streamlit as st


def render_navigation(active_page: str) -> None:
    """Render the top navigation with wave separators."""

    items = [
        ("Viaterra", "/"),
        ("Footprints", "/Footprints"),
        ("Echoes", "/Echoes"),
        ("The World in Cities", "/The_World_in_Cities"),
        ("Travel Statistics", "/Travel_Statistics"),
        ("About Viaterra", "/About_Viaterra"),
    ]

    wave_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 34 14">
        <path
            d="M1 7
            C5 7, 7 4.5, 11 5
            C14 5.3, 15 7.5, 19 7
            C23 6.5, 25 4.5, 29 5.5
            C31 6, 32 6.5, 33 6"
            fill="none"
            stroke="#376E80"
            stroke-width="1.1"
            stroke-linecap="round"
        />
        <path
            d="M7 9
            C11 8.3, 14 9.5, 18 9
            C22 8.5, 25 8.2, 29 9"
            fill="none"
            stroke="#78A8AD"
            stroke-width="0.7"
            stroke-linecap="round"
            opacity="0.8"
        />
    </svg>
    """

    wave_base64 = base64.b64encode(
        wave_svg.encode("utf-8")
    ).decode("ascii")

    parts = []

    for i, (label, href) in enumerate(items):
        active_class = " active" if label == active_page else ""

        parts.append(
            f"""
            <a class="viaterra-nav-link{active_class}" href="{href}" target="_self">
                {label}
            </a>
            """
        )

        if i < len(items) - 1:
            parts.append(
                f'<span class="viaterra-nav-separator" aria-hidden="true">'
                f'<img src="data:image/svg+xml;base64,{wave_base64}" '
                f'width="25" height="10" alt="">'
                f'</span>'
            )

    html = f"""
    <style>
    .viaterra-nav {{
        display: flex;
        align-items: center;
        justify-content: center;
        flex-wrap: wrap;
        gap: 0.95rem;
        line-height: 1.2;
    }}

    .viaterra-nav-link {{
        font-family: Georgia, "Times New Roman", serif;
        font-size: 0.91rem;
        font-weight: 400;
        color: #315B70;
        text-decoration: none;
        padding: 0.05rem 0.12rem;
        white-space: nowrap;
    }}

    .viaterra-nav-link:hover {{
        color: #24495C;
        text-decoration: none;
    }}

    .viaterra-nav-link.active {{
        color: #24495C;
        font-weight: 500;
    }}

    .viaterra-nav-separator {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        width: 25px;
        height: 12px;
        margin: 0 0.1rem;
    }}

    .viaterra-nav-separator img {{
        display: block;
        width: 25px;
        height: 10px;
    }}
    </style>

    <div class="viaterra-nav-wrap">
        <nav class="viaterra-nav">
            {''.join(parts)}
        </nav>
    </div>
    """

    st.html(html)