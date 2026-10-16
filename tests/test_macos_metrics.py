"""Menu bar and Dock geometry measured against macOS Tahoe at 1x.

Reference: a default macOS Tahoe 1280x720 capture at 1x, the Dock since
scaled to a macOS Tahoe desktop shown at 1920 px (62 px of glass, 39 px of
icon art on a 51 px pitch: 64 px thick, same ratios). Then: 43 px icons
14 px below the top edge of a 71 px Dock on a 59 px pitch, a 1 px divider 75%
of its height, floating 5 px above the screen edge; a 30 px menu bar with
~22 px between titles, a bold app name, a 13 px system-font clock without
separators and status items on a ~36 px pitch.
"""

import gzip
import re

import pytest

LAYOUTS = [
    "layouts/mac-tahoe.js",
    "look-and-feel/MacTahoeLiquidKde-Light/contents/layouts/"
    "org.kde.plasma.desktop-layout.js",
    "look-and-feel/MacTahoeLiquidKde-Dark/contents/layouts/"
    "org.kde.plasma.desktop-layout.js",
]
PLASMOIDS = "plasmoids"
TASKS_UI = f"{PLASMOIDS}/org.kde.mac.tahoe.liquid.taskmanager/contents/ui"
LAUNCHER = (f"{PLASMOIDS}/org.kde.mac-tahoe-liquid-kde.launcher/"
            "contents/ui/CompactRepresentation.qml")
TRASH = f"{PLASMOIDS}/org.kde.mac-tahoe-liquid-kde.trashcan/contents/ui/main.qml"
CLOCK = f"{PLASMOIDS}/org.kde.mac-tahoe-liquid-kde.clock/contents/ui/main.qml"
GLOBALMENU = f"{PLASMOIDS}/org.kde.mac.tahoe.liquid.globalmenu/qml"


@pytest.mark.parametrize("relative_path", LAYOUTS)
def test_layouts_use_macos_clock_dock_size_and_trash_divider(offline, relative_path):
    script = (offline / relative_path).read_text()

    assert 'addWidget("org.kde.mac-tahoe-liquid-kde.clock")' in script
    # The stock clock was pinned to a font family and point size, which
    # scaled with the screen's physical DPI (~17 px text on a 13" laptop).
    assert "fontFamily" not in script
    assert "fontSize" not in script
    assert "' | '" not in script
    assert "dock.height = 64;" in script
    assert "bar.height = 30;" in script
    assert 'tray.writeConfig("iconSpacing", 4);' in script

    separator = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.separator")')
    trash = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.trashcan")')
    tasks = script.index('addWidget("org.kde.mac.tahoe.liquid.icontasks")')
    assert tasks < separator < trash
    # macOS shows no gap or divider between the Apps launcher and the apps.
    launcher = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.launcher")')
    assert "marginsseparator" not in script[launcher:tasks]


def _ratio(text, name):
    match = re.search(rf"const {name} = ([0-9.]+);", text)
    assert match, name
    return match.group(1)


def test_dock_widgets_share_task_icon_proportions(offline):
    metrics = (offline / TASKS_UI / "LayoutMetrics.js").read_text()
    icon = _ratio(metrics, "dockIconRatio")
    top = _ratio(metrics, "dockIconTopRatio")
    slot = _ratio(metrics, "dockSlotRatio")
    # Slot 0.75: a 59 px pitch, 0.827 x the 71 px glass as on macOS 26.
    assert (icon, top, slot) == ("0.685", "0.16", "0.75")

    for relative_path in (LAUNCHER, TRASH):
        source = (offline / relative_path).read_text()
        assert f"* {icon})" in source, relative_path
        assert f"* {top}" in source, relative_path
        # The panel adds smallSpacing between applets; tasks don't have it.
        assert f"* {slot}) - Kirigami.Units.smallSpacing" in source, relative_path
        assert re.search(r"roundToIconSize: (false|!root\.dockLayout)", source), relative_path

    # Without CanFillArea the panel insets these applets by 8 px top and
    # bottom, so their icons would no longer line up with the tasks.
    for relative_path in (LAUNCHER.replace("CompactRepresentation", "main"), TRASH):
        assert "Plasmoid.CanFillArea" in (offline / relative_path).read_text()


