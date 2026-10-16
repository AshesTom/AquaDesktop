/*
    AquaDesktop — org.kde.desktop's menu, building the items it makes
    for plain Actions with this style's MenuItem (no icons, see there).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.desktop as Desktop

Desktop.Menu {
    delegate: MenuItem {}
}
