/*
    MacTahoe Liquid KDE — the macOS Input menu: the keyboard layouts with a check
    mark on the current one, then Show Emoji & Symbols, Show Keyboard
    Viewer, Show Clipboard History and Open Keyboard Settings...

    Measured at 1x on the reference capture: 278 px wide, 24 px rows,
    6 px above the first row and below the last, separators 12 px tall
    with a 1 px line 14 px in from each side. The check mark sits 14 px in,
    the layouts' names 32 px in, the other entries 18 px in; shortcuts end
    16 px from the right edge, dimmed. The highlight is the accent, 6 px in
    from each side.

    No Plasmoid API here, so the view also works outside Plasma.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.kirigami as Kirigami
import org.kde.ki18n as KI18n

Item {
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.keyboard"
    }
    function i18nc(context, text) {
        return widgetI18n.i18nc(context, text);
    }

    id: view

    // The accent itself (see AccentColor.qml); every child inherits it.
    AccentColor {
        id: kdeAccent
    }
    Binding {
        target: view.Kirigami.Theme
        property: "highlightColor"
        value: kdeAccent.value
        when: kdeAccent.valid
        restoreMode: Binding.RestoreBindingOrValue
    }

    // [{name: "English (US)"}, ...] in KDE's order.
    property var layouts: []
    property int current: 0
    // KDE's shortcuts ("Meta+."), drawn the macOS way.
    property string emojiShortcut: ""
    property string clipboardShortcut: ""

    signal closeRequested()
    signal layoutRequested(int index)
    signal emojiRequested()
    signal keyboardViewerRequested()
    signal clipboardRequested()
    signal settingsRequested()

    readonly property int textSize: 13
    readonly property int rowHeight: 24
    readonly property int edgePadding: 6
    readonly property color dimmed: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                            Kirigami.Theme.textColor.b, 0.55)

    implicitWidth: Math.max(278, column.widest)
    implicitHeight: column.implicitHeight + 2 * edgePadding

    // "Ctrl+Shift+N" as macOS draws it, "⇧⌘N": modifiers in macOS order
    // (⌃⌥⇧⌘, Ctrl being Linux' ⌘, like the Kvantum engine's menus), then
    // the key. Only the first of several shortcuts; "" for none.
    function macShortcut(shortcut: string): string {
        const first = String(shortcut).split("\t")[0].trim();
        if (first.length === 0 || first === "none") {
            return "";
        }
        // "Meta++": the last "+" is the key.
        const parts = first.endsWith("++") ? first.slice(0, -2).split("+").concat("+") : first.split("+");
        const key = parts.pop();
        const glyphs = {Meta: "⌃", Alt: "⌥", Shift: "⇧", Ctrl: "⌘"};
        let mods = "";
        for (const name of ["Meta", "Alt", "Shift", "Ctrl"]) {
            if (parts.indexOf(name) >= 0) {
                mods += glyphs[name];
            }
        }
        const keys = {
            Space: i18nc("@item:keyboard the space bar, as macOS menus name it", "Space"),
            Return: "↩", Enter: "⌤", Tab: "⇥", Backspace: "⌫", Del: "⌦", Delete: "⌦",
            Esc: "⎋", Escape: "⎋", Left: "←", Right: "→", Up: "↑", Down: "↓",
        };
        return mods + (keys[key] !== undefined ? keys[key] : key.toUpperCase());
    }

    component Separator: Item {
        width: column.width
        height: 12
        Rectangle {
            x: 14
            y: 5
            width: parent.width - 28
            height: 1
            color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                           Kirigami.Theme.textColor.b, 0.15)
        }
    }

    // A menu entry, highlighted with the accent under the pointer.
    component MenuEntry: Item {
        id: entry

        property alias text: label.text
        property string shortcut: ""
        // Layouts: the check mark's column before the name.
        property bool checkable: false
        property bool checked: false
        readonly property bool highlighted: area.containsMouse
        readonly property int naturalWidth: label.x + label.implicitWidth
            + (shortcutLabel.text.length > 0 ? 24 + shortcutLabel.implicitWidth : 0) + 16

        signal triggered()

        width: column.width
        height: view.rowHeight

        Rectangle {
            x: view.edgePadding
            width: parent.width - 2 * view.edgePadding
            height: parent.height
            radius: 8
            color: entry.highlighted ? Kirigami.Theme.highlightColor : "transparent"
        }
        Text {
            x: 14
            anchors.verticalCenter: parent.verticalCenter
            visible: entry.checked
            text: "✓"
            color: label.color
            font.pixelSize: view.textSize
            font.weight: Font.Bold
        }
        Text {
            id: label
            x: entry.checkable ? 32 : 18
            anchors.verticalCenter: parent.verticalCenter
            color: entry.highlighted ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
            font.pixelSize: view.textSize
        }
        Text {
            id: shortcutLabel
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            text: view.macShortcut(entry.shortcut)
            color: entry.highlighted ? Kirigami.Theme.highlightedTextColor : view.dimmed
            font.pixelSize: view.textSize
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            onClicked: {
                entry.triggered();
                view.closeRequested();
            }
        }
    }

    Column {
        id: column

        // The widest entry, so long names or shortcuts widen the menu.
        readonly property real widest: {
            let widest = 0;
            for (let i = 0; i < children.length; ++i) {
                const child = children[i];
                if (child.visible && child.naturalWidth !== undefined) {
                    widest = Math.max(widest, child.naturalWidth);
                }
            }
            return widest;
        }

        y: view.edgePadding
        width: view.width

        Repeater {
            model: view.layouts
            delegate: MenuEntry {
                required property var modelData
                required property int index
                text: modelData.name
                checkable: true
                checked: index === view.current
                onTriggered: view.layoutRequested(index)
            }
        }

        Separator {
            visible: view.layouts.length > 0
        }

        MenuEntry {
            text: view.i18nc("@action Input menu", "Show Emoji & Symbols")
            shortcut: view.emojiShortcut
            onTriggered: view.emojiRequested()
        }
        MenuEntry {
            text: view.i18nc("@action Input menu", "Show Keyboard Viewer")
            onTriggered: view.keyboardViewerRequested()
        }
        MenuEntry {
            text: view.i18nc("@action Input menu", "Show Clipboard History")
            shortcut: view.clipboardShortcut
            onTriggered: view.clipboardRequested()
        }

        Separator {}

        MenuEntry {
            text: view.i18nc("@action Input menu", "Open Keyboard Settings…")
            onTriggered: view.settingsRequested()
        }
    }
}
