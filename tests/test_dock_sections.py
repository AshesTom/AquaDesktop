"""The AquaDesktop Dock sections on the upstream Dock: the Apps pin after
Finder, a separator, the Downloads stack, a minimized-windows section and
the Trash last, all on the shared Dock cells (DockCell / DockIcon)."""

import json
import re
import shutil
import subprocess

import pytest

import steps.layout as layout
import steps.plasmoids as plasmoids

LAYOUTS = (
    "layouts/mac-tahoe.js",
    "look-and-feel/MacTahoeLiquidKde-Light/contents/layouts/org.kde.plasma.desktop-layout.js",
    "look-and-feel/MacTahoeLiquidKde-Dark/contents/layouts/org.kde.plasma.desktop-layout.js",
)
APPS = "applications:org.kde.mac-tahoe-liquid-kde.apps.desktop"


@pytest.mark.parametrize("relative", LAYOUTS)
def test_dock_order_ends_with_stacks_minimized_windows_and_trash(offline, relative):
    script = (offline / relative).read_text()
    dock = script[script.index('addWidget("org.kde.mac-tahoe-liquid-kde.launcher")'):]
    order = [m.group(1) for m in re.finditer(r'addWidget\("([^"]+)"\)', dock)]
    assert order == [
        "org.kde.mac-tahoe-liquid-kde.launcher",
        "org.kde.mac.tahoe.liquid.icontasks",
        "org.kde.mac-tahoe-liquid-kde.separator",
        "org.kde.plasma.marginsseparator",  # fallback without our separator
        "org.kde.mac-tahoe-liquid-kde.downloads",
        "org.kde.mac.tahoe.liquid.icontasks",
        "org.kde.mac-tahoe-liquid-kde.trashcan",
    ]
    assert 'launcher.writeConfig("hiddenInDock", "true");' in dock
    assert 'minimized.writeConfig("showOnlyMinimized", "true");' in dock
    assert 'minimized.writeConfig("launchers", "");' in dock


