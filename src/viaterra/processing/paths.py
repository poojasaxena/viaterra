
"""Centralized filesystem paths for Viaterra."""

from pathlib import Path
import tomllib


# -------------------------------------------------
# Project directories
# -------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = DATA_DIR / "assets"
HEADER_DIR = ASSETS_DIR / "header"
BRANDING_DIR = ASSETS_DIR / "branding"
GALLERY_DIR = DATA_DIR / "gallary"

CONFIG_PATH = PROJECT_ROOT / "config.toml"


# -------------------------------------------------
# Configuration
# -------------------------------------------------

def load_config() -> dict:
    """Load project configuration."""

    with CONFIG_PATH.open("rb") as file:
        return tomllib.load(file)


CONFIG = load_config()


# -------------------------------------------------
# Path resolution
# -------------------------------------------------

def resolve_path(value: str | Path) -> Path:
    """Resolve a path relative to the project root."""

    path = Path(value).expanduser()

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


def gallery_path(name: str) -> Path:
    """Return a configured gallery asset path."""

    try:
        value = CONFIG["gallary"][name]
    except KeyError as exc:
        raise KeyError(
            f"Gallery asset '{name}' is not configured."
        ) from exc

    return resolve_path(value)


# -------------------------------------------------
# Named assets
# -------------------------------------------------

VIATERRA_HEADER = gallery_path("viaterra")
