/*
    MacTahoe Liquid KDE — Control Center Focus module: Plasma's Do Not
    Disturb, toggled exactly like the Notifications applet does.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.notificationmanager as NotificationManager
import "Palette.js" as Palette
import org.kde.ki18n as KI18n

ToggleTile {
    // Translations from this widget's catalog in any host: Plasma, or the
    // MacTahoe Liquid KDE shell (Quickshell has no KLocalizedContext).
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.controlcenter"
    }
    function i18nc(context, text, arg1, arg2) {
        if (arg1 === undefined) {
            return widgetI18n.i18nc(context, text);
        }
        return arg2 === undefined ? widgetI18n.i18nc(context, text, arg1)
                                  : widgetI18n.i18nc(context, text, arg1, arg2);
    }
    function i18n(text, arg1) {
        return arg1 === undefined ? widgetI18n.i18n(text) : widgetI18n.i18n(text, arg1);
    }

    id: tile

    signal openSettings()

    glyph: "moon"
    title: i18nc("@title Control Center module", "Focus")
    subtitle: active ? i18nc("@info Focus state", "Do Not Disturb") : ""
    activeColor: Palette.focusColor
    active: NotificationManager.Server.inhibited

    onToggled: {
        if (NotificationManager.Server.inhibited) {
            settings.notificationsInhibitedUntil = undefined;
            settings.revokeApplicationInhibitions();
        } else {
            const until = new Date();
            until.setFullYear(until.getFullYear() + 1);
            settings.notificationsInhibitedUntil = until;
        }
        settings.save();
    }
    onDetailsRequested: openSettings()

    NotificationManager.Settings {
        id: settings
    }
}
