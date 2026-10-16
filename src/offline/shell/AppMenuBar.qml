/*
    AquaDesktop shell — the left half of the menu bar: the Apple menu, the
    active app's name in bold, then its menus (File, Edit, View…), as
    native menus under their titles.

    Loaded by MenuBar.qml: without the compiled appmenu module only the
    Apple logo shows.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.mac.tahoe.liquid.appmenu
import "views/globalmenu" as GlobalMenu

Row {
    id: row

    property color ink: "white"

    height: parent ? parent.height : 30

    function buttonFor(index: int): Item {
        if (index === -3) {
            return appleButton;
        }
        if (index === -2) {
            return appNameButton.visible ? appNameButton : null;
        }
        return titleRepeater.itemAt(index);
    }
    // Opens menu `index` (-3 Apple, -2 app name, else a title).
    function activate(index: int): void {
        const button = buttonFor(index);
        if (!button) {
            return;
        }
        if (index === -3) {
            appMenu.openAppleMenu(button);
        } else if (index === -2) {
            appMenu.openWindowMenu(button);
        } else {
            appMenu.open(index, button);
        }
    }

    AppMenu {
        id: appMenu
        buttonRow: row
        onRequestActivateIndex: index => row.activate(index)
        onAboutRequested: {
            about.show();
            about.raise();
            about.requestActivate();
        }
    }

    GlobalMenu.AboutWindow {
        id: about
        visible: false
    }

    // The Apple logo, 18 px from the screen edge (the bar's own margin
    // is 0 here, so the highlight can extend to the logo's sides).
    Title {
        id: appleButton
        buttonIndex: -3
        leftPadding: 8
        rightPadding: 11
        Image {
            anchors.verticalCenter: parent.verticalCenter
            x: appleButton.leftPadding
            source: "assets/apple-logo.svg"
            sourceSize: Qt.size(14, 17)
            width: 14
            height: 17
        }
        implicitContentWidth: 14
    }

    Title {
        id: appNameButton
        buttonIndex: -2
        text: appMenu.appName
        bold: true
        visible: text !== ""
    }

    Repeater {
        id: titleRepeater
        model: appMenu.titles
        delegate: Title {
            required property int index
            required property string modelData
            buttonIndex: index
            // Mnemonics ("&File") are for in-window menu bars.
            text: modelData.replace(/&(.)/g, "$1")
        }
    }

    // One menu title: 10 px on each side of its text (20 px between
    // titles, as on macOS), highlighted while its menu is open.
    component Title: MouseArea {
        id: title

        required property int buttonIndex
        property string text: ""
        property bool bold: false
        property real leftPadding: 10
        property real rightPadding: 10
        property real implicitContentWidth: label.implicitWidth
        readonly property bool open: appMenu.currentIndex === buttonIndex

        width: leftPadding + implicitContentWidth + rightPadding
        height: row.height
        hoverEnabled: true
        // Not accepted: the menu takes the release, so an accepted press
        // would leave the title pressed, deaf to the next press.
        onPressed: mouse => {
            row.activate(buttonIndex);
            mouse.accepted = false;
        }
        // Sliding along the bar with a menu open opens each one in turn.
        onContainsMouseChanged: {
            if (containsMouse && appMenu.currentIndex !== -1 && !open) {
                row.activate(buttonIndex);
            }
        }

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            height: 22
            radius: 6
            color: Qt.rgba(1, 1, 1, 0.22)
            visible: title.open
        }
        Text {
            id: label
            visible: title.text !== ""
            anchors.verticalCenter: parent.verticalCenter
            x: title.leftPadding
            text: title.text
            color: row.ink
            font.pixelSize: 13
            font.weight: title.bold ? Font.Bold : Font.Normal
        }
    }
}
