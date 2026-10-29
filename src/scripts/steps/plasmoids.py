from localization import tr
import shutil
from pathlib import Path

from distro import qt6_plugins_dir, qt6_qml_dir
from launcher_defaults import LAUNCHER_ID, apply_launcher_default, remember_installed_edition
from steps._helpers import (
    DATA_HOME, HOME, build_dir, cmake_build, fail, info, install_tree, ok, offline,
    remove_tree,
    sudo_install_file, sudo_install_tree, sudo_remove, temp_dir,
)

SRC_DIR = offline("plasmoids")
DEST_DIR = DATA_HOME / "plasma/plasmoids"

TASKMANAGER_SRC = SRC_DIR / "org.kde.mac.tahoe.liquid.taskmanager"
TASKMANAGER_BUILD = build_dir("plasmoids/org.kde.mac.tahoe.liquid.taskmanager")
# Qt6 never scans user paths for plugins/QML — these go under the qmake6-
# reported libdir. Lazy __getattr__ keeps a missing qmake6 a preflight
# failure, not a module-import crash.
_TASKMANAGER_SO_RELPATH = "plasma/applets/org.kde.mac.tahoe.liquid.taskmanager.so"
_TASKMANAGER_QML_RELPATH = "plasma/applet/org/kde/mac/tahoe/liquid/taskmanager"
# Plasma's notifications applet, built under our own ID so its popups can be
# macOS banners (see org.kde.mac.tahoe.liquid.notifications/UPSTREAM.md).
NOTIFICATIONS_SRC = SRC_DIR / "org.kde.mac.tahoe.liquid.notifications"
NOTIFICATIONS_BUILD = build_dir("plasmoids/org.kde.mac.tahoe.liquid.notifications")
_NOTIFICATIONS_SO_RELPATH = "plasma/applets/org.kde.mac.tahoe.liquid.notifications.so"
_NOTIFICATIONS_QML_RELPATH = "plasma/applet/org/kde/mac/tahoe/liquid/notifications"
# Plasma's system tray, built under our own ID so the menu bar has no
# overflow arrow and its other items open as a macOS menu (see UPSTREAM.md).
SYSTEMTRAY_SRC = SRC_DIR / "org.kde.mac.tahoe.liquid.systemtray"
SYSTEMTRAY_BUILD = build_dir("plasmoids/org.kde.mac.tahoe.liquid.systemtray")
_SYSTEMTRAY_SO_RELPATH = "plasma/applets/org.kde.mac.tahoe.liquid.systemtray.so"
_SYSTEMTRAY_QML_RELPATH = "plasma/applet/org/kde/mac/tahoe/liquid/systemtray"
# Pure-QML module shared by every Dock widget for the parabolic
# magnification. All applets run in plasmashell's single QML engine, so its
# singleton is the one place they can share the cursor position.
DOCKZOOM_SRC = offline("qml") / "org.kde.mac.tahoe.liquid.dockzoom"
# The "Apps" launcher the Dock pins after Finder (it opens the Launcher
# applet's grid, see layout.py).
APPS_DESKTOP = offline("applications") / "org.kde.mac-tahoe-liquid-kde.apps.desktop"


def _apps_desktop_dest() -> Path:
    # Next to the plasmoids' data dir (…/share/plasma/plasmoids → …/share).
    return DEST_DIR.parent.parent / "applications" / APPS_DESKTOP.name
_DOCKZOOM_QML_RELPATH = "org/kde/mac/tahoe/liquid/dockzoom"
# Compiled QML module asking KWin to blur behind the Control Center's
# modules only (each one a separate glass bubble, like macOS).
GLASS_SRC = offline("qml") / "org.kde.mac.tahoe.liquid.glass"
GLASS_BUILD = build_dir("qml/org.kde.mac.tahoe.liquid.glass")
_GLASS_QML_RELPATH = "org/kde/mac/tahoe/liquid/glass"
_LAUNCHER_QML_RELPATH = "org/kde/mac/tahoe/launcher"


