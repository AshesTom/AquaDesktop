"""GTK's active CSD shadows must not resize Chromium during a mode switch."""
import re


def test_active_window_shadow_geometry_matches_between_modes(repo):
    shadows = []
    for mode in ('Light', 'Dark'):
        path = repo / f'src/offline/gtk/MacTahoeLiquidKde-{mode}/gtk-3.0/gtk.css'
        text = path.read_text()
        block = re.search(r'^decoration \{(.*?)\n\}', text, re.M | re.S).group(1)
        shadow = re.search(r'box-shadow: ([^;]+)', block).group(1)
        # Outer blurred shadows determine the alpha-scanned frame extent;
        # the one-pixel light/dark outlines intentionally keep their colors.
        shadows.append(re.findall(r'0 (?:3|8|16)px (?:3|8|16)px 0 rgba\([^)]*\)', shadow))
    assert len(shadows[0]) == 3
    assert shadows[0] == shadows[1]
