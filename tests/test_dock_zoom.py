"""macOS Dock behaviour: parabolic magnification, Downloads stack and the
minimized-windows section before the Trash.

The magnification is shared between independent applets through the
``org.kde.mac.tahoe.liquid.dockzoom`` QML singleton; the theme reserves the
headroom above the Dock glass, and the Trash widens the glass while the
Dock magnifies. These are shape tests: the live behaviour needs a Plasma
session.
"""

import gzip
import math
import re

import pytest

from steps import layout, plasmoids

DOCKZOOM = "qml/org.kde.mac.tahoe.liquid.dockzoom"
PLASMOIDS = "plasmoids"
TASKS_UI = f"{PLASMOIDS}/org.kde.mac.tahoe.liquid.taskmanager/contents/ui"
DOWNLOADS = f"{PLASMOIDS}/org.kde.mac-tahoe-liquid-kde.downloads"
DOCK_WIDGETS = [
    f"{PLASMOIDS}/org.kde.mac-tahoe-liquid-kde.launcher/contents/ui/CompactRepresentation.qml",
    f"{TASKS_UI}/main.qml",
    f"{PLASMOIDS}/org.kde.mac-tahoe-liquid-kde.separator/contents/ui/main.qml",
    f"{DOWNLOADS}/contents/ui/main.qml",
    f"{PLASMOIDS}/org.kde.mac-tahoe-liquid-kde.trashcan/contents/ui/main.qml",
]
LAYOUTS = [
    "layouts/mac-tahoe.js",
    "look-and-feel/MacTahoeLiquidKde-Light/contents/layouts/"
    "org.kde.plasma.desktop-layout.js",
    "look-and-feel/MacTahoeLiquidKde-Dark/contents/layouts/"
    "org.kde.plasma.desktop-layout.js",
]
THEMES = ["MacTahoeLiquidKde-Light", "MacTahoeLiquidKde-Dark"]


def test_dockzoom_module_exports_singleton_and_tracker(offline):
    qmldir = (offline / DOCKZOOM / "qmldir").read_text()
    assert "module org.kde.mac.tahoe.liquid.dockzoom" in qmldir
    assert "singleton DockZoom 1.0 DockZoom.qml" in qmldir
    assert "DockZoomTracker 1.0 DockZoomTracker.qml" in qmldir
    assert (offline / DOCKZOOM / "DockZoom.qml").read_text().startswith(
        "/*") and "pragma Singleton" in (offline / DOCKZOOM / "DockZoom.qml").read_text()


@pytest.mark.parametrize("relative_path", DOCK_WIDGETS)
def test_every_dock_widget_joins_the_shared_magnification(offline, relative_path):
    source = (offline / relative_path).read_text()
    assert "import org.kde.mac.tahoe.liquid.dockzoom" in source
    assert "DockZoomTracker {" in source
    # Widgets move with the bell; the task manager also drives its peak.
    assert ("DockZoom.shiftFor(" in source or "DockZoom.scaleFor(" in source
            or "target: DockZoom" in source or "DockZoomSlot {" in source)


def test_one_window_wide_catcher_watches_the_cursor(offline):
    """Hover inside an applet never reports a leave through the floating gap,
    so one catcher per Dock window tracks the cursor and releases outside the
    band the Dock widgets cover. It never blocks or takes clicks."""
    catcher = (offline / DOCKZOOM / "DockZoomCatcher.qml").read_text()
    zoom = (offline / DOCKZOOM / "DockZoom.qml").read_text()
    tracker = (offline / DOCKZOOM / "DockZoomTracker.qml").read_text()

    assert "blocking: false" in catcher
    assert "DockZoom.trackWindowPoint(catcher, point.scenePosition.x, point.scenePosition.y)" in catcher
    assert "MouseArea" not in catcher.split("*/", 1)[1]
    assert 'Qt.createComponent("DockZoomCatcher.qml")' in zoom
    assert "catcherComponent.createObject(root)" in zoom
    assert "DockZoomCatcher 1.0 DockZoomCatcher.qml" in (offline / DOCKZOOM / "qmldir").read_text()

    # Trackers only register the applet slot and raise its panel container.
    assert "HoverHandler" not in tracker
    assert "DockZoom.registerTracker(tracker, windowRoot)" in tracker
    assert "item.applet !== undefined" in tracker
    assert "value: DockZoom.stackingFor(tracker)" in tracker


