#!/usr/bin/env python3
"""AquaDesktop — Icon Manager, the engine of Theme Settings' Icons page.

Gives any installed app a macOS icon from an .icns file (macosicons.com
and the like), with a light and a dark version, and keeps it in the icon
theme instead of editing the app: the Light / Dark switch then picks the
right one by itself.

How it works:
- The icons are kept, already fitted, in DATA/mac-tahoe-liquid-kde/
  icon-manager/<app id>.<light|dark>.png.
- Two hidden "overlay" icon themes are rebuilt from them,
  MacTahoeLiquidKde-Icons-custom and MacTahoeLiquidKde-Icons-dark-custom,
  each inheriting its MacTahoeLiquidKde theme: they hold only the custom
  icons. The theme switch (theme_switch.custom_icon_theme) applies the
  overlay of the mode when it exists.
- An app whose launcher names an icon file instead of an icon name gets a
  per-user copy of its launcher naming an icon the overlay can provide.

macOS icons sit on Apple's grid (an 824 px rounded square in 1024 px, ~80 %);
this theme's icons use 87.5 % (448 in 512). Each icon is cropped to its
rounded square and placed on the theme's grid so it matches the others in
the Dock.

SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import configparser
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import (
    QBitmap, QColor, QGuiApplication, QIcon, QImage, QLinearGradient, QPainter, QRegion, qGray,
)

# dmg.py and car.py live next to this file (also when loaded by path).
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
STORE = DATA / "mac-tahoe-liquid-kde/icon-manager"
STATE = CONFIG / "mac-tahoe-liquid-kde/icon-manager.json"
ICONS = DATA / "icons"
APPLICATIONS = DATA / "applications"
BASE_THEMES = {"light": "MacTahoeLiquidKde-Icons", "dark": "MacTahoeLiquidKde-Icons-dark"}
MODES = ("light", "dark")
# Hidden from the menus but on the Dock: the "Apps" launcher.
ALWAYS_LISTED = {"org.kde.mac-tahoe-liquid-kde.apps"}

# The theme's grid: a 448 px rounded square in a 512 px icon.
CANVAS = 512
SQUARE = 448
# An icon naming a file instead of an icon name gets this one instead.
CUSTOM_PREFIX = "mactahoe-custom-"
# macOS 26's own Dark renders and tinted/clear drawing masks for the icon
# pack's Apple icons, decoded from the apps' layered icons (.iconstack):
# <stem>.dark.png and <stem>.glyph.png, index.json mapping every icon name
# that shows one of them to its stem.
MACOS_STYLES = Path(__file__).resolve().parent / "macos-styles"
_MACOS_STYLE_INDEX: dict[str, str] | None = None


def macos_style(name: str) -> str | None:
    """The bundled macOS style assets' stem for icon `name`, if any."""
    global _MACOS_STYLE_INDEX
    if _MACOS_STYLE_INDEX is None:
        try:
            _MACOS_STYLE_INDEX = json.loads((MACOS_STYLES / "index.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _MACOS_STYLE_INDEX = {}
    return _MACOS_STYLE_INDEX.get(name)


def style_asset(app_id: str, kind: str) -> Path:
    """An app's own macOS style asset (`kind` "dark" or "glyph"), rendered
    from the layered icon of the .dmg its icon came from."""
    return STORE / f"{app_id}.macos-{kind}.png"


def _style_assets(app_id: str | None, stem: str | None) -> Callable[[str, object], QImage | None]:
    """The style assets an icon has: the app's own, else the bundled ones."""
    def asset(kind: str, size) -> QImage | None:
        if app_id:
            image = QImage(str(style_asset(app_id, kind)))
            if not image.isNull():
                return image.scaled(size, Qt.AspectRatioMode.IgnoreAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
        return _macos_asset(stem, kind, size)
    return asset


def _macos_asset(stem: str | None, kind: str, size) -> QImage | None:
    """A bundled asset (`kind` "dark" or "glyph") scaled to `size`."""
    if not stem:
        return None
    image = QImage(str(MACOS_STYLES / f"{stem}.{kind}.png"))
    if image.isNull():
        return None
    return image.scaled(size, Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)


def _alpha_mask(grey: QImage) -> QImage:
    """A grey-level image as an alpha mask (white = full strength)."""
    grey8 = grey.convertToFormat(QImage.Format.Format_Grayscale8)
    width, height, stride = grey8.width(), grey8.height(), grey8.bytesPerLine()
    data = bytes(grey8.constBits().asstring(stride * height))
    return QImage(data, width, height, stride, QImage.Format.Format_Alpha8).copy()


# ── .icns ─────────────────────────────────────────────────────────────


def icns_png(data: bytes) -> bytes | None:
    """The largest PNG image of an .icns file (modern .icns store PNGs for
    every size from 16 to 1024 px)."""
    if data[:4] != b"icns":
        return None
    best, best_width, offset = None, 0, 8
    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset + 4:offset + 8])[0]
        if length < 8:
            break
        body = data[offset + 8:offset + length]
        if body[:8] == b"\x89PNG\r\n\x1a\n" and len(body) >= 24:
            width = struct.unpack(">I", body[16:20])[0]
            if width > best_width:
                best, best_width = body, width
        offset += length
    return best


def load_image(path: Path) -> QImage | None:
    """An .icns or a plain image file."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if path.suffix.lower() == ".icns":
        data = icns_png(data)
        if data is None:
            return None
    image = QImage()
    if not image.loadFromData(data):
        return None
    return image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)


def grid_square(image: QImage) -> QRect:
    """The icon's rounded square (its opaque area), as a square."""
    mask = image.createAlphaMask(Qt.ImageConversionFlag.ThresholdAlphaDither)
    box = QRegion(QBitmap.fromImage(mask)).boundingRect()
    if box.isEmpty():
        box = image.rect()
    side = max(box.width(), box.height())
    return QRect(box.center().x() - side // 2, box.center().y() - side // 2, side, side)


def fit_to_grid(image: QImage, square: QRect | None = None) -> QImage:
    """Crop to the icon's rounded square (or `square`, for a drawing mask
    matching an icon) and place it on the theme's grid, 448 px in 512."""
    if square is None:
        square = grid_square(image)
    out = QImage(CANVAS, CANVAS, QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    offset = (CANVAS - SQUARE) // 2
    painter.drawImage(QRect(offset, offset, SQUARE, SQUARE), image, square)
    painter.end()
    return out


# ── Tinted (macOS 26 "Tinted" icon style) ─────────────────────────────


def accent_color() -> QColor:
    """KDE's accent colour: [General] AccentColor, else the colour scheme's
    selection colour."""
    for group, key in (("General", "AccentColor"), ("Colors:Selection", "BackgroundNormal")):
        value = _kread("kdeglobals", group, key)
        parts = [p for p in value.split(",") if p.strip()]
        if len(parts) >= 3:
            try:
                return QColor(*(int(p) for p in parts[:3]))
            except ValueError:
                pass
    return QColor("#0091ff")


def _mix(a: QColor, b: QColor, t: float, alpha: int = 255) -> QColor:
    """`a` moved by `t` (0..1) towards `b`."""
    return QColor(round(a.red() + (b.red() - a.red()) * t),
                  round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t), alpha)


def _scaled(color: QColor, factor: float) -> QColor:
    return QColor(round(color.red() * factor), round(color.green() * factor),
                  round(color.blue() * factor))


# macOS 26's icon styles, measured on a Dock capture in each style (dark
# appearance, systemBlue #0088FF accent): every tile is a vertical
# gradient, a 1 px lighter rim runs along its top, and the drawing becomes
# one glyph. Light values are mirrored until a light capture is measured.
#   Clear:  tile grey 26 at the top to 2 at the bottom, glyph grey ~240.
#   Tinted: tile the accent at 9 % down to 2 %, glyph the accent itself.
#   Dark:   tile grey 45 down to 22, glyph in the icon's own colours.


def tint(image: QImage, accent: QColor, dark: bool = True,
         glyph: QImage | None = None) -> QImage:
    """macOS 26's Tinted style: a near-black tile faintly tinted with the
    accent and the drawing in the accent (a light tile and a deeper accent
    glyph in the light appearance)."""
    if dark:
        return _redraw(image, _scaled(accent, 0.09), _scaled(accent, 0.02), accent,
                       QColor(255, 255, 255, 40), glyph)
    return _redraw(image, _mix(QColor(255, 255, 255), accent, 0.10),
                   _mix(QColor(255, 255, 255), accent, 0.22), accent.darker(115),
                   QColor(255, 255, 255, 200), glyph)


# ── Clear (macOS 26 "Clear" icon style) ───────────────────────────────


def _edge_samples(source: QImage) -> list[QColor]:
    """Opaque pixels just inside the icon's rounded square, along its four
    edges (where the drawing rarely reaches)."""
    w, h = source.width(), source.height()
    samples = []
    for i in range(16):
        t = 0.2 + 0.6 * i / 15
        for x, y in ((t * w, 0.12 * h), (t * w, 0.88 * h), (0.12 * w, t * h), (0.88 * w, t * h)):
            c = source.pixelColor(int(x), int(y))
            if c.alpha() > 200:
                samples.append(c)
    return samples


def _background_samples(source: QImage) -> list[QColor]:
    """The edge samples that are the background. A two-tone icon (Finder:
    a blue half and a white face reaching the edges) has its background in
    the coloured part, as macOS treats it: when a quarter of the edge is
    coloured, only the coloured samples count."""
    samples = _edge_samples(source)
    coloured = [c for c in samples if c.hsvSaturation() > 90 and c.value() > 60]
    return coloured if len(coloured) * 4 >= len(samples) and coloured else samples


def _background_grey(source: QImage, grey: QImage) -> int:
    """The icon background's grey level (median of _background_samples)."""
    levels = sorted(qGray(c.rgb()) for c in _background_samples(source))
    return levels[len(levels) // 2] if levels else 0


def clear(image: QImage, dark: bool, glyph: QImage | None = None) -> QImage:
    """macOS 26's Clear style: a dark glass tile and the drawing as one
    light grey glyph (a light tile and a dark glyph in the light
    appearance)."""
    if dark:
        return _redraw(image, QColor(28, 28, 30, 240), QColor(3, 3, 3, 240),
                       QColor(242, 242, 242), QColor(255, 255, 255, 40), glyph)
    return _redraw(image, QColor(250, 250, 252, 235), QColor(226, 226, 232, 235),
                   QColor(60, 60, 66), QColor(255, 255, 255, 220), glyph)


def _background_color(source: QImage) -> QColor:
    """The icon background's colour (median of _background_samples)."""
    samples = _background_samples(source)
    if not samples:
        return QColor(0, 0, 0)
    mid = len(samples) // 2
    return QColor(*(sorted(getattr(c, ch)() for c in samples)[mid] for ch in ("red", "green", "blue")))


def dark_icon(image: QImage) -> QImage:
    """macOS 26's Dark style: a dark grey tile; the drawing takes the icon's
    background colour when that is a colour (Messages' bubble turns green,
    Mail's envelope blue), else keeps its own colours (Safari, Photos)."""
    source = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    background = _background_color(source)
    colourful = background.hsvSaturation() > 90 and background.value() > 70
    return _redraw(image, QColor(46, 46, 46), QColor(22, 22, 22),
                   background.lighter(112) if colourful else None,
                   QColor(255, 255, 255, 45))


def _glyph_mask(source: QImage) -> QImage:
    """The drawing as an alpha mask, from each pixel's grey level against
    the background's, as macOS 26 maps an icon to one colour (measured on
    its Tinted Finder): what is lighter than the background is the glyph,
    at full strength from two thirds of the way to white (the Finder's
    face); what is clearly darker shows at 45 % (its eyes and smile: dim on
    the background, dark on the face). On a light background the darker
    drawing is the glyph, at full strength (Safari's dial)."""
    grey8 = source.convertToFormat(QImage.Format.Format_Grayscale8)
    background = _background_grey(source, grey8)
    # A dead zone around the background's level keeps its own gradient
    # (the Finder's blue, lighter at the top) out of the glyph.
    light_start = background + 0.35 * (255 - background)
    light_span = max(1.0, 0.30 * (255 - background))
    dark_start = background * 0.75
    dark_span = max(1.0, 0.30 * background)
    # On a light background (Safari, Calculator, a text editor) the drawing
    # is what is darker, and it is the glyph at full strength.
    light_background = background > 170
    if light_background:
        # Coloured drawings (a red mid-grey) come out whole as well.
        dark_span = max(1.0, 0.20 * background)
    table = bytearray(256)
    for level in range(256):
        if level >= background:
            strength = 0.0 if light_background else min(1.0, max(0.0, (level - light_start) / light_span))
        else:
            darker = min(1.0, max(0.0, (dark_start - level) / dark_span))
            strength = darker if light_background else 0.45 * darker
        table[level] = round(255 * strength)
    width, height, stride = grey8.width(), grey8.height(), grey8.bytesPerLine()
    data = bytes(grey8.constBits().asstring(stride * height)).translate(bytes(table))
    mask = QImage(data, width, height, stride, QImage.Format.Format_Alpha8).copy()
    return mask


def _redraw(image: QImage, top: QColor, bottom: QColor, ink: QColor | None,
            rim: QColor, glyph: QImage | None = None) -> QImage:
    """The icon on a top-to-bottom gradient tile, its drawing in `ink` (or
    in its own colours when `ink` is None), a `rim` along the top edge; the
    icon's own shape (alpha) is kept."""
    source = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    # macOS' own drawing (its Tintable layers) when bundled, else guessed.
    mask = _alpha_mask(glyph.scaled(source.size())) if glyph is not None else _glyph_mask(source)
    size = source.size()

    ink_layer = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    if ink is None:
        ink_layer = source.copy()
    else:
        ink_layer.fill(ink)
    painter = QPainter(ink_layer)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, mask)
    # Not on the icon's own outline (a darker ring on most icons, which
    # would draw a coloured border): only inside the shape inset by 3 %.
    inset = round(size.width() * 0.03)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawImage(QRect(inset, inset, size.width() - 2 * inset, size.height() - 2 * inset), source)
    painter.end()

    # The rim: the shape minus itself moved down, i.e. its top edge.
    edge = max(2, size.height() // 96)
    rim_layer = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    rim_layer.fill(Qt.GlobalColor.transparent)
    painter = QPainter(rim_layer)
    painter.drawImage(0, 0, source)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(rim_layer.rect(), rim)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
    painter.drawImage(0, edge, source)
    painter.end()

    out = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    gradient = QLinearGradient(0, 0, 0, size.height())
    gradient.setColorAt(0, top)
    gradient.setColorAt(1, bottom)
    painter.fillRect(out.rect(), gradient)
    painter.drawImage(0, 0, ink_layer)
    painter.drawImage(0, 0, rim_layer)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, source)
    painter.end()
    return out


def theme_icon(name: str, mode: str) -> QImage | None:
    """`name` from the plain MacTahoeLiquidKde theme of `mode` (never the
    overlay, which may already hold tinted icons)."""
    if not name:
        return None
    if name.startswith("/"):
        return load_image(Path(name))
    _ensure_icon_paths()
    previous = QIcon.themeName()
    QIcon.setThemeName(BASE_THEMES[mode])
    try:
        icon = QIcon.fromTheme(name)
        if icon.isNull():
            return None
        image = icon.pixmap(CANVAS, CANVAS).toImage()
    finally:
        QIcon.setThemeName(previous)
    return None if image.isNull() else image


def _ensure_icon_paths() -> None:
    """The XDG icon directories, which Qt only knows inside a Plasma session
    (its platform theme provides them)."""
    paths = [str(ICONS), str(HOME / ".icons")]
    for base in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":"):
        if base:
            paths.append(str(Path(base) / "icons"))
    current = QIcon.themeSearchPaths()
    QIcon.setThemeSearchPaths(current + [p for p in paths if p not in current])
    if "/usr/share/pixmaps" not in QIcon.fallbackSearchPaths():
        QIcon.setFallbackSearchPaths(QIcon.fallbackSearchPaths() + ["/usr/share/pixmaps"])


# The icon styles: the icons as they are, or every app icon redrawn
# (macOS 26 "Tinted" in the accent colour, "Clear" as frosted glass).
STYLES = ("default", "dark", "clear", "tinted")


def tinted(app_id: str, mode: str) -> Path:
    """An app's icon redrawn in the current style (Tinted or Clear)."""
    return STORE / "tinted" / f"{app_id}.{mode}.png"


# ── Apps ──────────────────────────────────────────────────────────────


def _application_dirs() -> list[Path]:
    dirs = [APPLICATIONS]
    for base in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":"):
        if base:
            dirs.append(Path(base) / "applications")
    flatpak = [DATA / "flatpak/exports/share/applications",
               Path("/var/lib/flatpak/exports/share/applications")]
    return dirs + flatpak


