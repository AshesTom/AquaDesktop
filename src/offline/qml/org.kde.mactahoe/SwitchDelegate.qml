/*
    AquaDesktop — org.kde.desktop's SwitchDelegate with the macOS Tahoe
    indicator and selection.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Templates as T
import org.kde.kirigami as Kirigami
import org.kde.desktop as Desktop

Desktop.SwitchDelegate {
    id: control

    indicator: MacSwitchIndicator {
        control: control
        x: !control.mirrored ? control.horizontalPadding : control.width - width - control.horizontalPadding
        y: control.topPadding + (control.display === T.AbstractButton.TextUnderIcon ? 0 : (control.availableHeight - height) / 2)
    }

    background: Item {
        Rectangle {
            anchors.fill: parent
            radius: 6
            color: Kirigami.Theme.highlightColor
            visible: control.highlighted || control.down
        }
    }
}