def __getattr__(name: str):
    if name == "TASKMANAGER_DEST_SO":
        return qt6_plugins_dir() / _TASKMANAGER_SO_RELPATH
    if name == "TASKMANAGER_DEST_QML":
        return qt6_qml_dir() / _TASKMANAGER_QML_RELPATH
    if name == "NOTIFICATIONS_DEST_SO":
        return qt6_plugins_dir() / _NOTIFICATIONS_SO_RELPATH
    if name == "NOTIFICATIONS_DEST_QML":
        return qt6_qml_dir() / _NOTIFICATIONS_QML_RELPATH
    if name == "DOCKZOOM_DEST_QML":
        return qt6_qml_dir() / _DOCKZOOM_QML_RELPATH
    if name == "GLASS_DEST_QML":
        return qt6_qml_dir() / _GLASS_QML_RELPATH
    if name == "LAUNCHER_DEST_QML":
        return qt6_qml_dir() / _LAUNCHER_QML_RELPATH
    raise AttributeError(name)
# Leftover from old sudoless installs under the user path.
LEGACY_TASKMANAGER_USER_SO = HOME / (
    ".local/lib/qt6/plugins/plasma/applets/"
    "org.kde.mac.tahoe.liquid.taskmanager.so"
)

LEGACY_DIRS = (
    "org.kde.mac.tahoe.liquid.taskmanager",
    "org.kde.mac-tahoe-liquid-kde.taskmanager",
    "org.kde.mac-tahoe-liquid-kde.icontasks",
)
# org.kde.plasma.taskmanager / org.kde.plasma.icontasks used to be in this
# tuple (this project briefly overlaid the stock IDs before it had its own
# namespace) — dropped because those IDs aren't ours: they're the real
# upstream Plasma applet IDs, and "install a local QML override at
# ~/.local/share/plasma/plasmoids/<id>" is a documented, common KDE
# customisation. Cleanup here can't tell "our old leftover" apart from a
# user's own override of the same stock plasmoid, so it must not touch
# them at all rather than risk deleting someone else's customization.
LEGACY_TASKMANAGER_QML_DIRS = (
    HOME / ".local/lib/qt6/qml/plasma/applet/org/kde/mac/tahoe/liquid/taskmanager",
    HOME / ".local/lib/qt6/qml/plasma/applet/org/kde/mac/tahoe/liquid/icontasks",
    HOME / ".local/lib/qt6/qml/plasma/applet/org/kde/mac-tahoe-liquid-kde/taskmanager",
    HOME / ".local/lib/qt6/qml/plasma/applet/org/kde/mac-tahoe-liquid-kde/icontasks",
)

def deps():
    return [
        "qmake6:qt6-base",
        "qt6-gui-cmake:qt6-base",
        "qt6-widgets-cmake:qt6-base",
        "qt6-dbus-cmake:qt6-base",
        "qt6-qml-cmake:qt6-declarative",
        "plasma5support-qml:plasma5support",
        "kf6-itemmodels-qml:kitemmodels",
        "qt6-wayland-cmake:qt6-wayland",
        "wayland-cmake:wayland",
        "cmake",
        "ecm:extra-cmake-modules",
        "make",
        "g++:gcc",
        "pkg-config:pkgconf",
        # KF6 components required by the taskmanager CMakeLists.
        "kf6-config-cmake:kconfig",
        "kf6-coreaddons-cmake:kcoreaddons",
        "kf6-i18n-cmake:ki18n",
        "kf6-kio-cmake:kio",
        "kf6-notifications-cmake:knotifications",
        "kf6-service-cmake:kservice",
        "kf6-windowsystem-cmake:kwindowsystem",
        "kf6-itemmodels-cmake:kitemmodels",
        # The system tray fork.
        "kf6-xmlgui-cmake:kxmlgui",
        "kf6-statusnotifieritem-cmake:kstatusnotifieritem",
        "kf6-iconthemes-cmake:kiconthemes",
        "kf6-jobwidgets-cmake:kjobwidgets",
        # The notifications fork: global shortcuts (its popup windows'
        # plasma-shell Wayland role uses the Wayland packages above).
        "kf6-globalaccel-cmake:kglobalaccel",
        # Plasma / KSysGuard / plasma-workspace (provides
        # LibNotificationManager + LibTaskManager cmake config).
        "plasma-cmake:libplasma",
        "plasma-activities-cmake:plasma-activities",
        "plasma-activities-stats-cmake:plasma-activities-stats",
        "ksysguard-cmake:libksysguard",
        "libnotificationmanager-cmake:plasma-workspace",
    ]


