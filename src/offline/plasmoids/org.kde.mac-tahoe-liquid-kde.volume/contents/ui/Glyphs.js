/*
    MacTahoe Liquid KDE — sound menu glyphs, drawn on a 24 px grid (the Control
    Center's speaker, with 0 to 3 waves, or struck through when muted).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
.pragma library

const cone = "<path d=\"M2.5 9h3.6L11 4.8v14.4L6.1 15H2.5z\"/>";
function wave(d) {
    return "<path d=\"" + d + "\" fill=\"none\" stroke=\"#000\" stroke-linecap=\"round\" "
        + "stroke-linejoin=\"round\" stroke-width=\"1.8\"/>";
}
const waves = [wave("M14.2 9.3a4 4 0 0 1 0 5.4"), wave("M16.8 6.6a8 8 0 0 1 0 10.8"),
               wave("M19.4 4a11.7 11.7 0 0 1 0 16")];

const shapes = {
    "speaker-0": cone,
    "speaker-1": cone + waves[0],
    "speaker-2": cone + waves[0] + waves[1],
    "speaker-3": cone + waves[0] + waves[1] + waves[2],
    "speaker-muted": cone + wave("M15 9l5 6") + wave("M20 9l-5 6"),
};

function hex(v) {
    const s = Math.round(v * 255).toString(16);
    return s.length < 2 ? "0" + s : s;
}

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
