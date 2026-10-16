"""Icon Manager (src/offline/icon-manager): .icns reading, Apple grid to
theme grid, file-name matching, the overlay icon themes and their
launchers, and how the theme switch and the icons step use them."""

import importlib.util
import json
import struct

import pytest

pytest.importorskip("PyQt6.QtGui")
from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QGuiApplication, QImage, QColor, QPainter  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def im(offline, tmp_path, monkeypatch, qt_app):
    spec = importlib.util.spec_from_file_location(
        "icon_manager", offline / "icon-manager/icon_manager.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data, config = tmp_path / "data", tmp_path / "config"
    monkeypatch.setattr(module, "DATA", data)
    monkeypatch.setattr(module, "STORE", data / "mac-tahoe-liquid-kde/icon-manager")
    monkeypatch.setattr(module, "STATE", config / "mac-tahoe-liquid-kde/icon-manager.json")
    monkeypatch.setattr(module, "ICONS", data / "icons")
    monkeypatch.setattr(module, "APPLICATIONS", data / "applications")
    # Never reach the live session.
    module.real_apply_icon_theme = module.apply_icon_theme
    monkeypatch.setattr(module, "apply_icon_theme", lambda: None)
    monkeypatch.setattr(module, "_kread", lambda *_args: "")
    return module


def _apple_icon(path, size=256):
    """A PNG on Apple's grid: an 80.5 % rounded square, transparent margin."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    side = round(size * 824 / 1024)
    offset = (size - side) // 2
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#2a2a2a"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(offset, offset, side, side, side * 0.22, side * 0.22)
    painter.end()
    image.save(str(path), "PNG")
    return path.read_bytes()


def _icns(png_small, png_big):
    entries = b""
    for kind, png in ((b"ic07", png_small), (b"ic10", png_big)):
        entries += kind + struct.pack(">I", 8 + len(png)) + png
    return b"icns" + struct.pack(">I", 8 + len(entries)) + entries


def test_reads_the_largest_png_of_an_icns(im, tmp_path):
    small = _apple_icon(tmp_path / "s.png", 128)
    big = _apple_icon(tmp_path / "b.png", 512)
    assert im.icns_png(_icns(small, big)) == big
    assert im.icns_png(b"not an icns") is None
    icns = tmp_path / "Steam__Golden_Gate__Dark__viIFr16TlG-2ff8b9cd6f.icns"
    icns.write_bytes(_icns(small, big))
    assert im.load_image(icns).width() == 512


def test_fits_apple_grid_icons_to_the_theme_grid(im, tmp_path):
    """macOS icons are 824/1024 (80.5 %); this theme's 448/512 (87.5 %): a
    custom icon must be as large as the theme's next to it in the Dock."""
    _apple_icon(tmp_path / "a.png", 1024)
    fitted = im.fit_to_grid(QImage(str(tmp_path / "a.png")))
    assert (fitted.width(), fitted.height()) == (512, 512)
    opaque = [x for x in range(512) if fitted.pixelColor(x, 256).alpha() > 128]
    assert abs(opaque[0] - 32) <= 1 and abs(opaque[-1] - 479) <= 1


@pytest.mark.parametrize("name,app_id,dark", [
    ("Steam__Golden_Gate__Dark__viIFr16TlG-2ff8b9cd6f.icns", "steam", True),
    ("Finder_Dark_macOS_27_icon-ad8730d3d4.icns", "org.kde.dolphin", True),
    ("Settings_macOS_Golden_Gate_iR77bVvZBc-75364d378c.icns", "systemsettings", False),
    ("Launchpad-4201d67e55.icns", "org.kde.mac-tahoe-liquid-kde.apps", False),
    ("terminal_f0y75RJ5ju-47bcebf88f.icns", "org.kde.konsole", False),
    ("Discord__Tahoe_dark__GUdIkvYx2E_icns-71a2c04ea1.icns", "equibop", True),
    ("Prism_Launcher__Liquid_Glass___Dark__18BTP7wC9n_icns-f319076014.icns",
     "org.prismlauncher.PrismLauncher", True),
])
def test_matches_macosicons_file_names_to_apps(im, tmp_path, name, app_id, dark):
    apps = [{"id": i, "name": n, "icon": i, "path": ""} for i, n in (
        ("steam", "Steam"), ("org.kde.dolphin", "Dolphin"), ("systemsettings", "System Settings"),
        ("org.kde.mac-tahoe-liquid-kde.apps", "Apps"), ("org.kde.konsole", "Konsole"),
        ("equibop", "Equibop"), ("org.prismlauncher.PrismLauncher", "Prism Launcher"),
        ("firefox", "Firefox"))]
    app, is_dark = im.match_app(tmp_path / name, apps)
    assert app is not None and app["id"] == app_id
    assert is_dark is dark


def test_overlays_follow_the_appearance_and_reset_restores_launchers(im, tmp_path):
    apps_dir = im.APPLICATIONS
    apps_dir.mkdir(parents=True)
    # An app whose own launcher names an icon file (as the old macosicons
    # tool leaves them) and one naming a theme icon.
    old = tmp_path / "old.png"
    _apple_icon(old, 256)
    (apps_dir / "equibop.desktop").write_text(
        f"[Desktop Entry]\nType=Application\nName=Equibop\nIcon={old}\nExec=equibop\n")
    (apps_dir / "steam.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Steam\nIcon=steam\nExec=steam\n")
    icns = tmp_path / "x.icns"
    png = _apple_icon(tmp_path / "x.png", 256)
    icns.write_bytes(_icns(png, png))

    assert im.set_icon("steam", "dark", icns) == ""
    assert im.set_icon("equibop", "dark", icns) == ""
    im.apply()
    light = im.ICONS / "MacTahoeLiquidKde-Icons-custom"
    dark = im.ICONS / "MacTahoeLiquidKde-Icons-dark-custom"
    # Dark only: the light overlay keeps steam's theme icon.
    assert (dark / "apps/512/steam.png").is_file()
    assert not (light / "apps/512/steam.png").exists()
    index = (dark / "index.theme").read_text()
    assert "Inherits=MacTahoeLiquidKde-Icons-dark" in index and "Hidden=true" in index
    # Equibop's launcher now names an icon the overlays provide; light mode
    # keeps its former icon file.
    assert "Icon=mactahoe-custom-equibop" in (apps_dir / "equibop.desktop").read_text()
    assert (light / "apps/512/mactahoe-custom-equibop.png").is_file()
    assert json.loads(im.STATE.read_text())["launchers"]["equibop"]["icon"] == str(old)

    im.reset_all()
    im.apply()
    assert f"Icon={old}" in (apps_dir / "equibop.desktop").read_text()
    assert not light.exists() and not dark.exists()


def test_theme_switch_uses_the_overlay_of_the_mode(monkeypatch, tmp_path):
    import theme_switch as ts
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert ts.custom_icon_theme("MacTahoeLiquidKde-Icons-dark") == "MacTahoeLiquidKde-Icons-dark"
    overlay = tmp_path / "icons/MacTahoeLiquidKde-Icons-dark-custom"
    (overlay / "apps/512").mkdir(parents=True)
    (overlay / "index.theme").write_text("[Icon Theme]\n")
    # Emptied while in use (all icons reset): the plain theme again.
    assert ts.custom_icon_theme("MacTahoeLiquidKde-Icons-dark") == "MacTahoeLiquidKde-Icons-dark"
    (overlay / "apps/512/steam.png").write_bytes(b"png")
    assert ts.custom_icon_theme("MacTahoeLiquidKde-Icons-dark") == "MacTahoeLiquidKde-Icons-dark-custom"
    assert ts.custom_icon_theme("MacTahoeLiquidKde-Icons") == "MacTahoeLiquidKde-Icons"


def test_icon_manager_notifies_kde_when_applying_dark_icons(im, monkeypatch):
    dark = im.ICONS / "MacTahoeLiquidKde-Icons-dark-custom"
    (dark / "apps/512").mkdir(parents=True)
    (dark / "index.theme").write_text("[Icon Theme]\n")
    (dark / "apps/512/steam.png").write_bytes(b"png")
    monkeypatch.setattr(im, "_kread", lambda *_args: "MacTahoeLiquidKde-Icons-dark")
    monkeypatch.setattr(
        im.shutil, "which",
        lambda command: "/usr/bin/dbus-send" if command == "dbus-send"
        else ("/usr/bin/kbuildsycoca6" if command == "kbuildsycoca6" else None),
    )
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(im.subprocess, "run", run)

    im.real_apply_icon_theme()

    write = next(call for call in calls if call[0] == "kwriteconfig6")
    assert write[1:2] == ["--notify"]
    assert write[-1] == "MacTahoeLiquidKde-Icons-dark-custom"
    notify = next(call for call in calls if call[0] == "dbus-send")
    assert notify[-2:] == ["int32:4", "int32:0"]
    assert calls[-1] == ["kbuildsycoca6"]


def test_icons_step_keeps_the_overlays_and_installs_the_engine(src):
    step = (src / "scripts/steps/icons.py").read_text()
    assert "not old.name.endswith(_OVERLAY_SUFFIX)" in step
    assert "_install_icon_manager()" in step and "_uninstall_icon_manager()" in step
    # Theme Settings is its window: no Qt UI or launcher of its own.
    assert sorted(p.name for p in (src / "offline/icon-manager").iterdir()
                  if not p.name.startswith((".", "__"))) == ["car.py", "dmg.py", "icon_manager.py", "macos-styles"]
    assert 'ICON_MANAGER_FILES = ("icon_manager.py", "dmg.py", "car.py")' in step
    assert 'ICON_MANAGER_DIRS = ("macos-styles",)' in step


def test_overlay_in_use_is_never_missing(im, tmp_path, monkeypatch):
    """Rebuilding swaps a finished overlay in with one rename; an overlay
    the session uses that loses its last icon stays a valid (empty) theme
    until apply_icon_theme moved the session off it — KDE otherwise warns
    'Icon theme ...-custom not found' and falls back mid-switch."""
    apps_dir = im.APPLICATIONS
    apps_dir.mkdir(parents=True)
    (apps_dir / "steam.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Steam\nIcon=steam\nExec=steam\n")
    icns = tmp_path / "x.icns"
    png = _apple_icon(tmp_path / "x.png", 256)
    icns.write_bytes(_icns(png, png))
    im.set_icon("steam", "dark", icns)
    im.apply()
    dark = im.ICONS / "MacTahoeLiquidKde-Icons-dark-custom"
    assert im.overlay_has_icons(dark.name)
    assert not list(im.ICONS.glob(".*"))  # no staging left behind

    monkeypatch.setattr(im, "_kread", lambda *_args: dark.name)
    im.reset_icon("steam", "both")
    im.rebuild_overlays(im.list_apps())
    assert (dark / "index.theme").is_file() and not im.overlay_has_icons(dark.name)


def test_command_line_lists_apps_and_reports_progress(im, tmp_path, capsys):
    apps_dir = im.APPLICATIONS
    apps_dir.mkdir(parents=True)
    (apps_dir / "steam.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Steam\nIcon=steam\nExec=steam\n")
    assert im.main(["list"]) == 0
    listed = [a for a in json.loads(capsys.readouterr().out) if a["id"] == "steam"]
    assert listed and listed[0]["dark"] == "" and listed[0]["dark_custom"] is False

    icns = tmp_path / "Steam__Golden_Gate__Dark__viIFr16TlG-2ff8b9cd6f.icns"
    png = _apple_icon(tmp_path / "x.png", 256)
    icns.write_bytes(_icns(png, png))
    assert im.main(["set", "steam", "dark", str(icns)]) == 0
    assert "progress 100" in capsys.readouterr().out
    assert im.main(["list"]) == 0
    steam = next(a for a in json.loads(capsys.readouterr().out) if a["id"] == "steam")
    assert steam["dark_custom"] and steam["dark"].endswith("steam.dark.png")
    assert im.main(["set", "steam", "sepia", str(icns)]) == 1
    assert im.main(["bogus"]) == 2


def test_tinted_style_follows_the_macos_capture(im, tmp_path):
    """macOS 26's Tinted style (TintedDark.png): a near-black tile faintly
    tinted with the accent (13 % at the top, 2 % at the bottom) and the
    drawing in the accent itself."""
    accent = QColor("#0088ff")
    icon = QImage(64, 64, QImage.Format.Format_ARGB32_Premultiplied)
    icon.fill(QColor("#ffffff"))
    painter = QPainter(icon)
    painter.fillRect(24, 24, 16, 16, QColor("#202020"))
    painter.end()
    dark = im.tint(icon, accent, True)
    top, bottom, glyph = dark.pixelColor(10, 6), dark.pixelColor(10, 58), dark.pixelColor(32, 32)
    assert top.red() < 10 and 20 < top.blue() < 45          # accent at ~13 %
    assert bottom.blue() < top.blue()                        # darker towards the bottom
    assert abs(glyph.blue() - 255) < 20 and glyph.red() < 20  # the accent itself
    light = im.tint(icon, accent, False)
    assert light.pixelColor(10, 32).red() > 180                # light glass
    transparent = QImage(8, 8, QImage.Format.Format_ARGB32_Premultiplied)
    transparent.fill(Qt.GlobalColor.transparent)
    assert im.tint(transparent, accent).pixelColor(4, 4).alpha() == 0


def test_dark_style_keeps_the_app_colour(im, tmp_path, monkeypatch):
    """macOS 26's Dark style (Dark.png): a dark grey tile (45 down to 22);
    a white drawing on a coloured icon takes that colour (Mail's envelope
    turns blue), a drawing on a white icon keeps its own colours."""
    blue = QImage(64, 64, QImage.Format.Format_ARGB32_Premultiplied)
    blue.fill(QColor("#1a9bfa"))
    painter = QPainter(blue)
    painter.fillRect(20, 20, 24, 24, QColor("#ffffff"))
    painter.end()
    out = im.dark_icon(blue)
    tile, glyph = out.pixelColor(8, 32), out.pixelColor(32, 32)
    assert max(tile.red(), tile.green(), tile.blue()) < 50 and abs(tile.red() - tile.blue()) < 6
    assert glyph.blue() > 200 and glyph.red() < 90           # blue, not white
    white = QImage(64, 64, QImage.Format.Format_ARGB32_Premultiplied)
    white.fill(QColor("#ffffff"))
    painter = QPainter(white)
    painter.fillRect(20, 20, 24, 24, QColor("#ff3b30"))
    painter.end()
    red = im.dark_icon(white).pixelColor(32, 32)
    assert red.red() > 200 and red.blue() < 90                 # its own red

    apps_dir = im.APPLICATIONS
    apps_dir.mkdir(parents=True)
    (apps_dir / "steam.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Steam\nIcon=steam\nExec=steam\n")
    monkeypatch.setattr(im, "list_apps", lambda: [
        {"id": "steam", "name": "Steam", "icon": "steam", "path": str(apps_dir / "steam.desktop")}])
    monkeypatch.setattr(im, "theme_icon", lambda name, mode: blue)
    assert im.main(["style", "dark"]) == 0
    assert (im.ICONS / "MacTahoeLiquidKde-Icons-dark-custom/apps/512/steam.png").is_file()


def test_tinted_style_switch_rebuilds_the_overlays(im, tmp_path, monkeypatch):
    apps_dir = im.APPLICATIONS
    apps_dir.mkdir(parents=True)
    (apps_dir / "steam.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Steam\nIcon=steam\nExec=steam\n")
    monkeypatch.setattr(im, "list_apps", lambda: [
        {"id": "steam", "name": "Steam", "icon": "steam", "path": str(apps_dir / "steam.desktop")}])
    icon = QImage(64, 64, QImage.Format.Format_ARGB32_Premultiplied)
    icon.fill(QColor("#303030"))
    monkeypatch.setattr(im, "theme_icon", lambda name, mode: icon)
    monkeypatch.setattr(im, "accent_color", lambda: QColor("#ff2d55"))
    assert im.main(["style", "tinted"]) == 0
    assert json.loads(im.STATE.read_text())["style"] == "tinted"
    for theme in ("MacTahoeLiquidKde-Icons-custom", "MacTahoeLiquidKde-Icons-dark-custom"):
        assert (im.ICONS / theme / "apps/512/steam.png").is_file()
    assert json.loads(im.STATE.read_text())["accent"] == "#ff2d55"
    assert im.main(["style", "default"]) == 0
    assert not (im.ICONS / "MacTahoeLiquidKde-Icons-custom").exists()


def test_clear_style_draws_frosted_glass_icons(im, tmp_path, monkeypatch):
    """macOS 26's Clear style: a dark frosted tile (light in the light
    appearance) and the drawing as one light glyph, whatever the icon's own
    background colour; transparent pixels stay transparent."""
    blue = QImage(64, 64, QImage.Format.Format_ARGB32_Premultiplied)
    blue.fill(QColor("#2aabee"))
    painter = QPainter(blue)
    painter.fillRect(24, 24, 16, 16, QColor("#ffffff"))
    painter.end()
    dark = im.clear(blue, True)
    tile, glyph = dark.pixelColor(10, 32), dark.pixelColor(32, 32)
    assert max(tile.red(), tile.green(), tile.blue()) < 90      # deep glass, not blue
    assert abs(tile.blue() - tile.red()) < 20                    # neutral grey
    assert min(glyph.red(), glyph.green(), glyph.blue()) > 180  # light glyph
    light = im.clear(blue, False)
    assert light.pixelColor(10, 32).red() > 180                  # light glass
    assert light.pixelColor(32, 32).red() < light.pixelColor(10, 32).red()
    transparent = QImage(8, 8, QImage.Format.Format_ARGB32_Premultiplied)
    transparent.fill(Qt.GlobalColor.transparent)
    assert im.clear(transparent, True).pixelColor(4, 4).alpha() == 0

    apps_dir = im.APPLICATIONS
    apps_dir.mkdir(parents=True)
    (apps_dir / "steam.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Steam\nIcon=steam\nExec=steam\n")
    monkeypatch.setattr(im, "list_apps", lambda: [
        {"id": "steam", "name": "Steam", "icon": "steam", "path": str(apps_dir / "steam.desktop")}])
    monkeypatch.setattr(im, "theme_icon", lambda name, mode: blue)
    assert im.main(["style", "clear"]) == 0
    assert json.loads(im.STATE.read_text())["style"] == "clear"
    for theme in ("MacTahoeLiquidKde-Icons-custom", "MacTahoeLiquidKde-Icons-dark-custom"):
        assert (im.ICONS / theme / "apps/512/steam.png").is_file()
    # Clear does not follow the accent: no refresh after an accent change.
    assert im.needs_refresh() is False


def test_tinted_finder_matches_macos(im):
    """macOS 26's Tinted Finder (TintedDark.png): the blue half becomes the
    near-black tile, the white face the accent at full strength, the black
    eyes a dim accent (45 %); a light background flips it (Safari's dial
    is the glyph)."""
    accent = QColor("#0088ff")
    finder = QImage(100, 100, QImage.Format.Format_ARGB32_Premultiplied)
    finder.fill(QColor("#1ab0ff"))
    painter = QPainter(finder)
    painter.fillRect(50, 0, 50, 100, QColor("#f4f8ff"))   # the face, reaching the edges
    painter.fillRect(25, 40, 6, 12, QColor("#101010"))    # an eye on the blue half
    painter.fillRect(75, 40, 6, 12, QColor("#101010"))    # an eye on the face
    painter.end()
    out = im.tint(finder, accent, True)
    tile, face = out.pixelColor(15, 70), out.pixelColor(70, 70)
    eye_left, eye_right = out.pixelColor(27, 46), out.pixelColor(77, 46)
    assert tile.blue() < 40                                 # near black
    assert face.blue() > 230 and abs(face.green() - 136) < 25  # the accent
    assert 60 < eye_left.blue() < 160                       # dim accent on the tile
    assert eye_right.blue() < face.blue() - 60              # dark on the face

    safari = QImage(100, 100, QImage.Format.Format_ARGB32_Premultiplied)
    safari.fill(QColor("#ffffff"))
    painter = QPainter(safari)
    painter.fillRect(25, 25, 50, 50, QColor("#1a8cff"))   # the dial
    painter.end()
    dial = im.tint(safari, accent, True).pixelColor(50, 50)
    assert dial.blue() > 230


def test_bundled_macos_styles_cover_the_pack_apple_icons(src):
    """macOS 26's own Dark render and drawing mask (decoded from the apps'
    .iconstack) for the pack's Apple icons, under every name showing them."""
    import json
    styles = src / "offline/icon-manager/macos-styles"
    index = json.loads((styles / "index.json").read_text())
    for name in ("org.kde.dolphin", "org.kde.kcalc", "org.kde.konsole", "systemsettings"):
        assert name in index, name
    for stem in set(index.values()):
        assert (styles / f"{stem}.dark.png").is_file(), stem
        assert (styles / f"{stem}.glyph.png").is_file(), stem


def test_styles_use_the_bundled_macos_drawing(im, tmp_path, monkeypatch):
    """Tinted and Clear draw a bundled icon with macOS' own mask, Dark takes
    macOS' own render; other icons keep the guessed mask."""
    from PyQt6.QtGui import QColor, QImage
    assert im.macos_style("org.kde.konsole") == "terminal"
    assert im.macos_style("not-an-icon") is None
    icon = QImage(64, 64, QImage.Format.Format_ARGB32_Premultiplied)
    icon.fill(QColor(30, 30, 30))
    glyph = im._macos_asset("terminal", "glyph", icon.size())
    assert glyph is not None and glyph.size() == icon.size()
    dark = im._macos_asset("terminal", "dark", icon.size())
    assert dark is not None and dark.size() == icon.size()
    calls = []
    real = im._glyph_mask
    monkeypatch.setattr(im, "_glyph_mask", lambda source: calls.append(1) or real(source))
    im.tint(icon, QColor(0, 136, 255), True, glyph)
    assert calls == []
    im.tint(icon, QColor(0, 136, 255), True)
    assert calls == [1]


def test_an_app_own_macos_styles_win_over_the_redraw(im, tmp_path, monkeypatch):
    """An icon from a .dmg with a layered icon brings its own Dark render
    and drawing mask (style_asset): the Dark style shows that render as is,
    Tinted draws with that mask; a new light icon or a reset drops them."""
    apps_dir = im.APPLICATIONS
    apps_dir.mkdir(parents=True)
    (apps_dir / "firefox.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Firefox\nIcon=firefox\nExec=firefox\n")
    monkeypatch.setattr(im, "list_apps", lambda: [
        {"id": "firefox", "name": "Firefox", "icon": "firefox",
         "path": str(apps_dir / "firefox.desktop")}])
    im.STORE.mkdir(parents=True)
    light = QImage(im.CANVAS, im.CANVAS, QImage.Format.Format_ARGB32_Premultiplied)
    light.fill(QColor("#21143a"))
    light.save(str(im.stored("firefox", "light")))
    own = QImage(im.CANVAS, im.CANVAS, QImage.Format.Format_ARGB32_Premultiplied)
    own.fill(QColor("#ff8800"))                         # unlike any redraw
    own.save(str(im.style_asset("firefox", "dark")))
    glyph = QImage(im.CANVAS, im.CANVAS, QImage.Format.Format_Grayscale8)
    glyph.fill(QColor("#ffffff"))
    glyph.save(str(im.style_asset("firefox", "glyph")))

    assert im._style_assets("firefox", None)("dark", own.size()).pixelColor(9, 9) == QColor("#ff8800")
    assert im._style_assets(None, "terminal")("dark", own.size()) is not None   # bundled
    assert im._style_assets("other", None)("dark", own.size()) is None

    assert im.main(["style", "dark"]) == 0
    shown = QImage(str(im.tinted("firefox", "dark")))
    assert shown.pixelColor(256, 256) == QColor("#ff8800")
    calls = []
    real = im._glyph_mask
    monkeypatch.setattr(im, "_glyph_mask", lambda source: calls.append(1) or real(source))
    assert im.main(["style", "tinted"]) == 0
    assert calls == []                                  # the app's own mask

    im.reset_icon("firefox", "light")
    assert not im.style_asset("firefox", "dark").exists()
    assert not im.style_asset("firefox", "glyph").exists()
    own.save(str(im.style_asset("firefox", "dark")))
    png = tmp_path / "new.png"
    light.save(str(png))
    assert im.set_icon("firefox", "light", png) == ""
    assert not im.style_asset("firefox", "dark").exists()


def test_bundled_dmg_apps_have_their_macos_styles(src):
    """The pack's icons from .dmg (Firefox, Steam, ChatGPT, Claude) bring
    their DarkAqua render and Tintable mask, under every name."""
    styles = src / "offline/icon-manager/macos-styles"
    index = json.loads((styles / "index.json").read_text())
    for name in ("firefox", "org.mozilla.firefox", "firefox-esr"):
        assert index.get(name) == "firefox", name
    assert "firefox-nightly" not in index
    # Steam, ChatGPT and Claude: the layered icons of their .dmg.
    for name, stem in (("steam", "steam"), ("com.valvesoftware.Steam", "steam"),
                       ("chatgpt", "chatgpt"), ("openai", "chatgpt"),
                       ("claude-desktop", "claude-desktop"), ("com.anthropic.Claude", "claude-desktop")):
        assert index.get(name) == stem, name
