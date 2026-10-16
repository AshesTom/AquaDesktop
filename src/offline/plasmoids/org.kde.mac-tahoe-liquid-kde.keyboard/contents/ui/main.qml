/*
    AquaDesktop — the macOS Input menu: the current keyboard layout's letters
    cut out of a white box in the menu bar (InputSourceIcon.qml), and the
    Input menu on click (KeyboardView.qml). Like macOS, it shows only while
    more than one layout is set up. Plasma's keyboard layout applet stays
    hidden in the tray.

    Layouts come from Plasma's KeyboardLayout (the keyboard kded module);
    the emoji picker is plasma-emojier, the keyboard viewer KDE's
    tastenbrett, the clipboard history Klipper's "Show Clipboard Items at
    Mouse Position" shortcut.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtCore
import QtQuick
import QtQuick.Layouts

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as P5Support
import org.kde.plasma.workspace.dbus as DBus
import org.kde.plasma.workspace.keyboardlayout as Keyboards
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    readonly property var layouts: keyboardLayout.layoutsList || []
    readonly property var currentLayout: layouts.length > 0 ? layouts[Math.min(keyboardLayout.layout, layouts.length - 1)]
                                                            : null
    // "fr" -> "FR"; a label set in Keyboard Settings is kept as typed.
    readonly property string label: !currentLayout ? ""
        : currentLayout.displayName ? currentLayout.displayName
        : String(currentLayout.shortName).toUpperCase()

    readonly property int popoverGap: 6
    // Transparent room above and below the glass (see the Wi-Fi menu):
    // the Glass effect rounds this window like a normal one.
    readonly property int glassPad: 28
    property double popoverHiddenAt: 0

    Plasmoid.status: layouts.length > 1 ? PlasmaCore.Types.ActiveStatus : PlasmaCore.Types.HiddenStatus
    Plasmoid.icon: "input-keyboard"
    // No tooltip: macOS shows none on its menu bar extras.
    toolTipMainText: ""
    toolTipSubText: ""

    preferredRepresentation: compactRepresentation
    fullRepresentation: Item {}

    Keyboards.KeyboardLayout {
        id: keyboardLayout
    }

    // The configured layouts' XKB names, for the keyboard viewer.
    Settings {
        id: kxkbrc
        location: StandardPaths.writableLocation(StandardPaths.GenericConfigLocation) + "/kxkbrc"
        category: "Layout"
    }
    // Klipper's shortcut ("Meta+V\tCtrl+Alt+V,Meta+V,Show Clipboard...").
    Settings {
        id: shortcuts
        location: StandardPaths.writableLocation(StandardPaths.GenericConfigLocation) + "/kglobalshortcutsrc"
        category: "plasmashell"
    }

    // [{name: "English (US)"}, ...] for the menu (a plain array: the
    // layouts are a C++ value-type list).
    function layoutNames(): var {
        const names = [];
        for (let i = 0; i < layouts.length; ++i) {
            names.push({name: layouts[i].longName || layouts[i].shortName});
        }
        return names;
    }

    function listValue(settings, key: string): var {
        const raw = settings.value(key, "");
        return Array.isArray(raw) ? raw : String(raw).split(",");
    }
    // XKB names only reach the shell command: letters, digits, _ + -.
    function xkbName(name): string {
        return String(name || "").replace(/[^A-Za-z0-9_+-]/g, "");
    }

    function keyboardViewerCommand(): string {
        kxkbrc.sync();
        const index = keyboardLayout.layout;
        const layout = xkbName(listValue(kxkbrc, "LayoutList")[index]) || xkbName(currentLayout && currentLayout.shortName);
        const variant = xkbName(listValue(kxkbrc, "VariantList")[index]);
        const model = xkbName(kxkbrc.value("Model", "")) || "pc105";
        let command = "tastenbrett --model " + model + " --layout " + layout;
        if (variant.length > 0) {
            command += " --variant " + variant;
        }
        // Without the viewer, its settings page.
        return command + " || systemsettings kcm_keyboard";
    }

    function clipboardShortcut(): string {
        shortcuts.sync();
        const entry = listValue(shortcuts, "show-on-mouse-pos");
        return entry.length > 0 && String(entry[0]).length > 0 ? String(entry[0]) : "Meta+V";
    }

    Connections {
        target: Plasmoid
        function onActivated(): void {
            root.togglePopover();
        }
    }

    function togglePopover(): void {
        if (popover.visible) {
            popover.visible = false;
            return;
        }
        if (Date.now() - popoverHiddenAt < 300) {
            return;
        }
        view.clipboardShortcut = clipboardShortcut();
        placePopover();
        popover.visible = true;
        popover.requestActivate();
    }

    // Below the item, its left edge on the item's like a macOS menu,
    // kept inside the screen.
    function placePopover(): void {
        const anchor = root.compactRepresentationItem;
        if (!anchor) {
            return;
        }
        const origin = anchor.mapToGlobal(0, 0);
        const screen = Plasmoid.containment.screenGeometry;
        const width = popover.width > 0 ? popover.width : view.implicitWidth;
        let x = Math.round(origin.x);
        x = Math.max(screen.x + popoverGap, Math.min(x, screen.x + screen.width - width - popoverGap));
        popover.x = x;
        popover.y = Math.round(origin.y + anchor.height + popoverGap) - glassPad;
    }

    compactRepresentation: MouseArea {
        id: compact

        Layout.minimumWidth: icon.implicitWidth + Kirigami.Units.smallSpacing * 4
        Layout.preferredWidth: Layout.minimumWidth
        Layout.fillHeight: true
        hoverEnabled: true
        onClicked: root.togglePopover()

        // Highlighted only while open, never on hover, like macOS.
        Rectangle {
            anchors.centerIn: parent
            width: parent.width
            height: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.smallSpacing * 2
            radius: Kirigami.Units.cornerRadius
            color: Qt.rgba(0.5, 0.5, 0.5, 0.25)
            visible: popover.visible
        }

        InputSourceIcon {
            id: icon
            anchors.centerIn: parent
            width: implicitWidth
            height: implicitHeight
            label: root.label
            // Pure white, like the other menu bar extras.
            color: "white"
        }
    }

    PlasmaCore.Dialog {
        id: popover

        location: PlasmaCore.Types.Floating
        backgroundHints: PlasmaCore.Dialog.NoBackground
        type: PlasmaCore.Dialog.PopupMenu
        flags: Qt.WindowStaysOnTopHint
        hideOnWindowDeactivate: true
        visible: false
        onVisibleChanged: if (!visible) root.popoverHiddenAt = Date.now()

        mainItem: Item {
            width: frame.width
            height: frame.height + 2 * root.glassPad

            // One glass panel, like the Wi-Fi menu.
            Item {
                id: frame

                readonly property real glassRadius: 14

                y: root.glassPad
                width: view.implicitWidth
                height: view.implicitHeight

                // The Liquid Glass face (GlassSurface.qml); KWin blurs behind it.
                GlassSurface {
                    anchors.fill: parent
                    z: -1
                    radius: frame.glassRadius
                }

                KeyboardView {
                    id: view
                    anchors.fill: parent
                    layouts: root.layoutNames()
                    current: keyboardLayout.layout
                    // KDE's default for the emoji picker (plasma-emojier).
                    emojiShortcut: "Meta+."
                    onCloseRequested: popover.visible = false
                    onLayoutRequested: index => keyboardLayout.layout = index
                    onEmojiRequested: executable.connectSource("plasma-emojier")
                    onKeyboardViewerRequested: executable.connectSource(root.keyboardViewerCommand())
                    onClipboardRequested: clipboardTimer.start()
                    onSettingsRequested: executable.connectSource("systemsettings kcm_keyboard")
                }
            }

            Loader {
                id: blurLoader
                source: "WindowBlur.qml"
                onLoaded: item.target = frame.parent
            }
            BlurSettler {
                active: popover.visible
                blur: blurLoader.item
            }
        }
    }

    // Klipper's menu opens at the pointer once this menu has closed
    // (closing it later would take the focus back from Klipper's).
    Timer {
        id: clipboardTimer
        interval: 200
        onTriggered: DBus.SessionBus.asyncCall({
            service: "org.kde.kglobalaccel",
            path: "/component/plasmashell",
            iface: "org.kde.kglobalaccel.Component",
            member: "invokeShortcut",
            arguments: ["show-on-mouse-pos"],
            signature: "(s)",
        })
    }

    P5Support.DataSource {
        id: executable
        engine: "executable"
        onNewData: (sourceName, data) => disconnectSource(sourceName)
    }
}
