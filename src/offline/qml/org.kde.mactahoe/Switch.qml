/*
    AquaDesktop — org.kde.desktop's Switch with the macOS Tahoe indicator.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.desktop as Desktop

Desktop.Switch {
    id: control

    indicator: MacSwitchIndicator {
        control: control
        x: control.contentItem !== null && control.contentItem.width > 0
            ? (control.mirrored ? control.width - width - control.rightPadding : control.leftPadding)
            : control.leftPadding + (control.availableWidth - width) / 2
        y: control.topPadding + Math.round((control.availableHeight - height) / 2)
    }
}
