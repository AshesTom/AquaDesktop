/*
    SPDX-FileCopyrightText: 2020 Carson Black <uhhadd@gmail.com>
    SPDX-License-Identifier: GPL-2.0-or-later
*/

import QtQuick
import QtQuick.Controls

import org.kde.plasma.components as PC3
import org.kde.kirigami as Kirigami

AbstractButton {
    id: controlRoot

    // macOS menu titles use the regular weight; only the app name is bold.
    font.weight: Font.Normal
    font.pointSize: Kirigami.Theme.defaultFont.pointSize - 0.75
    property bool menuIsOpen: false

    signal activated()

    hoverEnabled: true

    onHoveredChanged: if (hovered && menuIsOpen) { activated(); }
    onPressed: activated()

    enum State {
        Rest,
        Hover,
        Down
    }

    property int menuState: {
        if (down) {
            return MenuDelegate.State.Down;
        } else if (hovered && !menuIsOpen) {
            return MenuDelegate.State.Hover;
        }
        return MenuDelegate.State.Rest;
    }

    Kirigami.MnemonicData.controlType: Kirigami.MnemonicData.SecondaryControl
    Kirigami.MnemonicData.label: text

    // Caps sit on rows 10-19 of the 30 px bar: optically centred, on the
    // clock's baseline.
    topPadding: Kirigami.Units.smallSpacing - 1
    bottomPadding: Kirigami.Units.smallSpacing - 2
    // ~20 px between titles, as in the macOS menu bar.
    leftPadding: Kirigami.Units.largeSpacing + Kirigami.Units.smallSpacing / 2
    rightPadding: Kirigami.Units.largeSpacing + Kirigami.Units.smallSpacing / 2

    Accessible.description: i18nc("@info:usagetip", "Open a menu")

    background: Rectangle {
        radius: Kirigami.Units.cornerRadius
        color: controlRoot.menuState === MenuDelegate.State.Rest
               ? "transparent"
               : Qt.rgba(0.5, 0.5, 0.5, controlRoot.menuState === MenuDelegate.State.Down ? 0.25 : 0.18)
    }

    contentItem: PC3.Label {
        text: controlRoot.Kirigami.MnemonicData.richTextLabel
        textFormat: Text.StyledText
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        color: Kirigami.Theme.textColor
        font: controlRoot.font
    }
}
