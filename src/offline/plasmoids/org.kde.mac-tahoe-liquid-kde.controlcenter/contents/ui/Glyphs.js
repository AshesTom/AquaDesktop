/*
    MacTahoe Liquid KDE — Control Center glyphs, drawn on a 24 px grid.

    Kept as SVG markup so Glyph.qml can colour them itself: every glyph
    follows the panel text colour (or an accent) on any icon theme and
    any scene graph backend.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
.pragma library

const shapes = {
    "calculator": "<path fill-rule=\"evenodd\" d=\"M7.45 1.5h9.1a3.2 3.2 0 0 1 3.2 3.2v14.6a3.2 3.2 0 0 1 -3.2 3.2h-9.1a3.2 3.2 0 0 1 -3.2 -3.2v-14.6a3.2 3.2 0 0 1 3.2 -3.2zM8 4.2h8a1 1 0 0 1 1 1v2a1 1 0 0 1 -1 1h-8a1 1 0 0 1 -1 -1v-2a1 1 0 0 1 1 -1zM7.15 11.3a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0 -2.5 0zM10.75 11.3a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0 -2.5 0zM14.35 11.3a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0 -2.5 0zM7.15 14.6a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0 -2.5 0zM10.75 14.6a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0 -2.5 0zM14.35 14.6a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0 -2.5 0zM7.15 17.9a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0 -2.5 0zM10.75 17.9a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0 -2.5 0zM14.35 17.9a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0 -2.5 0z\"/>",
    "timer": "<path d=\"M14.28 3.50A8.8 8.8 0 1 1 9.72 3.50\" fill=\"none\" stroke=\"#000\" stroke-width=\"2\" stroke-linecap=\"round\"/><path d=\"M12 12 8.6 7.4\" fill=\"none\" stroke=\"#000\" stroke-width=\"2.1\" stroke-linecap=\"round\"/><circle cx=\"12\" cy=\"12\" r=\"1.5\"/>",
    "record": "<rect x=\"3\" y=\"4\" width=\"18\" height=\"16\" rx=\"3.5\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.8\"/><circle cx=\"12\" cy=\"12\" r=\"3.6\"/>",
    "airplane": "<rect x=\"10.7\" y=\"2.2\" width=\"2.6\" height=\"19\" rx=\"1.3\"/><path d=\"M12 8.6 21.6 14v1.9L12 13 2.4 15.9V14z\"/><path d=\"M12 18.1l3.8 2.1v1.4L12 20.7l-3.8.9v-1.4z\"/>",
    "airdrop": "<circle cx=\"12\" cy=\"12\" r=\"2.1\"/><circle cx=\"12\" cy=\"12\" r=\"5.1\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.8\"/><circle cx=\"12\" cy=\"12\" r=\"8.4\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.8\"/>",
    "airplay": "<path d=\"M7 17.5H4.5a2 2 0 0 1-2-2v-10a2 2 0 0 1 2-2h15a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H17\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"1.7\"/><path d=\"M12 13.5l5.2 7H6.8z\"/>",
    "bluetooth": "<path d=\"M6.8 7.6 17 16.4l-5 4.4V3.2l5 4.4L6.8 16.4\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"/>",
    "contrast": "<circle cx=\"12\" cy=\"12\" r=\"8.6\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2.4\"/><path d=\"M12 3.4a8.6 8.6 0 0 1 0 17.2z\"/>",
    "controlcenter": "<rect x=\"2.5\" y=\"3.5\" width=\"19\" height=\"7\" rx=\"3.5\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"1.6\"/><circle cx=\"6\" cy=\"7\" r=\"2.1\"/><rect x=\"2.5\" y=\"13.5\" width=\"19\" height=\"7\" rx=\"3.5\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"1.6\"/><circle cx=\"18\" cy=\"17\" r=\"2.1\"/>",
    "mirroring": "<rect x=\"2.5\" y=\"4\" width=\"13\" height=\"10\" rx=\"2\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"1.8\"/><rect x=\"8.5\" y=\"10\" width=\"13\" height=\"10\" rx=\"2\" fill=\"#000\" stroke=\"#000\" stroke-width=\"1.8\" stroke-linejoin=\"round\"/>",
    "moon": "<path d=\"M14.2 2.9a9.3 9.3 0 1 0 6.9 13.9 7.6 7.6 0 0 1-6.9-13.9z\"/>",
    "next": "<path d=\"M2.5 6.2v11.6a.8.8 0 0 0 1.2.7l8.8-5.8a.8.8 0 0 0 0-1.4L3.7 5.5a.8.8 0 0 0-1.2.7z\"/><path d=\"M11.5 6.2v11.6a.8.8 0 0 0 1.2.7l8.8-5.8a.8.8 0 0 0 0-1.4l-8.8-5.8a.8.8 0 0 0-1.2.7z\"/>",
    "pause": "<rect x=\"5.5\" y=\"4\" width=\"4.6\" height=\"16\" rx=\"1.2\"/><rect x=\"13.9\" y=\"4\" width=\"4.6\" height=\"16\" rx=\"1.2\"/>",
    "play": "<path d=\"M7 4.2v15.6a1 1 0 0 0 1.5.9l12.4-7.8a1 1 0 0 0 0-1.8L8.5 3.3A1 1 0 0 0 7 4.2z\"/>",
    "previous": "<g transform=\"matrix(-1 0 0 1 24 0)\"><path d=\"M2.5 6.2v11.6a.8.8 0 0 0 1.2.7l8.8-5.8a.8.8 0 0 0 0-1.4L3.7 5.5a.8.8 0 0 0-1.2.7z\"/><path d=\"M11.5 6.2v11.6a.8.8 0 0 0 1.2.7l8.8-5.8a.8.8 0 0 0 0-1.4l-8.8-5.8a.8.8 0 0 0-1.2.7z\"/></g>",
    "screenshot": "<path d=\"M3 8V5.5A2.5 2.5 0 0 1 5.5 3H8M16 3h2.5A2.5 2.5 0 0 1 21 5.5V8M21 16v2.5a2.5 2.5 0 0 1-2.5 2.5H16M8 21H5.5A2.5 2.5 0 0 1 3 18.5V16\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"1.9\"/><g transform=\"translate(12 12.4) scale(1.35) translate(-12 -12.4)\"><path fill-rule=\"evenodd\" d=\"M8.2 10.2h1.6l1-1.4h2.4l1 1.4h1.6c.6 0 1 .4 1 1v4c0 .6-.4 1-1 1H8.2c-.6 0-1-.4-1-1v-4c0-.6.4-1 1-1zM10.4 13.2a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0-3.2 0z\"/></g>",
    "speaker-high": "<path d=\"M2.5 9h3.6L11 4.8v14.4L6.1 15H2.5z\"/><path d=\"M14.2 9.3a4 4 0 0 1 0 5.4\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"1.8\"/><path d=\"M16.8 6.6a8 8 0 0 1 0 10.8\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"1.8\"/><path d=\"M19.4 4a11.7 11.7 0 0 1 0 16\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"1.8\"/>",
    "speaker-low": "<path d=\"M3.5 9h3.6L12 4.8v14.4L7.1 15H3.5z\"/><path d=\"M15.2 9.3a4 4 0 0 1 0 5.4\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"1.8\"/>",
    "stage": "<rect x=\"8.5\" y=\"5\" width=\"13\" height=\"14\" rx=\"2.2\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"1.8\"/><rect x=\"2.5\" y=\"6\" width=\"3.6\" height=\"3.4\" rx=\"1\"/><rect x=\"2.5\" y=\"10.3\" width=\"3.6\" height=\"3.4\" rx=\"1\"/><rect x=\"2.5\" y=\"14.6\" width=\"3.6\" height=\"3.4\" rx=\"1\"/>",
    "sun-high": "<circle cx=\"12\" cy=\"12\" r=\"4.4\"/><path d=\"M19.00 12.00L22.20 12.00\" fill=\"none\" stroke=\"#000\" stroke-width=\"2.0\" stroke-linecap=\"round\"/><path d=\"M16.95 16.95L19.21 19.21\" fill=\"none\" stroke=\"#000\" stroke-width=\"2.0\" stroke-linecap=\"round\"/><path d=\"M12.00 19.00L12.00 22.20\" fill=\"none\" stroke=\"#000\" stroke-width=\"2.0\" stroke-linecap=\"round\"/><path d=\"M7.05 16.95L4.79 19.21\" fill=\"none\" stroke=\"#000\" stroke-width=\"2.0\" stroke-linecap=\"round\"/><path d=\"M5.00 12.00L1.80 12.00\" fill=\"none\" stroke=\"#000\" stroke-width=\"2.0\" stroke-linecap=\"round\"/><path d=\"M7.05 7.05L4.79 4.79\" fill=\"none\" stroke=\"#000\" stroke-width=\"2.0\" stroke-linecap=\"round\"/><path d=\"M12.00 5.00L12.00 1.80\" fill=\"none\" stroke=\"#000\" stroke-width=\"2.0\" stroke-linecap=\"round\"/><path d=\"M16.95 7.05L19.21 4.79\" fill=\"none\" stroke=\"#000\" stroke-width=\"2.0\" stroke-linecap=\"round\"/>",
    "sun-low": "<circle cx=\"12\" cy=\"12\" r=\"3.6\"/><path d=\"M18.20 12.00L19.60 12.00\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.6\" stroke-linecap=\"round\"/><path d=\"M16.38 16.38L17.37 17.37\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.6\" stroke-linecap=\"round\"/><path d=\"M12.00 18.20L12.00 19.60\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.6\" stroke-linecap=\"round\"/><path d=\"M7.62 16.38L6.63 17.37\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.6\" stroke-linecap=\"round\"/><path d=\"M5.80 12.00L4.40 12.00\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.6\" stroke-linecap=\"round\"/><path d=\"M7.62 7.62L6.63 6.63\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.6\" stroke-linecap=\"round\"/><path d=\"M12.00 5.80L12.00 4.40\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.6\" stroke-linecap=\"round\"/><path d=\"M16.38 7.62L17.37 6.63\" fill=\"none\" stroke=\"#000\" stroke-width=\"1.6\" stroke-linecap=\"round\"/>",
    "wifi": "<path d=\"M2.6 9.2a13.3 13.3 0 0 1 18.8 0\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2.3\"/><path d=\"M5.9 12.6a8.6 8.6 0 0 1 12.2 0\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2.3\"/><path d=\"M9.2 16a3.9 3.9 0 0 1 5.6 0\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2.3\"/><circle cx=\"12\" cy=\"19.4\" r=\"1.7\"/>",
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
