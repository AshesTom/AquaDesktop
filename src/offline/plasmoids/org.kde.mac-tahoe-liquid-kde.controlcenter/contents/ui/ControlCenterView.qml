/*
    AquaDesktop — Control Center panel.

    The macOS Tahoe Control Center grid, matched to ~/Downloads/tahoe.jpg:
    four 64 px cells 12 px apart (292 px). Wi-Fi and Now Playing lead;
    Bluetooth and AirDrop are round controls, then Focus, Stage Manager,
    Screen Mirroring, Display, Sound, and the compact utility row. There is
    no panel behind the modules:
    each one is its own glass bubble (Tile, CircleButton) floating under
    the menu bar. Every module that talks to a Plasma backend lives in its
    own file and is loaded with a Loader, so a missing optional module (no
    Bluetooth stack, no plasma-pa, ...) only dims that module instead of
    breaking the whole panel.

    This item uses no Plasmoid API, so it can also be rendered on its own.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.workspace.dbus as DBus
import "Palette.js" as Palette
import org.kde.ki18n as KI18n

Item {
    // Translations from this widget's catalog in any host: Plasma, or the
    // AquaDesktop shell (Quickshell has no KLocalizedContext).
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.controlcenter"
    }
    function i18nc(context, text, arg1, arg2) {
        if (arg1 === undefined) {
            return widgetI18n.i18nc(context, text);
        }
        return arg2 === undefined ? widgetI18n.i18nc(context, text, arg1)
                                  : widgetI18n.i18nc(context, text, arg1, arg2);
    }
    function i18n(text, arg1) {
        return arg1 === undefined ? widgetI18n.i18n(text) : widgetI18n.i18n(text, arg1);
    }

    id: view

    // The accent itself, in Plasma as in Quickshell (see AccentColor.qml);
    // every child inherits it.
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
    // macOS Tahoe draws the Control Center in white on clear glass, in
    // light and dark mode alike (Apple's Control Center image).
    Binding {
        target: view.Kirigami.Theme
        property: "textColor"
        value: "#ffffff"
        restoreMode: Binding.RestoreBindingOrValue
    }
    // The host's own colours, for the system's appearance.
    Item {
        id: host
        Kirigami.Theme.inherit: false
    }

    property bool showEditControls: true
    // The menu bar's other status items (the tray's menu): the bar shows
    // no overflow arrow, as on macOS, so they are reached from here.
    property bool showStatusItems: false

    signal runCommand(string command)
    signal closeRequested()
    signal editControlsRequested()
    signal statusItemsRequested()

    readonly property int cell: 64
    readonly property int gap: 12
    readonly property int sliderHeight: 64
    // The system's appearance (the Dark Mode toggle), not the text's.
    readonly property bool dark: Palette.isDark(host.Kirigami.Theme.textColor)

    function span(cells: int): int {
        return cells * cell + (cells - 1) * gap;
    }

    function pos(index: int): int {
        return index * (cell + gap);
    }

    function launch(command: string): void {
        if (command.length > 0) {
            closeRequested();
            runCommand(command);
        }
    }

    function invokeKWinShortcut(name: string): void {
        closeRequested();
        DBus.SessionBus.asyncCall({
            service: "org.kde.kglobalaccel",
            path: "/component/kwin",
            iface: "org.kde.kglobalaccel.Component",
            member: "invokeShortcut",
            arguments: [name],
            signature: "(s)",
        });
    }

    implicitWidth: span(4)
    implicitHeight: grid.height + (statusItems.visible ? statusItems.height + gap : 0)
                    + (editButton.visible ? editButton.height + gap : 0)

    Item {
        id: grid

        // The supplied Tahoe capture: modules, two sliders, then utilities.
        readonly property int displayY: view.pos(3)
        readonly property int soundY: view.pos(4)
        readonly property int utilitiesY: view.pos(5)

        width: view.span(4)
        height: utilitiesY + view.cell

        // Wi-Fi and Now Playing, with the two round controls below Wi-Fi.
        ModuleLoader {
            x: 0; y: 0
            width: view.span(2); height: view.cell
            source: "WifiTile.qml"
            fallbackGlyph: "wifi"
            onLoaded: item.openSettings.connect(() => view.launch("systemsettings kcm_networkmanagement"))
        }
        ModuleLoader {
            x: view.pos(2); y: 0
            width: view.span(2); height: view.span(2)
            source: "NowPlayingTile.qml"
        }
        ModuleLoader {
            x: 0; y: view.pos(1)
            width: view.cell; height: view.cell
            source: "BluetoothTile.qml"
            fallbackGlyph: "bluetooth"
            round: true
        }
        ModuleLoader {
            x: view.pos(1); y: view.pos(1)
            width: view.cell; height: view.cell
            source: "AirDropTile.qml"
            fallbackGlyph: "airdrop"
            round: true
            onLoaded: item.openSettings.connect(() => view.launch("systemsettings kcm_bluetooth"))
        }

        // Focus, Stage Manager and Screen Mirroring share the third tile row.
        ModuleLoader {
            x: 0; y: view.pos(2)
            width: view.span(2); height: view.cell
            source: "FocusTile.qml"
            fallbackGlyph: "moon"
            onLoaded: item.openSettings.connect(() => view.launch("systemsettings kcm_notifications"))
        }
        CircleButton {
            x: view.pos(2); y: view.pos(2)
            width: view.cell; height: view.cell
            glyph: "stage"
            toolTip: i18nc("@action:button", "Stage Manager")
            onClicked: view.invokeKWinShortcut("Overview")
        }
        CircleButton {
            x: view.pos(3); y: view.pos(2)
            width: view.cell; height: view.cell
            glyph: "mirroring"
            toolTip: i18nc("@action:button", "Screen Mirroring")
            onClicked: {
                view.closeRequested();
                DBus.SessionBus.asyncCall({
                    service: "org.kde.kscreen.osdService",
                    path: "/org/kde/kscreen/osdService",
                    iface: "org.kde.kscreen.osdService",
                    member: "showActionSelector",
                    arguments: [],
                    signature: "",
                });
            }
        }
        ModuleLoader {
            x: 0; y: grid.displayY
            width: view.span(4); height: view.sliderHeight
            source: "DisplayTile.qml"
        }
        ModuleLoader {
            x: 0; y: grid.soundY
            width: view.span(4); height: view.sliderHeight
            source: "SoundTile.qml"
            onLoaded: item.openSettings.connect(() => view.launch("systemsettings kcm_pulseaudio"))
        }

        // Tahoe's bottom row: appearance, Calculator, Timer, Screenshot.
        CircleButton {
            x: 0; y: grid.utilitiesY
            width: view.cell; height: view.cell
            glyph: "contrast"
            toolTip: i18nc("@action:button", "Dark Mode")
            active: view.dark
            onClicked: view.launch("\"$HOME/.local/bin/mac-tahoe-theme-switch\" "
                + (view.dark ? "light" : "dark"))
        }
        CircleButton {
            x: view.pos(1); y: grid.utilitiesY
            width: view.cell; height: view.cell
            glyph: "calculator"
            toolTip: i18nc("@action:button", "Calculator")
            onClicked: view.launch("kcalc")
        }
        CircleButton {
            x: view.pos(2); y: grid.utilitiesY
            width: view.cell; height: view.cell
            glyph: "timer"
            toolTip: i18nc("@action:button", "Timer")
            onClicked: view.launch("kclock")
        }
        CircleButton {
            x: view.pos(3); y: grid.utilitiesY
            width: view.cell; height: view.cell
            glyph: "screenshot"
            toolTip: i18nc("@action:button", "Screenshot")
            onClicked: view.launch("spectacle --region")
        }
    }

    // A full-width bubble opening the tray's menu.
    Tile {
        id: statusItems

        anchors.top: grid.bottom
        anchors.topMargin: view.gap
        visible: view.showStatusItems
        width: view.span(4)
        height: 46
        hovered: statusArea.containsMouse

        Text {
            x: 18
            anchors.verticalCenter: parent.verticalCenter
            text: i18nc("@action:button", "Other Status Items")
            color: Kirigami.Theme.textColor
            font.weight: Font.Bold
            font.pixelSize: Palette.textSize
        }
        Text {
            anchors.right: parent.right
            anchors.rightMargin: 18
            anchors.verticalCenter: parent.verticalCenter
            text: "›"
            color: Kirigami.Theme.textColor
            opacity: 0.6
            font.pixelSize: 20
        }
        MouseArea {
            id: statusArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: view.statusItemsRequested()
        }
    }

    Rectangle {
        id: editButton

        anchors {
            top: statusItems.visible ? statusItems.bottom : grid.bottom
            topMargin: view.gap
            horizontalCenter: parent.horizontalCenter
        }
        visible: view.showEditControls
        // 21 px tall, 12 px text (measured on the capture).
        width: editLabel.implicitWidth + 24
        height: 21
        radius: height / 2
        readonly property real glassRadius: radius
        color: Palette.innerDisc(true, editArea.containsMouse)
        border.width: 1
        border.color: Palette.glassRimSide(true)

        Text {
            id: editLabel
            anchors.centerIn: parent
            text: i18nc("@action:button", "Edit Controls")
            color: Kirigami.Theme.textColor
            font.pixelSize: Palette.textSize - 1
        }
        MouseArea {
            id: editArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: view.editControlsRequested()
        }
    }

    // Loads a backend module; if its Plasma module is missing, shows the
    // same shape dimmed so the grid never gets holes.
    component ModuleLoader: Loader {
        id: moduleLoader

        property string fallbackGlyph
        property bool round: false

        asynchronous: false

        Loader {
            anchors.fill: parent
            active: moduleLoader.status === Loader.Error
            sourceComponent: moduleLoader.round ? roundFallback : tileFallback
        }

        Component {
            id: roundFallback
            CircleButton {
                glyph: moduleLoader.fallbackGlyph
                enabled: false
            }
        }
        Component {
            id: tileFallback
            Tile {
                // The corners of the module it stands in for.
                radius: moduleLoader.height > view.cell ? 30
                        : moduleLoader.width > view.span(2) ? 24 : height / 2
                opacity: 0.5
                Glyph {
                    anchors.centerIn: parent
                    width: 22
                    height: 22
                    glyph: moduleLoader.fallbackGlyph
                    visible: moduleLoader.fallbackGlyph.length > 0
                }
            }
        }
    }
}
