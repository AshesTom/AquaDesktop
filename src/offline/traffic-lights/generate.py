#!/usr/bin/env python3
"""AquaDesktop — the macOS Tahoe (Golden Gate) traffic lights.

One drawing for every toolkit, so KWin's Aurorae buttons and the GTK title
buttons can never drift apart. Measured on a Golden Gate Finder capture:
14 px glass lights: a vertical gradient under a light specular rim;
unfocused windows show grey glass lights; hovering shows the glyphs, even
on an unfocused window.

Run it after changing the drawing; it rewrites the bundled assets:

    python3 src/offline/traffic-lights/generate.py

It needs rsvg-convert (librsvg) for the GTK PNGs. The outputs are committed,
the installer never runs this.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

OFFLINE = Path(__file__).resolve().parent.parent

# Fill gradient, top / middle / bottom, per appearance. Golden Gate lights
# are glass beads: deepest just above the middle, lighter towards both
# edges, inside a light specular rim that is brightest at the top and the
# bottom. Light-mode lights also keep a faint dark outline.
COLOURS = {
    "Light": {
        "close": ("#fc6157", "#f76a60", "#f07e72"),
        "minimize": ("#fcb02d", "#fcbd2c", "#fccc3c"),
        "maximize": ("#52c924", "#6bcb3f", "#8ad56c"),
        "grey": ("#d4d4d7", "#cfcfd2", "#c9c9cc"),
    },
    "Dark": {
        "close": ("#e86f62", "#e25c4e", "#df7066"),
        "minimize": ("#f0b835", "#f0b500", "#f6d054"),
        "maximize": ("#6ec343", "#4dba00", "#70c150"),
        "grey": ("#52514f", "#4e4c4c", "#4a4849"),
    },
}
for palette in COLOURS.values():
    palette["restore"] = palette["maximize"]
# Specular rim opacity (white), top / middle / bottom.
RIM = {"Light": (0.55, 0.05, 0.45), "Dark": (0.55, 0.05, 0.45)}
OUTLINE = {"Light": 0.2, "Dark": 0.0}
GLYPH = "#000000"
GLYPH_OPACITY = 0.5

GLYPHS = {
    # 16 x 16 box, light centred on (8, 8).
    "close": '<path d="M5.4 5.4 10.6 10.6M10.6 5.4 5.4 10.6" fill="none" '
             'stroke="{c}" stroke-opacity="{o}" stroke-width="1.5" stroke-linecap="round"/>',
    "minimize": '<path d="M4.8 8H11.2" fill="none" stroke="{c}" stroke-opacity="{o}" '
                'stroke-width="1.5" stroke-linecap="round"/>',
    # Full screen: a square split along its diagonal, the halves pointing
    # out to the corners.
    "maximize": '<path d="M5.3 5.3H9.9L5.3 9.9Z M10.7 10.7H6.1L10.7 6.1Z" fill="{c}" fill-opacity="{o}"/>',
    # Exit full screen: the same triangles pointing in.
    "restore": '<path d="M7.6 3.9V7.6H3.9Z M8.4 12.1V8.4H12.1Z" fill="{c}" fill-opacity="{o}"/>',
}


def light(button: str, state: str, mode: str, gid: str, ox: float = 0, oy: float = 0) -> str:
    """One 16 x 16 light, as (gradient definitions, element); state is
    normal, hover, pressed, grey or disabled."""
    palette = COLOURS[mode]["grey" if state in ("grey", "disabled") else button]
    top, middle, bottom = palette
    rim_top, rim_middle, rim_bottom = RIM[mode]
    gradients = (
        f'<linearGradient id="{gid}-fill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{top}"/><stop offset="0.4" stop-color="{middle}"/>'
        f'<stop offset="1" stop-color="{bottom}"/></linearGradient>'
        f'<linearGradient id="{gid}-rim" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#ffffff" stop-opacity="{rim_top}"/>'
        f'<stop offset="0.5" stop-color="#ffffff" stop-opacity="{rim_middle}"/>'
        f'<stop offset="1" stop-color="#ffffff" stop-opacity="{rim_bottom}"/></linearGradient>')
    parts = [f'<circle cx="8" cy="8" r="7" fill="url(#{gid}-fill)"/>']
    if OUTLINE[mode]:
        parts.append(f'<circle cx="8" cy="8" r="6.9" fill="none" stroke="#000000" '
                     f'stroke-opacity="{OUTLINE[mode]}" stroke-width="0.2"/>')
    parts.append(f'<circle cx="8" cy="8" r="6.5" fill="none" stroke="url(#{gid}-rim)" '
                 'stroke-width="0.6"/>')
    if state == "pressed":
        parts.append('<circle cx="8" cy="8" r="7" fill="#000000" fill-opacity="0.18"/>')
    if state in ("hover", "pressed"):
        parts.append(GLYPHS[button].format(c=GLYPH, o=GLYPH_OPACITY))
    opacity = ' opacity="0.5"' if state == "disabled" else ""
    # The transparent square fixes the element's bounds at 16 x 16 for Aurorae.
    return gradients, (f'<g id="{gid}" transform="translate({ox},{oy})"{opacity}>'
                       '<rect width="16" height="16" fill="#000000" opacity="0"/>'
                       + "".join(parts) + "</g>")


def svg(lights: list, width: int, height: int) -> str:
    gradients = "".join(gradient for gradient, _ in lights)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}"><defs>{gradients}</defs>'
            + "".join(element for _, element in lights) + "</svg>\n")


# Aurorae element -> light state.
AURORAE_STATES = {
    "active-center": "normal",
    "hover-center": "hover",
    "pressed-center": "pressed",
    "inactive-center": "grey",
    "hover-inactive-center": "hover",
    "deactivated-center": "disabled",
    "deactivated-inactive-center": "disabled",
}

# GTK asset suffix -> light state (hovering an unfocused window shows the
# coloured light, like macOS).
GTK_STATES = {
    "": "normal",
    "-hover": "hover",
    "-active": "pressed",
    "-backdrop": "grey",
    "-backdrop-hover": "hover",
}


def write_aurorae() -> None:
    for mode in ("Light", "Dark"):
        for button in ("close", "minimize", "maximize", "restore"):
            lights = [light(button, state, mode, element, 0, 20 * row)
                      for row, (element, state) in enumerate(AURORAE_STATES.items())]
            target = OFFLINE / f"aurorae/icons-{mode}/{button}.svg"
            target.write_text(svg(lights, 16, 20 * len(AURORAE_STATES)), encoding="utf-8")


def write_gtk() -> None:
    dirs = [OFFLINE / f"gtk/MacTahoeLiquidKde-{theme}/gtk-{gtk}/windows-assets"
            for theme in ("Dark", "Light") for gtk in ("3.0", "4.0")]
    with tempfile.TemporaryDirectory() as tmp:
        for button in ("close", "minimize", "maximize", "restore"):
            for suffix, state in GTK_STATES.items():
                for variant, mode in (("", "Light"), ("-dark", "Dark")):
                    source = Path(tmp) / "light.svg"
                    source.write_text(svg([light(button, state, mode, "light")], 16, 16))
                    for scale, tail in ((1, ""), (2, "@2")):
                        name = f"titlebutton-{button}{suffix}{variant}{tail}.png"
                        png = Path(tmp) / name
                        subprocess.run(["rsvg-convert", "-w", str(16 * scale),
                                        "-h", str(16 * scale), "-o", str(png), str(source)],
                                       check=True)
                        for directory in dirs:
                            (directory / name).write_bytes(png.read_bytes())


def main() -> int:
    write_aurorae()
    write_gtk()
    return 0


if __name__ == "__main__":
    sys.exit(main())
