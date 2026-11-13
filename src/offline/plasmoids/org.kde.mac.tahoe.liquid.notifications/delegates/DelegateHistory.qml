/*
    SPDX-FileCopyrightText: 2018-2019 Kai Uwe Broulik <kde@privat.broulik.de>
    SPDX-FileCopyrightText: 2024 Marco Martin <mart@kde.org>
    SPDX-FileCopyrightText: 2026 MacTahoe Liquid KDE contributors

    SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/

/*
    MacTahoe Liquid KDE — a notification of the history, laid out like the macOS
    banner (DelegatePopup.qml) it was: the 32 px app icon 13 px from the
    card's left edge, the bold title over the body (13 px, four lines at
    most), the age on the right of the title. The card around it, its
    buttons and the group stack belong to FullRepresentation.qml.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.kquickcontrolsaddons as KQuickControlsAddons

import "../components" as Components


BaseDelegate {
    id: delegateRoot

    body: bodyLabel
    icon: icon
    footer: footerLoader.item as Item
    columns: 2
    columnSpacing: 13

    readonly property int edgeInset: 13
    readonly property int topInset: 12
    readonly property int bottomInset: 12
    // The card's hover buttons take the age's place.
    property bool showAge: true

    Components.Icon {
        id: icon
        Layout.row: 0
        Layout.column: 0
        Layout.rowSpan: 2
        Layout.alignment: Qt.AlignVCenter
        Layout.leftMargin: delegateRoot.edgeInset
        Layout.topMargin: delegateRoot.topInset
        Layout.bottomMargin: footerLoader.item ? 0 : delegateRoot.bottomInset
        Layout.preferredWidth: 32
        Layout.preferredHeight: 32
        implicitWidth: 32
        implicitHeight: 32
        modelInterface: delegateRoot.modelInterface
        // macOS always shows an icon: the app's when the notification
        // brings no image of its own.
        source: modelInterface.icon || modelInterface.applicationIconSource
        visible: true
    }

    RowLayout {
        Layout.row: 0
        Layout.column: 1
        Layout.fillWidth: true
        Layout.topMargin: delegateRoot.topInset
        Layout.rightMargin: delegateRoot.edgeInset
        spacing: Kirigami.Units.smallSpacing

        // Its text only: it knows the job states and drops a summary that
        // repeats the app name.
        Components.Summary {
            id: summarySource
            visible: false
            modelInterface: delegateRoot.modelInterface
        }

        Kirigami.Heading {
            id: title
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            level: 5
            font.pixelSize: 13
            font.weight: Font.Bold
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
            text: summarySource.text || delegateRoot.modelInterface.applicationName
        }

        Components.HeadingButtons {
            Layout.alignment: Qt.AlignRight | Qt.AlignTop
            visible: delegateRoot.showAge
            modelInterface: delegateRoot.modelInterface
            showButtons: false
        }
    }

    KQuickControlsAddons.MouseEventListener {
        Layout.row: 1
        Layout.column: 1
        Layout.fillWidth: true
        Layout.rightMargin: delegateRoot.edgeInset
        Layout.bottomMargin: footerLoader.item ? 0 : delegateRoot.bottomInset
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
        Layout.row: 1
        Layout.column: 1
        visible: !delegateRoot.hasBodyText
        implicitHeight: footerLoader.item ? 0 : delegateRoot.bottomInset
    }

    Components.FooterLoader {
        id: footerLoader
        Layout.row: 2
        Layout.column: 1
        Layout.fillWidth: true
        Layout.rightMargin: delegateRoot.edgeInset
        Layout.bottomMargin: delegateRoot.bottomInset
        modelInterface: delegateRoot.modelInterface
        iconContainerItem: icon
    }
}
