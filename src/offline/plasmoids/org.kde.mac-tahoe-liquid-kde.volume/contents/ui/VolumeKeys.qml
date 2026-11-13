/*
    MacTahoe Liquid KDE — the volume keys, heard on the session bus: KGlobalAccel
    tells its clients about a shortcut with the globalShortcutPressed
    signal of the component's object, here plasma-pa's "kmix" (the volume
    applet hidden in the tray changes the volume on the same signal). Kept
    in its own file, loaded by main.qml: without Plasma's D-Bus QML module
    only the HUD is lost, not the menu bar extra.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.plasma.workspace.dbus as DBus

Item {
    id: keys

    // A volume or mute key was pressed.
    signal pressed()

    readonly property var actions: ["increase_volume", "decrease_volume", "increase_volume_small",
                                    "decrease_volume_small", "mute"]

    DBus.SignalWatcher {
        service: "org.kde.kglobalaccel"
        path: "/component/kmix"
        iface: "org.kde.kglobalaccel.Component"

        // SignalWatcher calls "dbus" + the signal's name. The arguments
        // come as wrapped values, not JS strings: compare their text.
        function dbusglobalShortcutPressed(component, action, timestamp) {
            if (keys.actions.includes(String(action))) {
                keys.pressed();
            }
        }
    }
}
