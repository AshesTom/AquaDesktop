"""The Quickshell menu bar (src/offline/shell): not installed, the reference
the Plasma menu bar's plasmoids are styled after, sharing their views."""

from pathlib import Path


def test_shell_reuses_the_plasmoid_views(offline):
    views = offline / "shell/views"
    for name in ("controlcenter", "wifi", "spotlight", "nowplaying", "globalmenu"):
        link = views / name
        assert link.is_symlink() and (link / "Glyph.qml" if name in ("controlcenter", "wifi")
                                      else link).exists(), name
    shell = (offline / "shell/shell.qml").read_text()
    assert 'import "views/controlcenter" as CC' in shell
    assert "IpcHandler {" in shell and "function toggle(name: string)" in shell
    # One popover at a time; a click elsewhere closes it.
    assert 'onPressed: shell.openPopover = ""' in shell


def test_popovers_blur_only_their_glass(offline):
    popover = (offline / "shell/Popover.qml").read_text()
    assert "BackgroundEffect.blurRegion: glass" in popover and "mask: glass" in popover
    # The Glass effect never force-blurs dock surfaces.
    assert 'WlrLayershell.namespace: "dock"' in popover
    region = (offline / "shell/GlassRegion.qml").read_text()
    assert "item.glassRadius" in region


def test_views_translate_without_plasma(offline):
    """Quickshell has no KLocalizedContext: each shared view brings its own."""
    ui = offline / "plasmoids/org.kde.mac-tahoe-liquid-kde.wifi/contents/ui/WifiView.qml"
    text = ui.read_text()
    assert "import org.kde.ki18n as KI18n" in text
    assert 'translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.wifi"' in text


def test_menu_bar_shows_the_active_apps_menus(offline):
    """The Global Menu's model outside Plasma: a compiled QML module (not
    installed), loaded so a missing module keeps the Apple logo."""
    module = offline / "qml/org.kde.mac.tahoe.liquid.appmenu"
    cmake = (module / "CMakeLists.txt").read_text()
    assert "ecm_add_qml_module(macTahoeAppMenu URI org.kde.mac.tahoe.liquid.appmenu" in cmake
    assert "plasmoids/org.kde.mac.tahoe.liquid.globalmenu/libdbusmenuqt" in cmake
    assert (offline / "plasmoids/org.kde.mac.tahoe.liquid.globalmenu/libdbusmenuqt/CMakeLists.txt").is_file()
    assert "find_package(Plasma" not in cmake
    source = (module / "appmenu.cpp").read_text()
    # Apps export their menus while a global menu view exists.
    assert 'QStringLiteral("org.kde.kappmenuview")' in source
    # One proxy QMenu: switching menus never opens a new popup (KWin
    # refuses a grabbing popup opened on a key press).
    assert "m_proxy->move(pos);" in source
    assert "m_importer->updateMenu(source);" in source

    bar = (offline / "shell/MenuBar.qml").read_text()
    assert 'source: "AppMenuBar.qml"' in bar
    assert "visible: appMenus.status === Loader.Error" in bar
    menus = (offline / "shell/AppMenuBar.qml").read_text()
    assert "import org.kde.mac.tahoe.liquid.appmenu" in menus
    # The opening press is left unaccepted: the menu takes its release.
    assert "mouse.accepted = false;" in menus
    # macOS: the app name in bold, menu titles in the regular weight.
    assert "bold: true" in menus and "font.weight: title.bold ? Font.Bold : Font.Normal" in menus


def test_about_window_translates_without_plasma(offline):
    about = (offline / "plasmoids/org.kde.mac.tahoe.liquid.globalmenu/qml/AboutWindow.qml").read_text()
    assert "import org.kde.ki18n as KI18n" in about
    assert 'translationDomain: "plasma_applet_org.kde.mac.tahoe.liquid.globalmenu"' in about


def test_popovers_keep_their_corners_clear_of_glass_rounding(offline):
    """Glass rounds a dock surface with DockCornerRadius (24 px): the window
    keeps transparent room so it never cuts the views' own corners."""
    popover = (offline / "shell/Popover.qml").read_text()
    assert "readonly property int pad: 28" in popover
    assert "top: popoverY - padTop" in popover and "left: popoverX - padLeft" in popover
    assert "implicitWidth: padLeft + viewWidth + padRight" in popover
    # Never wider than the room left on screen (layer surfaces get moved).
    assert "screen.width - popoverX - viewWidth" in popover


def test_kvantum_sends_no_blur_request_for_hidden_windows(offline):
    patch = (offline / "kvantum-engine/patches/0002-no-blur-request-on-hidden-windows.patch").read_text()
    assert "+++ b/Kvantum/style/blur/blurhelper.cpp" in patch
    assert "+  if (!win->isVisible())\n+    return;" in patch
    assert "+  if (win != nullptr && win->isVisible()) // see update()" in patch