def _read_desktop(path: Path, listed: bool = False) -> dict | None:
    parser = configparser.RawConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    try:
        parser.read(path, encoding="utf-8")
    except (configparser.Error, OSError, UnicodeError):
        return None
    if not parser.has_section("Desktop Entry"):
        return None
    entry = parser["Desktop Entry"]
    if entry.get("Type", "Application") != "Application":
        return None
    if entry.get("Hidden", "false").lower() == "true":
        return None
    if entry.get("NoDisplay", "false").lower() == "true" and not listed:
        return None
    return dict(entry)


def _localized_name(entry: dict) -> str:
    lang = (os.environ.get("LANGUAGE") or os.environ.get("LANG") or "").split(":")[0]
    for key in (f"Name[{lang.split('.')[0]}]", f"Name[{lang.split('_')[0]}]", "Name"):
        if entry.get(key):
            return entry[key]
    return ""


def list_apps() -> list[dict]:
    """Installed apps, one per desktop id (the first data dir wins, as in
    the menus)."""
    apps: dict[str, dict] = {}
    for directory in _application_dirs():
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.desktop")):
            app_id = str(path.relative_to(directory)).replace("/", "-")[:-len(".desktop")]
            if app_id in apps:
                continue
            entry = _read_desktop(path, app_id in ALWAYS_LISTED)
            if entry is None:
                apps[app_id] = None  # hidden here: hidden everywhere
                continue
            name = _localized_name(entry)
            if not name:
                continue
            apps[app_id] = {"id": app_id, "name": name, "icon": entry.get("Icon", ""),
                            "path": str(path)}
    return sorted((a for a in apps.values() if a), key=lambda a: a["name"].lower())


