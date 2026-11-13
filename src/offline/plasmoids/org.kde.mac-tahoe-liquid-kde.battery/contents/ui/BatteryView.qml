/*
    MacTahoe Liquid KDE — Battery menu, measured on the supplied macOS capture at 2x.
    No Plasmoid API here, so the view also works outside Plasma.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami
import org.kde.ki18n as KI18n

Item {
    id: view
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.battery"
    }
    function i18nc(context, text, arg1) {
        return arg1 === undefined ? widgetI18n.i18nc(context, text) : widgetI18n.i18nc(context, text, arg1);
    }

    property real percent: 100
    property bool pluggedIn: false
    property bool charging: false
    property real remainingMs: 0
    // Unknown on hardware without charge-control support.
    property int chargeLimit: 0
    // Apps using significant energy, [{ name, icon }], highest first:
    // measured by the plasmoid (code/significant-energy.sh). Null while
    // unknown; the section shows only for a non-empty list.
    property var energyApplications: null
    signal closeRequested()
    signal runCommand(string command)

    readonly property color dim: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                         Kirigami.Theme.textColor.b, 0.45)
    implicitWidth: 280
    implicitHeight: column.implicitHeight

    function refresh(): void {
        if (energyLoader.item) energyLoader.item.expanded = false;
    }

    function duration(ms: real): string {
        const minutes = Math.round(ms / 60000);
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        return h > 0 ? widgetI18n.i18nc("@info hours and minutes", "%1 h %2 min", h, m)
                     : widgetI18n.i18nc("@info minutes", "%1 min", m);
    }

    readonly property string chargeStatus: {
        if (charging) {
            return chargeLimit > 0 && chargeLimit < 100
                ? i18nc("@info", "Charging to %1% Limit", chargeLimit)
                : i18nc("@info", "Charging to Full");
        }
        if (pluggedIn) {
            if (percent >= 100) return i18nc("@info", "Fully Charged");
            if (chargeLimit > 0 && chargeLimit < 100 && percent >= chargeLimit)
                return i18nc("@info", "Charged to %1% Limit", chargeLimit);
            return i18nc("@info", "Not Charging");
        }
        return remainingMs > 0 ? i18nc("@info", "%1 remaining", duration(remainingMs)) : "";
    }

    component Label: Text {
        width: column.width
        color: Kirigami.Theme.textColor
        font: Kirigami.Theme.defaultFont
        wrapMode: Text.Wrap
        textFormat: Text.PlainText
    }
    component Separator: Rectangle {
        width: column.width
        height: 1
        color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                       Kirigami.Theme.textColor.b, 0.10)
    }

    Column {
        id: column
        width: parent.width
        spacing: 6
        Label {
            text: view.i18nc("@title", "Battery")
            font.weight: Font.Bold
        }
        Column {
            width: parent.width
            spacing: 3
            Label {
                text: view.i18nc("@info", "Power Source: %1",
                                 view.pluggedIn ? view.i18nc("@info power source", "Power Adapter")
                                                : view.i18nc("@info power source", "Battery"))
                color: view.dim
            }
            Label {
                visible: text.length > 0
                text: view.chargeStatus
                color: view.dim
            }
        }
        Separator {
            visible: energyLoader.item !== null && energyLoader.item.available
        }
        Loader {
            id: energyLoader
            visible: item !== null && item.available
            width: parent.width
            height: item && item.available ? item.implicitHeight : 0
            source: "EnergyMode.qml"
            onLoaded: item.width = Qt.binding(() => width)
        }
        // Hidden, like macOS, while no app uses significant energy.
        Separator {
            visible: energySection.visible
        }
        Column {
            id: energySection
            visible: view.energyApplications !== null && view.energyApplications.length > 0
            width: parent.width
            spacing: 6
            Label {
                text: view.i18nc("@title Battery menu section", "Using Significant Energy")
                color: view.dim
                font.weight: Font.Bold
            }
            Repeater {
                model: view.energyApplications || []
                delegate: Row {
                    required property var modelData
                    width: column.width
                    spacing: 8
                    Kirigami.Icon {
                        width: 16
                        height: 16
                        source: modelData.icon || "application-x-executable"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: parent.width - 24
                        text: modelData.name
                        textFormat: Text.PlainText
                        color: Kirigami.Theme.textColor
                        font: Kirigami.Theme.defaultFont
                        elide: Text.ElideRight
                    }
                }
            }
        }
        Separator {}
        Rectangle {
            // Highlight extends around the aligned label, like a menu item.
            x: -6
            width: parent.width + 12
            height: Math.max(18, settingsLabel.implicitHeight + 2)
            radius: 8
            color: settingsArea.containsMouse ? Kirigami.Theme.highlightColor : "transparent"
            Text {
                id: settingsLabel
                x: 6
                width: parent.width - 12
                anchors.verticalCenter: parent.verticalCenter
                text: view.i18nc("@action", "Battery Settings…")
                color: settingsArea.containsMouse ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                font: Kirigami.Theme.defaultFont
                elide: Text.ElideRight
            }
            MouseArea {
                id: settingsArea
                anchors.fill: parent
                hoverEnabled: true
                onClicked: {
                    view.runCommand("systemsettings kcm_powerdevilprofilesconfig");
                    view.closeRequested();
                }
            }
        }
    }
}
