"""Window shadow levels applied only to freshly installed theme resources."""

from pathlib import Path
import re

from installer_choices import selected

LEVELS = {"none": 0, "soft": .30, "medium": .65, "hard": 1.0}
GTK_SHADOWS = {
    "none": "none",
    "soft": "0 8px 28px rgba(0, 0, 0, 0.12)",
    "medium": "0 8px 20px rgba(0, 0, 0, 0.24)",
    "hard": "0 8px 12px rgba(0, 0, 0, 0.40)",
}


def aurorae_svg(source: str, level: str) -> str:
    strength = LEVELS[level]

    def gradient(match):
        return re.sub(r"(stop-opacity:)([\d.]+)",
                      lambda stop: stop[1] + f"{float(stop[2]) * strength:.8g}",
                      match[0])

    # Aurorae extracts its shadow from the SVG's padded perimeter. Its rc
    # Shadow key is not a switch for this image; leave frame geometry intact.
    return re.sub(r'<linearGradient\b[^>]*\bid="shadow_(?:active|inactive)"[^>]*>.*?</linearGradient>',
                  gradient, source, flags=re.DOTALL)


def gtk_css(source: str, level: str, version: int) -> str:
    shadow = GTK_SHADOWS[level]
    selector = r"decoration" if version == 3 else r"window\.csd|window\.background\.chromium"

    def window_rule(match):
        def replace_shadow(declaration):
            # Keep zero-blur outlines: borders and rounded corners are separate
            # controls. Tiled/fullscreen/popup rules remain untouched.
            outline = re.search(r",\s*(0 0 0 .*)$", declaration[1])
            border = outline[1] if outline else ""
            value = border if shadow == "none" and border else shadow
            if border and shadow != "none":
                value += ", " + border
            return "box-shadow: " + value + ";"
        return re.sub(r"box-shadow:\s*([^;]+);", replace_shadow, match[0])

    return re.sub(r"^(?:" + selector + r")(?::backdrop)?\s*\{[^}]*\}",
                  window_rule, source, flags=re.MULTILINE)


def apply_aurorae(path: Path) -> None:
    options = selected()
    if options:
        path.write_text(aurorae_svg(path.read_text(), options["shadows"]))


def apply_gtk(path: Path) -> None:
    options = selected()
    if not options:
        return
    for version in (3, 4):
        for css in (path / f"gtk-{version}.0").glob("*.css"):
            if not css.is_symlink():
                css.write_text(gtk_css(css.read_text(), options["shadows"], version))