def test_plasma_menu_bar_matches_the_quickshell_render(offline):
    """The Plasma menu bar draws its extras and popovers like the reference
    Quickshell bar: pure white 18 px glyphs, the Wi-Fi menu in a glass panel
    of its own, and KDE's accent itself rather than the darker selection."""
    plasmoids = offline / "plasmoids"
    wifi = (plasmoids / "org.kde.mac-tahoe-liquid-kde.wifi/contents/ui/main.qml").read_text()
    assert 'glyph: "wifi"' in wifi and 'color: "white"' in wifi and "width: 18" in wifi
    assert "backgroundHints: PlasmaCore.Dialog.NoBackground" in wifi
    assert "readonly property real glassRadius: radius" in wifi and "radius: 14" in wifi
    assert 'source: "WindowBlur.qml"' in wifi
    cc = (plasmoids / "org.kde.mac-tahoe-liquid-kde.controlcenter/contents/ui/main.qml").read_text()
    assert 'glyph: "controlcenter"\n            color: "white"' in cc
    search = (plasmoids / "org.kde.mac-tahoe-liquid-kde.spotlight/contents/ui/main.qml").read_text()
    assert 'isMask: true\n            color: "white"' in search

    for plasmoid, view in (("wifi", "WifiView"), ("controlcenter", "ControlCenterView"),
                           ("spotlight", "SpotlightView")):
        ui = plasmoids / f"org.kde.mac-tahoe-liquid-kde.{plasmoid}/contents/ui"
        accent = (ui / "AccentColor.qml").read_text()
        # [General] is QSettings' top level: a category would read nothing.
        assert "category:" not in accent
        assert 'kdeglobals.value("AccentColor", "")' in accent
        text = (ui / f"{view}.qml").read_text()
        assert 'target: view.Kirigami.Theme' in text and "when: kdeAccent.valid" in text


def test_plasma_popovers_keep_their_corners_clear_of_glass_rounding(offline):
    """Glass rounds these dialogs like normal windows (22 px): each keeps
    transparent room above and below its glass, so the rounding never cuts
    the glass's own corners; the dialog moves up by as much."""
    for plasmoid in ("wifi", "controlcenter", "spotlight"):
        main = (offline / f"plasmoids/org.kde.mac-tahoe-liquid-kde.{plasmoid}/contents/ui/main.qml").read_text()
        assert "readonly property int glassPad: 28" in main, plasmoid
        assert ") - glassPad;" in main, plasmoid
        assert "2 * root.glassPad" in main, plasmoid


def test_menu_bar_extras_are_macos_ones(offline):
    """Battery ("72%" beside the glyph, a bolt while charging) and Sound
    (the speaker by level, the macOS sound bubble) replace the tray's
    applets, and the tray shows no overflow arrow."""
    plasmoids = offline / "plasmoids"
    battery = plasmoids / "org.kde.mac-tahoe-liquid-kde.battery/contents/ui"
    main = (battery / "main.qml").read_text()
    assert 'engine: "powermanagement"' in main
    assert 'text: Math.round(root.percent) + "%"' in main
    assert "PlasmaCore.Types.HiddenStatus" in main  # gone without a battery
    glyph = (battery / "BatteryGlyph.qml").read_text()
    assert 'c.globalCompositeOperation = "destination-out";' in glyph  # the bolt's gap
    assert '"#ff453a"' in glyph                                        # low battery
    volume = plasmoids / "org.kde.mac-tahoe-liquid-kde.volume/contents/ui"
    vmain = (volume / "main.qml").read_text()
    assert "PlasmaPa.PreferredDevice.sink" in vmain and "onWheel:" in vmain
    view = (volume / "VolumeView.qml").read_text()
    # The menu's bubble; the volume HUD has its own (test_volume_hud.py).
    assert "implicitWidth: hud ? 292 : 322" in view and "implicitHeight: hud ? 64 : 68" in view
    assert "view.sink.description" in view
    # No overflow arrow: the tray fork hides it, the Control Center's
    # "Other Status Items" bubble opens the tray's menu.
    tray = plasmoids / "org.kde.mac.tahoe.liquid.systemtray"
    main_qml = (tray / "qml/main.qml").read_text()
    assert "AquaDesktop: no arrow in the menu bar" in main_qml
    assert "systemTrayState.expanded = !systemTrayState.expanded;" in main_qml
    cc = (plasmoids / "org.kde.mac-tahoe-liquid-kde.controlcenter/contents/ui/main.qml").read_text()
    assert 'applet.pluginName === "org.kde.mac.tahoe.liquid.systemtray"' in cc
    assert "root.trayApplet.activated()" in cc
    view = (plasmoids / "org.kde.mac-tahoe-liquid-kde.controlcenter/contents/ui/ControlCenterView.qml").read_text()
    assert '"Other Status Items"' in view and "signal statusItemsRequested()" in view