def build_artifacts() -> list[Path]:
    return [
        TASKMANAGER_BUILD / "bin/plasma/applets/org.kde.mac.tahoe.liquid.taskmanager.so",
        TASKMANAGER_BUILD / "bin/plasma/applet/org/kde/mac/tahoe/liquid/taskmanager",
        NOTIFICATIONS_BUILD / "bin" / _NOTIFICATIONS_SO_RELPATH,
        NOTIFICATIONS_BUILD / "bin" / _NOTIFICATIONS_QML_RELPATH,
        SYSTEMTRAY_BUILD / "bin" / _SYSTEMTRAY_SO_RELPATH,
        GLASS_BUILD / "bin" / _GLASS_QML_RELPATH,
        TASKMANAGER_BUILD / "bin" / _LAUNCHER_QML_RELPATH / "libmactahoelauncher.so",
    ]


def build() -> None:
    if (TASKMANAGER_SRC / "CMakeLists.txt").is_file():
        cmake_build(TASKMANAGER_SRC, TASKMANAGER_BUILD, "Dock Task Manager")
    if (NOTIFICATIONS_SRC / "CMakeLists.txt").is_file():
        cmake_build(NOTIFICATIONS_SRC, NOTIFICATIONS_BUILD, "Notifications")
    if (SYSTEMTRAY_SRC / "CMakeLists.txt").is_file():
        cmake_build(SYSTEMTRAY_SRC, SYSTEMTRAY_BUILD, "System Tray")
    if (GLASS_SRC / "CMakeLists.txt").is_file():
        cmake_build(GLASS_SRC, GLASS_BUILD, "Control Center glass blur")


def _migrate_appletsrc() -> None:
    # The rename lives in a bundled kconf_update helper; run just
    # that one so the upgrade keeps the dock and the user's pinned launchers.
    from steps.kconf_update import run_migration
    run_migration("mac-tahoe-migrate-appletsrc.sh")
    ok(tr('dock config migrated to MacTahoe dock fork'))


def _install_taskmanager_package() -> bool:
    """Install the dock applet's QML/runtime package. The .so alone is not
    enough: the icons-only wrapper resolves via X-Plasma-RootPath and needs
    the package metadata + contents/ in the local plasmoid dir too."""
    metadata = TASKMANAGER_SRC / "metadata.json"
    contents = TASKMANAGER_SRC / "contents"
    if not metadata.is_file():
        fail(tr('org.kde.mac.tahoe.liquid.taskmanager (missing metadata.json)'))
        return False
    if not contents.is_dir():
        fail(tr('org.kde.mac.tahoe.liquid.taskmanager (missing contents/)'))
        return False

    with temp_dir("mttkde-taskmanager-package") as tmp:
        runtime = tmp / TASKMANAGER_SRC.name
        runtime.mkdir(parents=True, exist_ok=True)
        shutil.copy2(metadata, runtime / "metadata.json")
        shutil.copytree(contents, runtime / "contents", symlinks=True)
        return install_tree(runtime, DEST_DIR / TASKMANAGER_SRC.name,
                            TASKMANAGER_SRC.name)


def _install_taskmanager_qml() -> bool:
    module_src = TASKMANAGER_BUILD / "bin/plasma/applet/org/kde/mac/tahoe/liquid/taskmanager"
    if not module_src.is_dir():
        fail(tr('org.kde.mac.tahoe.liquid.taskmanager (missing runtime QML)'))
        return False
    return sudo_install_tree(
        module_src, qt6_qml_dir() / _TASKMANAGER_QML_RELPATH,
        tr('org.kde.mac.tahoe.liquid.taskmanager (installed runtime QML)'),
    )


def _install_notifications() -> bool:
    """The macOS-banner notifications applet: a compiled plugin plus its
    runtime QML module, both under the system Qt dirs like the Dock's."""
    if not (SRC_DIR / NOTIFICATIONS_SRC.name / "CMakeLists.txt").is_file():
        return False
    artifact = NOTIFICATIONS_BUILD / "bin" / _NOTIFICATIONS_SO_RELPATH
    module_src = NOTIFICATIONS_BUILD / "bin" / _NOTIFICATIONS_QML_RELPATH
    if not artifact.is_file() or not module_src.is_dir():
        fail(tr('org.kde.mac.tahoe.liquid.notifications (missing build artifact)'))
        return False
    if not sudo_install_file(
        artifact, qt6_plugins_dir() / _NOTIFICATIONS_SO_RELPATH,
        "org.kde.mac.tahoe.liquid.notifications (macOS notification banners)",
    ):
        return False
    return sudo_install_tree(
        module_src, qt6_qml_dir() / _NOTIFICATIONS_QML_RELPATH,
        "org.kde.mac.tahoe.liquid.notifications (installed runtime QML)",
    )


