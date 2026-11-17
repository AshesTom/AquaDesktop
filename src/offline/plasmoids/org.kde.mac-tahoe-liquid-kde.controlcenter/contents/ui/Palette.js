/*
    MacTahoe Liquid KDE — Control Center colours, measured on a macOS Tahoe
    capture (dark, 1x) and mirrored for light mode.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
.pragma library

function isDark(textColor) {
    return (0.299 * textColor.r + 0.587 * textColor.g + 0.114 * textColor.b) > 0.5;
}

function tint(textColor, alpha) {
    return Qt.rgba(textColor.r, textColor.g, textColor.b, alpha);
}

// macOS Focus purple.
const focusColor = "#5e5ce6";

// Every module floats as its own bubble over the blurred desktop
// (GlassBlur asks KWin to blur behind each one), drawn by GlassSurface.qml.
// The 1 px rim of the smaller glass pills (Edit Controls).
function glassRimSide(dark) {
    return Qt.rgba(1, 1, 1, dark ? 0.24 : 0.60);
}

// A disc inside a tile (Focus off, no artwork): 66,68,72 on the capture.
function innerDisc(dark, hovered) {
    return dark ? Qt.rgba(1, 1, 1, hovered ? 0.32 : 0.25)
                : Qt.rgba(0, 0, 0, hovered ? 0.14 : 0.10);
}

// Slider track (71,70,82) and fill (242,242,244).
function trackColor(dark) {
    return dark ? Qt.rgba(1, 1, 1, 0.26) : Qt.rgba(0, 0, 0, 0.12);
}

const fillColor = "#f2f2f4";

// Module titles 13 px bold, states 11 px.
const textSize = 13;
const smallTextSize = 11;
