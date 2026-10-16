/*
    AquaDesktop — Control Center Display module: brightness of the
    first (preferably built-in) screen PowerDevil can dim.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.plasma.private.brightnesscontrolplugin as BC
import org.kde.ki18n as KI18n

SliderTile {
    // Translations from this widget's catalog in any host: Plasma, or the
    // AquaDesktop shell (Quickshell has no KLocalizedContext).
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

    property string displayName: ""
    property int maxBrightness: 1
    property int brightness: 0

    title: i18nc("@title Control Center module", "Display")
    leadingGlyph: "sun-low"
    trailingGlyph: "sun-high"
    enabled: control.isBrightnessAvailable && displayName.length > 0
    opacity: enabled ? 1 : 0.5
    value: brightness / Math.max(1, maxBrightness)

    onMoved: value => {
        if (displayName.length > 0) {
            // Never go fully black from the Control Center.
            control.setBrightness(displayName, Math.max(1, Math.round(value * maxBrightness)));
        }
    }

    BC.ScreenBrightnessControl {
        id: control
    }

    Instantiator {
        model: control.displays
        delegate: QtObject {
            required property int index
            required property string displayName
            required property int brightness
            required property int maxBrightness
            required property bool isInternal

            function publish(): void {
                if (index === 0 || isInternal) {
                    tile.displayName = displayName;
                    tile.brightness = brightness;
                    tile.maxBrightness = maxBrightness;
                }
            }
            Component.onCompleted: publish()
            onBrightnessChanged: publish()
            onMaxBrightnessChanged: publish()
        }
    }
}
