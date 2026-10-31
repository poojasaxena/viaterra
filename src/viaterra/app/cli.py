
"""Command-line entry point for Viaterra."""

from pathlib import Path

from streamlit.web import cli as stcli


def main() -> None:
    app_path = Path(__file__).resolve().parent / "main.py"

    stcli.main_run([str(app_path)])
