"""The icon pack's Apple app icons: macOS Tahoe's own, as pre-scaled PNGs.

An SVG embedding a 512 px PNG aliases at Dock size (the SVG renderer
downscales it 12x with no averaging), so those icons ship as area-averaged
PNGs in sized directories instead, found by KIconLoader only because the
themes list .png in KDE-Extensions."""

import subprocess
import tarfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TARBALL = REPO / "src/offline/icons/MacTahoeLiquidKde-Icons.tar.zst"
SIZES = ("48", "64", "96", "128", "256", "512")


@pytest.fixture(scope="module")
def pack(tmp_path_factory) -> dict:
    out = tmp_path_factory.mktemp("icons")
    tar = out / "icons.tar"
    subprocess.run(["zstd", "-d", "-q", "-o", str(tar), str(TARBALL)], check=True)
    with tarfile.open(tar) as archive:
        names = set(archive.getnames())
        themes = {t: archive.extractfile(f"{t}/index.theme").read().decode()
                  for t in ("MacTahoeLiquidKde-Icons", "MacTahoeLiquidKde-Icons-dark")}
    return {"names": names, "themes": themes}


def test_apple_icons_are_prescaled_pngs(pack):
    names = pack["names"]
    for icon in ("calc", "terminal", "file-manager", "preferences-system",
                 "org.kde.konsole", "org.kde.dolphin", "systemsettings"):
        for size in SIZES:
            assert f"MacTahoeLiquidKde-Icons/apps/{size}/{icon}.png" in names, (icon, size)
        # No SVG left in apps/scalable: KIconTheme would pick it first.
        assert f"MacTahoeLiquidKde-Icons/apps/scalable/{icon}.svg" not in names, icon
    # The dark theme reaches the same files.
    for size in SIZES:
        assert f"MacTahoeLiquidKde-Icons-dark/apps/{size}" in names
    # Firefox, Steam, ChatGPT and Claude are the macOS apps' own icons (from
    # their .dmg: Firefox.app's .icns, the others' layered icon as macOS 26
    # shows it), every name of the app with them; Firefox Nightly and
    # Developer Edition keep the pack's drawings. The Anthropic "AI" logo
    # the pack shipped as claude.svg stays gone.
    for icon in ("firefox", "org.mozilla.firefox", "firefox-esr",
                 "steam", "com.valvesoftware.Steam", "steam-native",
                 "chatgpt", "com.openai.chat", "openai",
                 "claude-desktop", "com.anthropic.Claude", "claude"):
        for size in SIZES:
            assert f"MacTahoeLiquidKde-Icons/apps/{size}/{icon}.png" in names, (icon, size)
        assert f"MacTahoeLiquidKde-Icons/apps/scalable/{icon}.svg" not in names, icon
    assert "MacTahoeLiquidKde-Icons/apps/scalable/firefox-nightly.svg" in names


@pytest.mark.parametrize("theme", ["MacTahoeLiquidKde-Icons", "MacTahoeLiquidKde-Icons-dark"])
def test_themes_list_the_png_directories(pack, theme):
    text = pack["themes"][theme]
    assert "KDE-Extensions=.png,.svg" in text
    directories = next(l for l in text.splitlines() if l.startswith("Directories=")).split("=", 1)[1].split(",")
    assert directories.index("apps/48") < directories.index("apps/scalable")
    for size in SIZES:
        assert f"apps/{size}" in directories
        assert f"[apps/{size}]\nSize={size}\nContext=Applications\nType=Threshold" in text
