"""macOS Tahoe accent colour and Plasma tooltips (AquaDesktop).

macOS 26 moved systemBlue to #0088FF (light) / #0091FF (dark); the KDE
colour schemes, Kvantum and GTK share it so a selection looks the same in
every toolkit. Tooltips are small 8 px rounded labels, not 22 px panels.
"""

import gzip
import re

import pytest

ACCENT = {"Dark": "0,145,255", "Light": "0,136,255"}


@pytest.mark.parametrize("variant", ["Dark", "Light"])
def test_colour_scheme_uses_tahoe_system_blue(offline, variant):
    colors = (offline / f"color-schemes/MacTahoeLiquidKde{variant}.colors").read_text()
    selection = colors[colors.index("[Colors:Selection]"):]
    selection = selection[:selection.index("\n[")]
    assert f"BackgroundNormal={ACCENT[variant]}" in selection
    # No leftover of the old indigo accent or of Breeze's blue.
    assert "49,91,239" not in colors
    assert "61,174,233" not in colors


def test_gtk_accent_matches(offline):
    for sheet in sorted((offline / "gtk").glob("MacTahoeLiquidKde-*/gtk-4.0/*.css")):
        css = sheet.read_text()
        dark = "@define-color window_bg_color #242424;" in css
        hexa = "#0091FF" if dark else "#0088FF"
        assert f"@define-color accent_bg_color {hexa};" in css, sheet


@pytest.mark.parametrize("path", [
    "plasma-theme/MacTahoeLiquidKde-Dark/widgets/tooltip.svgz",
    "plasma-theme/MacTahoeLiquidKde-Dark/solid/widgets/tooltip.svgz",
    "plasma-theme/MacTahoeLiquidKde-Light/widgets/tooltip.svgz",
    "plasma-theme/MacTahoeLiquidKde-Light/solid/widgets/tooltip.svgz",
])
def test_tooltip_corners_are_8px(offline, path):
    svg = gzip.decompress((offline / path).read_bytes()).decode()
    corner = re.search(r'<g\s[^>]*id="topleft"[^>]*>(.*?)</g>', svg, re.S).group(1)
    # A 4-unit radius in a corner group scaled 2x: 8 px on screen.
    assert "H 17 C 14.790861" in corner
    assert "c -6.093976,0 -11" not in corner
    mask = re.search(r'<g\s[^>]*id="mask-topleft"[^>]*>(.*?)</g>', svg, re.S).group(1)
    assert "H 17.5 C" in mask
