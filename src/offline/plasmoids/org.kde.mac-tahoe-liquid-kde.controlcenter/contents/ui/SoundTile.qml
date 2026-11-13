/*
    MacTahoe Liquid KDE — Control Center Sound module: volume of the
    preferred output (plasma-pa).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.plasma.private.volume as PlasmaPa
import org.kde.ki18n as KI18n

SliderTile {
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

    readonly property var sink: PlasmaPa.PreferredDevice.sink

    title: i18nc("@title Control Center module", "Sound")
    leadingGlyph: "speaker-low"
    trailingGlyph: "speaker-high"
    accessoryGlyph: "airplay"
    accessoryToolTip: i18nc("@action:button", "Sound Output")
    onAccessoryClicked: openSettings()
    enabled: !!sink
    opacity: enabled ? 1 : 0.5
    value: sink && !sink.muted ? sink.volume / PlasmaPa.PulseAudio.NormalVolume : 0

    onMoved: value => {
        if (!sink) {
            return;
        }
        sink.volume = Math.round(value * PlasmaPa.PulseAudio.NormalVolume);
        sink.muted = value <= 0;
    }
}