def test_slot_grows_from_the_dock_bottom_edge(offline):
    slot = (offline / DOCKZOOM / "DockZoomSlot.qml").read_text()
    assert "origin.y: slot.height" in slot
    assert "DockZoom.scaleFor(slot)" in slot
    assert "DockZoom.shiftFor(slot)" in slot
    assert "DockZoomSlot 1.0 DockZoomSlot.qml" in (offline / DOCKZOOM / "qmldir").read_text()


@pytest.mark.parametrize("relative_path", [
    DOCK_WIDGETS[0], DOCK_WIDGETS[3], DOCK_WIDGETS[4],
])
def test_click_targets_move_with_the_magnified_icon(offline, relative_path):
    """A click lands where the icon is drawn: the MouseArea that opens the
    widget lives inside its DockZoomSlot, not on the resting slot."""
    source = (offline / relative_path).read_text()
    slot = source.index("DockZoomSlot {")
    assert source.index("MouseArea {", slot) > slot
    assert re.search(r"DockZoomSlot \{.*?MouseArea \{.*?onClicked:", source, re.S)


def test_launch_bounce_survives_the_launcher_to_window_swap(offline):
    tools = (offline / TASKS_UI / "TaskTools.js").read_text()
    task = (offline / TASKS_UI / "Task.qml").read_text()
    activate = tools[tools.index("function activateTask"):]
    assert "recordLaunch(model.LauncherUrlWithoutIcon);" in activate
    assert "task.startLaunchBounce();" in activate
    assert "running: task.launchBouncing" in task
    assert "alwaysRunToEnd: true" in task
    assert "&& ((model.IsStartup && !startupBounceOver) || pendingBounces > 0)" in task
    assert "TaskTools.launchedRecently(model.LauncherUrlWithoutIcon)" in task


def test_launch_bounce_stops_once_the_app_is_open(offline):
    tools = (offline / TASKS_UI / "TaskTools.js").read_text()
    task = (offline / TASKS_UI / "Task.qml").read_text()
    main = (offline / TASKS_UI / "main.qml").read_text()
    # A startup that never ends (no window, ignored token) hops for a while only.
    assert "var launchBounceWindowMs = 6000;" in tools
    assert "running: model.IsStartup && !task.startupBounceOver" in task
    # A window ends the bounce of every delegate still reporting that launch.
    assert "signal appWindowOpened(launcherUrl: string)" in main
    assert "tasksRoot.appWindowOpened(String(model.LauncherUrlWithoutIcon));" in task
    assert "function onAppWindowOpened(launcherUrl: string): void" in task
    # Only a launch too quick to have shown a hop still plays one.
    assert "TaskTools.launchedWithin(model.LauncherUrlWithoutIcon, TaskTools.launchLandingWindowMs)" in task
    assert "pendingBounces = Math.min(pendingBounces, 1);" in task


def test_launchpad_pin_never_bounces(offline):
    tools = (offline / TASKS_UI / "TaskTools.js").read_text()
    task = (offline / TASKS_UI / "Task.qml").read_text()
    assert 'includes("org.kde.mac-tahoe-liquid-kde.apps")' in tools
    assert "readonly property bool launchBouncing: !inPopup && !launchpadPin" in task
    assert "!tasksRoot.minimizedShelf && !launchpadPin" in task


def _svg(offline, theme):
    path = offline / f"plasma-theme/{theme}/widgets/panel-background.svgz"
    return gzip.decompress(path.read_bytes()).decode()


def _hint(svg, side, attribute):
    match = re.search(
        rf'<rect id="floating-hint-{side}-margin"[^>]*\b{attribute}="([0-9.]+)"', svg)
    assert match, (side, attribute)
    return float(match.group(1))


@pytest.mark.parametrize("theme", THEMES)
def test_theme_reserves_headroom_for_the_largest_magnification(offline, theme):
    svg = _svg(offline, theme)
    assert 'id="floating-center"' in svg
    top = _hint(svg, "top", "height")
    # Plasma's default floating gap stays on the other sides.
    # The glass floats 5 px above the screen edge (4 px + its 1 px inset).
    assert _hint(svg, "bottom", "height") == 4
    assert _hint(svg, "left", "width") == 8
    assert _hint(svg, "right", "width") == 8

    config = (offline / f"{TASKS_UI}/../config/main.xml").read_text()
    maximum = int(re.search(
        r'<entry name="dockMagnification".*?<max>(\d+)</max>', config, re.S).group(1))
    # A 73 px Dock with icons 16% below its top edge, scaled from the
    # bottom edge, must stay inside the window.
    thickness = 73
    overflow = (thickness - thickness * 0.16) * maximum / 100 - thickness
    assert overflow <= top