def _install_systemtray() -> bool:
    """The menu bar's system tray: a compiled plugin, plus its runtime QML
    module when the build made one."""
    if not (SRC_DIR / SYSTEMTRAY_SRC.name / "CMakeLists.txt").is_file():
        return False
    artifact = SYSTEMTRAY_BUILD / "bin" / _SYSTEMTRAY_SO_RELPATH
    module_src = SYSTEMTRAY_BUILD / "bin" / _SYSTEMTRAY_QML_RELPATH
    if not artifact.is_file():
        fail(tr('org.kde.mac.tahoe.liquid.systemtray (missing build artifact)'))
        return False
    if not sudo_install_file(
        artifact, qt6_plugins_dir() / _SYSTEMTRAY_SO_RELPATH,
        "org.kde.mac.tahoe.liquid.systemtray (macOS menu bar tray)",
    ):
        return False
    if not module_src.is_dir():
        return True
    return sudo_install_tree(
        module_src, qt6_qml_dir() / _SYSTEMTRAY_QML_RELPATH,
        "org.kde.mac.tahoe.liquid.systemtray (installed runtime QML)",
    )


def _install_dockzoom_qml() -> bool:
    if not (DOCKZOOM_SRC / "qmldir").is_file():
        fail(tr('org.kde.mac.tahoe.liquid.dockzoom (missing qmldir)'))
        return False
    return sudo_install_tree(
        DOCKZOOM_SRC, qt6_qml_dir() / _DOCKZOOM_QML_RELPATH,
        "org.kde.mac.tahoe.liquid.dockzoom (Dock magnification module)",
    )


def _install_glass_qml() -> bool:
    """The Control Center loads it through a Loader: without it the modules
    only lose their blur."""
    if not (GLASS_SRC / "CMakeLists.txt").is_file():
        return False
    module_src = GLASS_BUILD / "bin" / _GLASS_QML_RELPATH
    if not (module_src / "qmldir").is_file():
        fail(tr('org.kde.mac.tahoe.liquid.glass (missing build artifact)'))
        return False
    return sudo_install_tree(
        module_src, qt6_qml_dir() / _GLASS_QML_RELPATH,
        "org.kde.mac.tahoe.liquid.glass (Control Center glass blur)",
    )


def _install_apps_launcher() -> None:
    if not APPS_DESKTOP.is_file():
        fail(tr('{name} (missing)', name=APPS_DESKTOP.name))
        return
    dest = _apps_desktop_dest()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(APPS_DESKTOP, dest)
    ok(tr('Apps launcher (pinned after Finder)'))


def _install_launcher_package(widget: Path) -> bool:
    remember_installed_edition(HOME, DEST_DIR / widget.name)
    with temp_dir("mttkde-launcher-package") as tmp:
        staged = tmp / widget.name
        shutil.copytree(widget, staged, symlinks=True)
        apply_launcher_default(staged)
        return install_tree(staged, DEST_DIR / widget.name, widget.name)