def test_tray_fork_is_a_macos_menu(offline):
    tray = offline / "plasmoids/org.kde.mac.tahoe.liquid.systemtray"
    meta = (tray / "metadata.json").read_text()
    assert '"Id": "org.kde.mac.tahoe.liquid.systemtray"' in meta
    cmake = (tray / "CMakeLists.txt").read_text()
    assert "plasma_add_applet(org.kde.mac.tahoe.liquid.systemtray" in cmake
    assert 'TRANSLATION_DOMAIN="plasma_applet_org.kde.plasma.systemtray"' in cmake
    assert "org.kde.mac.tahoe.liquid.globalmenu/libdbusmenuqt" in cmake
    expanded = (tray / "qml/ExpandedRepresentation.qml").read_text()
    assert "Layout.minimumWidth: menuMode ? 280" in expanded
    assert '"Status Items Settings…"' in expanded
    hidden = (tray / "qml/HiddenItemsView.qml").read_text()
    assert "readonly property int columns: 1" in hidden and "readonly property int delegateHeight: 28" in hidden
    assert (tray / "UPSTREAM.md").read_text().count("v6.7.5") >= 1
    step = (offline.parent / "scripts/steps/plasmoids.py").read_text()
    assert 'cmake_build(SYSTEMTRAY_SRC, SYSTEMTRAY_BUILD, "System Tray")' in step
    assert "_install_systemtray()" in step


def test_dock_draws_macos_running_dots(offline):
    """One small dot under every running app, whatever its state (macOS has
    no focus, hover or attention variants), in the accent colour (blue by
    default, as the user asked), and no spinner at launch."""
    import gzip
    import re
    for theme in ("MacTahoeLiquidKde-Dark", "MacTahoeLiquidKde-Light"):
        svg = gzip.decompress((offline / f"plasma-theme/{theme}/widgets/tasks.svgz").read_bytes()).decode()
        for state in ("normal", "focus", "hover", "minimized", "attention"):
            body = re.search(r'<g\b[^>]*\bid="%s-bottom"[^>]*>(.*?)</g>' % state, svg, re.S).group(1)
            dot = re.search(r'<rect[^>]*width="4"\s+height="4"[^>]*>', body, re.S).group(0)
            assert 'class="ColorScheme-Highlight"' in dot and "opacity:1" in dot, (theme, state)
            assert 'width="48"' not in body
    task = (offline / "plasmoids/org.kde.mac.tahoe.liquid.taskmanager/contents/ui/Task.qml").read_text()
    assert "active: task.model.IsStartup && !task.dockLayout" in task


def test_battery_menu_has_the_energy_mode_choices(offline):
    """Supported power profiles in the macOS mode row's expandable choices;
    a missing module or daemon only drops the section."""
    ui = offline / "plasmoids/org.kde.mac-tahoe-liquid-kde.battery/contents/ui"
    energy = (ui / "EnergyMode.qml").read_text()
    assert 'readonly property var stops: ["power-saver", "balanced", "performance"]' in energy
    assert "BatteryMonitor.PowerProfilesControl {" in energy
    assert "control.setProfile(profile);" in energy
    for name in ('"Low Power"', '"Automatic"', '"High Power"'):
        assert name in energy
    view = (ui / "BatteryView.qml").read_text()
    assert 'source: "EnergyMode.qml"' in view
    assert "org.kde.plasma.private.batterymonitor" not in view


def test_dock_and_shortcuts_follow_macos(offline):
    tooltip = (offline / "plasmoids/org.kde.mac.tahoe.liquid.taskmanager/contents/ui/ToolTipDelegate.qml").read_text()
    # The Dock shows the app's name only, no thumbnails or media controls.
    assert "sourceComponent: dockLabel ? dockNameLabel : isGroup ? groupToolTip : singleTooltip" in tooltip
    task = (offline / "plasmoids/org.kde.mac.tahoe.liquid.taskmanager/contents/ui/Task.qml").read_text()
    assert "interactive: !dockLayout && (model.IsWindow || mainItem.playerData)" in task
    for layout in ("layouts/mac-tahoe.js",
                   "look-and-feel/MacTahoeLiquidKde-Dark/contents/layouts/org.kde.plasma.desktop-layout.js",
                   "look-and-feel/MacTahoeLiquidKde-Light/contents/layouts/org.kde.plasma.desktop-layout.js"):
        assert 'spotlight.globalShortcut = "Meta+Space";' in (offline / layout).read_text(), layout


def test_kvantum_menus_get_the_tahoe_metrics(offline):
    """Patch 0003: 13 px above and below a menu's items, 24 px rows."""
    patch = (offline / "kvantum-engine/patches/0003-tahoe-menu-metrics.patch").read_text()
    assert "Kvantum/style/tahoe_menu.h" in patch
    assert "Tahoe::menuExtraVMargin(widget)" in patch
    assert "Tahoe::menuItemPadding()" in patch
