/*
    MacTahoe Liquid KDE — Energy Mode in the Battery menu: power-profiles-daemon's
    profiles (power-saver, balanced, performance), named Low Power,
    Automatic and High Power. A grey battery disc beside the active mode;
    click the row to reveal the supported choices.

    Loaded by BatteryView.qml: without Plasma's batterymonitor module or
    the daemon, the Battery menu just has no Energy Mode.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.kirigami as Kirigami
import org.kde.ki18n as KI18n
import org.kde.plasma.private.batterymonitor as BatteryMonitor

Column {
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.battery"
    }
    function i18nc(context, text) {
        return widgetI18n.i18nc(context, text);
    }

    id: energy

    readonly property var stops: ["power-saver", "balanced", "performance"]
    readonly property bool available: control.isPowerProfileDaemonInstalled && control.profiles.length > 0
    readonly property int current: Math.max(0, stops.indexOf(control.activeProfile || control.configuredProfile))
    readonly property color dim: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                         Kirigami.Theme.textColor.b, 0.45)

    property bool expanded: false
    onVisibleChanged: if (!visible) expanded = false
    function modeName(index: int): string {
        return index === 0 ? i18nc("@option energy mode", "Low Power")
             : index === 2 ? i18nc("@option energy mode", "High Power")
                           : i18nc("@option energy mode", "Automatic");
    }

    spacing: 6
    visible: available

    function choose(index: int): void {
        const profile = stops[Math.max(0, Math.min(2, index))];
        if (control.profiles.indexOf(profile) >= 0 && profile !== control.configuredProfile) {
            control.setProfile(profile);
        }
    }

    BatteryMonitor.PowerProfilesControl {
        id: control
        isSilent: true
    }

    Text {
        text: energy.i18nc("@title Battery menu section", "Energy Mode")
        color: energy.dim
        font.family: Kirigami.Theme.defaultFont.family
        font.pointSize: Kirigami.Theme.defaultFont.pointSize
        font.weight: Font.Bold
    }

    Rectangle {
        id: modeRow
        width: parent.width
        height: Math.max(28, modeLabel.implicitHeight + 8)
        radius: 8
        color: modeArea.containsMouse ? Qt.rgba(Kirigami.Theme.textColor.r,
                    Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.06) : "transparent"
        Rectangle {
            width: 26
            height: 26
            radius: 13
            anchors.verticalCenter: parent.verticalCenter
            color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                           Kirigami.Theme.textColor.b, 0.07)
            BatteryGlyph {
                anchors.centerIn: parent
                scale: 0.65
                percent: 25
                color: energy.dim
            }
        }
        Text {
            id: modeLabel
            x: 34
            width: parent.width - x
            anchors.verticalCenter: parent.verticalCenter
            text: energy.modeName(energy.current)
            color: Kirigami.Theme.textColor
            font: Kirigami.Theme.defaultFont
            elide: Text.ElideRight
        }
        MouseArea {
            id: modeArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: energy.expanded = !energy.expanded
        }
    }
    // Reveal only profiles this machine supports; never select a missing stop.
    Column {
        width: parent.width
        visible: energy.expanded
        Repeater {
            model: energy.stops
            delegate: Rectangle {
                required property int index
                required property string modelData
                width: energy.width
                height: 26
                visible: control.profiles.indexOf(modelData) >= 0
                radius: 8
                color: choiceArea.containsMouse ? Kirigami.Theme.highlightColor : "transparent"
                Text {
                    x: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: (energy.current === index ? "✓  " : "    ") + energy.modeName(index)
                    color: choiceArea.containsMouse ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                    font: Kirigami.Theme.defaultFont
                }
                MouseArea {
                    id: choiceArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: { energy.choose(index); energy.expanded = false; }
                }
            }
        }
    }

    // Why a mode is held back (an app holds a profile, or the laptop is hot).
    Text {
        width: parent.width
        visible: text.length > 0
        text: {
            switch (control.degradationReason) {
            case "lap-detected":
                return energy.i18nc("@info", "High Power is limited: the computer may be on your lap.");
            case "high-operating-temperature":
                return energy.i18nc("@info", "High Power is limited: the computer is running hot.");
            case "":
                break;
            default:
                return energy.i18nc("@info", "High Power is limited for now.");
            }
            return control.inhibitionReason.length > 0
                ? energy.i18nc("@info", "High Power is unavailable for now.") : "";
        }
        color: energy.dim
        font: Kirigami.Theme.defaultFont
        wrapMode: Text.Wrap
    }
}