def install() -> None:
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    # Every Dock widget imports it, so it goes in before any of them.
    _install_dockzoom_qml()
    _install_apps_launcher()

    dest_qml = qt6_qml_dir() / _TASKMANAGER_QML_RELPATH
    for name in LEGACY_DIRS:
        d = DEST_DIR / name
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            ok(tr('{name} (removed local override)', name=name))
    for qml_dir in LEGACY_TASKMANAGER_QML_DIRS:
        if qml_dir != dest_qml:
            remove_tree(qml_dir, qml_dir.name)
    if LEGACY_TASKMANAGER_USER_SO.is_file():
        try:
            LEGACY_TASKMANAGER_USER_SO.unlink()
            ok(tr('{value1} (user-path leftover)', value1=LEGACY_TASKMANAGER_USER_SO.name))
        except OSError:
            pass

    _migrate_appletsrc()

    artifact = TASKMANAGER_BUILD / "bin/plasma/applets/org.kde.mac.tahoe.liquid.taskmanager.so"
    if artifact.is_file():
        if sudo_install_file(
            artifact, qt6_plugins_dir() / _TASKMANAGER_SO_RELPATH,
            tr('org.kde.mac.tahoe.liquid.taskmanager (installed compiled dock base)'),
        ):
            _install_taskmanager_package()
            _install_taskmanager_qml()
    else:
        fail(tr('org.kde.mac.tahoe.liquid.taskmanager (missing build artifact)'))

    _install_notifications()
    _install_systemtray()
    _install_glass_qml()
    launcher_module = TASKMANAGER_BUILD / "bin" / _LAUNCHER_QML_RELPATH
    if (launcher_module / "libmactahoelauncher.so").is_file():
        sudo_install_tree(launcher_module, qt6_qml_dir() / _LAUNCHER_QML_RELPATH,
                          tr('Launcher (installed native search popup)'))
    else:
        fail(tr('Launcher (missing native search popup build artifact)'))

    n = 0
    for widget in sorted(SRC_DIR.glob("*/")):
        if not widget.is_dir():
            continue
        # C++ applets are installed via their own build steps.
        if (widget / "CMakeLists.txt").is_file():
            continue
        # Panel Colorizer is installed by the layout step behind a
        # presence check so an existing copy isn't clobbered.
        if widget.name == "luisbocanegra.panel.colorizer":
            continue
        if not (widget / "metadata.json").is_file():
            fail(tr('{value1} (no metadata.json — skipping)', value1=widget.name))
            continue
        installed = (_install_launcher_package(widget) if widget.name == LAUNCHER_ID
                     else install_tree(widget, DEST_DIR / widget.name))
        if installed:
            n += 1
    label = "plasmoid" if n == 1 else "plasmoids"
    info(tr('{n} {label} installed/reinstalled', n=n, label=tr(label)))


def uninstall() -> None:
    n = 0
    apps = _apps_desktop_dest()
    if apps.is_file():
        apps.unlink()
        ok(apps.name)
        n += 1
    dest_so = qt6_plugins_dir() / _TASKMANAGER_SO_RELPATH
    dest_qml = qt6_qml_dir() / _TASKMANAGER_QML_RELPATH
    if sudo_remove(dest_so, dest_so.name):
        n += 1
    if sudo_remove(dest_qml, dest_qml.name):
        n += 1
    dest_dockzoom = qt6_qml_dir() / _DOCKZOOM_QML_RELPATH
    if sudo_remove(dest_dockzoom, dest_dockzoom.name):
        n += 1
    dest_glass = qt6_qml_dir() / _GLASS_QML_RELPATH
    if sudo_remove(dest_glass, dest_glass.name):
        n += 1
    for dest in (qt6_plugins_dir() / _NOTIFICATIONS_SO_RELPATH,
                 qt6_qml_dir() / _NOTIFICATIONS_QML_RELPATH,
                 qt6_plugins_dir() / _SYSTEMTRAY_SO_RELPATH,
                 qt6_qml_dir() / _SYSTEMTRAY_QML_RELPATH):
        if sudo_remove(dest, dest.name):
            n += 1
    if sudo_remove(qt6_qml_dir() / _LAUNCHER_QML_RELPATH, tr('Launcher native search popup')):
        n += 1
    if LEGACY_TASKMANAGER_USER_SO.is_file():
        try:
            LEGACY_TASKMANAGER_USER_SO.unlink()
            ok(tr('{value1} (user-path leftover)', value1=LEGACY_TASKMANAGER_USER_SO.name)); n += 1
        except OSError:
            pass
    targets = [
        DEST_DIR / "org.kde.mac.tahoe.liquid.taskmanager",
        DEST_DIR / "org.kde.mac.tahoe.liquid.icontasks",
        *DEST_DIR.glob("org.kde.mac-tahoe-liquid-kde.*"),
        *DEST_DIR.glob("org.kde.mactahoe-liquid-kde.*"),
    ]
    for d in targets:
        if d.is_dir():
            try:
                shutil.rmtree(d)
                ok(d.name); n += 1
            except OSError:
                fail(d.name)
    info(tr('{n} plasmoids removed', n=n))
