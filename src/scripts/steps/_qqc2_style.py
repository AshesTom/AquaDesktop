"""macOS controls for Qt Quick / Kirigami apps (System Settings, Discover...).

Kvantum styles QWidget apps; Qt Quick apps draw their own controls through a
Qt Quick Controls style, org.kde.desktop by default. ``org.kde.mactahoe``
(src/offline/qml/org.kde.mactahoe) inherits it and only replaces the list
rows (macOS accent selection) and the switches (Tahoe capsule knob).

Kirigami picks its platform plugin by the Qt Quick Controls style name, so
``org.kde.mactahoe.so`` must exist next to ``org.kde.desktop.so``. It is a
symlink, never a copy: a Kirigami update replaces the real plugin and the
link follows, where a stale copy would crash every Kirigami app.

The style is selected per session through Plasma's env hook, and only while
both halves are installed, so a removed module never leaves Qt Quick apps
without a style.
"""

import os
from pathlib import Path

from distro import qt6_plugins_dir, qt6_qml_dir
from log import note
from steps._helpers import (
    HOME, _as_root, fail, offline, ok, sudo_install_file, sudo_install_tree,
    sudo_remove, temp_dir, warn,
)

STYLE_NAME = "org.kde.mactahoe"
STYLE_SRC = offline("qml") / STYLE_NAME
_STYLE_QML_RELPATH = "org/kde/mactahoe"
_KIRIGAMI_PLATFORM_RELPATH = "kf6/kirigami/platform"
_BASE_PLUGIN = "org.kde.desktop.so"
ENV_MARKER = "# Managed by mac-tahoe-liquid-kde: Qt Quick Controls style\n"


def style_dest() -> Path:
    return qt6_qml_dir() / _STYLE_QML_RELPATH


def platform_link() -> Path:
    return qt6_plugins_dir() / _KIRIGAMI_PLATFORM_RELPATH / f"{STYLE_NAME}.so"


def env_path() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
    return config_home / "plasma-workspace/env/mac-tahoe-qqc2-style.sh"


def env_script(qmldir: Path, link: Path) -> str:
    return (
        ENV_MARKER
        + "# Only while the style module and its Kirigami platform link exist.\n"
        + f"if [ -f '{qmldir}' ] && [ -e '{link}' ]; then\n"
        + f"    export QT_QUICK_CONTROLS_STYLE={STYLE_NAME}\n"
        + "fi\n"
    )


def _env_owned(path: Path) -> bool:
    try:
        return not path.is_symlink() and path.read_text(encoding="utf-8").startswith(ENV_MARKER)
    except (OSError, UnicodeError):
        return False


def install() -> None:
    if not (STYLE_SRC / "qmldir").is_file():
        warn(f"{STYLE_NAME} style source missing — Qt Quick apps keep org.kde.desktop")
        return
    link = platform_link()
    if not (link.parent / _BASE_PLUGIN).is_file():
        warn("Kirigami's org.kde.desktop platform plugin not found — "
             "macOS Qt Quick controls skipped")
        return
    if not sudo_install_tree(STYLE_SRC, style_dest(), f"{STYLE_NAME} (macOS Qt Quick controls)"):
        return
    try:
        with _as_root():
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(_BASE_PLUGIN)
    except OSError as exc:
        fail(f"{STYLE_NAME} Kirigami platform link ({exc.__class__.__name__}: {exc})")
        return
    ok(f"{STYLE_NAME} Kirigami platform link")

    destination = env_path()
    if (destination.exists() or destination.is_symlink()) and not _env_owned(destination):
        warn(f"Custom Qt Quick style environment preserved: {destination}")
        return
    with temp_dir("mttkde-qqc2-style-") as staging:
        source = staging / destination.name
        source.write_text(env_script(style_dest() / "qmldir", link), encoding="utf-8")
        source.chmod(0o644)
        if sudo_install_file(source, destination, "macOS Qt Quick controls session setting",
                             user_owned=True):
            note("Log out and back in to apply the macOS controls to Qt Quick apps")


def uninstall() -> None:
    destination = env_path()
    if (destination.exists() or destination.is_symlink()) and _env_owned(destination):
        sudo_remove(destination, "macOS Qt Quick controls session setting removed")
    link = platform_link()
    try:
        ours = link.is_symlink() and os.readlink(link) == _BASE_PLUGIN
    except OSError:
        ours = False
    if ours:
        sudo_remove(link, f"{STYLE_NAME} Kirigami platform link removed")
    sudo_remove(style_dest(), f"{STYLE_NAME} style removed")
