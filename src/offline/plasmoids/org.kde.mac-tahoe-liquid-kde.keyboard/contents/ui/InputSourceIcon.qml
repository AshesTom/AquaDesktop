/*
    AquaDesktop — the macOS input source icon: the layout's letters cut out
    of a white rounded box, like the template icons macOS draws in the menu
    bar ("A" for ABC). Measured at 1x on the reference capture: a 20 x 18 px
    box with 5 px corners, the letters bold with a 9 px cap height; longer
    labels widen the box.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.kirigami as Kirigami

Canvas {
    id: icon

    property string label: "A"
    property color color: "white"

    readonly property int boxHeight: 18
    readonly property int minimumWidth: 20
    readonly property int sidePadding: 4
    readonly property real radius: 5
    // A 9 px cap height in the system font.
    readonly property int pixelSize: 13
    readonly property real capHeight: 9

    TextMetrics {
        id: metrics
        font.family: Kirigami.Theme.defaultFont.family
        font.pixelSize: icon.pixelSize
        font.weight: Font.Bold
        text: icon.label
    }

    implicitWidth: Math.max(minimumWidth, Math.ceil(metrics.advanceWidth) + 2 * sidePadding)
    implicitHeight: boxHeight

    onLabelChanged: requestPaint()
    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()

    function roundRect(c, x: real, y: real, w: real, h: real, r: real): void {
        c.beginPath();
        c.moveTo(x + r, y);
        c.arcTo(x + w, y, x + w, y + h, r);
        c.arcTo(x + w, y + h, x, y + h, r);
        c.arcTo(x, y + h, x, y, r);
        c.arcTo(x, y, x + w, y, r);
        c.closePath();
    }

    onPaint: {
        const c = getContext("2d");
        c.reset();
        c.fillStyle = Qt.rgba(color.r, color.g, color.b, 1);
        roundRect(c, 0, 0, width, height, radius);
        c.fill();

        // The letters show what lies behind the menu bar.
        c.globalCompositeOperation = "destination-out";
        // The system font; Context2D keeps the generic one when it refuses
        // a family (Qt's "Sans Serif" alias outside Plasma).
        c.font = "bold " + pixelSize + "px sans-serif";
        c.font = "bold " + pixelSize + "px \"" + metrics.font.family + "\"";
        c.textAlign = "center";
        c.textBaseline = "alphabetic";
        c.fillStyle = "black";
        // Capitals 5 px under the top, 4 px over the bottom.
        c.fillText(label, width / 2, height / 2 + capHeight / 2 + 0.5);
        c.globalCompositeOperation = "source-over";
    }
}
