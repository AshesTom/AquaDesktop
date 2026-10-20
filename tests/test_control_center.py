"""macOS Tahoe Control Center plasmoid: menu bar glyph, Tahoe grid and
backend isolation. Shape tests only; the live modules need a Plasma
session."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = "plasmoids/org.kde.mac-tahoe-liquid-kde.controlcenter"
UI = f"{ROOT}/contents/ui"
BACKENDS = {
    "WifiTile.qml": "import org.kde.plasma.networkmanagement as PlasmaNM",
    "BluetoothTile.qml": "import org.kde.bluezqt as BluezQt",
    "FocusTile.qml": "import org.kde.notificationmanager as NotificationManager",
    "DisplayTile.qml": "import org.kde.plasma.private.brightnesscontrolplugin as BC",
    "SoundTile.qml": "import org.kde.plasma.private.volume as PlasmaPa",
    "NowPlayingTile.qml": "import org.kde.plasma.private.mpris as Mpris",
}
LAYOUTS = [
    "layouts/mac-tahoe.js",
    "look-and-feel/MacTahoeLiquidKde-Light/contents/layouts/org.kde.plasma.desktop-layout.js",
    "look-and-feel/MacTahoeLiquidKde-Dark/contents/layouts/org.kde.plasma.desktop-layout.js",
]


def test_metadata_id_matches_directory(offline):
    metadata = json.loads((offline / ROOT / "metadata.json").read_text())
    assert metadata["KPlugin"]["Id"] == "org.kde.mac-tahoe-liquid-kde.controlcenter"


@pytest.mark.parametrize("relative_path", LAYOUTS)
def test_menu_bar_places_control_center_between_search_and_clock(offline, relative_path):
    script = (offline / relative_path).read_text()
    search = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.spotlight")')
    control_center = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.controlcenter")')
    clock = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.clock")')
    assert search < control_center < clock


def test_grid_matches_the_tahoe_capture(offline):
    view = (offline / UI / "ControlCenterView.qml").read_text()
    # Four 64 px cells, 12 px apart: 292 px; 64 px sliders (tahoe.jpg).
    assert "readonly property int cell: 64" in view
    assert "readonly property int gap: 12" in view
    assert "readonly property int sliderHeight: 64" in view
    assert "implicitWidth: span(4)" in view
    # Tahoe's rows: Wi-Fi/media; Bluetooth/AirDrop; Focus/Stage Manager/
    # Screen Mirroring; Display; Sound; then the four compact utilities.
    order = [view.index(marker) for marker in (
        '"WifiTile.qml"', '"NowPlayingTile.qml"', '"BluetoothTile.qml"', '"AirDropTile.qml"',
        '"FocusTile.qml"', 'glyph: "stage"', 'glyph: "mirroring"',
        '"DisplayTile.qml"', '"SoundTile.qml"', 'glyph: "contrast"',
        'glyph: "calculator"', 'glyph: "timer"', 'glyph: "screenshot"')]
    assert order == sorted(order)
    assert 'view.invokeKWinShortcut("Overview")' in view
    assert "property bool showEditControls: true" in view


@pytest.mark.parametrize("file_name,module_import", BACKENDS.items())
def test_each_backend_lives_in_its_own_file(offline, file_name, module_import):
    """A missing optional Plasma module must only dim its own module."""
    assert module_import in (offline / UI / file_name).read_text()
    view = (offline / UI / "ControlCenterView.qml").read_text()
    if file_name in ("WifiTile.qml", "BluetoothTile.qml",
                     "FocusTile.qml", "DisplayTile.qml", "SoundTile.qml", "NowPlayingTile.qml"):
        assert f'source: "{file_name}"' in view
    # The view and the generic widgets never import a backend directly.
    for generic in ("ControlCenterView.qml", "Tile.qml", "CircleButton.qml",
                    "ToggleTile.qml", "SliderTile.qml", "Glyph.qml", "main.qml"):
        assert module_import not in (offline / UI / generic).read_text(), generic


def test_module_loader_falls_back_instead_of_leaving_a_hole(offline):
    view = (offline / UI / "ControlCenterView.qml").read_text()
    assert "component ModuleLoader: Loader {" in view
    assert "active: moduleLoader.status === Loader.Error" in view


def test_popup_is_a_fixed_size_floating_popover(offline):
    """Fixed size like every macOS menu bar extra, and floating fully rounded
    under the menu bar: Plasma glues applet popups to a non-floating panel,
    square top corners under the bar."""
    main = (offline / UI / "main.qml").read_text()
    assert "width: implicitWidth" in main and "height: implicitHeight" in main
    assert "PlasmaCore.Dialog {" in main
    assert "location: PlasmaCore.Types.Floating" in main
    assert "fullRepresentation: Item {}" in main
    assert "readonly property int popoverGap: 6" in main
    assert "function onActivated(): void" in main
    # Golden Gate: no panel behind the modules, each one is its own bubble.
    assert "backgroundHints: PlasmaCore.Dialog.NoBackground" in main


def test_modules_are_neutral_tahoe_glass(offline):
    tile = (offline / UI / "Tile.qml").read_text()
    circle = (offline / UI / "CircleButton.qml").read_text()
    palette = (offline / UI / "Palette.js").read_text()
    # Liquid Glass bubbles: GlassSurface draws the face, KWin the glass.
    assert not (offline / UI / "GlassRim.qml").exists()
    assert "glassBody" not in palette
    for source in (tile, circle):
        assert "GlassSurface {" in source
    # macOS Tahoe: active toggles are a white disc under an accent glyph.
    assert 'if (button.active) {\n                return "white";' in circle
    assert "color: button.active ? button.activeColor : Kirigami.Theme.textColor" in circle
    # 36 px discs centred in the supplied 64 px toggle tiles. Display and
    # Sound keep rounded corners; Now Playing spans the two-row tile.
    toggle = (offline / UI / "ToggleTile.qml").read_text()
    assert "width: 36" in toggle and "leftMargin: (parent.height - width) / 2" in toggle
    assert "    radius: height / 2\n" in tile
    assert "    radius: 24\n" in (offline / UI / "SliderTile.qml").read_text()
    assert "    radius: 28\n" in (offline / UI / "NowPlayingTile.qml").read_text()
    assert "readonly property real glassRadius: radius" in tile
    assert "readonly property real glassRadius: bubble ? width / 2 : -1" in circle
    # 13 px titles, 11 px states.
    assert "const textSize = 13;" in palette and "const smallTextSize = 11;" in palette
    for name in ("ToggleTile.qml", "SliderTile.qml", "NowPlayingTile.qml"):
        assert "font.pixelSize: Palette.textSize" in (offline / UI / name).read_text()
    # 9 px bars without a knob between a glyph at each end; Sound ends with
    # the AirPlay accessory.
    slider = (offline / UI / "SliderTile.qml").read_text()
    assert "knob" not in slider.split("*/", 1)[1]
    assert "height: 9" in slider and "color: Palette.fillColor" in slider
    assert "glyph: tile.leadingGlyph" in slider and "glyph: tile.trailingGlyph" in slider
    sound = (offline / UI / "SoundTile.qml").read_text()
    assert 'accessoryGlyph: "airplay"' in sound and 'trailingGlyph: "speaker-high"' in sound
    assert 'trailingGlyph: "sun-high"' in (offline / UI / "DisplayTile.qml").read_text()


def test_glyphs_are_coloured_by_the_widget_not_the_icon_theme(offline):
    glyphs = (offline / UI / "Glyphs.js").read_text()
    glyph = (offline / UI / "Glyph.qml").read_text()
    names = set(re.findall(r'^    "([a-z-]+)": ', glyphs, re.M))
    used = set()
    for path in (offline / UI).glob("*.qml"):
        used |= set(re.findall(r'[gG]lyph: "([a-z-]+)"', path.read_text()))
    assert used <= names, used - names
    assert "controlcenter" in names
    assert 'body.split("#000").join(rgb)' in glyphs
    assert "Glyphs.url(glyph, color)" in glyph
    assert "isMask" not in glyph


def test_dark_mode_button_uses_the_project_theme_switch(offline):
    view = (offline / UI / "ControlCenterView.qml").read_text()
    assert '$HOME/.local/bin/mac-tahoe-theme-switch' in view


def test_menu_bar_extras_do_not_highlight_on_hover(offline):
    spotlight = (offline / "plasmoids/org.kde.mac-tahoe-liquid-kde.spotlight"
                 / "contents/ui/main.qml").read_text()
    control_center = (offline / UI / "main.qml").read_text()
    assert "containsMouse" not in spotlight
    # Highlighted only while its popover is open.
    assert "visible: popover.visible" in control_center
    assert "button.containsMouse ||" not in control_center


def test_glass_blur_is_optional_and_shaped(offline, src):
    """KWin blurs behind each module only; a missing compiled module only
    loses the blur, never the Control Center."""
    main = (offline / UI / "main.qml").read_text()
    assert 'source: "WindowBlur.qml"' in main
    assert "onLoaded: item.target = view" in main
    # Frameless: the popover itself keeps the gap under the menu bar.
    assert "readonly property int topInset: 8" in main
    blur = (offline / UI / "WindowBlur.qml").read_text()
    assert "import org.kde.mac.tahoe.liquid.glass as Glass" in blur
    for generic in ("ControlCenterView.qml", "main.qml", "Tile.qml", "CircleButton.qml"):
        assert "org.kde.mac.tahoe.liquid.glass" not in (offline / UI / generic).read_text()
    cpp = (offline / "qml/org.kde.mac.tahoe.liquid.glass/glassblur.cpp").read_text()
    assert 'property("glassRadius")' in cpp
    assert "KWindowEffects::enableBlurBehind(m_window, !region.isEmpty(), region)" in cpp
    # Plasma's Dialog rewrites the blur on show / resize: ask again after.
    assert "case QEvent::PlatformSurface:" in cpp and "m_settleTimer" in cpp
    # The blur region only applies on the surface's next commit: a popup
    # that had stopped repainting came up unblurred one time in two.
    apply = cpp[cpp.index("void GlassBlur::apply()"):]
    assert apply.index("enableBlurBehind") < apply.index("m_window->update();")
    steps = (src / "scripts/steps/plasmoids.py").read_text()
    assert '"Control Center glass blur"' in steps


GLASS_SURFACE_PACKAGES = ("controlcenter", "wifi", "clock", "volume", "battery", "spotlight",
                          "keyboard")


def _glass_surfaces(offline):
    plasmoids = offline / "plasmoids"
    for name in GLASS_SURFACE_PACKAGES:
        yield name, plasmoids / f"org.kde.mac-tahoe-liquid-kde.{name}/contents/ui"


def test_glass_surface_is_the_tahoe_glass_face(offline):
    """GlassSurface, measured on Apple's macOS Tahoe Control Center image:
    clear glass ringed by added light, the same file in every popover."""
    first = None
    for name, ui in _glass_surfaces(offline):
        files = tuple((ui / f).read_bytes() for f in (
            "GlassSurface.qml", "shaders/glasssurface.frag", "shaders/glasssurface.frag.qsb"))
        assert files[2], name
        first = first or files
        assert files == first, name
    surface, frag = first[0].decode(), first[1].decode()
    # The Plasma popups' face over Acrylic Glass (8 % white), or the accent
    # with the accent tint of Theme Settings.
    assert 'readonly property color tint: accentTint ? "#" + accentHex : "#ffffff"' in surface
    assert "readonly property real defaultTintAlpha: accentTint ? 0.20 : 0.08" in surface
    assert 'glassTint.value("GlassLevel", 50)' in surface
    assert '+ "/mac-tahoe-liquid-kde/glass.ini"' in surface
    assert 'glassTint.value("Tint", "macos")' in surface
    # A 1 px light edge, no glow, over Acrylic Glass' own highlight.
    for line in ("rimLight: 0.08", "rimWidth: 1.0", "glowLight: 0"):
        assert f"readonly property real {line}\n" in surface
    # The light has no alpha of its own: added to the desktop, it keeps the
    # desktop's colour as on macOS.
    assert "vec4(tint.rgb * tint.a + vec3(light), tint.a)" in frag
    assert "jaxparrow07" in frag and "vec3 sceneSDFAndNormal(vec2 p)" in frag
    for gone in ("cornerSpec", "edgeSpec", "mousePos", "specStrength"):
        assert gone not in surface + frag


def test_glass_surface_shader_is_compiled_from_its_source(offline):
    """The .qsb must carry the uniforms GlassSurface.qml sets (a stale
    build would silently ignore them)."""
    qsb = shutil.which("qsb") or next(
        (p for p in ("/usr/lib/qt6/bin/qsb", "/usr/lib64/qt6/bin/qsb") if Path(p).exists()), None)
    if qsb is None:
        pytest.skip("qsb not installed")
    ui = next(_glass_surfaces(offline))[1]
    dump = subprocess.run([qsb, "-d", str(ui / "shaders/glasssurface.frag.qsb")],
                          capture_output=True, text=True, check=True).stdout
    for uniform in ("tint", "rimLight", "rimWidth", "glowLight", "glowWidth", "hoverLight"):
        assert f'"name": "{uniform}"' in dump, uniform


def test_control_center_is_white_on_glass_in_both_modes(offline):
    view = (offline / UI / "ControlCenterView.qml").read_text()
    # Apple's image: white text and glyphs, in light and dark mode alike.
    assert 'property: "textColor"\n        value: "#ffffff"' in view
    # The Dark Mode toggle still follows the system, not the white text.
    assert "readonly property bool dark: Palette.isDark(host.Kirigami.Theme.textColor)" in view
    # 26-30 px glyphs in the 70 px bubbles, the calculator filled.
    circle = (offline / UI / "CircleButton.qml").read_text()
    assert "property real glyphScale: 0.48" in circle
    glyphs = (offline / UI / "Glyphs.js").read_text()
    calculator = re.search(r'^    "calculator": "(.*)",$', glyphs, re.M).group(1)
    assert 'fill-rule=\\"evenodd\\"' in calculator and "stroke" not in calculator


@pytest.mark.parametrize("name,file", [
    ("wifi", "main.qml"), ("volume", "SoundBubble.qml"), ("battery", "main.qml"),
    ("clock", "GlassCard.qml"), ("spotlight", "SpotlightView.qml"), ("keyboard", "main.qml"),
])
def test_popovers_draw_their_glass_with_glass_surface(offline, name, file):
    source = (offline / "plasmoids" / f"org.kde.mac-tahoe-liquid-kde.{name}/contents/ui" / file).read_text()
    assert "GlassSurface {" in source
