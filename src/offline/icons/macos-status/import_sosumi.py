#!/usr/bin/env python3
"""Import the macOS menu bar (system tray) icons from the Sosumi Plasma theme.

Maintainer tool. Sosumi (by zayronxio, LGPL) is a Plasma 5 desktop theme
whose ``icons/*.svg`` sheets hold one tray glyph per element id. Plasma 6 no
longer reads those sheets, so this script cuts each glyph out into a
standalone ``<name>-symbolic.svg`` that the icons step overlays onto both
bundled icon themes. Glyphs keep their ``ColorScheme-Text`` classes, so
Plasma recolours them for light and dark themes. Batteries are composed
from Sosumi's outline, fill-level and charger elements.

Run: python3 import_sosumi.py /path/to/Sosumi-Dark/icons
"""

import copy
import gzip
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path(__file__).resolve().parent
SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", XLINK)

# Our icon name (without -symbolic) -> (Sosumi sheet, element ids stacked
# bottom to top).
WIFI_LEVELS = ("0", "20", "40", "60", "80", "100")
MAP: dict[str, tuple[str, tuple[str, ...]]] = {}
for level in WIFI_LEVELS:
    for suffix in ("", "-locked", "-limited"):
        MAP[f"network-wireless-{level}{suffix}"] = ("network", (f"network-wireless-{level}{suffix}",))
for level in ("00", "20", "40", "60", "80", "100"):
    MAP[f"network-wireless-connected-{level}"] = ("network", (f"network-wireless-connected-{level}",))
MAP.update({
    "network-wireless": ("network", ("network-wireless",)),
    "network-wireless-disconnected": ("network", ("network-wireless-disconnected",)),
    "network-wired": ("network", ("network-wired",)),
    "network-wired-activated": ("network", ("network-wired-activated",)),
    "network-wired-disconnected": ("network", ("network-unavailable",)),
    "network-bluetooth": ("network", ("network-bluetooth",)),
    "network-bluetooth-activated": ("network", ("network-bluetooth-activated",)),
    "network-bluetooth-inactive": ("preferences", ("preferences-system-bluetooth-inactive",)),
    "audio-volume-muted": ("audio", ("audio-volume-muted",)),
    "audio-volume-low": ("audio", ("audio-volume-low",)),
    "audio-volume-medium": ("audio", ("audio-volume-medium",)),
    "audio-volume-high": ("audio", ("audio-volume-high",)),
    "audio-volume-high-warning": ("audio", ("audio-volume-high",)),
    "audio-volume-high-danger": ("audio", ("audio-volume-high",)),
    "brightness-high": ("video", ("video-display-brightness",)),
    "system-search": ("system", ("system-search",)),
    "battery-missing": ("battery", ("Battery", "Unavailable")),
})
for p in range(0, 101, 10):
    MAP[f"battery-{p:03d}"] = ("battery", ("Battery", f"Fill{p}"))
    MAP[f"battery-{p:03d}-charging"] = ("battery", ("Battery", f"Fill{p}", "AcAdapter"))
# Plugged in and fully charged, Plasma shows only the power profile icon
# (a bolt for "performance"); macOS keeps the full battery with its plug.
for profile in ("performance", "balanced", "powersave"):
    MAP[f"battery-profile-{profile}"] = MAP["battery-100-charging"]


# ── affine transforms ───────────────────────────────────────────────────
def mul(a, b):
    return (a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1],
            a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3],
            a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5])


def parse_transform(text):
    m = (1, 0, 0, 1, 0, 0)
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", text or ""):
        v = [float(x) for x in re.split(r"[\s,]+", args.strip()) if x]
        if name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "matrix":
            t = tuple(v)
        elif name == "rotate":
            a = math.radians(v[0])
            t = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) == 3:
                t = mul(mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
        else:
            raise ValueError(f"unsupported transform {name}")
        m = mul(m, t)
    return m


def apply(m, x, y):
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


# ── sheet handling ──────────────────────────────────────────────────────
def load(sheet_dir: Path, name: str) -> ET.Element:
    for ext in (".svg", ".svgz"):
        path = sheet_dir / f"{name}{ext}"
        if path.is_file():
            data = path.read_bytes()
            if data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            return ET.fromstring(data)
    raise FileNotFoundError(f"{name}.svg[z] not in {sheet_dir}")


def ancestry(root: ET.Element, element_id: str):
    """Return (element, cumulative transform of its ancestors)."""
    def walk(node, matrix):
        for child in node:
            if child.get("id") == element_id:
                return child, matrix
            found = walk(child, mul(matrix, parse_transform(child.get("transform"))))
            if found:
                return found
        return None
    found = walk(root, (1, 0, 0, 1, 0, 0))
    if not found:
        raise KeyError(element_id)
    return found


def path_points(d: str):
    """Absolute end and control points of a path. Their hull bounds every
    segment, which is all a frame computation needs."""
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)
    points, i, cmd = [], 0, None
    x = y = sx = sy = 0.0
    arity = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}

    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                x, y = sx, sy
                continue
        up = cmd.upper()
        args = [float(t) for t in tokens[i:i + arity[up]]]
        i += arity[up]
        rel = cmd.islower()
        if up == "H":
            x = x + args[0] if rel else args[0]
        elif up == "V":
            y = y + args[0] if rel else args[0]
        elif up == "A":
            r = max(abs(args[0]), abs(args[1]))
            nx, ny = (x + args[5], y + args[6]) if rel else (args[5], args[6])
            points += [(min(x, nx) - r, min(y, ny) - r), (max(x, nx) + r, max(y, ny) + r)]
            x, y = nx, ny
        else:
            for j in range(0, len(args), 2):
                px, py = (x + args[j], y + args[j + 1]) if rel else (args[j], args[j + 1])
                points.append((px, py))
            x, y = points[-1]
        points.append((x, y))
        if up == "M":
            sx, sy = x, y
            cmd = "l" if rel else "L"  # implicit lineto after moveto
    return points


