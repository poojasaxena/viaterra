
"""Centralized configuration and filesystem paths for Viaterra."""

from pathlib import Path
import tomllib


# -------------------------------------------------
# Project location
# -------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT / "config.toml"


# -------------------------------------------------
# Configuration
# -------------------------------------------------

def load_config() -> dict:
    """Load Viaterra's configuration."""

    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(
            f"Viaterra configuration missing: {CONFIG_PATH}"
        )

    with CONFIG_PATH.open("rb") as file:
        return tomllib.load(file)


# -------------------------------------------------
# Path resolution
# -------------------------------------------------

def resolve_path(value: str | Path) -> Path:
    """Resolve absolute or project-relative paths."""

    path = Path(value).expanduser()

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


def configured_asset(*keys: str) -> Path | None:
    """Resolve an asset from a nested configuration section.

    Example:
        configured_asset("illustrations", "travel", "italy_postcard")
    """

    value = load_config()

    for key in keys:
        if not isinstance(value, dict):
            return None

        value = value.get(key)

        if value is None:
            return None

    if not isinstance(value, str) or not value:
        return None

    path = resolve_path(value)

    return path if path.is_file() else None


def require_asset(*keys: str) -> Path:
    """Resolve a required asset or raise a descriptive error."""

    path = configured_asset(*keys)

    if path is None:
        raise FileNotFoundError(
            f"Missing configured asset: {'.'.join(keys)}"
        )

    return path


# -------------------------------------------------
# Convenient accessors
# -------------------------------------------------

def header_path(name: str) -> Path:
    return require_asset("headers", name)


def branding_path(name: str) -> Path | None:
    return configured_asset("branding", name)


def illustration_path(name: str, *nested: str) -> Path | None:
    return configured_asset("illustrations", name, *nested)


# -------------------------------------------------
# Existing constants — compatibility layer
# -------------------------------------------------

def configured_directory(name: str) -> Path:
    return resolve_path(load_config()["directories"][name])


DATA_DIR = configured_directory("data")
ASSETS_DIR = configured_directory("assets")
HEADER_DIR = configured_directory("headers")
BRANDING_DIR = configured_directory("branding")
GALLERY_DIR = configured_directory("gallery")
ILLUSTRATIONS_DIR = configured_directory("illustrations")
COMPASS_DIR = configured_directory("compasses")

ANCHOR_OCTOPUS = require_asset("branding", "anchor_octopus")
ANCHOR_DOLPHIN = require_asset("branding", "anchor_dolphin")
ANCHOR_BIRDS = require_asset("branding", "anchor_birds")
AUTHOR_LOGO = require_asset("branding", "author_logo")
MARITIME_LOGO = require_asset("branding", "maritime_logo")

SAILBOAT_VINTAGE = require_asset("illustrations", "sailboat_vintage")
SAILBOAT_PENNANT = require_asset("illustrations", "sailboat_pennant")
SAILBOAT_MEDITERRANEAN = require_asset("illustrations", "sailboat_mediterranean")

COMPASS = require_asset("illustrations", "compass")

LEFT_HEADER_IMAGE = MARITIME_LOGO
VIATERRA_HEADER = header_path("viaterra")
