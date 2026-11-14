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
def test_fresh_dock_starts_with_the_apps_pin(offline, relative):
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
    assert main == [APPS, "applications:org.kde.dolphin.desktop", "applications:firefox.desktop"]
    assert minimized == ""


def test_user_pins_get_the_apps_pin_and_the_minimized_section_none():
    assert layout._with_apps_pin([]) == []
    assert layout._with_apps_pin(["applications:firefox.desktop", APPS, "preferred://filemanager"]) == [
        APPS, "applications:firefox.desktop", "preferred://filemanager"]
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
    assert "active: !kicker.hiddenInDock && Plasmoid.formFactor === PlasmaCore.Types.Vertical" in main
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
    assert "DockZoom.registerGrowthOwner(root, NativeLauncher.DockMetrics.preferredCellSize(height), false);" in main
    assert "NativeLauncher.DockMetrics.preferredCellSize(height) + DockZoom.growthFor(root)" in main
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


@pytest.mark.parametrize("widget", ("launcher", "trashcan", "downloads", "separator"))
def test_dock_widgets_set_each_root_property_once(offline, widget):
    """QML refuses an applet whose root sets a property twice ("Property
    value set multiple times"): the widget then vanishes from the Dock."""
    main = (offline / f"plasmoids/org.kde.mac-tahoe-liquid-kde.{widget}/contents/ui/main.qml").read_text()
    root = re.findall(r"^    ((?:Plasmoid|Layout)\.\w+|preferredRepresentation):", main, re.M)
    assert sorted(root) == sorted(set(root))


def test_apps_entry_is_indexed_before_the_dock_is_created():
    """Plasma drops a pin whose application is not in its cache yet."""
    import inspect
    source = inspect.getsource(layout.install)
    assert source.index("_index_apps_launcher()") < source.index("_evaluate_layout_with_launchers(")


def test_apps_pin_is_put_back_after_the_cache_rebuild(repo):
    """The install rebuilds KDE's application cache after the Dock exists;
    Plasma drops the pin meanwhile."""
    apply_step = (repo / "src/scripts/steps/apply.py").read_text()
    assert apply_step.index("kbuildsycoca6") < apply_step.index("layout.ensure_apps_pin()")
    assert "showOnlyMinimized" in layout._APPS_PIN_SCRIPT and layout.APPS_PIN in layout._APPS_PIN_SCRIPT


def test_apps_pin_opens_the_grid_without_starting_a_process(offline):
    """Starting the pin's desktop entry showed a second, starting icon."""
    ui = offline / "plasmoids/org.kde.mac.tahoe.liquid.taskmanager/contents/ui"
    tools = (ui / "TaskTools.js").read_text()
    activate = tools[tools.index("function activateTask("):]
    assert activate.index("tasks.openLaunchpad();") < activate.index("requestNewInstance")
    assert 'member: "activateLauncherMenu"' in (ui / "main.qml").read_text()


@pytest.mark.parametrize("widget", ("launcher", "trashcan", "downloads"))
def test_horizontal_dock_cells_follow_only_the_thickness(offline, widget):
    """The magnification resizes the Dock: a horizontal cell computed from
    the panel's widths (DockCell) followed it and the whole Dock shook. Only
    a vertical Dock shares compression between its cells."""
    main = (offline / f"plasmoids/org.kde.mac-tahoe-liquid-kde.{widget}/contents/ui/main.qml").read_text()
    cell = re.search(r"NativeLauncher\.DockCell \{.*?\n    \}", main, re.S).group(0)
    assert re.search(r"active: .*Plasmoid\.formFactor === PlasmaCore\.Types\.Vertical$", cell, re.M)
    assert "Horizontal" not in cell
    for key in ("minimumWidth", "preferredWidth", "maximumWidth"):
        hint = re.search(rf"^    Layout\.{key}: (.*)$", main, re.M).group(1)
        assert "dockCell" not in hint and "NativeLauncher.DockMetrics.preferredCellSize(height)" in hint, hint
    tasks = (offline / "plasmoids/org.kde.mac.tahoe.liquid.taskmanager/contents/ui/main.qml").read_text()
    assert "active: iconsOnly && Plasmoid.formFactor === PlasmaCore.Types.Vertical" in tasks