def shape_points(node: ET.Element):
    tag = node.tag.split("}")[-1]
    f = lambda k: float(node.get(k, 0))
    if tag == "rect":
        x, y, w, h = f("x"), f("y"), f("width"), f("height")
        return [(x, y), (x + w, y + h), (x + w, y), (x, y + h)]
    if tag in ("circle", "ellipse"):
        rx = f("r") or f("rx")
        ry = f("r") or f("ry")
        cx, cy = f("cx"), f("cy")
        return [(cx - rx, cy - ry), (cx + rx, cy + ry), (cx + rx, cy - ry), (cx - rx, cy + ry)]
    if tag == "path" and node.get("d"):
        return path_points(node.get("d"))
    return []


def frame(element: ET.Element, matrix):
    """Icon frame: the element's bounds in sheet coordinates, the same box
    Plasma 5 rendered (QSvgRenderer::boundsOnElement), which includes the
    invisible framing rect most glyphs carry."""
    xs, ys = [], []

    def visit(node, m):
        cm = mul(m, parse_transform(node.get("transform")))
        for px, py in shape_points(node):
            tx, ty = apply(cm, px, py)
            xs.append(tx)
            ys.append(ty)
        for child in node:
            visit(child, cm)

    visit(element, matrix)
    if not xs:
        raise ValueError(f"{element.get('id')}: empty element")
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def referenced_defs(root: ET.Element, nodes) -> list[ET.Element]:
    """Copy gradients/clip paths/masks the glyphs point at."""
    ids = set()
    for node in nodes:
        for el in node.iter():
            for value in el.attrib.values():
                ids.update(re.findall(r"url\(#([^)]+)\)", value))
            href = el.get(f"{{{XLINK}}}href") or el.get("href")
            if href and href.startswith("#"):
                ids.add(href[1:])
    out, seen = [], set()
    while ids:
        i = ids.pop()
        if i in seen:
            continue
        seen.add(i)
        el = root.find(f".//*[@id='{i}']")
        if el is None:
            continue
        out.append(copy.deepcopy(el))
        for sub in el.iter():
            href = sub.get(f"{{{XLINK}}}href") or sub.get("href")
            if href and href.startswith("#"):
                ids.add(href[1:])
    return out


def expand_uses(root: ET.Element, node: ET.Element) -> ET.Element:
    """Return a copy of node with every <use> replaced by the group it
    references, so a cut-out glyph does not point back into the sheet."""
    def expanded(n):
        if n.tag == f"{{{SVG}}}use":
            href = (n.get(f"{{{XLINK}}}href") or n.get("href") or "").lstrip("#")
            target = root.find(f".//*[@id='{href}']")
            if target is None:
                raise KeyError(href)
            transform = (n.get("transform") or "") + \
                f" translate({n.get('x', '0')},{n.get('y', '0')})"
            g = ET.Element(f"{{{SVG}}}g", {"transform": transform.strip()})
            if n.get("id"):
                g.set("id", n.get("id"))
            g.append(expanded(target))
            return g
        out = ET.Element(n.tag, dict(n.attrib))
        out.text, out.tail = n.text, n.tail
        out.extend(expanded(child) for child in n)
        return out
    return expanded(node)


def build(root: ET.Element, ids) -> str:
    style = root.find(f".//{{{SVG}}}style[@id='current-color-scheme']")
    first_frame = None
    layers = []
    for element_id in ids:
        element, matrix = ancestry(root, element_id)
        element = expand_uses(root, element)
        box = frame(element, matrix)
        if first_frame is None:
            first_frame = box
        # Map this element's frame onto the first one (Sosumi draws battery
        # outline, fill and charger in separate, same-sized frames).
        sx, sy = first_frame[2] / box[2], first_frame[3] / box[3]
        place = mul((1, 0, 0, 1, first_frame[0] - box[0] * sx, first_frame[1] - box[1] * sy),
                    (sx, 0, 0, sy, 0, 0))
        g = ET.Element(f"{{{SVG}}}g", {"transform": "matrix(%g %g %g %g %g %g)" % mul(place, matrix)})
        g.append(element)
        layers.append(g)
    x, y, w, h = first_frame
    svg = ET.Element(f"{{{SVG}}}svg", {
        "width": "22", "height": "22", "viewBox": f"{x:g} {y:g} {w:g} {h:g}"})
    defs = referenced_defs(root, layers)
    if style is not None or defs:
        d = ET.SubElement(svg, f"{{{SVG}}}defs")
        if style is not None:
            d.append(copy.deepcopy(style))
        d.extend(defs)
    svg.extend(layers)
    # Inkscape/sodipodi attributes are editor metadata only.
    for el in svg.iter():
        for key in [k for k in el.attrib if "inkscape" in k or "sodipodi" in k]:
            del el.attrib[key]
    ET.indent(svg, space=" ")
    return ET.tostring(svg, encoding="unicode") + "\n"


def main(sheet_dir: Path) -> None:
    sheets = {}
    for old in OUT.glob("*-symbolic.svg"):
        old.unlink()
    for name, (sheet, ids) in sorted(MAP.items()):
        root = sheets.setdefault(sheet, load(sheet_dir, sheet))
        (OUT / f"{name}-symbolic.svg").write_text(build(root, ids), encoding="utf-8")
    print(f"{len(MAP)} icons imported into {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
