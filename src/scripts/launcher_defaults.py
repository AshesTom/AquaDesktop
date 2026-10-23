"""Launcher defaults and migration between the Tahoe and Golden Gate editions."""

import json
import os
from pathlib import Path
import re
import tempfile

from localization import tr

DEFAULTS_FILE = Path(__file__).with_name("defaults.json")
LAUNCHER_ID = "org.kde.mac-tahoe-liquid-kde.launcher"


def edition_name() -> str:
    return ("MacGoldenGate" if _edition_defaults().get("wallpaper") == "MacGoldenGate"
            else "MacTahoe")


def edition_state_file(home: Path) -> Path:
    return home / ".local/state/mac-tahoe-liquid-kde/launcher-edition"


def applied_edition(home: Path) -> str | None:
    try:
        value = edition_state_file(home).read_text().strip()
    except FileNotFoundError:
        return None
    if value not in ("MacTahoe", "MacGoldenGate", "unknown"):
        raise ValueError(f"Invalid launcher edition state: {edition_state_file(home)}")
    return value


def record_applied_edition(home: Path, edition: str) -> None:
    path = edition_state_file(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(edition + "\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def remember_installed_edition(home: Path, package: Path) -> None:
    """Keep the outgoing edition until its layout is successfully replaced.

    Older installs have no state file. Read their staged appearance flag before
    replacing the package; never infer the edition from a user's chosen preset.
    This also preserves the transition across --no-apply-theme and failed runs.
    """
    if applied_edition(home) is not None:
        return
    view = package / "contents/ui/MainView.qml"
    try:
        text = view.read_text()
    except FileNotFoundError:
        text = ""
    match = re.search(r"readonly property bool goldenGateEdition: (true|false)", text)
    previous = ("MacGoldenGate" if match[1] == "true" else "MacTahoe") if match else "unknown"
    record_applied_edition(home, previous)


def _edition_defaults() -> dict:
    try:
        defaults = json.loads(DEFAULTS_FILE.read_text())
    except (OSError, ValueError):
        return {}
    return defaults if isinstance(defaults, dict) else {}


def default_launcher_preset() -> int:
    preset = _edition_defaults().get("launcher_preset")
    return preset if type(preset) is int and preset in (1, 2) else 1


def apply_launcher_default(package: Path) -> None:
    """Stamp a staged package, never a user's applet configuration."""
    config = package / "contents/config/main.xml"
    text = config.read_text()
    updated, count = re.subn(
        r'(<entry name="defaultLauncherPreset" type="Int">\s*'
        r'<label>[^<]*</label>\s*<default>)[12](</default>)',
        lambda match: match[1] + str(default_launcher_preset()) + match[2],
        text,
    )
    if count != 1:
        raise ValueError(tr("Launcher package lacks edition preset support"))
    config.write_text(updated)
    view = package / "contents/ui/MainView.qml"
    golden_gate = _edition_defaults().get("wallpaper") == "MacGoldenGate"
    updated, count = re.subn(
        r'(readonly property bool goldenGateEdition: )(?:true|false)',
        lambda match: match[1] + str(golden_gate).lower(),
        view.read_text(),
    )
    if count != 1:
        raise ValueError(tr("Launcher package lacks edition appearance support"))
    view.write_text(updated)
