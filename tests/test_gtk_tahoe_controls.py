"""GTK4 / libadwaita controls styled like macOS Tahoe (AquaDesktop)."""

import pytest

START = "/* >>> MacOS-Tahoe-KDE Tahoe controls block (src/offline/gtk/tahoe-controls-gtk4.css) >>> */"
END = "/* <<< MacOS-Tahoe-KDE Tahoe controls block <<< */"
FINDER = "/* >>> MacOS-Tahoe-KDE Finder block"
SHEETS = [
    f"gtk/MacTahoeLiquidKde-{theme}/gtk-4.0/{name}"
    for theme in ("Dark", "Light")
    for name in ("gtk.css", "gtk-dark.css", "gtk-Dark.css", "gtk-Light.css")
]


@pytest.mark.parametrize("relative_path", SHEETS)
def test_every_gtk4_sheet_carries_the_current_block(offline, relative_path):
    """Same contract as the Finder block: every variant ends with the
    current block, placed before the Nautilus-only Finder block so the
    latter still wins in Nautilus."""
    block = (offline / "gtk/tahoe-controls-gtk4.css").read_text().strip()
    sheet = (offline / relative_path).read_text()
    assert sheet.count(START) == 1
    assert sheet[sheet.index(START) + len(START):sheet.index(END)].strip() == block
    assert sheet.index(END) < sheet.index(FINDER)


def test_block_matches_the_kvantum_look(offline):
    css = (offline / "gtk/tahoe-controls-gtk4.css").read_text()
    # Capsule push buttons with a regular-weight label.
    assert "border-radius: 999px;" in css
    assert "font-weight: normal;" in css
    # Window controls (under windowcontrols) keep their traffic lights:
    # header bar rules only reach buttons packed straight into the bar, and
    # stay low in specificity so app blocks (Finder) win.
    assert "headerbar box.start > button:not(.suggested-action)" in css
    rules = __import__("re").sub(r"/\*.*?\*/", "", css, flags=__import__("re").S)
    assert "windowcontrols" not in rules
    assert ":not(.titlebutton)" not in css
    # Segmented controls: grey pill, never the accent colour.
    segment = css[css.index("stackswitcher > button:checked"):]
    segment = segment[:segment.index("}")]
    assert "alpha(@window_fg_color, 0.22)" in segment
    assert "accent" not in segment
    # GTK CSS has no :has(); a rule using it would be dropped.
    assert ":has(" not in css
