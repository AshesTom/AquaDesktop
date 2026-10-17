"""Static guards for the Dock Task Manager QML against Plasma API removals."""

import re
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
UI = REPO / "src/offline/plasmoids/org.kde.mac.tahoe.liquid.taskmanager/contents/ui"


def test_taskmanager_does_not_use_removed_window_thumbnail():
    """Plasma 6.8 removed the X11-only PlasmaCore.WindowThumbnail type.
    Referencing it makes ToolTipInstance.qml fail to compile, which takes
    down the whole applet and leaves the dock empty."""
    offenders = [
        path.relative_to(REPO).as_posix()
        for path in sorted(UI.rglob("*.qml"))
        if re.search(r"\bWindowThumbnail\s*\{", path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