# ── State ─────────────────────────────────────────────────────────────


def _load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def stored(app_id: str, mode: str) -> Path:
    return STORE / f"{app_id}.{mode}.png"


def customized_ids() -> set[str]:
    if not STORE.is_dir():
        return set()
    return {p.name.rsplit(".", 2)[0] for p in STORE.glob("*.png") if not p.name.startswith(".")}


# ── Overlay themes ────────────────────────────────────────────────────


def _icon_name(app: dict) -> str:
    """The icon name the overlay provides for `app`: its own, or a custom
    one when its launcher names a file."""
    icon = app.get("icon", "")
    if icon and "/" not in icon and not icon.endswith((".png", ".svg", ".xpm")):
        return icon
    return CUSTOM_PREFIX + app["id"]


def _override_launcher(app: dict, icon_name: str, state: dict) -> None:
    """Point a launcher that names an icon file at `icon_name`, through a
    per-user copy (or the user's own launcher, restored on reset)."""
    source = Path(app["path"])
    target = APPLICATIONS / (app["id"] + ".desktop")
    record = state.setdefault("launchers", {}).get(app["id"])
    text = source.read_text(encoding="utf-8")
    if record is None:
        record = {"icon": app.get("icon", ""), "created": source != target}
        state["launchers"][app["id"]] = record
    new = re.sub(r"(?m)^Icon=.*$", f"Icon={icon_name}", text)
    APPLICATIONS.mkdir(parents=True, exist_ok=True)
    target.write_text(new, encoding="utf-8")


