/*
    AquaDesktop — KDE's accent colour itself ([General] AccentColor in
    kdeglobals), the macOS accent of the switches, selections and active
    buttons. Plasma's Kirigami theme gives the selection colour instead,
    which KDE derives darker from the accent; Quickshell's gives the accent.
    `valid` is false without a custom accent (Multicolour): the view then
    keeps the theme's highlight.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtCore
import QtQuick

import org.kde.kirigami as Kirigami

Item {
    visible: false
    // The host's own colours, whatever the view overrides.
    Kirigami.Theme.inherit: false

    // QSettings reads [General] as the file's top level: no category.
    Settings {
        id: kdeglobals
        location: StandardPaths.writableLocation(StandardPaths.GenericConfigLocation) + "/kdeglobals"
    }

    // "r,g,b" as numbers, or [] without a custom accent.
    readonly property var rgb: {
        // Read again on every palette change (a new accent is one).
        Kirigami.Theme.highlightColor;
        kdeglobals.sync();
        const raw = kdeglobals.value("AccentColor", "");
        const parts = (Array.isArray(raw) ? raw : String(raw).split(",")).map(Number);
        return parts.length === 3 && parts.every(n => n >= 0 && n <= 255) ? parts : [];
    }
    readonly property bool valid: rgb.length === 3
    readonly property color value: valid ? Qt.rgba(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1) : "transparent"
}