def test_dock_task_icons_are_not_snapped_to_standard_sizes(offline):
    task = (offline / TASKS_UI / "Task.qml").read_text()

    # Kirigami rounds a 60 px icon down to 48 px unless told otherwise.
    assert "roundToIconSize: !task.dockLayout" in task
    assert "LayoutMetrics.dockIconSize()" in task
    assert "LayoutMetrics.dockIconTopMargin()" in task


def test_clock_uses_system_font_and_locale_order(offline):
    clock = (offline / CLOCK).read_text()

    assert "font: Kirigami.Theme.defaultFont" in clock
    assert "pixelSize" not in clock
    assert "pointSize" not in clock
    assert "family" not in clock
    assert 'Qt.locale().dateFormat(Locale.ShortFormat)' in clock
    assert 'Qt.locale().timeFormat(Locale.ShortFormat)' in clock
    assert "intervalAlignment" in clock


def test_global_menu_names_active_app_and_uses_regular_titles(offline):
    main = (offline / GLOBALMENU / "main.qml").read_text()
    delegate = (offline / GLOBALMENU / "MenuDelegate.qml").read_text()

    assert 'visible: appMenuModel.activeAppName !== ""\n' in main
    assert "font.weight: Font.Bold" in main
    assert "font.weight: Font.Normal" in delegate
    assert ("leftPadding: Kirigami.Units.largeSpacing + "
            "Kirigami.Units.smallSpacing / 2") in delegate


@pytest.mark.parametrize("theme", ["Light", "Dark"])
def test_dock_side_padding_matches_macos(offline, theme):
    svg = gzip.decompress(
        (offline / f"plasma-theme/MacTahoeLiquidKde-{theme}"
         "/widgets/panel-background.svgz").read_bytes()).decode()

    for side in ("left", "right"):
        rect = re.search(
            rf'<rect\b[^>]*id="south-hint-{side}-margin"[^>]*/>', svg, re.S)
        assert rect, side
        # Rotated 90 degrees: the height is the horizontal margin. 2 px puts
        # the first icon's art 12 px from the rim, 0.19 x the glass, as on
        # Apple's Docks (Golden Gate and dark captures).
        assert 'transform="rotate(90)"' in rect.group(0)
        assert 'height="2"' in rect.group(0)


def test_default_apple_logo_renders_at_macos_size(offline):
    root = offline / PLASMOIDS / "org.kde.mac.tahoe.liquid.globalmenu"
    main = (root / "qml/main.qml").read_text()
    svg = (root / "qml/apple-logo.svg").read_text()

    # Themes only ship the logo at fixed 16/22 px sizes (12x14 / 15x18 px
    # glyphs); the cropped copy is drawn 16x18 px like the macOS logo.
    assert 'root.cfgIcon === "start-here-kde-symbolic"' in main
    assert 'Qt.resolvedUrl("apple-logo.svg")' in main
    assert 'viewBox="4.8 2.7 22.4 26.6"' in svg
    assert "height: parent.appleLogo ? 18" in main
    assert "qml/apple-logo.svg" in (root / "CMakeLists.txt").read_text()


@pytest.mark.parametrize("relative_path", LAYOUTS)
def test_tray_keeps_only_macos_extras_in_the_menu_bar(offline, relative_path):
    script = (offline / relative_path).read_text()

    shown = re.search(r'tray\.writeConfig\("shownItems", "([^"]*)"\)', script).group(1)
    hidden = re.search(r'tray\.writeConfig\("hiddenItems", "([^"]*)"\)', script).group(1)
    # Nothing is forced into the bar: Battery and Sound are our own extras
    # after the tray, whose applets stay hidden (and its arrow too).
    assert shown == ""
    # The network applet stays (hidden) for its notifications and password
    # prompts; the macOS Wi-Fi menu sits right after the tray.
    assert "org.kde.plasma.networkmanagement" in hidden.split(",")
    for item in ("org.kde.plasma.bluetooth", "org.kde.plasma.brightness",
                 "org.kde.plasma.volume", "org.kde.plasma.battery", "Cachy-Update"):
        assert item in hidden.split(","), item

    tray = script.index('var tray = bar.addWidget(')
    # Our tray when installed, Plasma's otherwise.
    assert 'knownWidgetTypes.indexOf("org.kde.mac.tahoe.liquid.systemtray") >= 0' in script
    search = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.spotlight")')
    control_center = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.controlcenter")')
    clock = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.clock")')
    wifi = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.wifi")')
    keyboard = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.keyboard")')
    volume = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.volume")')
    battery = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.battery")')
    # macOS: the Input menu, Sound, Battery, Wi-Fi, Spotlight, Control
    # Center, the clock.
    assert tray < keyboard < volume < battery < wifi < search < control_center < clock