def _restore_launcher(app_id: str, state: dict) -> None:
    record = state.get("launchers", {}).pop(app_id, None)
    if record is None:
        return
    target = APPLICATIONS / (app_id + ".desktop")
    if record.get("created"):
        target.unlink(missing_ok=True)
    elif target.is_file():
        text = target.read_text(encoding="utf-8")
        target.write_text(re.sub(r"(?m)^Icon=.*$", f"Icon={record['icon']}", text), encoding="utf-8")


def _original_icon(app_id: str, state: dict, mode: str) -> Path | None:
    """The icon file a launcher named before, fitted like the custom ones."""
    original = Path(state.get("launchers", {}).get(app_id, {}).get("icon", ""))
    image = load_image(original) if original.is_file() else None
    if image is None:
        return None
    STORE.mkdir(parents=True, exist_ok=True)
    fitted = STORE / f".original-{app_id}.png"
    fit_to_grid(image).save(str(fitted), "PNG")
    return fitted


def _tinted_icons(apps: list[dict], ids: set[str], mode: str,
                  render: Callable[[QImage, Callable], QImage],
                  state: dict, theme_images: dict[tuple[str, str], QImage],
                  progressed: Callable[[], None] | None = None) -> dict[str, Path]:
    """Every app's icon of `mode` redrawn by `render` (Tinted or Clear): its
    custom icon when it has one, else the theme's. `render` gets the style
    assets the icon has: the app's own (an icon from a .dmg), or for a theme
    icon showing a bundled macOS one, its macos_style(). Apps whose launcher names an icon
    file are left alone unless customized (that would edit their launcher)."""
    icons: dict[str, Path] = {}
    out_dir = STORE / "tinted"
    out_dir.mkdir(parents=True, exist_ok=True)
    for app in apps:
        name = _icon_name(app)
        custom = app["id"] in ids
        if name.startswith(CUSTOM_PREFIX) and not custom:
            if progressed:
                progressed()
            continue
        # The per-user launcher has to be redirected before looking up its
        # original file: _override_launcher records that path in state.
        if name.startswith(CUSTOM_PREFIX):
            _override_launcher(app, name, state)
        source = stored(app["id"], mode)
        if not source.is_file() and mode == "dark":
            source = stored(app["id"], "light")
        stem, own = None, None
        if source.is_file():
            image = load_image(source)
            own = app["id"]
        elif name.startswith(CUSTOM_PREFIX):
            original = _original_icon(app["id"], state, mode)
            image = load_image(original) if original else None
        else:
            image = theme_images.get((app["id"], mode))
            stem = macos_style(name)
        if image is None:
            if progressed:
                progressed()
            continue
        target = tinted(app["id"], mode)
        if render(image, _style_assets(own, stem)).save(str(target), "PNG"):
            icons[name] = target
        if progressed:
            progressed()
    return icons


