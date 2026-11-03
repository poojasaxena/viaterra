
"""Centralized configuration and filesystem paths for Viaterra."""

from pathlib import Path
import tomllib


# -------------------------------------------------
# Project directories
# -------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT / "config.toml"

DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = DATA_DIR / "assets"
HEADER_DIR = ASSETS_DIR / "header"
BRANDING_DIR = ASSETS_DIR / "branding"
GALLERY_DIR = DATA_DIR / "gallary"
ILLUSTRATIONS_DIR = ASSETS_DIR / "illustrations"
COMPASS_DIR = ILLUSTRATIONS_DIR / "compass"

ANCHOR_OCTOPUS = BRANDING_DIR / "anchor_octopus.png"
ANCHOR_DOLPHIN = BRANDING_DIR / "anchor_dolphin_octopus.png"
ANCHOR_BIRDS = BRANDING_DIR / "anchor_birds.png" # preferable
AUTHOR_LOGO = BRANDING_DIR / "author_logo.svg"
MARITIME_LOGO = BRANDING_DIR / "anchor_maritime.png"

SAILBOAT_VINTAGE =  ILLUSTRATIONS_DIR / "sailboat_vintage.png"
SAILBOAT_PENNANT = ILLUSTRATIONS_DIR / "sailboat_pennant.png"
SAILBOAT_MEDITERRANEAN = ILLUSTRATIONS_DIR / "sailboat_mediterranean.png"

COMPASS = COMPASS_DIR / "coastal_explorer.png"

LEFT_HEADER_IMAGE = MARITIME_LOGO

# -------------------------------------------------
# Header assets
# -------------------------------------------------

HEADER_FILES = {
    "Viaterra": "Viaterra.svg",
    "About Viaterra": "AboutViaterra.svg",
    "Finding My Anchor": "FindingMyAnchor.svg",
    "A Thousand Shores, One Anchor": "AThousandShoreOneAnchor.svg",
    "The Geography of Belonging": "TheGeographyOfBelonging.svg",
    "Where Horizon Begins": "WhereHorizonBegins.svg",
    "Not All Anchors Hold Us Still": "NotAllAnchorsHoldsUsStill.svg",
}

VIATERRA_HEADER = HEADER_DIR / HEADER_FILES["Viaterra"]


# -------------------------------------------------
# Branding assets
# -------------------------------------------------

PERSONAL_SIGNATURE = BRANDING_DIR / "nostalgic.svg"


# -------------------------------------------------
# Configuration
# -------------------------------------------------

def load_config() -> dict:
    """Load the project configuration."""

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


def header_path(name: str) -> Path:
    """Return the path for a named header SVG."""

    try:
        filename = HEADER_FILES[name]
    except KeyError as exc:
        raise KeyError(
            f"Unknown header '{name}'. "
            f"Available headers: {list(HEADER_FILES)}"
        ) from exc

    return HEADER_DIR / filename


def configured_asset(section: str, name: str) -> Path | None:
    """Return a configured asset if it exists."""

    value = load_config().get(section, {}).get(name)

    if not value:
        return None

    path = resolve_path(value)
    return path if path.is_file() else None


def branding_path(name: str) -> Path | None:
    """Return a configured branding asset."""

    return configured_asset("branding", name)


def illustration_path(name: str) -> Path | None:
    """Return a configured illustration."""

    return configured_asset("illustrations", name)