STATUS_ICONS = "icons/macos-status"
# Names the Plasma tray applets request (with the -symbolic suffix added
# in panels); a missing one silently falls back to Breeze.
TRAY_ICON_NAMES = [
    *(f"network-wireless-{level}" for level in ("0", "20", "40", "60", "80", "100")),
    *(f"network-wireless-{level}-locked" for level in ("0", "20", "40", "60", "80", "100")),
    *(f"network-wireless-connected-{level}" for level in ("00", "20", "40", "60", "80", "100")),
    "network-wireless-disconnected", "network-wired-activated",
    "network-bluetooth", "network-bluetooth-activated", "network-bluetooth-inactive",
    "audio-volume-muted", "audio-volume-low", "audio-volume-medium", "audio-volume-high",
    "brightness-high", "battery-missing", "system-search",
    *(f"battery-{p:03d}" for p in range(0, 101, 10)),
    *(f"battery-{p:03d}-charging" for p in range(0, 101, 10)),
    # Plugged in and full: BatteryIcon.qml asks for the power profile only.
    *(f"battery-profile-{profile}" for profile in ("performance", "balanced", "powersave")),
]


@pytest.mark.parametrize("name", TRAY_ICON_NAMES)
def test_macos_tray_icon_ships_for_every_requested_name(offline, name):
    svg = (offline / STATUS_ICONS / f"{name}-symbolic.svg").read_text()

    assert "ColorScheme-Text" in svg
    assert 'width="22" height="22"' in svg


@pytest.mark.parametrize("name", TRAY_ICON_NAMES)
def test_macos_tray_icons_are_self_contained(offline, name):
    svg = (offline / STATUS_ICONS / f"{name}-symbolic.svg").read_text()

    # Cut out of Sosumi's Plasma 5 sheets: every reference must resolve
    # inside the file and no editor metadata may leak through.
    ids = set(re.findall(r'\bid="([^"]+)"', svg))
    refs = set(re.findall(r"url\(#([^)]+)\)", svg)) | set(re.findall(r'href="#([^"]+)"', svg))
    assert refs <= ids, refs - ids
    assert "<use" not in svg
    assert "inkscape" not in svg and "sodipodi" not in svg
    assert 'id="current-color-scheme"' in svg


def test_macos_tray_icon_set_matches_importer_map(offline):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "import_sosumi", offline / STATUS_ICONS / "import_sosumi.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    shipped = {p.name[:-len("-symbolic.svg")] for p in (offline / STATUS_ICONS).glob("*.svg")}
    assert shipped == set(module.MAP)
    assert (offline / STATUS_ICONS / "LICENSE-Sosumi").is_file()


def test_icon_overlay_replaces_symlinks_and_first_matching_context(tmp_path, monkeypatch):
    from steps import icons

    overlay = tmp_path / "overlay"
    overlay.mkdir()
    (overlay / "system-search-symbolic.svg").write_text(
        '<style>.ColorScheme-Text { color:#363636; }</style>')
    (overlay / "network-bluetooth-symbolic.svg").write_text(
        '<style>.ColorScheme-Text { color:#363636; }</style>')
    monkeypatch.setattr(icons, "STATUS_OVERLAY_DIR", overlay)

    theme = tmp_path / "theme"
    for d in ("actions/22", "actions/16", "status/22", "status/symbolic", "status/16"):
        (theme / d).mkdir(parents=True)
    (theme / "status/22/audio-volume-high-symbolic.svg").write_text(
        '<style>.ColorScheme-Text { color:#f2f2f2; }</style>')
    (theme / "actions/22/system-search-symbolic.svg").write_text("breeze-like")
    (theme / "status/22/network-bluetooth.svg").write_text("other icon")
    (theme / "status/22/network-bluetooth-symbolic.svg").symlink_to("network-bluetooth.svg")

    icons._overlay_status_icons(theme)

    # actions/ precedes status/ in index.theme, so its copy must be replaced.
    assert "#f2f2f2" in (theme / "actions/22/system-search-symbolic.svg").read_text()
    assert not (theme / "actions/16/system-search-symbolic.svg").exists()
    link = theme / "status/22/network-bluetooth-symbolic.svg"
    assert not link.is_symlink()
    assert (theme / "status/22/network-bluetooth.svg").read_text() == "other icon"
    assert (theme / "status/symbolic/network-bluetooth-symbolic.svg").is_file()
    assert not (theme / "status/16/network-bluetooth-symbolic.svg").exists()


