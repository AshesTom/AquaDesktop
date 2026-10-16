"""App icons out of a compiled asset catalog (Assets.car), per appearance.

macOS 26 apps made with Icon Composer ship no rendered dark icon: their
Assets.car holds an `.iconstack` per appearance (NSAppearanceNameAqua,
...DarkAqua, ISAppearanceTintable) that IconServices renders at run time.
A stack is a background fill then groups of layers, bottom first; a layer
is an SVG (or a bitmap) placed on the 1024 px canvas, drawn with its own
fills or with a colour / gradient that the appearance names. This module
reads the catalog (a BOM file) and draws a stack with Qt, the Liquid Glass
approximated (`render_stack`).
"""

from __future__ import annotations

import struct

from dmg import DmgError, lzfse_decode

# Rendition key attributes.
APPEARANCE, PART, IDENTIFIER, ELEMENT = 7, 2, 17, 1
# Parts of an Icon Composer icon.
PART_SVG, PART_COLOR, PART_FLAT, PART_STACK, PART_GROUP, PART_GRADIENT = 181, 217, 220, 245, 246, 247


def _bom(data: bytes):
    if data[:8] != b"BOMStore":
        raise DmgError("not an asset catalog")
    index_off = struct.unpack_from(">I", data, 16)[0]
    vars_off = struct.unpack_from(">I", data, 24)[0]
    count = struct.unpack_from(">I", data, index_off)[0]
    blocks = [struct.unpack_from(">II", data, index_off + 4 + 8 * k) for k in range(count)]

    def block(i: int) -> bytes:
        addr, length = blocks[i]
        return data[addr:addr + length]
    variables, p = {}, vars_off + 4
    for _ in range(struct.unpack_from(">I", data, vars_off)[0]):
        idx, length = struct.unpack_from(">IB", data, p)
        variables[data[p + 5:p + 5 + length].decode("ascii", "replace")] = idx
        p += 5 + length
    return block, variables


def _tree(block, index: int):
    """(key, value) of a BOM B-tree, in order."""
    tree = block(index)
    if tree[:4] != b"tree":
        raise DmgError("bad asset catalog tree")
    node = block(struct.unpack_from(">I", tree, 8)[0])
    while not struct.unpack_from(">H", node, 0)[0]:          # down to the first leaf
        node = block(struct.unpack_from(">I", node, 12)[0])
    seen = set()
    while True:
        _leaf, count, forward = struct.unpack_from(">HHI", node, 0)
        for k in range(count):
            value, key = struct.unpack_from(">II", node, 12 + 8 * k)
            yield block(key), block(value)
        if not forward or forward in seen:
            return
        seen.add(forward)
        node = block(forward)


class Rendition:
    __slots__ = ("key", "name", "format", "width", "height", "tlv", "payload")

    def __init__(self, key: dict, csi: bytes):
        self.key = key
        self.format = csi[24:28][::-1]
        self.width, self.height = struct.unpack_from("<II", csi, 12)
        self.name = csi[40:168].split(b"\0")[0].decode("utf-8", "replace")
        tlv_len = struct.unpack_from("<I", csi, 168)[0]
        self.tlv: dict[int, bytes] = {}
        t, p = csi[184:184 + tlv_len], 0
        while p + 8 <= len(t):
            kind, length = struct.unpack_from("<II", t, p)
            self.tlv[kind] = t[p + 8:p + 8 + length]
            p += 8 + length
        self.payload = csi[184 + tlv_len:]

    def raw(self) -> bytes:
        """The data of a 'DWAR' (raw data: SVG, PDF...) payload."""
        if self.payload[:4] != b"DWAR":
            return b""
        length = struct.unpack_from("<I", self.payload, 8)[0]
        data = self.payload[12:12 + length]
        return lzfse_decode(data) if data[:3] == b"bvx" else data   # version 1: compressed


