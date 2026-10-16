"""Nautilus styled as a macOS Tahoe Finder window (libadwaita / GTK4)."""

from pathlib import Path

import pytest

START = "/* >>> MacOS-Tahoe-KDE Finder block (src/offline/nautilus/finder-gtk4.css) >>> */"
END = "/* <<< MacOS-Tahoe-KDE Finder block <<< */"
SHEETS = [
    f"gtk/MacTahoeLiquidKde-{theme}/gtk-4.0/{name}"
    for theme in ("Dark", "Light")
    for name in ("gtk.css", "gtk-dark.css", "gtk-Dark.css", "gtk-Light.css")
]


@pytest.mark.parametrize("relative_path", SHEETS)
def test_every_gtk4_sheet_carries_the_current_finder_block(offline, relative_path):
    """theme_switch links ~/.config/gtk-4.0/gtk.css to gtk-<Mode>.css, so
    every variant must end with the same, current Finder block."""
    block = (offline / "nautilus/finder-gtk4.css").read_text().strip()
    sheet = (offline / relative_path).read_text()
    assert sheet.count(START) == 1
    assert sheet[sheet.index(START) + len(START):sheet.index(END)].strip() == block


def test_finder_block_targets_nautilus_51_classes(offline):
    block = (offline / "nautilus/finder-gtk4.css").read_text()
    # Nautilus 51 dropped the #NautilusPathBar / #NautilusPathButton names.
    assert ".nautilus-pathbar" in block
    assert ".nautilus-path-button.current-dir" in block
    # Golden Gate: the sidebar is flush with the window edges, no card.
    sidebar = block[block.index(".nautilus-window .sidebar-pane {"):]
    sidebar = sidebar[:sidebar.index("}")]
    assert "margin: 0;" in sidebar
    assert "border-radius: 23px 0 0 23px;" in sidebar
    assert "min-height: 36px;" in block


def test_finder_toolbar_metrics(offline):
    """Pixel metrics measured on Finder (Tahoe, 1x) and checked on a real
    Nautilus 51 rendered in a virtual KWin: back / forward 72 x 36 with a
    1 x 18 hairline, the title 13 px after it, capsules 16 px apart, 8 px
    from the window edge and 8 px after the sidebar card."""
    block = (offline / "nautilus/finder-gtk4.css").read_text()
    # Nautilus' history box keeps a 6 px GtkBox spacing: 33 + 6 + 33 = 72.
    assert "min-width: 33px;" in block
    assert "background-size: 1px 18px;" in block
    assert "background-position: 35px center;" in block
    # Centred in the 42 px bar, 2 px further from the sidebar card.
    assert "margin: 3px 0 3px 2px;" in block
    # Capsule gap and window-edge inset.
    assert "margin: 0 3px 0 4px;" in block
    # Title 13 px after the capsule.
    assert "margin-left: -10px;" in block
    # No frame or gutter around the sidebar, a hairline under the toolbar.
    assert "@view_bg_color" not in block
    assert "box-shadow: inset 0 -1px alpha(@window_fg_color, 0.08);" in block
