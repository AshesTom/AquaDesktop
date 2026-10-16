/*
    AquaDesktop — asks GlassBlur again a few times after the popup shows:
    Plasma's Dialog rewrites the window's blur from its background hints
    when it maps, sometimes after GlassBlur's own passes.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

Item {
    id: settler

    // The popup is showing.
    property bool active: false
    property var blur: null
    // Since the previous pass (ms).
    readonly property var delays: [0, 60, 140, 300, 700, 1200]
    property int pass: 0

    onActiveChanged: {
        timer.stop();
        if (active) {
            pass = 0;
            timer.interval = delays[0];
            timer.start();
        }
    }

    Timer {
        id: timer
        repeat: false
        onTriggered: {
            if (settler.blur) {
                settler.blur.update();
            }
            settler.pass += 1;
            if (settler.active && settler.pass < settler.delays.length) {
                interval = settler.delays[settler.pass];
                start();
            }
        }
    }
}
