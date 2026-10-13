"""Build reduced-transparency assets from the bundled sources, never live files.

Shared by the imperative installer and Nix packaging. Geometry, shadows,
gradients and controls stay intact; only surface fills become more opaque.
"""

from __future__ import annotations

import gzip
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

SUFFIX = "-ReducedTransparency"
SURFACES = {
    "center", "top", "bottom", "left", "right", "topleft", "topright",
    "bottomleft", "bottomright",
}
PLASMA_FILES = (
    "widgets/panel-background.svgz", "widgets/translucentbackground.svgz",
    "widgets/background.svgz", "widgets/tooltip.svgz", "dialogs/background.svgz",
)


def _surface(identifier: str, kind: str) -> bool:
    if kind == "plasma":
        return identifier.removeprefix("thick-") in SURFACES
    return identifier.startswith(("window-normal", "dialog-normal", "menu-normal", "tooltip-normal"))


def opaque_svg(data: bytes, kind: str) -> bytes:
    # Keep the default SVG namespace: Qt's SVG renderer must see real SVG nodes.
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    root = ET.fromstring(data)

    def visit(node, active=False):
        active = active or _surface(node.get("id", ""), kind)
        if active:
            style = dict(part.split(":", 1) for part in node.get("style", "").split(";") if ":" in part)
            fill = style.get("fill", node.get("fill", ""))
            if fill and fill != "none" and not fill.startswith("url("):
                opacity = float(style.get("opacity", node.get("opacity", "1")))
                fill_opacity = float(style.get("fill-opacity", node.get("fill-opacity", "1")))
                if 0 < opacity * fill_opacity < 0.96:
                    style["opacity"] = "0.96"
                    node.attrib.pop("opacity", None)
                    if fill_opacity != 1:
                        style["fill-opacity"] = "1"
                        node.attrib.pop("fill-opacity", None)
            elif node.tag.endswith("}g") and "opacity" in style:
                style["opacity"] = "1"
            if style:
                node.set("style", ";".join(f"{k}:{v}" for k, v in style.items()))
        for child in node:
            visit(child, active)

    visit(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def generate(source: Path, destination: Path, kind: str, name: str | None = None) -> None:
    """Write a fresh variant in a staging directory supplied by the caller."""
    name = name or source.name
    destination.mkdir(parents=True, exist_ok=True)
    if kind == "kvantum":
        for ext in (".svg", ".kvconfig"):
            data = (source / f"{name}{ext}").read_bytes()
            if ext == ".svg":
                data = opaque_svg(data, kind)
            else:
                data = re.sub(rb"(reduce_(?:menu|window)_opacity)=\d+", rb"\1=0", data)
            (destination / f"{name}{SUFFIX}{ext}").write_bytes(data)
        return

    shutil.copytree(source, destination, dirs_exist_ok=True)
    if kind == "plasma":
        for relative in PLASMA_FILES:
            path = destination / relative
            if path.is_file():
                path.write_bytes(gzip.compress(opaque_svg(gzip.decompress(path.read_bytes()), kind), mtime=0))
        metadata = destination / "metadata.json"
        payload = json.loads(metadata.read_text())
        payload["KPlugin"]["Id"] = name + SUFFIX
        payload["KPlugin"]["Name"] = name + " (Reduced Transparency)"
        metadata.write_text(json.dumps(payload, indent=2) + "\n")
    elif kind == "gtk":
        for path in destination.glob("gtk-*/*.css"):
            # CSS color choice follows the sheet, including GTK's dark override.
            dark = "dark" in path.name.lower() or ("Dark" in name and "Light" not in path.name)
            rgb = "32, 32, 32" if dark else "246, 246, 246"
            selectors = ("window.background, .background, headerbar, menu, .menu, "
                         "popover.background, popover > contents, .sidebar, .navigation-sidebar")
            with path.open("a") as stream:
                stream.write(f"\n/* MacTahoe reduced transparency: surface fills only. */\n"
                             f"{selectors} {{ background-color: rgba({rgb}, 0.96); }}\n")
    else:
        raise ValueError(f"unknown asset kind: {kind}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("plasma", "gtk", "kvantum"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--name")
    args = parser.parse_args()
    generate(args.source, args.destination, args.kind, args.name)