def rebuild_overlays(apps: list[dict],
                     theme_images: dict[tuple[str, str], QImage] | None = None,
                     progress: Callable[[int], None] | None = None) -> None:
    """Both overlay themes from the stored icons: light uses the light icon;
    dark uses the dark one, else the light one (macOS shows an app's only
    icon in both appearances)."""
    by_id = {a["id"]: a for a in apps}
    state = _load_state()
    ids = customized_ids()
    for app_id in list(state.get("launchers", {})):
        if app_id not in ids:
            _restore_launcher(app_id, state)
    style = state.get("style", "default")
    shutil.rmtree(STORE / "tinted", ignore_errors=True)
    accent = accent_color()
    if style == "tinted":
        state["accent"] = accent.name()
    if style in ("tinted", "clear", "dark"):
        if theme_images is None:
            theme_images = {}
            for index, app in enumerate(apps):
                if not _icon_name(app).startswith(CUSTOM_PREFIX):
                    for mode in MODES:
                        image = theme_icon(app.get("icon", ""), mode)
                        if image is not None:
                            theme_images[(app["id"], mode)] = image
                if progress:
                    progress(int(50 * (index + 1) / max(1, len(apps))))
    theme_images = theme_images or {}
    total = max(1, len(apps) * len(MODES))
    completed = 0

    def report_tinted_progress() -> None:
        nonlocal completed
        completed += 1
        if progress:
            progress(50 + int(50 * completed / total))

    current = _kread("kdeglobals", "Icons", "Theme")
    for mode in MODES:
        name = f"{BASE_THEMES[mode]}-custom"
        icons = {}
        if style in ("tinted", "clear", "dark"):
            dark = mode == "dark"
            if style == "tinted":
                render = lambda image, assets, dark=dark: tint(
                    image, accent, dark, assets("glyph", image.size()))
            elif style == "clear":
                render = lambda image, assets, dark=dark: clear(
                    image, dark, assets("glyph", image.size()))
            else:
                render = lambda image, assets: (assets("dark", image.size())
                                                or dark_icon(image))
            icons.update(_tinted_icons(apps, ids, mode, render, state,
                                       theme_images, report_tinted_progress))
        for app_id in sorted(ids):
            if style in ("tinted", "clear", "dark"):
                break
            app = by_id.get(app_id)
            if app is None:
                continue
            source = stored(app_id, mode)
            if not source.is_file() and mode == "dark":
                source = stored(app_id, "light")
            icon_name = _icon_name(app)
            if icon_name.startswith(CUSTOM_PREFIX):
                _override_launcher(app, icon_name, state)
                if not source.is_file():
                    # Only the other appearance was set: this one keeps the
                    # icon file the launcher named.
                    source = _original_icon(app_id, state, mode)
            if source is None or not source.is_file():
                continue
            icons[icon_name] = source
        _write_overlay(name, mode, icons, in_use=current == name)
    _save_state(state)
    if progress:
        progress(100)


def _write_overlay(name: str, mode: str, icons: dict[str, Path], in_use: bool) -> None:
    """Replace the overlay theme `name` in one rename, so a running session
    never looks it up half written or missing. An overlay left without icons
    is removed, unless the session uses it: it is then emptied (still a
    valid theme, inheriting its base) and apply_icon_theme removes it once
    the session moved to the plain theme."""
    theme = ICONS / name
    if not icons:
        if in_use and theme.is_dir():
            shutil.rmtree(theme / "apps", ignore_errors=True)
        else:
            shutil.rmtree(theme, ignore_errors=True)
        return
    staging = ICONS / f".{name}.new"
    shutil.rmtree(staging, ignore_errors=True)
    apps_dir = staging / "apps/512"
    apps_dir.mkdir(parents=True)
    for icon_name, source in icons.items():
        shutil.copy2(source, apps_dir / f"{icon_name}.png")
    staging.joinpath("index.theme").write_text(
        "[Icon Theme]\n"
        f"Name={BASE_THEMES[mode]} (custom app icons)\n"
        "Comment=App icons set in AquaDesktop Theme Settings\n"
        f"Inherits={BASE_THEMES[mode]}\n"
        "Hidden=true\n"
        "Directories=apps/512\n\n"
        "[apps/512]\nSize=512\nMinSize=8\nMaxSize=1024\nType=Scalable\nContext=Applications\n",
        encoding="utf-8")
    previous = ICONS / f".{name}.old"
    shutil.rmtree(previous, ignore_errors=True)
    if theme.exists():
        theme.rename(previous)
    staging.rename(theme)
    shutil.rmtree(previous, ignore_errors=True)


