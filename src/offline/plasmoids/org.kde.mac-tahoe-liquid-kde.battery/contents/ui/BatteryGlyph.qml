/*
    AquaDesktop — the macOS menu bar battery, drawn like macOS: a 23 x 12 px
    rounded body with a faint outline, the charge level 2 px inside it, a
    small nub on the right. While charging, a bolt as tall as the body
    stands over the level in the same colour, cut out of it by a thin
    transparent gap. The level turns red at 10 % or less.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

Canvas {
    id: glyph

    // 0..100
    property real percent: 100
    property bool charging: false
    property color color: "white"

    implicitWidth: 27
    implicitHeight: 14

    onPercentChanged: requestPaint()
    onChargingChanged: requestPaint()
    onColorChanged: requestPaint()

    function roundRect(c, x: real, y: real, w: real, h: real, r: real): void {
        c.beginPath();
        c.moveTo(x + r, y);
        c.arcTo(x + w, y, x + w, y + h, r);
        c.arcTo(x + w, y + h, x, y + h, r);
        c.arcTo(x, y + h, x, y, r);
        c.arcTo(x, y, x + w, y, r);
        c.closePath();
    }

    function bolt(c, cx: real, cy: real, h: real): void {
        const s = h / 14;
        c.beginPath();
        c.moveTo(cx + 1.6 * s, cy - 7 * s);
        c.lineTo(cx - 4.2 * s, cy + 1.2 * s);
        c.lineTo(cx - 0.4 * s, cy + 1.2 * s);
        c.lineTo(cx - 1.6 * s, cy + 7 * s);
        c.lineTo(cx + 4.2 * s, cy - 1.2 * s);
        c.lineTo(cx + 0.4 * s, cy - 1.2 * s);
        c.closePath();
    }

    onPaint: {
        const c = getContext("2d");
        c.reset();
        const ink = Qt.rgba(color.r, color.g, color.b, 1);
        const faint = Qt.rgba(color.r, color.g, color.b, 0.5);
        const x = 0.5, y = 1.5, w = 23, h = 11;

        // Outline and nub.
        c.lineWidth = 1;
        c.strokeStyle = faint;
        roundRect(c, x, y, w, h, 3.5);
        c.stroke();
        c.fillStyle = faint;
        roundRect(c, x + w + 1.5, y + 3.5, 1.5, 4, 0.75);
        c.fill();

        // The level.
        const level = Math.max(0, Math.min(100, percent)) / 100;
        if (level > 0) {
            c.fillStyle = percent <= 10 && !charging ? "#ff453a" : ink;
            roundRect(c, x + 2, y + 2, Math.max(2, (w - 4) * level), h - 4, 1.5);
            c.fill();
        }

        if (charging) {
            const cx = x + w / 2, cy = y + h / 2;
            // The gap around the bolt.
            c.globalCompositeOperation = "destination-out";
            c.lineWidth = 2.2;
            c.lineJoin = "round";
            bolt(c, cx, cy, 14);
            c.stroke();
            c.fill();
            c.globalCompositeOperation = "source-over";
            c.fillStyle = ink;
            bolt(c, cx, cy, 14);
            c.fill();
        }
    }
}
