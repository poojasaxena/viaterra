
"""Shared page navigation for Viaterra."""

import base64

import streamlit as st


PAGES = [
    ("Viaterra", "main.py"),
    ("The Atlas", "pages/1_The_Atlas.py"),
    ("My Journeys", "pages/2_My_Journeys.py"),
    ("Places & Memories", "pages/3_Places_and_Memories.py"),
    ("Travel Statistics", "pages/4_Travel_Statistics.py"),
    ("About Viaterra", "pages/5_About_Viaterra.py"),
]


# -------------------------------------------------
# Navigation styling
# -------------------------------------------------

def apply_navigation_style() -> None:
    """Apply Viaterra's maritime navigation styling."""

    st.html(
        """
        <style>
        /* Hide default sidebar navigation */
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
            display: none !important;
        }

        /* Compact centered desktop navigation */
        .st-key-viaterra_desktop_nav {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            gap: 0.7rem !important;
            width: 100%;
            margin: 0 auto 0.8rem;
        }

        .st-key-viaterra_desktop_nav
        [data-testid="stElementContainer"],
        .st-key-viaterra_desktop_nav
        [data-testid="stPageLink"] {
            width: auto !important;
            min-width: 0 !important;
            flex: 0 0 auto !important;
        }

        /* Navigation links */
        .st-key-viaterra_desktop_nav
        a[data-testid="stPageLink-NavLink"] {
            display: inline-flex !important;
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 0 !important;
            min-height: 0 !important;
            width: auto !important;
        }

        .st-key-viaterra_desktop_nav
        a[data-testid="stPageLink-NavLink"] p {
            color: #557786 !important;
            font-family: Georgia, serif !important;
            font-size: 13px !important;
            font-weight: 400 !important;
            white-space: nowrap;
            margin: 0 !important;
        }

        /* Hover */
        .st-key-viaterra_desktop_nav
        a[data-testid="stPageLink-NavLink"]:hover p {
            color: #17466C !important;
        }

        /* Active page */
        .st-key-viaterra_desktop_nav
        a[aria-current="page"] p,
        .st-key-viaterra_desktop_nav
        a[aria-disabled="true"] p {
            color: #17466C !important;
            font-weight: 700 !important;
            text-decoration: underline !important;
            text-underline-offset: 4px;
            text-decoration-color: #C7A165 !important;
            opacity: 1 !important;
        }

        /* Sailing boat separators */
        .viaterra-nav-separator {
            color: #17466C;
            font-family: Georgia, serif;
            font-size: 14px;
            line-height: 1;
        }

        .viaterra-nav-separator img {
            display: block;
            width: 16px;
            height: 16px;
        }

        /* Mobile navigation */
        .st-key-viaterra_mobile_nav {
            display: none !important;
        }

        @media screen and (max-width: 640px) {
            .st-key-viaterra_desktop_nav {
                display: none !important;
            }

            .st-key-viaterra_mobile_nav {
                display: block !important;
                margin-bottom: 0.75rem;
            }

            .st-key-viaterra_mobile_nav button {
                background: #E6EFED !important;
                color: #17466C !important;
                border: 1px solid #83C9CB !important;
                font-family: Georgia, serif !important;
            }
        }
        </style>
        """
    )


# -------------------------------------------------
# Navigation rendering
# -------------------------------------------------

def render_navigation(active_page: str) -> None:
    """Render desktop navigation and mobile menu."""

    apply_navigation_style()

    with st.container(
        key="viaterra_desktop_nav",
        horizontal=True,
        horizontal_alignment="center",
        vertical_alignment="center",
        gap="small",
    ):
        for index, (label, path) in enumerate(PAGES):
            if index:
                st.html(
                    '<span class="viaterra-nav-separator">❦</span>',
                    width="content",
                )

            st.page_link(
                path,
                label=label,
                disabled=(label == active_page),
            )

    with st.container(key="viaterra_mobile_nav"):
        with st.popover("☰ Explore Viaterra"):
            for label, path in PAGES:
                st.page_link(
                    path,
                    label=label,
                    disabled=(label == active_page),
                )