KVANTUM = "kvantum/mac-tahoe-liquid-kde"


@pytest.mark.parametrize("theme", ["mac-tahoe-liquid-kde", "mac-tahoe-liquid-kdeDark"])
def test_menu_highlight_is_a_rounded_rect_not_a_pill(offline, theme):
    """Kvantum only rounds a frame narrower than its expansion when an
    expand-<element> exists; 16 gives the 8 px Tahoe highlight. 25+ would
    turn the 25 px menu item into a pill."""
    kv = (offline / KVANTUM / f"{theme}.kvconfig").read_text()
    svg = (offline / KVANTUM / f"{theme}.svg").read_text()
    item = kv[kv.index("[MenuItem]\ninherits"):kv.index("[ComboBox]")]
    assert "frame.expansion=16" in item
    assert 'id="expand-menuitem-normal"' in svg
    for part in ("top", "bottom", "left", "right",
                 "topleft", "topright", "bottomleft", "bottomright"):
        assert f'id="expand-menuitem-normal-{part}"' in svg, part


@pytest.mark.parametrize("mode", ["Dark", "Light"])
def test_traffic_lights_use_tahoe_colours_and_pitch(offline, mode):
    rc = (offline / f"aurorae/MacTahoeLiquidKde-{mode}rc").read_text()
    # 14 px lights on a 23 px pitch, like the macOS Tahoe capture.
    assert "ButtonWidth=16" in rc
    assert "ButtonSpacing=7" in rc


def _traffic_light_generator(offline):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "traffic_lights", offline / "traffic-lights/generate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("mode", ["Dark", "Light"])
@pytest.mark.parametrize("button", ["close", "minimize", "maximize", "restore"])
def test_aurorae_traffic_lights_match_the_generator(offline, mode, button):
    """Golden Gate glass lights: Aurorae and GTK share one drawing, so the
    bundled SVGs must be what traffic-lights/generate.py writes."""
    gen = _traffic_light_generator(offline)
    lights = [gen.light(button, state, mode, element, 0, 20 * row)
              for row, (element, state) in enumerate(gen.AURORAE_STATES.items())]
    expected = gen.svg(lights, 16, 20 * len(gen.AURORAE_STATES))
    svg = (offline / f"aurorae/icons-{mode}/{button}.svg").read_text()
    assert svg == expected
    for element in ("active-center", "inactive-center", "hover-center",
                    "pressed-center", "deactivated-center"):
        assert f'id="{element}"' in svg
    # The specular rim of a Golden Gate light.
    assert 'stroke="url(#active-center-rim)"' in svg


def test_gtk_traffic_lights_are_the_same_in_every_theme(offline):
    dirs = [offline / f"gtk/MacTahoeLiquidKde-{theme}/gtk-{gtk}/windows-assets"
            for theme in ("Dark", "Light") for gtk in ("3.0", "4.0")]
    names = sorted(path.name for path in dirs[0].glob("titlebutton-*.png"))
    assert len(names) == 80
    for directory in dirs[1:]:
        for name in names:
            assert (directory / name).read_bytes() == (dirs[0] / name).read_bytes(), name


@pytest.mark.parametrize("theme", ["Light", "Dark"])
def test_panel_background_lets_the_menu_bar_be_30px(offline, theme):
    """Plasma clamps a panel to the frame's minimum drawing height at
    startup, before the edge prefix applies: the default top/bottom borders
    (10 px rects scaled vertically) must stay within half of 30 px."""
    svg = gzip.decompress(
        (offline / f"plasma-theme/MacTahoeLiquidKde-{theme}"
         "/widgets/panel-background.svgz").read_bytes()).decode()
    top = re.search(r'<g\s+transform="matrix\(([^)]*)\)"\s+id="top"', svg)
    assert top, theme
    scale_y = float(top.group(1).split(",")[3])
    assert 10 * scale_y * 2 <= 30


def test_dock_draws_no_group_expander(offline):
    # macOS marks an app with several windows by its dot alone; Plasma's
    # group expander drew a green "+" under such Dock icons.
    task = (offline / TASKS_UI / "Task.qml").read_text()
    created = task.index('Qt.createComponent("GroupExpanderOverlay.qml")')
    assert "if (!dockLayout) {" in task[created - 200:created]
