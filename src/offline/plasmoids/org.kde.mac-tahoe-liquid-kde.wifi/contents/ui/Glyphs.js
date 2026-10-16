/*
    AquaDesktop — Wi-Fi menu glyphs, drawn on a 24 px grid.

    Kept as SVG markup so Glyph.qml can colour them itself: every glyph
    follows the panel text colour (or an accent) on any icon theme and
    any scene graph backend.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
.pragma library

const shapes = {
    "wifi": "<path d=\"M2.6 9.2a13.3 13.3 0 0 1 18.8 0\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2.3\"/><path d=\"M5.9 12.6a8.6 8.6 0 0 1 12.2 0\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2.3\"/><path d=\"M9.2 16a3.9 3.9 0 0 1 5.6 0\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2.3\"/><circle cx=\"12\" cy=\"19.4\" r=\"1.7\"/>",
    "lock": "<rect x=\"5\" y=\"10.5\" width=\"14\" height=\"11\" rx=\"2.2\"/><path d=\"M8 10.5V7.6a4 4 0 0 1 8 0v2.9\" fill=\"none\" stroke=\"#000\" stroke-width=\"2\" stroke-linecap=\"round\"/>",
};

function hex(channel) {
    return Math.round(channel * 255).toString(16).padStart(2, "0");
}

// A data URL for `name` filled and stroked with `color`.
function url(name, color) {
    const body = shapes[name];
    if (!body) {
        return "";
    }
    const rgb = "#" + hex(color.r) + hex(color.g) + hex(color.b);
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="'
        + rgb + '" fill-opacity="' + color.a + '">'
        + body.split("#000").join(rgb) + "</svg>";
    return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
}