class Car:
    def __init__(self, data: bytes):
        block, variables = _bom(data)
        fmt = block(variables["KEYFORMAT"])
        tokens = struct.unpack_from("<%dI" % struct.unpack_from("<I", fmt, 8)[0], fmt, 12)
        self.appearances: dict[str, int] = {}
        if "APPEARANCEKEYS" in variables:
            for key, value in _tree(block, variables["APPEARANCEKEYS"]):
                self.appearances[key.decode("utf-8", "replace")] = struct.unpack_from("<H", value)[0]
        self.facets: dict[str, dict] = {}
        for key, value in _tree(block, variables["FACETKEYS"]):
            n = struct.unpack_from("<H", value, 4)[0]
            attrs = dict(struct.unpack_from("<HH", value, 6 + 4 * k) for k in range(n))
            self.facets[key.decode("utf-8", "replace").rstrip("\0")] = attrs
        self.renditions: list[Rendition] = []
        for key, value in _tree(block, variables["RENDITIONS"]):
            values = struct.unpack_from("<%dH" % len(tokens), key)
            if value[:4] == b"ISTC":
                self.renditions.append(Rendition(dict(zip(tokens, values)), value))

    def find(self, appearance: int, part: int, identifier: int | None = None,
             name: str | None = None) -> list[Rendition]:
        """Renditions of that part (and identifier or name), in the given
        appearance, else in the default one."""
        def match(r: Rendition) -> bool:
            return (r.key.get(PART) == part
                    and (identifier is None or r.key.get(IDENTIFIER) == identifier)
                    and (name is None or r.name == name))
        for wanted in (appearance, 0):
            found = [r for r in self.renditions if match(r) and r.key.get(APPEARANCE, 0) == wanted]
            if found:
                return found
        return [r for r in self.renditions if match(r)]

    def named(self, appearance: int, name: str) -> Rendition | None:
        attrs = self.facets.get(name)
        if attrs is None:
            return None
        part, identifier = attrs.get(PART), attrs.get(IDENTIFIER)
        found = self.find(appearance, part, identifier) if part is not None else []
        return found[0] if found else None

    def stack_names(self) -> list[str]:
        return sorted({r.name for r in self.renditions if r.key.get(PART) == PART_STACK})