@pytest.mark.parametrize("relative", LAYOUTS)
def test_fresh_dock_pins_apps_right_after_the_file_manager(offline, relative):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required for Plasma layout script execution")
    harness = '''
const knownWidgetTypes = [];
const screenCount = 1;
const created = [];
function makeWidget(type) {
    return { type, config: {},
        readConfig(key, fallback) { return this.config[key] ?? fallback; },
        writeConfig(key, value) { this.config[key] = value; } };
}
function panels() { return created; }
function applicationExists(id) { return id === "org.kde.dolphin.desktop" || id === "firefox.desktop"; }
function Panel() {
    this.items = [];
    this.widgetIds = [];
    this.addWidget = type => { this.widgetIds.push(this.items.length);
        const item = makeWidget(type); this.items.push(item); return item; };
    this.widgetById = id => this.items[id];
    created.push(this);
}
'''
    output = '''
const bottom = created.find(p => p.location === "bottom");
console.log(JSON.stringify(bottom.items.filter(w => w.type === "org.kde.mac.tahoe.liquid.icontasks")
    .map(w => w.config.launchers)));
'''
    result = subprocess.run([node, "-e", harness + (offline / relative).read_text() + output],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    main, minimized = json.loads(result.stdout)
    assert main == ["applications:org.kde.dolphin.desktop", APPS, "applications:firefox.desktop"]
    assert minimized == ""


def test_user_pins_get_the_apps_pin_and_the_minimized_section_none():
    assert layout._with_apps_pin([]) == []
    assert layout._with_apps_pin(["applications:firefox.desktop", "preferred://filemanager"]) == [
        "applications:firefox.desktop", "preferred://filemanager", APPS]
    assert layout._with_apps_pin([APPS, "applications:a.desktop"]) == [APPS, "applications:a.desktop"]
    script = layout._append_launcher_restore("", ["applications:a.desktop"], layout.MAC_TASKS_ID)
    assert "if (String(w.readConfig('showOnlyMinimized', false)) === 'true') continue;" in script


def test_dock_migration_skips_the_minimized_section(offline):
    script = (offline / "layouts/migrate-dock-preset.js").read_text()
    skip = 'if (String(tasks.readConfig("showOnlyMinimized", false)) === "true") continue;'
    assert script.index(skip) < script.index('tasks.writeConfig("launchers", pins);')


def test_apps_pin_opens_the_hidden_launcher_grid(offline):
    desktop = (offline / "applications/org.kde.mac-tahoe-liquid-kde.apps.desktop").read_text()
    assert "org.kde.PlasmaShell.activateLauncherMenu" in desktop and "NoDisplay=true" in desktop
    launcher = offline / "plasmoids/org.kde.mac-tahoe-liquid-kde.launcher/contents"
    assert '<entry name="hiddenInDock" type="Bool">' in (launcher / "config/main.xml").read_text()
    main = (launcher / "ui/main.qml").read_text()
    assert "Plasmoid.status: hiddenInDock ? PlasmaCore.Types.HiddenStatus" in main
    assert "function onActivated(): void {\n            kicker.toggleDash();" in main
    assert "active: !kicker.hiddenInDock && (" in main
    assert "onClicked: kicker.toggleDash()" in (launcher / "ui/CompactRepresentation.qml").read_text()


def test_minimized_section_shows_ungrouped_thumbnails_and_hides_when_empty(offline):
    ui = offline / "plasmoids/org.kde.mac.tahoe.liquid.taskmanager/contents/ui"
    main = (ui / "main.qml").read_text()
    assert "readonly property bool minimizedShelf: iconsOnly && Plasmoid.configuration.showOnlyMinimized" in main
    assert "groupMode: tasks.minimizedShelf ? TaskManager.TasksModel.GroupDisabled" in main
    assert "if (tasks.minimizedShelf && tasks.shouldShrinkToZero) {\n                    return PlasmaCore.Types.HiddenStatus;" in main
    task = (ui / "Task.qml").read_text()
    assert 'source: "WindowThumbnail.qml"' in task
    assert "visible: !(windowThumbnail.item && windowThumbnail.item.ready)" in task
    assert "opacity: task.tasksRoot.minimizedShelf ? 0 : 1" in task
    assert "import org.kde.pipewire as PipeWire" in (ui / "WindowThumbnail.qml").read_text()


def test_downloads_stack_uses_the_shared_dock_cell_and_icon_box(offline):
    main = (offline / "plasmoids/org.kde.mac-tahoe-liquid-kde.downloads/contents/ui/main.qml").read_text()
    assert "NativeLauncher.DockCell {\n        id: dockCell\n        applet: root" in main
    assert "NativeLauncher.DockIcon {\n            id: dockIcon" in main
    assert "hovered: compactMouse.containsMouse" in main
    assert "readonly property Item iconBox: dockIcon.iconItem.parent" in main



def test_trash_widens_the_glass_from_its_resting_cell(offline):
    """The Trash ends the Dock: it is DockZoom's trailing growth owner, grows
    its upstream cell on the outer side and keeps its icon in that cell."""
    main = (offline / "plasmoids/org.kde.mac-tahoe-liquid-kde.trashcan/contents/ui/main.qml").read_text()
    assert "DockZoom.registerGrowthOwner(root, dockCell.size, false);" in main
    assert "Math.ceil(dockCell.size) + DockZoom.growthFor(root)" in main
    assert "rightMargin: DockZoom.growthFor(root)" in main
    assert "hovered: mouseArea.containsMouse && !root.horizontalDock" in main


@pytest.mark.parametrize("widget", ("launcher", "trashcan", "downloads"))
def test_dock_icons_magnify_instead_of_their_hover_zoom(offline, widget):
    ui = offline / f"plasmoids/org.kde.mac-tahoe-liquid-kde.{widget}/contents/ui"
    source = "".join(f.read_text() for f in ui.glob("*.qml"))
    assert "DockZoom.scaleFor(" in source and "DockZoom.shiftFor(" in source
    assert re.search(r"hovered: \w+\.containsMouse && !(\w+\.)?horizontalDock", source)



def test_downloads_stack_is_bundled_with_its_license(offline):
    widget = offline / "plasmoids/org.kde.mac-tahoe-liquid-kde.downloads"
    assert (widget / "LICENSE-DownloadsStack").is_file()
    metadata = json.loads((widget / "metadata.json").read_text())
    assert metadata["KPlugin"]["Id"] == "org.kde.mac-tahoe-liquid-kde.downloads"


def test_apps_launcher_is_installed_and_removed(tmp_path, monkeypatch):
    monkeypatch.setattr(plasmoids, "DEST_DIR", tmp_path / "share/plasma/plasmoids")
    monkeypatch.setattr(plasmoids, "ok", lambda message: None)
    plasmoids._install_apps_launcher()
    dest = tmp_path / "share/applications/org.kde.mac-tahoe-liquid-kde.apps.desktop"
    assert dest.read_text() == plasmoids.APPS_DESKTOP.read_text()
