import shutil
import gzip
import tempfile
from pathlib import Path
from theme_variants import SUFFIX
from theme_switch import default_wallpaper

from steps._helpers import (
    DATA_HOME, fail, info, install_tree, install_reduced_variant, kw_write, offline, remove_tree, warn,
)

DEST_DIR = DATA_HOME / "plasma/desktoptheme"
LEGACY = ("MacTahoe-Dark", "MacTahoe-Light")
VARIANTS = ("MacTahoeLiquidKde-Dark", "MacTahoeLiquidKde-Light")

def _prepare_golden_dark(source: Path, target: Path) -> None:
    """Stage the dark edition's surface fills; keep masks and shadows intact."""
    shutil.copytree(source, target)
    replacements = {
        "background.svgz": (("opacity:0.55;fill:#2a2a2a", "opacity:0.12;fill:#2a2a2a"),),
        "launcher-search.svgz": (
            ('opacity=".55"', 'opacity=".08"'),
            ('stop-opacity=".45"', 'stop-opacity=".03"'),
        ),
    }
    for name, pairs in replacements.items():
        path = target / "dialogs" / name
        text = gzip.decompress(path.read_bytes()).decode()
        for old, new in pairs:
            if old not in text:
                raise ValueError(f"Golden Gate surface pattern missing in {name}: {old}")
            text = text.replace(old, new)
        path.write_bytes(gzip.compress(text.encode(), mtime=0))


def install() -> None:
    src = offline("plasma-theme")
    if not src.is_dir():
        fail(f"Plasma theme source not found at {src}")
        return
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    # Purge legacy names from pre-0.6.2 installs.
    for stale in LEGACY:
        shutil.rmtree(DEST_DIR / stale, ignore_errors=True)

    n = 0
    for v in VARIANTS:
        if not (src / v).is_dir():
            continue
        with tempfile.TemporaryDirectory(prefix="mttkde-plasma-") as staging:
            source = src / v
            if v.endswith("-Dark") and default_wallpaper() == "MacGoldenGate":
                source = Path(staging) / v
                _prepare_golden_dark(src / v, source)
            if install_tree(source, DEST_DIR / v, v):
                n += 1
                install_reduced_variant(source, DEST_DIR / (v + SUFFIX), "plasma")
    info(f"{n} Plasma themes installed/reinstalled")


def uninstall() -> None:
    n = 0
    for v in VARIANTS:
        remove_tree(DEST_DIR / (v + SUFFIX))
        if remove_tree(DEST_DIR / v, v):
            n += 1
    if not kw_write("--file", "plasmarc", "--group", "Theme",
                    "--key", "name", "default"):
        warn("Active Plasma theme not reset to 'default' — "
             "kwriteconfig6 unavailable. Files are removed but "
             "Plasma will still try to load MacTahoeLiquidKde "
             "until you set plasmarc:Theme.name=default manually.")
    info(f"{n} Plasma themes removed")
