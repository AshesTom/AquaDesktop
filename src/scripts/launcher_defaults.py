"""Edition defaults for newly added launchers; explicit choices stay per applet."""

import json
from pathlib import Path
import re

DEFAULTS_FILE = Path(__file__).with_name("defaults.json")
LAUNCHER_ID = "org.kde.mac-tahoe-liquid-kde.launcher"


def default_launcher_preset() -> int:
    try:
        defaults = json.loads(DEFAULTS_FILE.read_text())
        preset = defaults.get("launcher_preset")
    except (OSError, ValueError, AttributeError):
        return 1
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
        raise ValueError("Launcher package lacks edition preset support")
    config.write_text(updated)