def _ref(buf: bytes, p: int) -> tuple[dict, int]:
    length = struct.unpack_from("<I", buf, p)[0]
    body = buf[p + 4:p + 4 + length]
    attrs = dict(struct.unpack_from("<HH", body, 4 * k) for k in range(len(body) // 4))
    attrs.pop(0, None)
    return attrs, p + 4 + length


def entries(rendition: Rendition) -> list[dict]:
    """TLV 1012 of a stack or group: its parts (rect, opacity, reference),
    bottom first; groups add each layer's fill override (TLV 1020)."""
    buf = rendition.tlv.get(1012, b"")
    if len(buf) < 8:
        return []
    count, p, out = struct.unpack_from("<I", buf, 0)[0], 8, []
    for _ in range(count):
        _a, x, y, w, h, _b = struct.unpack_from("<Iiiiii", buf, p)
        opacity = struct.unpack_from("<f", buf, p + 24)[0]
        ref, p = _ref(buf, p + 28)
        out.append({"rect": (x, y, w, h), "opacity": opacity, "ref": ref, "fill": ""})
    fills = rendition.tlv.get(1020, b"")
    if rendition.key.get(PART) == PART_GROUP and len(fills) >= 4:
        p = 4
        for entry in out:
            if p + 16 > len(fills):
                break
            length = struct.unpack_from("<I", fills, p + 12)[0]
            entry["fill"] = fills[p + 16:p + 16 + length].rstrip(b"\0").decode("utf-8", "replace")
            p += 16 + length
    return out


def color(rendition: Rendition) -> tuple[float, float, float, float] | None:
    """A 'RLOC' colour: grey or RGB, with alpha."""
    pay = rendition.payload
    if pay[:4] != b"RLOC":
        return None
    n = struct.unpack_from("<I", pay, 12)[0]
    comps = struct.unpack_from("<%dd" % n, pay, 16)
    if n == 2:
        return comps[0], comps[0], comps[0], comps[1]
    if n >= 4:
        return comps[0], comps[1], comps[2], comps[3]
    return None


def gradient(rendition: Rendition) -> dict | None:
    """An 'ARGG' gradient: start and end points (unit square, y down) and
    stops (location, colour name)."""
    pay = rendition.payload
    if pay[:4] != b"ARGG":
        return None
    n = struct.unpack_from("<I", pay, 4)[0]
    sx, sy, ex, ey = struct.unpack_from("<4f", pay, 16)
    stops, p = [], 32
    for _ in range(n):
        location, length = struct.unpack_from("<fI", pay, p)
        stops.append((location, pay[p + 8:p + 8 + length].rstrip(b"\0").decode("utf-8", "replace")))
        p += 8 + length
    return {"start": (sx, sy), "end": (ex, ey), "stops": stops}


def bitmap(rendition: Rendition):
    """An ARGB / GA8 bitmap, as a QImage (None for other encodings). The
    'MLEC' payload holds LZFSE 'KCBC' chunks (compression 4) or a deepmap2
    image (compression 11: 'dmp2', a byte of bytes per pixel, u16 width,
    u16 rows per chunk, then chunks of a u32 length and an LZFSE stream)."""
    from PyQt6.QtGui import QImage
    pay = rendition.payload
    if pay[:4] != b"MLEC":
        return None
    compression = struct.unpack_from("<I", pay, 8)[0]
    w, h = rendition.width, rendition.height
    gray = rendition.format == b"GA8 "
    pixels = bytearray()
    if compression == 4:
        p = 16
        while p + 20 <= len(pay) and pay[p:p + 4] == b"KCBC":
            length = struct.unpack_from("<I", pay, p + 16)[0]
            pixels += lzfse_decode(pay[p + 20:p + 20 + length])
            p += 20 + length
    elif compression == 11:
        p = pay.find(b"dmp2", 16)
        if p < 0:
            return None
        p += 12
        while p + 4 <= len(pay):
            length = struct.unpack_from("<I", pay, p)[0]
            if not length or pay[p + 4:p + 7] != b"bvx":
                break
            pixels += lzfse_decode(pay[p + 4:p + 4 + length])
            p += 4 + length
    else:
        return None
    if gray:
        if len(pixels) < 2 * w * h:
            return None
        rgba = bytearray(w * h * 4)
        rgba[0::4] = rgba[1::4] = rgba[2::4] = pixels[0:2 * w * h:2]
        rgba[3::4] = pixels[1:2 * w * h:2]
        pixels = rgba
    if len(pixels) < w * h * 4:
        return None
    image = QImage(bytes(pixels[:w * h * 4]), w, h, w * 4, QImage.Format.Format_ARGB32_Premultiplied)
    return image.copy()


def flat_icon(car: Car, stack: str, of_stack: bool = False):
    """The largest icon Xcode rendered (default appearance), as a QImage;
    with `of_stack`, only a render of the layered icon (named after its
    appearance), not a legacy .appiconset image."""
    best = None
    for r in car.renditions:
        if r.key.get(PART) == PART_FLAT and r.format in (b"ARGB", b"GA8 "):
            if of_stack and "NSAppearanceName" not in r.name:
                continue
            if best is None or r.width > best.width:
                best = r
    return bitmap(best) if best else None


# ── Drawing a stack ───────────────────────────────────────────────────

CANVAS = 1024


def _qcolor(rgba):
    from PyQt6.QtGui import QColor
    r, g, b, a = (min(1.0, max(0.0, c)) for c in rgba)
    return QColor.fromRgbF(r, g, b, a)


def _brush(car: Car, appearance: int, ref_or_name, rect):
    """A colour or a gradient (over `rect`) named or referenced."""
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QBrush, QLinearGradient
    if isinstance(ref_or_name, str):
        rendition = car.named(appearance, ref_or_name)
    else:
        found = car.find(appearance, ref_or_name.get(PART), ref_or_name.get(IDENTIFIER))
        rendition = found[0] if found else None
    if rendition is None:
        return None
    rgba = color(rendition)
    if rgba is not None:
        return QBrush(_qcolor(rgba))
    spec = gradient(rendition)
    if not spec or not spec["stops"]:
        return None
    x, y, w, h = rect
    grad = QLinearGradient(QPointF(x + spec["start"][0] * w, y + spec["start"][1] * h),
                           QPointF(x + spec["end"][0] * w, y + spec["end"][1] * h))
    for location, name in spec["stops"]:
        stop = car.named(appearance, name)
        rgba = color(stop) if stop else None
        if rgba is not None:
            grad.setColorAt(min(1.0, max(0.0, location)), _qcolor(rgba))
    return QBrush(grad)


def _layer_image(car: Car, appearance: int, layer: dict):
    """A layer drawn on the canvas: its SVG (or bitmap) in its rect, filled
    with the appearance's colour or gradient when it names one."""
    from PyQt6.QtCore import QByteArray, QRectF, Qt
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer
    image = QImage(CANVAS, CANVAS, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    ref = layer["ref"]
    found = car.find(appearance, ref.get(PART), ref.get(IDENTIFIER))
    if not found:
        return image
    x, y, w, h = layer["rect"]
    target = QRectF(x, y, w, h)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    svg = next((r for r in found if r.format == b"SVG "), None)
    if svg is not None:
        renderer = QSvgRenderer(QByteArray(svg.raw()))
        renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        renderer.render(painter, target)
    else:
        best = max((r for r in found if r.format in (b"ARGB", b"GA8 ")),
                   key=lambda r: r.width, default=None)
        picture = bitmap(best) if best else None
        if picture is not None:
            painter.drawImage(target, picture)
    if layer["fill"]:
        brush = _brush(car, appearance, layer["fill"], (x, y, w, h))
        if brush is not None:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(image.rect(), brush)
    painter.end()
    return image


def render_body(car: Car, stack: str, appearance: int):
    """The icon's square body, 1024 px, as the stack draws it in that
    appearance, without glass effects or the outline (None: no stack)."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QImage, QPainter
    stacks = [r for r in car.find(appearance, PART_STACK) if r.name == stack or not stack]
    if not stacks:
        return None
    parts = entries(stacks[0])
    body = QImage(CANVAS, CANVAS, QImage.Format.Format_ARGB32_Premultiplied)
    body.fill(Qt.GlobalColor.transparent)
    painter = QPainter(body)
    for index, part in enumerate(parts):
        ref = part["ref"]
        if ref.get(PART) == PART_GROUP:
            groups = car.find(appearance, PART_GROUP, ref.get(IDENTIFIER))
            if not groups:
                continue
            for layer in entries(groups[0]):
                painter.setOpacity(part["opacity"] * layer["opacity"])
                painter.drawImage(0, 0, _layer_image(car, appearance, layer))
        elif index == 0:
            brush = _brush(car, appearance, ref, (0, 0, CANVAS, CANVAS))
            if brush is not None:
                painter.setOpacity(part["opacity"])
                painter.fillRect(0, 0, CANVAS, CANVAS, brush)
    painter.end()
    return body


# ── The icon as macOS shows it ────────────────────────────────────────

# Apple's grid: the body is 824 px of 1024, its corners ~185 px.
BODY, INSET, RADIUS = 824, 100, 185.4
# Liquid Glass, approximated (fitted on Xcode's light renders of the same
# stacks): a 17 px inner rim lightening the tile by 41 % + 41 % x
# luminance^3 of what is left, the top 5 % lighter, the bottom 4 % darker.
RIM, RIM_BASE, RIM_LUMA, TOP_LIGHT, BOTTOM_DARK = 17.0, 0.41, 0.41, 0.05, 0.04
# The drop shadow (fitted on Xcode's renders): the body in black at 30 %,
# 8 px down, blurred by scaling it to 40 px and back.
SHADOW_OPACITY, SHADOW_DY, SHADOW_BLUR = 0.30, 8, 40


def _rim_distance(x: float, y: float) -> float:
    """Distance inside the body's rounded square (negative outside)."""
    half = BODY / 2
    qx, qy = abs(x - 512) - (half - RADIUS), abs(y - 512) - (half - RADIUS)
    outside = (max(qx, 0) ** 2 + max(qy, 0) ** 2) ** 0.5 + min(max(qx, qy), 0)
    return RADIUS - outside


def _glass(icon) -> None:
    """The rim and the vertical light, on the opaque body of `icon` (1024
    px, Apple's grid), in place."""
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QColor, QLinearGradient, QPainter
    painter = QPainter(icon)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
    light = QLinearGradient(QPointF(0, INSET), QPointF(0, INSET + BODY))
    light.setColorAt(0.0, QColor(255, 255, 255, round(255 * TOP_LIGHT)))
    light.setColorAt(0.5, QColor(0, 0, 0, 0))
    light.setColorAt(1.0, QColor(0, 0, 0, round(255 * BOTTOM_DARK)))
    painter.fillRect(icon.rect(), light)
    painter.end()
    stride = icon.bytesPerLine()
    bits = icon.bits()
    bits.setsize(stride * icon.height())
    buf = memoryview(bits).cast("B")
    band = int(RIM) + 1
    lo, hi = INSET, INSET + BODY
    for y in range(lo, hi):
        near_y = y < lo + RADIUS + band or y >= hi - RADIUS - band
        xs = range(lo, hi) if near_y else list(range(lo, lo + band)) + list(range(hi - band, hi))
        row = y * stride
        for x in xs:
            d = _rim_distance(x + 0.5, y + 0.5)
            if d <= 0 or d >= RIM:
                continue
            p = row + 4 * x
            if buf[p + 3] != 255:
                continue
            b, g, r = buf[p], buf[p + 1], buf[p + 2]
            luma = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
            k = (1 - d / RIM) * (RIM_BASE + RIM_LUMA * luma ** 3)
            buf[p] = round(b + (255 - b) * k)
            buf[p + 1] = round(g + (255 - g) * k)
            buf[p + 2] = round(r + (255 - r) * k)


def _shape():
    from PyQt6.QtGui import QPainterPath
    path = QPainterPath()
    path.addRoundedRect(INSET, INSET, BODY, BODY, RADIUS, RADIUS)
    return path


def _shadow():
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QImage, QPainter
    shadow = QImage(CANVAS, CANVAS, QImage.Format.Format_ARGB32_Premultiplied)
    shadow.fill(Qt.GlobalColor.transparent)
    painter = QPainter(shadow)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(0, SHADOW_DY)
    painter.fillPath(_shape(), QColor(0, 0, 0, round(255 * SHADOW_OPACITY)))
    painter.end()
    smooth = Qt.TransformationMode.SmoothTransformation
    for side in (SHADOW_BLUR, SHADOW_BLUR * 4, CANVAS):
        shadow = shadow.scaled(side, side, Qt.AspectRatioMode.IgnoreAspectRatio, smooth)
    return shadow


def render_icon(car: Car, stack: str, appearance: int):
    """The stack drawn as macOS shows it: 1024 px, Apple's grid, the glass
    and the drop shadow approximated. None: no stack."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QImage, QPainter
    body = render_body(car, stack, appearance)
    if body is None:
        return None
    icon = QImage(CANVAS, CANVAS, QImage.Format.Format_ARGB32_Premultiplied)
    icon.fill(Qt.GlobalColor.transparent)
    painter = QPainter(icon)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawImage(QRectF(INSET, INSET, BODY, BODY),
                      body.scaled(BODY, BODY, Qt.AspectRatioMode.IgnoreAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation))
    painter.end()
    _glass(icon)
    clipped = _shadow()
    painter = QPainter(clipped)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setClipPath(_shape())
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    painter.drawImage(0, 0, icon)
    painter.end()
    return clipped


def render_glyph(car: Car, stack: str):
    """macOS' drawing mask for the Tinted and Clear styles: the Tintable
    appearance's layers (no background), luminance x alpha, white on black,
    1024 px on Apple's grid. None: no Tintable stack."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QImage, QPainter
    appearance = car.appearances.get("ISAppearanceTintable")
    if appearance is None:
        return None
    stacks = [r for r in car.find(appearance, PART_STACK) if r.name == stack or not stack]
    if not stacks or stacks[0].key.get(APPEARANCE) != appearance:
        return None
    layers = QImage(CANVAS, CANVAS, QImage.Format.Format_ARGB32_Premultiplied)
    layers.fill(Qt.GlobalColor.transparent)
    painter = QPainter(layers)
    for part in entries(stacks[0]):
        ref = part["ref"]
        if ref.get(PART) != PART_GROUP:
            continue
        for group in car.find(appearance, PART_GROUP, ref.get(IDENTIFIER))[:1]:
            for layer in entries(group):
                painter.setOpacity(part["opacity"] * layer["opacity"])
                painter.drawImage(0, 0, _layer_image(car, appearance, layer))
    painter.end()
    # Over black, each pixel is its luminance x alpha.
    grey = QImage(CANVAS, CANVAS, QImage.Format.Format_ARGB32_Premultiplied)
    grey.fill(Qt.GlobalColor.black)
    painter = QPainter(grey)
    painter.drawImage(0, 0, layers)
    painter.end()
    grey = grey.convertToFormat(QImage.Format.Format_Grayscale8)
    glyph = QImage(CANVAS, CANVAS, QImage.Format.Format_ARGB32_Premultiplied)
    glyph.fill(Qt.GlobalColor.black)
    painter = QPainter(glyph)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setClipPath(_shape())                     # a full-canvas layer stays in the body
    painter.drawImage(QRectF(INSET, INSET, BODY, BODY),
                      grey.scaled(BODY, BODY, Qt.AspectRatioMode.IgnoreAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation))
    painter.end()
    return glyph