def test_dockzoom_side_room_matches_theme_gap(offline):
    zoom = (offline / DOCKZOOM / "DockZoom.qml").read_text()
    side = float(re.search(r"property real sideRoom: ([0-9.]+)", zoom).group(1))
    for theme in THEMES:
        assert _hint(_svg(offline, theme), "left", "width") == side


def _bell_integral(delta, amplitude, radius):
    clamped = max(-radius, min(radius, delta))
    return amplitude / 2 * (clamped + radius / math.pi * math.sin(math.pi * clamped / radius))


def test_spread_matches_the_extra_width_of_magnified_neighbours():
    """The shift is the integral of the scale bell, so neighbours never overlap."""
    # Tahoe Dock: 73 px thick, 59 px pitch, 43 px of visible icon art.
    amplitude, radius, slot = 0.6, 2.0 * 73, 59
    for cursor in range(-200, 201, 7):
        for i in range(-4, 4):
            left, right = i * slot - cursor, (i + 1) * slot - cursor
            gap = slot + _bell_integral(right, amplitude, radius) - _bell_integral(left, amplitude, radius)

            def scale(delta):
                if abs(delta) >= radius:
                    return 1
                return 1 + amplitude * (1 + math.cos(math.pi * delta / radius)) / 2

            half_widths = 43 / 59 * slot / 2 * (scale(left) + scale(right))
            assert gap >= half_widths - 1e-6


@pytest.mark.parametrize("relative_path", LAYOUTS)
def test_dock_ends_with_downloads_minimized_windows_and_trash(offline, relative_path):
    script = (offline / relative_path).read_text()
    dock = script[script.index("var dock = new Panel"):]
    tasks = dock.index('addWidget("org.kde.mac.tahoe.liquid.icontasks")')
    separator = dock.index('addWidget("org.kde.mac-tahoe-liquid-kde.separator")')
    downloads = dock.index('addWidget("org.kde.mac-tahoe-liquid-kde.downloads")')
    minimized = dock.index('var minimized = dock.addWidget("org.kde.mac.tahoe.liquid.icontasks")')
    trash = dock.index('addWidget("org.kde.mac-tahoe-liquid-kde.trashcan")')
    assert tasks < separator < downloads < minimized < trash
    assert 'minimized.writeConfig("showOnlyMinimized", "true");' in dock
    assert 'minimized.writeConfig("groupingStrategy", "0");' in dock
    assert 'minimized.writeConfig("launchers", "");' in dock
    # The Trash widens the glass while magnifying, so it must end the Dock.
    assert dock.rindex("addWidget(") == trash


def test_launcher_and_trash_widen_the_dock_on_their_outer_sides(offline):
    """Growing both ends keeps every applet container under its icon, so
    clicks reach the icon drawn under the cursor."""
    launcher = (offline / DOCK_WIDGETS[0]).read_text()
    trash = (offline / DOCK_WIDGETS[-1]).read_text()
    zoom = (offline / DOCKZOOM / "DockZoom.qml").read_text()

    assert "DockZoom.registerGrowthOwner(root, dockBaseWidth, true)" in launcher
    assert "dockBaseWidth + DockZoom.growthFor(root)" in launcher
    assert "x: root.dockLayout ? root.width - root.dockBaseWidth : 0" in launcher

    assert "DockZoom.registerGrowthOwner(mouseArea, dockBaseWidth)" in trash
    assert "DockZoom.unregisterGrowthOwner(mouseArea)" in trash
    assert "dockBaseWidth + DockZoom.growthFor(mouseArea)" in trash
    assert "width: mouseArea.dockBaseWidth" in trash
    assert "acceptedButtons: root.dockLayout ? Qt.NoButton : Qt.LeftButton" in trash

    # With both owners the panel's own re-centring slides the Dock.
    # The glass follows only `level`, symmetrically, never the cursor:
    # Plasma resizes and re-centres in separate steps, so growth that
    # tracked the cursor shook the whole Dock on every move.
    assert "const spread = fullSpread * level;" in zoom
    assert "return evenStep(spread);" in zoom
    assert "return evenStep(leadOwner ? spread : 2 * spread);" in zoom
    assert "cursorRest" not in zoom[zoom.index("function growthFor"):]
    assert "return 2 * Math.round(value / 2);" in zoom
    shift = zoom[zoom.index("function shiftFor"):zoom.index("function stackingFor")]
    assert shift.rstrip().endswith("return integral(delta);\n    }") or "return integral(delta);" in shift


