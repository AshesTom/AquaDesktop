/*
    SPDX-FileCopyrightText: 2018-2019 Kai Uwe Broulik <kde@privat.broulik.de>
    SPDX-FileCopyrightText: 2024 Marco Martin <mart@kde.org>
    SPDX-FileCopyrightText: 2026 MacTahoe Liquid KDE contributors

    SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/

/*
    MacTahoe Liquid KDE — a macOS Tahoe notification banner.

    Measured on a macOS capture at 1x: the app icon (32 px) sits 13 px from
    the banner's left edge, vertically centred; the text starts 13 px after
    it, with the title in bold over the body, both 13 px, 15 px above the
    first line and 14 px below the last. There is no header row (app name, time,
    buttons) and no timeout bar: hovering the banner shows a round close
    button in its top-left corner, like macOS.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.plasma.components as PlasmaComponents3
import org.kde.kirigami as Kirigami
import org.kde.kquickcontrolsaddons as KQuickControlsAddons

import org.kde.notificationmanager as NotificationManager

import "../components" as Components


BaseDelegate {
    id: delegateRoot

    Layout.preferredWidth: (footerLoader.item as Item)?.implicitWidth ?? -1

    body: bodyLabel
    icon: icon
    footer: footerLoader.item as Item
    columns: 2
    columnSpacing: 13

    Accessible.role: Accessible.Notification

    // macOS spacing, measured from the banner's outer edge; the window frame
    // already accounts for its own padding.
    readonly property int edgeInset: 13
    // 15 px above the first line's ink and 14 px below the last one, once
    // the font's own leading is taken out.
    readonly property int topInset: 13
    readonly property int bottomInset: 12

    HoverHandler {
        id: hover
    }

    Components.Icon {
        id: icon
        Layout.row: 0
        Layout.column: 0
        Layout.rowSpan: 3
        Layout.alignment: Qt.AlignVCenter
        Layout.leftMargin: delegateRoot.edgeInset - delegateRoot.modelInterface.popupLeftPadding
        Layout.preferredWidth: 32
        Layout.preferredHeight: 32
        implicitWidth: 32
        implicitHeight: 32
        modelInterface: delegateRoot.modelInterface
        // The app icon stands in when the notification brings no image of
        // its own; macOS always shows one.
        source: modelInterface.icon || modelInterface.applicationIconSource
        visible: true
    }

    Components.Summary {
        id: summary
        Layout.row: 0
        Layout.column: 1
        Layout.fillWidth: true
        Layout.topMargin: delegateRoot.topInset - delegateRoot.modelInterface.popupTopPadding
        Layout.rightMargin: delegateRoot.edgeInset - delegateRoot.modelInterface.popupRightPadding
        modelInterface: delegateRoot.modelInterface
        level: 5
        font.pixelSize: 13
        font.weight: Font.Bold
        maximumLineCount: 2

        KQuickControlsAddons.MouseEventListener {
            anchors.fill: parent
            visible: delegateRoot.modelInterface.hasDefaultAction && !delegateRoot.hasBodyText
            onClicked: delegateRoot.modelInterface.defaultActionInvoked();
        }
    }

    KQuickControlsAddons.MouseEventListener {
        Layout.row: 1
        Layout.column: 1
        Layout.fillWidth: true
        Layout.topMargin: summary.visible ? 0 : delegateRoot.topInset - delegateRoot.modelInterface.popupTopPadding
        Layout.rightMargin: delegateRoot.edgeInset - delegateRoot.modelInterface.popupRightPadding
        Layout.bottomMargin: footerLoader.item ? 0 : delegateRoot.bottomInset - delegateRoot.modelInterface.popupBottomPadding
        // macOS shows four lines in a banner.
        Layout.maximumHeight: bodyLabel.fontMetrics.lineSpacing * 4 + 2
        // The body doesn't need to influence the implicit width in any way, this avoids a binding loop
        implicitWidth: -1
        implicitHeight: Math.min(bodyLabel.implicitHeight, Layout.maximumHeight)
        visible: delegateRoot.hasBodyText
        clip: true
        onClicked: {
            if (delegateRoot.modelInterface.hasDefaultAction && !delegateRoot.hoveredLink) {
                delegateRoot.modelInterface.defaultActionInvoked();
            }
        }

        Components.Body {
            id: bodyLabel
            readonly property FontMetrics fontMetrics: FontMetrics { font: bodyLabel.font }
            width: parent.width
            font.pixelSize: 13
            modelInterface: delegateRoot.modelInterface
            Accessible.ignored: true // ignore HTML body in favor of Accessible.description on delegateRoot
        }
    }

    // Keeps the bottom inset when there is a title but no body.
    Item {
        Layout.row: 2
        Layout.column: 1
        visible: !delegateRoot.hasBodyText && !footerLoader.item
        implicitHeight: Math.max(0, delegateRoot.bottomInset - delegateRoot.modelInterface.popupBottomPadding)
    }

    Components.FooterLoader {
        id: footerLoader
        Layout.row: 3
        Layout.column: 1
        Layout.fillWidth: true
        Layout.rightMargin: delegateRoot.edgeInset - delegateRoot.modelInterface.popupRightPadding
        Layout.bottomMargin: delegateRoot.bottomInset - delegateRoot.modelInterface.popupBottomPadding
        modelInterface: delegateRoot.modelInterface
        iconContainerItem: icon
    }

    // macOS: a round close button in the top-left corner while hovered.
    Rectangle {
        id: closeButton
        parent: delegateRoot
        x: 4 - delegateRoot.modelInterface.popupLeftPadding
        y: 4 - delegateRoot.modelInterface.popupTopPadding
        z: 10
        width: 18
        height: 18
        radius: 9
        visible: delegateRoot.modelInterface.closable && (hover.hovered || closeArea.containsMouse)
        color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                       Kirigami.Theme.backgroundColor.b, 0.95)
        border.width: 1
        border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                              Kirigami.Theme.textColor.b, 0.18)

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -1
            text: "×"
            color: Kirigami.Theme.textColor
            opacity: closeArea.pressed ? 0.5 : 0.8
            font.pixelSize: 15
            font.weight: Font.DemiBold
        }

        MouseArea {
            id: closeArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: delegateRoot.modelInterface.closeClicked()
        }

        Accessible.role: Accessible.Button
        Accessible.name: i18nd("plasma_applet_org.kde.plasma.notifications", "Close")
    }
}
