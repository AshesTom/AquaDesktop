/*
    MacTahoe Liquid KDE — the AirDrop control shown in macOS Tahoe's Control Center.
    Plasma has no AirDrop service, so opening it takes the user to Bluetooth
    settings, where the required radio can be managed.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.ki18n as KI18n

CircleButton {
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.controlcenter"
    }
    function i18nc(context, text) {
        return widgetI18n.i18nc(context, text);
    }

    signal openSettings()

    glyph: "airdrop"
    toolTip: i18nc("@action:button", "AirDrop")
    onClicked: openSettings()
}