def overlay_has_icons(name: str) -> bool:
    theme = ICONS / name
    return (theme / "index.theme").is_file() and any((theme / "apps/512").glob("*.png"))


def apply_icon_theme() -> None:
    """Make the session use the overlay of the current mode (or the plain
    theme when it has none) and tell running apps."""
    current = _kread("kdeglobals", "Icons", "Theme")
    mode = "dark" if "-dark" in current else "light"
    base = BASE_THEMES[mode]
    overlay = f"{base}-custom"
    target = overlay if overlay_has_icons(overlay) else base
    applied = False
    if shutil.which("plasma-changeicons"):
        # Reapplying the same name still reloads the icons.
        try:
            result = subprocess.run(
                ["plasma-changeicons", target], check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=10,
            )
            applied = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            pass
    if not applied:
        # Keep the config watcher notification, then send the separate KDE
        # icon-change event. KIconLoader does not switch themes on the former
        # alone, so running apps otherwise remain on the previous appearance.
        try:
            subprocess.run(
                ["kwriteconfig6", "--notify", "--file", "kdeglobals",
                 "--group", "Icons", "--key", "Theme", target],
                check=False, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        _notify_icon_theme_changed()
    if shutil.which("kbuildsycoca6"):
        try:
            subprocess.run(["kbuildsycoca6"], check=False,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            pass
    # Overlays emptied while in use are no longer needed.
    for name in (f"{b}-custom" for b in BASE_THEMES.values()):
        if name != target and not overlay_has_icons(name):
            shutil.rmtree(ICONS / name, ignore_errors=True)


def _notify_icon_theme_changed() -> bool:
    """Ask KDE's running icon loaders to reread kdeglobals and their caches."""
    if not shutil.which("dbus-send"):
        return False
    try:
        result = subprocess.run(
            ["dbus-send", "--session", "--type=signal", "/KGlobalSettings",
             "org.kde.KGlobalSettings.notifyChange", "int32:4", "int32:0"],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _kread(file: str, group: str, key: str) -> str:
    try:
        return subprocess.run(["kreadconfig6", "--file", file, "--group", group, "--key", key],
                              check=False, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


# ── Matching .icns files to apps ──────────────────────────────────────

# Words that describe a style on macosicons.com, not the app.
_STYLE_WORDS = {
    "macos", "mac", "os", "tahoe", "golden", "gate", "goldengate", "sequoia", "sonoma",
    "dark", "light", "liquid", "glass", "clear", "tinted", "icon", "icons", "icns",
    "big", "sur", "style", "new", "app", "26", "27", "15", "14",
}
# macOS names for the apps standing in for them here.
_ALIASES = {
    "finder": ["org.kde.dolphin", "org.gnome.Nautilus", "nemo", "thunar", "pcmanfm"],
    "settings": ["systemsettings", "org.kde.systemsettings", "kdesystemsettings"],
    "systemsettings": ["systemsettings", "kdesystemsettings"],
    "launchpad": ["org.kde.mac-tahoe-liquid-kde.apps"],
    "apps": ["org.kde.mac-tahoe-liquid-kde.apps"],
    "terminal": ["org.kde.konsole", "org.gnome.Console", "org.gnome.Terminal", "kitty", "alacritty"],
    "textedit": ["org.kde.kate", "org.kde.kwrite", "org.gnome.TextEditor"],
    "preview": ["org.kde.okular", "org.kde.gwenview"],
    "music": ["org.kde.elisa", "rhythmbox"],
    "calculator": ["org.kde.kcalc", "org.gnome.Calculator"],
    "discord": ["discord", "com.discordapp.Discord", "vesktop", "dev.vencord.Vesktop", "equibop",
                "io.github.equicord.equibop"],
}


def describe_file(path: Path) -> tuple[list[str], bool]:
    """(app words, dark?) from a file name such as
    "Steam__Golden_Gate__Dark__viIFr16TlG-2ff8b9cd6f.icns"."""
    stem = path.stem
    stem = re.sub(r"-[0-9a-f]{8,}$", "", stem)          # download hash
    words = [w for w in re.split(r"[_\s.\-()]+", stem) if w]
    dark = any(w.lower() == "dark" for w in words)
    # Drop macosicons.com's random ids (mixed case letters and digits).
    words = [w for w in words
             if not re.fullmatch(r"(?=.*\d)(?=.*[a-z])(?=.*[A-Z])[A-Za-z0-9]{8,}", w)]
    names = [w.lower() for w in words if w.lower() not in _STYLE_WORDS]
    return names, dark


def match_app(path: Path, apps: list[dict]) -> tuple[dict | None, bool]:
    names, dark = describe_file(path)
    if not names:
        return None, dark
    by_id = {a["id"].lower(): a for a in apps}
    for candidate in (" ".join(names), names[0]):
        for alias in _ALIASES.get(candidate.replace(" ", ""), []):
            if alias.lower() in by_id:
                return by_id[alias.lower()], dark
    wanted = " ".join(names)
    for app in apps:
        if app["name"].lower() == wanted:
            return app, dark
    for app in apps:
        app_words = set(re.split(r"[\s.\-_]+", (app["name"] + " " + app["id"]).lower()))
        if names[0] in app_words:
            return app, dark
    return None, dark


# ── Actions (the Theme Settings app runs them through the CLI below) ──


def apply(progress: Callable[[int], None] | None = None) -> None:
    rebuild_overlays(list_apps(), progress=progress)
    apply_icon_theme()


def set_style(style: str) -> bool:
    """macOS 26's icon styles: "default" (the icons as they are), "dark"
    (on a dark tile, in their own colours), "clear" (frosted glass) or
    "tinted" (in the accent colour)."""
    if style not in STYLES:
        return False
    state = _load_state()
    state["style"] = style
    _save_state(state)
    return True


def set_icon(app_id: str, mode: str, path: Path) -> str:
    """Store `path` (.icns or image) as the `mode` icon of `app_id`; returns
    an error message, empty on success."""
    if mode not in MODES:
        return f"Unknown appearance {mode}"
    if path.suffix.lower() == ".dmg":
        return set_icon_from_dmg(app_id, mode, path)
    image = load_image(path)
    if image is None:
        return f"Could not read {path.name}"
    STORE.mkdir(parents=True, exist_ok=True)
    if mode == "light":
        _drop_style_assets(app_id)
    if not fit_to_grid(image).save(str(stored(app_id, mode)), "PNG"):
        return f"Could not save the icon for {app_id}"
    return ""


def dmg_apps(image: Path, apps: list[dict]) -> list[dict]:
    """The apps of a disk image (.dmg), each with the installed app its
    name designates (its id, or "")."""
    import dmg
    volume = dmg.open_volume(str(image))
    found = []
    for bundle in dmg.find_apps(volume):
        name = dmg.app_name(volume, bundle)
        match, _dark = match_app(Path(name + ".icns"), apps)
        if match is None:
            match, _dark = match_app(Path(Path(bundle).stem + ".icns"), apps)
        found.append({"name": name, "bundle": bundle, "match": match["id"] if match else ""})
    return found


def dmg_icons(image: Path, bundle: str) -> dict[str, QImage]:
    """An app of a disk image's icons, 1024 px on Apple's grid: "light"
    (what macOS 26 shows by default: its layered icon, Icon Composer's
    .iconstack in Assets.car named by CFBundleIconName, as Xcode rendered
    it, else as car.py draws it, else its .icns), and with a layered icon
    "dark" (the DarkAqua render) and "glyph" (the Tintable drawing mask).
    Raises dmg.DmgError (and OSError...) when the image cannot be read."""
    import car
    import dmg
    volume = dmg.open_volume(str(image))
    try:
        icns = QImage()
        icns.loadFromData(icns_png(dmg.app_icon(volume, bundle)) or b"")
    except dmg.DmgError:
        icns = QImage()
    catalog, stack = None, ""
    car_data, icon_name = dmg.app_car(volume, bundle)
    if car_data:
        catalog = car.Car(car_data)
        stacks = catalog.stack_names()
        stack = next((n for n in stacks if n.split(".")[0] == icon_name), stacks[0] if stacks else "")
    icons: dict[str, QImage] = {}
    light = QImage()
    if catalog is not None and stack:
        light = car.flat_icon(catalog, stack, of_stack=True) or QImage()
        aqua = catalog.appearances.get("NSAppearanceNameAqua")
        if light.isNull() and aqua is not None:
            light = car.render_icon(catalog, stack, aqua) or QImage()
        dark = catalog.appearances.get("NSAppearanceNameDarkAqua")
        rendered = car.render_icon(catalog, stack, dark) if dark is not None else None
        if rendered is not None:
            icons["dark"] = rendered
            glyph = car.render_glyph(catalog, stack)
            if glyph is not None:
                icons["glyph"] = glyph
    if light.isNull():
        light = icns
    if light.isNull() and catalog is not None:
        light = car.flat_icon(catalog, stack) or QImage()
    if not light.isNull():
        icons["light"] = light.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    return icons


def set_icon_from_dmg(app_id: str, mode: str, image: Path, bundle: str = "") -> str:
    """The icon of an app of a disk image (dmg_icons) as the `mode` icon of
    `app_id`; with no bundle given, the image's app matching `app_id`, else
    its only (or first) app. Light: also stores its Dark render and drawing
    mask when it has them (style_asset), as macOS draws those styles from
    the layered icon rather than from the light one. Dark: the Dark render."""
    import dmg
    try:
        if not bundle:
            volume = dmg.open_volume(str(image))
            bundles = dmg.find_apps(volume)
            if not bundles:
                return f"No app in {image.name}"
            matched = [b for b in bundles
                       if (match_app(Path(dmg.app_name(volume, b) + ".icns"), list_apps())[0]
                           or {}).get("id") == app_id]
            bundle = (matched or bundles)[0]
        styles = dmg_icons(image, bundle)
    except (dmg.DmgError, OSError, ValueError, KeyError, struct.error) as error:
        return f"{image.name}: {error}"
    light = styles.get("light", QImage())
    if mode == "dark" and "dark" in styles:
        light = styles["dark"]
    if light.isNull():
        return f"{image.name}: no icon found for this app"
    STORE.mkdir(parents=True, exist_ok=True)
    if not fit_to_grid(light).save(str(stored(app_id, mode)), "PNG"):
        return f"Could not save the icon for {app_id}"
    if mode == "light":
        _drop_style_assets(app_id)
        if "dark" in styles:
            square = grid_square(styles["dark"])
            fit_to_grid(styles["dark"], square).save(str(style_asset(app_id, "dark")), "PNG")
            if "glyph" in styles:
                fit_to_grid(styles["glyph"], square) \
                    .convertToFormat(QImage.Format.Format_Grayscale8) \
                    .save(str(style_asset(app_id, "glyph")), "PNG")
    return ""


def _drop_style_assets(app_id: str) -> None:
    for kind in ("dark", "glyph"):
        style_asset(app_id, kind).unlink(missing_ok=True)


def reset_icon(app_id: str, mode: str) -> None:
    for m in (MODES if mode == "both" else (mode,)):
        stored(app_id, m).unlink(missing_ok=True)
    if mode in ("light", "both"):
        _drop_style_assets(app_id)


def import_folder(folder: Path, apps: list[dict]) -> tuple[list[str], list[str]]:
    """Every .icns of a folder on the app its name designates, in the light
    or dark slot its name says: (applied, not matched)."""
    done, missed = [], []
    STORE.mkdir(parents=True, exist_ok=True)
    for path in sorted(folder.glob("*.icns")):
        app, dark = match_app(path, apps)
        image = load_image(path) if app else None
        if app is None or image is None:
            missed.append(path.name)
            continue
        mode = "dark" if dark else "light"
        fit_to_grid(image).save(str(stored(app["id"], mode)), "PNG")
        done.append(f"{app['name']} ({mode})")
    return done, missed


def reset_all() -> None:
    """Every custom icon removed and back to the Default style."""
    shutil.rmtree(STORE, ignore_errors=True)
    set_style("default")


def needs_refresh() -> bool:
    """Tinted icons follow the accent: regenerate when it changed since."""
    state = _load_state()
    return state.get("style") == "tinted" and state.get("accent") != accent_color().name()


def app_entries() -> list[dict]:
    """The apps with what each appearance shows: a file (custom or tinted
    icon) or else the app's own icon (a theme name or a file)."""
    style = _load_state().get("style", "default")
    entries = []
    for app in list_apps():
        entry = dict(app)
        for mode in MODES:
            custom = stored(app["id"], mode)
            entry[f"{mode}_custom"] = custom.is_file()
            styled = style in ("tinted", "clear", "dark")
            shown = tinted(app["id"], mode) if styled else custom
            if not shown.is_file() and mode == "dark" and not styled:
                shown = stored(app["id"], "light")
            entry[mode] = str(shown) if shown.is_file() else ""
        entries.append(entry)
    return entries


# ── Command line ──────────────────────────────────────────────────────

USAGE = """Usage: icon_manager.py COMMAND
  list                      apps and their icons, as JSON
  status                    style and accent, as JSON
  set APP_ID light|dark FILE  FILE: an .icns, an image or a .dmg
  dmg IMAGE                 the apps of a disk image, as JSON (name, bundle,
                            the installed app it matches)
  set-dmg APP_ID light|dark IMAGE BUNDLE
                            the icon of one app of a disk image
  reset APP_ID light|dark|both
  import FOLDER             every .icns of FOLDER, matched to apps by name
  style default|dark|clear|tinted
  reset-all
  refresh                   re-tint after an accent colour change
Changes print "progress N" lines while the icon themes are rebuilt."""


def _report_progress(value: int) -> None:
    print(f"progress {value}", flush=True)


def main(argv: list[str]) -> int:
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    # Qt only renders images and looks up theme icons: no window is shown.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])  # noqa: F841 - QIcon needs it
    command, args = argv[0], argv[1:]
    if command == "list" and not args:
        print(json.dumps(app_entries()))
        return 0
    if command == "status" and not args:
        print(json.dumps({"style": _load_state().get("style", "default"),
                          "accent": accent_color().name()}))
        return 0
    if command == "dmg" and len(args) == 1:
        import dmg
        try:
            print(json.dumps(dmg_apps(Path(args[0]), list_apps())))
        except (dmg.DmgError, OSError, ValueError, struct.error) as error:
            print(f"{Path(args[0]).name}: {error}", file=sys.stderr)
            return 1
        return 0
    if command == "set-dmg" and len(args) == 4 and args[1] in MODES:
        error = set_icon_from_dmg(args[0], args[1], Path(args[2]), args[3])
        if error:
            print(error, file=sys.stderr)
            return 1
    elif command == "set" and len(args) == 3:
        error = set_icon(args[0], args[1], Path(args[2]))
        if error:
            print(error, file=sys.stderr)
            return 1
    elif command == "reset" and len(args) == 2 and args[1] in (*MODES, "both"):
        reset_icon(args[0], args[1])
    elif command == "import" and len(args) == 1:
        done, missed = import_folder(Path(args[0]), list_apps())
        report = f"{len(done)} icon(s) applied"
        if done:
            report += ": " + ", ".join(done)
        if missed:
            report += f". Not matched: {', '.join(missed)}"
        print(f"report {report}", flush=True)
        if not done:
            return 0
    elif command == "style" and len(args) == 1:
        if not set_style(args[0]):
            print(USAGE, file=sys.stderr)
            return 2
    elif command == "reset-all" and not args:
        reset_all()
    elif command == "refresh" and not args:
        if not needs_refresh():
            return 0
    else:
        print(USAGE, file=sys.stderr)
        return 2
    apply(_report_progress)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
