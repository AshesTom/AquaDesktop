/*
    MacTahoe Liquid KDE — Now Playing glyphs, drawn on a 24 px grid.

    Kept as SVG markup so Glyph.qml can colour them itself: every glyph
    follows the panel text colour (or an accent) on any icon theme and
    any scene graph backend.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
.pragma library

const shapes = {
    "next": "<path d=\"M2.5 6.2v11.6a.8.8 0 0 0 1.2.7l8.8-5.8a.8.8 0 0 0 0-1.4L3.7 5.5a.8.8 0 0 0-1.2.7z\"/><path d=\"M11.5 6.2v11.6a.8.8 0 0 0 1.2.7l8.8-5.8a.8.8 0 0 0 0-1.4l-8.8-5.8a.8.8 0 0 0-1.2.7z\"/>",
    "pause": "<rect x=\"5.5\" y=\"4\" width=\"4.6\" height=\"16\" rx=\"1.2\"/><rect x=\"13.9\" y=\"4\" width=\"4.6\" height=\"16\" rx=\"1.2\"/>",
    "play": "<path d=\"M7 4.2v15.6a1 1 0 0 0 1.5.9l12.4-7.8a1 1 0 0 0 0-1.8L8.5 3.3A1 1 0 0 0 7 4.2z\"/>",
    "play-circle": "<circle cx=\"12\" cy=\"12\" r=\"9.2\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.7\"/><path d=\"M10 8.1v7.8a.6.6 0 0 0 .9.5l6.2-3.9a.6.6 0 0 0 0-1L10.9 7.6a.6.6 0 0 0-.9.5z\"/>",
    "previous": "<g transform=\"matrix(-1 0 0 1 24 0)\"><path d=\"M2.5 6.2v11.6a.8.8 0 0 0 1.2.7l8.8-5.8a.8.8 0 0 0 0-1.4L3.7 5.5a.8.8 0 0 0-1.2.7z\"/><path d=\"M11.5 6.2v11.6a.8.8 0 0 0 1.2.7l8.8-5.8a.8.8 0 0 0 0-1.4l-8.8-5.8a.8.8 0 0 0-1.2.7z\"/></g>",
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
