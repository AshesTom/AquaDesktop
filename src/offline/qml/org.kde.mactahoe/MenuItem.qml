/*
    AquaDesktop — macOS menu items for Kirigami / Qt Quick apps.

    org.kde.desktop's menu item without its icon column: macOS menus show
    only the label, with the shortcut right-aligned. The content row is
    upstream's (qqc2-desktop-style 6.x) minus the Kirigami.Icon; an icon an
    app sets on the item or its action is simply not drawn. QWidget menus
    get the same through kdeglobals' [KDE] ShowIconsInMenuItems=false
    (steps/kvantum.py).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.desktop as Desktop

Desktop.MenuItem {
    id: controlRoot

    contentItem: RowLayout {
        Item {
            Layout.preferredWidth: (controlRoot.ListView.view && controlRoot.ListView.view.hasCheckables) || controlRoot.checkable
                ? controlRoot.indicator.width : Kirigami.Units.smallSpacing
        }
        Desktop.Label {
            id: label
            Layout.alignment: Qt.AlignVCenter
            Layout.fillWidth: true

            text: controlRoot.Kirigami.MnemonicData.richTextLabel
            font: controlRoot.font
            color: controlRoot.pressed ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
            elide: Text.ElideRight
            visible: controlRoot.text
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
        }
        Desktop.Label {
            id: shortcut
            Layout.alignment: Qt.AlignVCenter
            visible: controlRoot.action && controlRoot.action.shortcut !== undefined

            Shortcut {
                id: itemShortcut
                sequence: (shortcut.visible && controlRoot.action !== null) ? controlRoot.action.shortcut : ""
            }

            text: visible ? itemShortcut.nativeText : ""
            font: controlRoot.font
            color: label.color
            opacity: 0.55
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
        }
        Item {
            Layout.preferredWidth: Kirigami.Units.smallSpacing
        }
    }
}
