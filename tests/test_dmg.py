"""The Icon Manager's .dmg reader (src/offline/icon-manager/dmg.py): UDIF
chunks, Apple's compressors, decmpfs, and a real Firefox image when one is
in ~/Downloads."""

import bz2
import lzma
import plistlib
import struct
import sys
import zlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src/offline/icon-manager"))

import dmg  # noqa: E402


def _udif(path: Path, disk: bytes, kinds: list[int]) -> None:
    """A UDIF image of `disk`, one 4 KiB chunk of each kind in turn."""
    size = 4096
    data, chunks = bytearray(), []
    for n, start in enumerate(range(0, len(disk), size)):
        piece, kind = disk[start:start + size], kinds[n % len(kinds)]
        if kind == 2:
            assert piece == bytes(len(piece))
            packed = b""
        else:
            packed = {1: lambda b: b, 0x80000005: zlib.compress, 0x80000006: bz2.compress,
                      0x80000008: lzma.compress, 0x80000004: _adc_literal}[kind](piece)
        chunks.append(struct.pack(">IIQQQQ", kind, 0, start // 512, len(piece) // 512,
                                  len(data), len(packed)))
        data += packed
    chunks.append(struct.pack(">IIQQQQ", 0xFFFFFFFF, 0, len(disk) // 512, 0, len(data), 0))
    mish = (b"mish" + struct.pack(">IQQQII", 1, 0, len(disk) // 512, 0, 0, 0)
            + bytes(200 - 40) + struct.pack(">I", len(chunks)) + b"".join(chunks))
    xml = plistlib.dumps({"resource-fork": {"blkx": [{"Name": "whole disk (Apple_HFS : 0)",
                                                      "Data": mish}]}})
    koly = bytearray(512)
    koly[:4] = b"koly"
    struct.pack_into(">QQ", koly, 0xD8, len(data), len(xml))
    path.write_bytes(bytes(data) + xml + bytes(koly))


def _adc_literal(piece: bytes) -> bytes:
    out = bytearray()
    for start in range(0, len(piece), 128):
        run = piece[start:start + 128]
        out += bytes([0x80 | (len(run) - 1)]) + run
    return bytes(out)


def test_udif_chunks_read_back(tmp_path):
    disk = bytearray()
    for n in range(12):
        disk += bytes(4096) if n % 6 == 5 else bytes((n * 7 + k) % 251 for k in range(4096))
    image = tmp_path / "disk.dmg"
    _udif(image, bytes(disk), [1, 0x80000005, 0x80000006, 0x80000008, 0x80000004, 2])
    udif = dmg.Udif(str(image))
    assert udif.size == len(disk)
    assert udif.read(0, len(disk)) == bytes(disk)
    # Reads across chunk boundaries.
    assert udif.read(4000, 9000) == bytes(disk[4000:13000])
    assert udif.partitions == [("whole disk (Apple_HFS : 0)", 0)]


def test_no_volume_is_an_error(tmp_path):
    image = tmp_path / "empty.dmg"
    _udif(image, bytes(8192), [1])
    with pytest.raises(dmg.DmgError):
        dmg.open_volume(str(image))


def test_adc_back_references():
    # "abc" then a 2-byte code: 3 bytes from 3 back, then a 3-byte code: 6
    # bytes from 6 back.
    src = bytes([0x82]) + b"abc" + bytes([0x00, 0x02]) + bytes([0x42, 0x00, 0x05])
    assert dmg.adc_decode(src) == b"abcabcabcabc"


def test_lzvn_literal_and_matches():
    # Small literal "ab", small-distance match (L=0, M=4, D=2), end.
    src = bytes([0xE2]) + b"ab" + bytes([0x08, 0x02]) + bytes([0x06]) + bytes(8)
    assert dmg.lzvn_decode(src) == b"ababab"
    # The same distance reused by a small match opcode.
    src = bytes([0xE2]) + b"xy" + bytes([0x00, 0x02, 0xF3, 0x06]) + bytes(8)
    assert dmg.lzvn_decode(src) == b"xy" + b"xyx" + b"yxy"


def test_lzfse_raw_and_lzvn_blocks():
    raw = b"bvx-" + struct.pack("<I", 5) + b"hello"
    vn_payload = bytes([0xE2]) + b"ab" + bytes([0x08, 0x02, 0x06]) + bytes(8)
    vn = b"bvxn" + struct.pack("<II", 6, len(vn_payload)) + vn_payload
    assert dmg.lzfse_decode(raw + vn + b"bvx$") == b"hello" + b"ababab"


def test_decmpfs_inline_and_resource_fork():
    text = b"Info.plist " * 50
    header = lambda kind, size: b"fpmc" + struct.pack("<IQ", kind, size)  # noqa: E731
    assert dmg.decmpfs(header(3, len(text)) + zlib.compress(text), None) == text
    assert dmg.decmpfs(header(3, 3) + b"\xffabc", None) == b"abc"
    # zlib in the resource fork: a 256-byte header, then the block table.
    blocks = [zlib.compress(text[:300]), zlib.compress(text[300:])]
    table = struct.pack("<I", 2)
    offset = 4 + 8 * 2
    for block in blocks:
        table += struct.pack("<II", offset, len(block))
        offset += len(block)
    body = table + b"".join(blocks)
    rsrc = struct.pack(">I", 0x100) + bytes(0x100 - 4) + struct.pack(">I", len(body)) + body
    assert dmg.decmpfs(header(4, len(text)), lambda: rsrc) == text


FIREFOX = Path.home() / "Downloads/Firefox 158.0.dmg"


@pytest.mark.skipif(not FIREFOX.is_file(), reason="no Firefox .dmg in ~/Downloads")
def test_firefox_dmg_icon():
    volume = dmg.open_volume(str(FIREFOX))
    assert isinstance(volume, dmg.Hfs)
    assert dmg.find_apps(volume) == ["Firefox.app"]
    assert dmg.app_name(volume, "Firefox.app") == "Firefox"
    icns = dmg.app_icon(volume, "Firefox.app")
    assert icns[:4] == b"icns" and struct.unpack(">I", icns[4:8])[0] == len(icns)


# ── Assets.car: Icon Composer's layered icons ─────────────────────────

import car  # noqa: E402


def _csi(name: str, tlv: dict[int, bytes], payload: bytes, key: dict,
         fmt: bytes = b"\0\0\0\0", size=(0, 0)) -> "car.Rendition":
    blob = b"".join(struct.pack("<II", k, len(v)) + v for k, v in tlv.items())
    header = (b"ISTC" + struct.pack("<IIIII", 1, 0, size[0], size[1], 100) + fmt[::-1]
              + struct.pack("<IIHH", 0, 0, 0, 0) + name.encode().ljust(128, b"\0")
              + struct.pack("<IIII", len(blob), 0, 0, 0))
    return car.Rendition(key, header + blob + payload)


def _ref(part: int, identifier: int) -> bytes:
    return struct.pack("<I", 16) + struct.pack("<8H", 1, 85, 2, part, 17, identifier, 0, 0)


def test_car_colour_and_gradient():
    grey = _csi("A/Color-1", {}, b"RLOC" + struct.pack("<III2d", 1, 2, 2, 0.5, 1.0), {})
    assert car.color(grey) == (0.5, 0.5, 0.5, 1.0)
    rgb = _csi("A/Color-2", {}, b"RLOC" + struct.pack("<III4d", 1, 3, 4, 0.1, 0.2, 0.3, 1.0), {})
    assert car.color(rgb) == (0.1, 0.2, 0.3, 1.0)
    stop = lambda at, name: struct.pack("<fI", at, len(name) + 1) + name.encode() + b"\0"  # noqa: E731
    grad = _csi("A/Gradient-1", {}, b"ARGG" + struct.pack("<III4f", 2, 1, 0, 0.5, 0, 0.5, 1)
                + stop(0, "A/Color-1") + stop(1, "A/Color-2"), {})
    assert car.gradient(grad) == {"start": (0.5, 0.0), "end": (0.5, 1.0),
                                  "stops": [(0.0, "A/Color-1"), (1.0, "A/Color-2")]}


def test_car_stack_and_group_entries():
    entry = lambda rect, ref: struct.pack("<Iiiiii", 0, *rect, 0) + struct.pack("<f", 1.0) + ref  # noqa: E731
    stack = _csi("AppIcon.iconstack", {1012: struct.pack("<II", 2, 0)
                                       + entry((0, 0, 0, 0), _ref(247, 7))
                                       + entry((0, 0, 0, 0), _ref(246, 9))},
                 b"DWAR" + bytes(8), {car.PART: car.PART_STACK})
    parts = car.entries(stack)
    assert [p["ref"] for p in parts] == [{1: 85, 2: 247, 17: 7}, {1: 85, 2: 246, 17: 9}]
    # A group: one layer placed on the 1024 canvas, filled with a colour.
    name = b"A/Color-1\0"
    fills = struct.pack("<I", 1) + bytes(12) + struct.pack("<I", len(name)) + name
    group = _csi("IconGroup", {1012: struct.pack("<II", 1, 0) + entry((-128, -128, 1280, 1280), _ref(181, 3)),
                               1020: fills}, b"DWAR" + bytes(8), {car.PART: car.PART_GROUP})
    (layer,) = car.entries(group)
    assert layer["rect"] == (-128, -128, 1280, 1280)
    assert layer["fill"] == "A/Color-1"


def test_car_raw_data_may_be_lzfse():
    svg = b"<svg/>"
    plain = _csi("image.svg", {}, b"DWAR" + struct.pack("<II", 0, len(svg)) + svg, {})
    assert plain.raw() == svg
    packed = b"bvx-" + struct.pack("<I", len(svg)) + svg + b"bvx$"
    compressed = _csi("image.svg", {}, b"DWAR" + struct.pack("<II", 1, len(packed)) + packed, {})
    assert compressed.raw() == svg


DMGS = {"Firefox 158.0": "Firefox.app", "ChatGPT_Classic": "ChatGPT Classic.app"}


@pytest.mark.parametrize("image,bundle", sorted(DMGS.items()))
def test_dark_render_from_a_real_dmg(image, bundle):
    """The DarkAqua stack drawn: a dark tile (macOS' dark grey gradient)
    under the app's own drawing, and the Tintable mask."""
    path = Path.home() / f"Downloads/{image}.dmg"
    if not path.is_file():
        pytest.skip(f"no {path.name} in ~/Downloads")
    pytest.importorskip("PyQt6.QtGui")
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtGui import QGuiApplication
    QGuiApplication.instance() or QGuiApplication([])
    volume = dmg.open_volume(str(path))
    data, icon_name = dmg.app_car(volume, bundle)
    catalog = car.Car(data)
    assert {"NSAppearanceNameAqua", "NSAppearanceNameDarkAqua", "ISAppearanceTintable"} <= set(catalog.appearances)
    stack = catalog.stack_names()[0]
    dark = car.render_icon(catalog, stack, catalog.appearances["NSAppearanceNameDarkAqua"])
    assert dark.width() == 1024
    tile = dark.pixelColor(130, 512)                      # left of the drawing
    assert tile.alpha() == 255 and tile.value() < 70 and tile.hsvSaturation() < 40
    assert dark.pixelColor(20, 20).alpha() == 0           # outside the rounded square
    glyph = car.render_glyph(catalog, stack)
    assert glyph.pixelColor(130, 512).value() < 20


def test_car_deepmap2_bitmap():
    """Compression 11 ('dmp2'): rows in chunks of a u32 length and an LZFSE
    stream (Steam's whole-canvas layer)."""
    pytest.importorskip("PyQt6.QtGui")
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtGui import QGuiApplication
    QGuiApplication.instance() or QGuiApplication([])
    w, h, rows = 4, 4, 2
    chunks = b""
    for top in range(0, h, rows):
        raw = bytes([0x20, 0x8B, 0xB8, 0xFF] * w * rows) if top == 0 else b"\xff" * 4 * w * rows
        stream = b"bvx-" + struct.pack("<I", len(raw)) + raw + b"bvx$"
        chunks += struct.pack("<I", len(stream)) + stream
    body = b"dmp2" + bytes([3, 1, 0x0A, 4]) + struct.pack("<HH", w, rows) + chunks
    payload = b"MLEC" + struct.pack("<III", 0, 11, len(body) + 16) + struct.pack("<IIII", 1, 4, len(body), 0) + body
    image = car.bitmap(_csi("image.png", {}, payload, {}, b"ARGB", (w, h)))
    assert image is not None and image.width() == w
    assert image.pixelColor(0, 0).getRgb() == (0xB8, 0x8B, 0x20, 255)
    assert image.pixelColor(3, 3).getRgb() == (255, 255, 255, 255)


def test_steam_dmg_layered_icon():
    """Steam's .icns is its old round logo; macOS 26 shows the layered icon
    (one bitmap layer, deepmap2), which is what the light icon must be."""
    path = Path.home() / "Downloads/steam.dmg"
    if not path.is_file():
        pytest.skip("no steam.dmg in ~/Downloads")
    pytest.importorskip("PyQt6.QtGui")
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtGui import QGuiApplication
    QGuiApplication.instance() or QGuiApplication([])
    volume = dmg.open_volume(str(path))
    catalog = car.Car(dmg.app_car(volume, "Steam.app")[0])
    light = car.render_icon(catalog, "Steam.iconstack", catalog.appearances["NSAppearanceNameAqua"])
    # The square body, opaque to its corners' start (the round .icns is not).
    assert light.pixelColor(130, 512).alpha() == 255
    assert light.pixelColor(512, 130).alpha() == 255
    assert light.pixelColor(20, 20).alpha() == 0
    assert light.pixelColor(512, 940).alpha() > 0          # its drop shadow