def test_launcher_restore_never_pins_apps_to_the_minimized_section():
    script = layout._append_launcher_restore(
        "", ["preferred://browser"], "org.kde.mac.tahoe.liquid.icontasks")
    skip = script.index("readConfig('showOnlyMinimized', false)")
    write = script.index("writeConfig('launchers'")
    assert skip < write
    assert "continue;" in script[skip:write]


def test_minimized_section_shows_ungrouped_window_thumbnails(offline):
    main = (offline / TASKS_UI / "main.qml").read_text()
    task = (offline / TASKS_UI / "Task.qml").read_text()
    thumbnail = (offline / TASKS_UI / "WindowThumbnail.qml").read_text()

    assert "readonly property bool minimizedShelf: iconsOnly && Plasmoid.configuration.showOnlyMinimized" in main
    assert "groupMode: tasks.minimizedShelf ? TaskManager.TasksModel.GroupDisabled" in main
    # An empty section leaves the Dock instead of keeping an edit-mode stub.
    assert "if (tasks.minimizedShelf && tasks.shouldShrinkToZero) {" in main
    assert "return PlasmaCore.Types.HiddenStatus;" in main

    assert "active: task.tasksRoot.minimizedShelf && task.model.IsWindow" in task
    assert "visible: !(windowThumbnail.item && windowThumbnail.item.ready)" in task
    # One frame is grabbed, then the PipeWire stream is dropped.
    assert "active: thumbnail.winId !== undefined && thumbnail.grab === null" in thumbnail
    assert "SPDX-License-Identifier: GPL-2.0-or-later" in thumbnail


def test_downloads_stack_is_bundled_with_its_license(offline):
    root = offline / DOWNLOADS
    metadata = (root / "metadata.json").read_text()
    assert '"Id": "org.kde.mac-tahoe-liquid-kde.downloads"' in metadata
    assert '"License": "GPL-3.0-or-later"' in metadata
    assert "GNU GENERAL PUBLIC LICENSE" in (root / "LICENSE-DownloadsStack").read_text()
    # The upstream curl | sh installer is not shipped.
    assert not (root / "install.sh").exists()

    main = (root / "contents/ui/main.qml").read_text()
    assert "https://github.com/cromewar/plasma-downloads-stack" in main
    assert "Plasmoid.CanFillArea" in main
    assert "Math.round(compact.height * 0.75) - Kirigami.Units.smallSpacing" in main
    assert "roundToIconSize: !compact.dockLayout" in main

    config = (root / "contents/config/main.xml").read_text()
    # macOS shows Downloads as a folder in the Dock, without a count badge.
    assert re.search(r'name="compactStyle".*?<default>folder</default>', config, re.S)
    assert re.search(r'name="showBadge".*?<default>false</default>', config, re.S)


def test_uninstall_removes_dockzoom_module(tmp_path, monkeypatch):
    removed = []
    monkeypatch.setattr(plasmoids, "DEST_DIR", tmp_path / "plasmoids")
    monkeypatch.setattr(plasmoids, "LEGACY_TASKMANAGER_USER_SO", tmp_path / "missing.so")
    monkeypatch.setattr(plasmoids, "qt6_plugins_dir", lambda: tmp_path / "plugins")
    monkeypatch.setattr(plasmoids, "qt6_qml_dir", lambda: tmp_path / "qml")
    monkeypatch.setattr(plasmoids, "sudo_remove",
                        lambda path, *_a, **_k: removed.append(path) or False)
    monkeypatch.setattr(plasmoids, "ok", lambda _message: None)
    monkeypatch.setattr(plasmoids, "info", lambda _message: None)

    plasmoids.uninstall()

    assert tmp_path / "qml/org/kde/mac/tahoe/liquid/dockzoom" in removed


def test_glass_leaves_frameless_applet_popups_clear(offline):
    """Acrylic Glass blurs a popup only where it asks for blur: the
    Downloads fan requests none, so it stays see-through."""
    effect = (offline / "kwin-effects/acrylic-glass/src/effect.cpp").read_text()
    update = effect[effect.index("void BlurEffect::updateBlurRegion"):]
    update = update[:update.index("\n}\n")]
    # Frames are only synthesized for decorated, non-popup windows.
    assert ("!(w->isDock() || w->isTooltip() || w->isMenu() || w->isDropdownMenu() "
            "|| w->isPopupMenu() || w->isPopupWindow() || w->isAppletPopup())") in update


