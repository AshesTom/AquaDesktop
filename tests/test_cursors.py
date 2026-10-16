"""The macOS pointer (AquaDesktop).

macOS draws the same pointers in light and dark mode: the arrow, I-beam and
resize cursors black with a white outline, the hands (link, grab, drag)
white with a black outline — Tahoe's plainer hand and Golden Gate's
returning glove alike. The bundled MacTahoeLiquidKde set is that one; its
inverted MacTahoeLiquidKde-Dark sibling stays installed but unused.
"""

import struct
import sys
import tarfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TARBALL = REPO / "src/offline/cursors/MacTahoeLiquidKde-Cursors.tar.zst"
LAF = REPO / "src/offline/look-and-feel"
sys.path.insert(0, str(REPO / "src/scripts"))

import theme_switch  # noqa: E402


@pytest.fixture(scope="module")
def cursors(tmp_path_factory) -> Path:
    import subprocess
    out = tmp_path_factory.mktemp("cursors")
    tar = out / "cursors.tar"
    subprocess.run(["zstd", "-d", "-q", "-o", str(tar), str(TARBALL)], check=True)
    with tarfile.open(tar) as archive:
        archive.extractall(out, filter="data")
    return out


def _ink(path: Path) -> float:
    """Share of the largest image's opaque pixels that are light."""
    data = path.read_bytes()
    assert data[:4] == b"Xcur"
    _header, _version, count = struct.unpack_from("<III", data, 4)
    images = []
    for i in range(count):
        kind, size, pos = struct.unpack_from("<III", data, 16 + i * 12)
        if kind == 0xFFFD0002:
            width, height = struct.unpack_from("<II", data, pos + 16)
            images.append((size, width, height, pos + 36))
    size, width, height, start = max(images)
    light = opaque = 0
    for i in range(width * height):
        b, g, r, a = data[start + 4 * i: start + 4 * i + 4]
        if a > 200:
            opaque += 1
            light += (r + g + b) / 3 > 128
    return light / opaque


def _theme(cursors: Path, name: str) -> Path:
    return cursors / "MacTahoeLiquidKde" / "cursors" / name


@pytest.mark.parametrize("name", ["pointer", "hand2", "openhand", "grabbing", "dnd-move"])
def test_hands_are_white_with_a_black_outline(cursors, name):
    assert _ink(_theme(cursors, name).resolve()) > 0.5


@pytest.mark.parametrize("name", ["default", "left_ptr", "size_hor", "size_ver"])
def test_arrows_are_black_with_a_white_outline(cursors, name):
    assert _ink(_theme(cursors, name).resolve()) < 0.5


def test_the_same_pointer_in_light_and_dark_mode():
    assert theme_switch.MACOS_CURSORS == "MacTahoeLiquidKde"
    for variant in ("Light", "Dark"):
        defaults = (LAF / f"MacTahoeLiquidKde-{variant}/contents/defaults").read_text()
        assert "cursorTheme=MacTahoeLiquidKde\n" in defaults, variant
    source = Path(theme_switch.__file__).read_text()
    assert '"MacTahoeLiquidKde-Dark" if mode == "dark" else "MacTahoeLiquidKde"' not in source
    assert source.count("MACOS_CURSORS") >= 4
