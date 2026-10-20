"""GTK window decorations stay shadowless in both modes."""
import re


def test_active_window_shadow_geometry_matches_between_modes(repo):
    for mode in ('Light', 'Dark'):
        path = repo / f'src/offline/gtk/MacTahoeLiquidKde-{mode}/gtk-3.0/gtk.css'
        text = path.read_text()
        for state in ('', ':backdrop'):
            block = re.search(r'^decoration' + state + r' \{(.*?)\n\}', text, re.M | re.S).group(1)
            assert 'box-shadow: none;' in block