def test_downloads_fan_matches_macos_tahoe(offline):
    """Measured on a macOS Tahoe 1x capture: files on a 64 px pitch along a
    shallow arc that leans, black name pills, a round "Open in Finder"
    button on top, at most ten files, and a chevron tile in the Dock while
    the fan is open."""
    ui = offline / DOWNLOADS / "contents/ui"
    fan = (ui / "FanMode.qml").read_text()
    tile = (ui / "FileTile.qml").read_text()
    pill = (ui / "LabelPill.qml").read_text()
    main = (ui / "main.qml").read_text()

    assert "readonly property real pitch: iconSize" in fan
    assert "readonly property int maxFiles: 10" in fan
    assert "return h * h / arcScale;" in fan
    assert "readonly property real arcScale: iconSize * 32" in fan
    assert 'i18n("Open in Finder")' in fan
    # Plasma aligns the popup with the applet's outer edge: the arc fits.
    assert "readonly property real driftFit:" in fan
    assert "Flickable" not in fan

    assert "rotation: shown ? tileRotation : 0" in tile
    assert "LabelPill {" in tile
    assert "Qt.rgba(0.04, 0.04, 0.04, 0.92)" in pill
    assert 'color: "white"' in pill

    assert 'color: "#313131"' in main
    assert "visible: root.fanOpen" in main


def test_apps_launcher_follows_finder_like_macos(offline, repo):
    """macOS keeps Finder first and Apps right after it: the Dock pins an
    "Apps" launcher after the file manager, and the Launcher applet hides
    its own button (it still answers PlasmaShell.activateLauncherMenu)."""
    from steps import layout
    apps = layout.APPS_PIN
    assert layout._with_apps_pin([]) == [apps]
    assert layout._with_apps_pin(["preferred://filemanager", "preferred://browser"]) == [
        "preferred://filemanager", apps, "preferred://browser"]
    assert layout._with_apps_pin(["applications:firefox.desktop", "applications:org.kde.dolphin.desktop"]) == [
        "applications:firefox.desktop", "applications:org.kde.dolphin.desktop", apps]
    # No duplicate when it is already there.
    assert layout._with_apps_pin(["preferred://filemanager", apps]).count(apps) == 1

    desktop = (offline / "applications/org.kde.mac-tahoe-liquid-kde.apps.desktop").read_text()
    assert "org.kde.PlasmaShell.activateLauncherMenu" in desktop
    assert "NoDisplay=true" in desktop and "StartupNotify=false" in desktop
    launcher = offline / "plasmoids/org.kde.mac-tahoe-liquid-kde.launcher"
    assert '"org.kde.plasma.launchermenu"' in (launcher / "metadata.json").read_text()
    assert '<entry name="hiddenInDock" type="Bool">' in (launcher / "contents/config/main.xml").read_text()
    assert "PlasmaCore.Types.HiddenStatus" in (launcher / "contents/ui/main.qml").read_text()
    for relative_path in LAYOUTS:
        assert 'launcher.writeConfig("hiddenInDock", "true");' in (offline / relative_path).read_text()
    for theme in ("Light", "Dark"):
        laf = (offline / f"look-and-feel/MacTahoeLiquidKde-{theme}/contents/layouts"
               "/org.kde.plasma.desktop-layout.js").read_text()
        assert "preferred://filemanager,applications:org.kde.mac-tahoe-liquid-kde.apps.desktop," in laf


def test_applet_containers_follow_their_icons(offline):
    """With the Launcher hidden behind the Apps pin only the Trash widens the
    Dock, and re-centring slides every applet container left by half the
    growth. Each tracker slides its container back: Qt delivers no input to
    the part of an icon drawn outside its container (the Downloads stack
    could not be clicked while the Dock magnified)."""
    zoom = (offline / "qml/org.kde.mac.tahoe.liquid.dockzoom/DockZoom.qml").read_text()
    tracker = (offline / "qml/org.kde.mac.tahoe.liquid.dockzoom/DockZoomTracker.qml").read_text()
    assert "readonly property real containerShift: !leadOwner && trailOwner ? appliedTrail / 2 : 0" in zoom
    assert "appliedTrail / 2;" not in zoom[zoom.index("function shiftFor"):zoom.index("function stackingFor")]
    assert "centre - containerShift - (leadOwner ? appliedLead : 0) - cursorRest" in zoom
    assert "container.transform = [containerShift];" in tracker
    assert "? DockZoom.containerShift : 0" in tracker
