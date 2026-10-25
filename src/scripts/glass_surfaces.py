"""Edition-specific client fills; compositor gradients remain material-owned."""

import gzip
from pathlib import Path
import xml.etree.ElementTree as ET

from theme_switch import default_wallpaper

PLASMA_SURFACES = (
    "dialogs/background.svgz", "dialogs/launcher-search.svgz",
    "widgets/background.svgz", "widgets/translucentbackground.svgz",
    "widgets/tooltip.svgz",
)
_TILES = ("center", "top", "bottom", "left", "right",
          "topleft", "topright", "bottomleft", "bottomright")
_TAHOE_DARK_FILL = "0.82"
_TAHOE_LAUNCHER_DARK_FILL = "0.48"
_TAHOE_LAUNCHER_EDGE_OPACITY = {("#000000", .18): "0.08", ("#ffffff", .22): "0.10"}
_SVG = "http://www.w3.org/2000/svg"
_XLINK = "http://www.w3.org/1999/xlink"


def surface_nodes(root: ET.Element, ids: tuple[str, ...]):
    """Follow tile references without touching masks, shadows or fallbacks."""
    indexed = {node.get("id"): node for node in root.iter() if node.get("id")}
    seen = set()

    def visit(node):
        if node in seen:
            return
        seen.add(node)
        yield node
        reference = node.get(f"{{{_XLINK}}}href", node.get("href", ""))
        if reference.startswith("#") and reference[1:] in indexed:
            yield from visit(indexed[reference[1:]])
        for child in node:
            yield from visit(child)

    for id_ in ids:
        if id_ in indexed:
            yield from visit(indexed[id_])


def set_surface_fill(root: ET.Element, ids: tuple[str, ...], opacity: str,
                     color: str | None = None) -> None:
    for node in surface_nodes(root, ids):
        style = dict(part.split(":", 1) for part in node.get("style", "").split(";") if ":" in part)
        if node.tag.rsplit("}", 1)[-1] not in ("rect", "path", "polygon", "ellipse"):
            continue
        fill = style.get("fill", node.get("fill"))
        alpha = style.get("opacity", node.get("opacity", "1"))
        fill_opacity = style.get("fill-opacity", node.get("fill-opacity", "1"))
        effective_alpha = float(alpha) * float(fill_opacity)
        # Only update the broad surface fill. Keep the black and white
        # 0.18/0.22 edge reflections intact; changing those creates visible
        # tile seams and bright horizontal lines around the launcher.
        target_fills = ("#000000",) if color is None else ("#000000", "#ffffff")
        prior_opacities = (.01, .1, .48, .55, .60, .62, .68, .82)
        if fill not in target_fills or not any(
                abs(effective_alpha - value) < 0.001 for value in prior_opacities):
            continue
        # Theme assets encode the reusable fill as rects inside each tile
        # group; update those leaves while leaving borders and highlights intact.
        if "opacity" in style:
            style["opacity"] = opacity
        else:
            node.set("opacity", opacity)
        if color:
            if "fill" in style:
                style["fill"] = color
            else:
                node.set("fill", color)
        if style:
            node.set("style", ";".join(f"{key}:{value}" for key, value in style.items()))


def soften_launcher_tile_edges(root: ET.Element) -> None:
    """Reduce repeated tile reflections that read as seams on the launcher."""
    for node in surface_nodes(root, _TILES):
        if node.tag.rsplit("}", 1)[-1] not in ("rect", "path", "polygon", "ellipse"):
            continue
        style = dict(part.split(":", 1) for part in node.get("style", "").split(";") if ":" in part)
        fill = style.get("fill", node.get("fill"))
        opacity = float(style.get("opacity", node.get("opacity", "1")))
        fill_opacity = float(style.get("fill-opacity", node.get("fill-opacity", "1")))
        effective = opacity * fill_opacity
        target = next((value for (edge_fill, source_alpha), value
                       in _TAHOE_LAUNCHER_EDGE_OPACITY.items()
                       if fill == edge_fill and abs(effective - source_alpha) < .001), None)
        if target is None:
            continue
        if "opacity" in style:
            style["opacity"] = target
        else:
            node.set("opacity", target)
        if style:
            node.set("style", ";".join(f"{key}:{value}" for key, value in style.items()))


def _write_svg(path: Path, root: ET.Element) -> None:
    ET.register_namespace("", _SVG)
    ET.register_namespace("xlink", _XLINK)
    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    path.write_bytes(gzip.compress(data, mtime=0) if path.suffix == ".svgz" else data)


def apply_plasma_surface_defaults(theme: Path) -> None:
    """Apply edition-specific fills to a staged copy of the bundled theme."""
    golden_gate = default_wallpaper() == "MacGoldenGate"
    light = theme.name.endswith("-Light")
    if not golden_gate and light:
        return
    if golden_gate:
        # Golden Gate uses an almost clear dark fill and a light surface so its
        # stronger compositor gradient can supply the material tint.
        opacity, color = (("0.60", "#ffffff") if light else ("0.01", "#ffffff"))
    else:
        # Tahoe keeps enough dark glass behind white menu labels on bright
        # wallpaper while preserving a visible blurred backdrop.
        opacity, color = (("0.55", None) if light else (_TAHOE_DARK_FILL, None))
    for name in PLASMA_SURFACES:
        path = theme / name
        root = ET.fromstring(gzip.decompress(path.read_bytes()))
        surface_opacity = opacity
        if not golden_gate and not light and name == "dialogs/launcher-search.svgz":
            surface_opacity = _TAHOE_LAUNCHER_DARK_FILL
        set_surface_fill(root, _TILES, surface_opacity, color)
        if not golden_gate and not light and name == "dialogs/launcher-search.svgz":
            soften_launcher_tile_edges(root)
        if name == "dialogs/background.svgz" and not any(
                node.get("id") == "hint-clear-surface" for node in root):
            ET.SubElement(root, f"{{{_SVG}}}rect", {
                "id": "hint-clear-surface", "width": "1", "height": "1", "opacity": "0",
            })
        _write_svg(path, root)


def apply_kvantum_surface_defaults(path: Path) -> None:
    golden_gate = default_wallpaper() == "MacGoldenGate"
    if not golden_gate and path.stem == "mac-tahoe-liquid-kde":
        return
    root = ET.parse(path).getroot()
    # The shadow frame also references the menu's surface tiles.
    ids = tuple(node.get("id") for node in root.iter()
                if node.get("id", "").startswith(("menu-normal", "menu-shadow")))
    if golden_gate:
        # Native Qt menus retain dark text in light mode. A translucent white
        # client surface keeps it readable above the compositor's dark gradient.
        opacity, color = (("0.60", "#ffffff") if path.stem == "mac-tahoe-liquid-kde"
                          else ("0.01", "#ffffff"))
    else:
        # Keep Tahoe's dark menu fill opaque enough for white labels.
        opacity, color = (("0.55", None) if path.stem == "mac-tahoe-liquid-kde"
                          else (_TAHOE_DARK_FILL, None))
    set_surface_fill(root, ids, opacity, color)
    _write_svg(path, root)
