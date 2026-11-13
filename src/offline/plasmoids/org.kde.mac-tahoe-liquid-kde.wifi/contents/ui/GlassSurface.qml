/*
    MacTahoe Liquid KDE — the face of a Liquid Glass bubble, over the blur KWin's
    Glass effect draws behind it (shaders/glasssurface.frag): measured on
    Apple's macOS Tahoe Control Center image, the body is the blurred
    desktop itself, ringed by added light (a bright edge line, then a glow
    fading inward). White content sits on clear glass; dark content (light
    mode menus) on a light veil that keeps it legible. Shared by the menu
    bar popovers (each package has a copy). Without shader support: the
    tint with a 1 px rim.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtCore
import QtQuick

import org.kde.kirigami as Kirigami

Item {
    id: surface

    property real radius: 20
    property bool hovered: false
    // White content on this glass (the Control Center, dark mode menus).
    readonly property bool dark: luminance(Kirigami.Theme.textColor) > 0.5

    // The context menus' colour (Kvantum's menu fill at its opacity: #333333
    // at 55 % with white content, white at 33 % with dark content), like
    // macOS' Control Center next to the menu bar's menus. Theme Settings
    // writes the tint and Golden Gate's clear-to-tinted level to glass.ini.
    readonly property bool accentTint: tintName === "accent" && accentHex.length === 6
    readonly property color tint: accentTint ? "#" + accentHex : dark ? "#1c1c1e" : "#ffffff"
    // Dark mode: Apple's near-black #1c1c1e at 50 %, so the glass stays
    // dark over a bright wallpaper without the old #333333 veil's grey cast.
    // Light mode: the slider's clear end.
    readonly property real defaultTintAlpha: accentTint ? (dark ? 0.35 : 0.20) : dark ? 0.50 : 0.05
    readonly property real tintAlpha: {
        const level = glassLevel;
        const clear = dark ? 0.08 : 0.05;
        const tinted = dark ? 0.82 : 0.72;
        return level <= 0.5
            ? clear + (defaultTintAlpha - clear) * level * 2
            : defaultTintAlpha + (tinted - defaultTintAlpha) * (level - 0.5) * 2;
    }

    // QSettings reads the file's top level as no category.
    Settings {
        id: glassTint
        location: StandardPaths.writableLocation(StandardPaths.GenericConfigLocation)
                  + "/mac-tahoe-liquid-kde/glass.ini"
    }
    // Read again whenever the popover is shown or the palette changes.
    readonly property string tintName: {
        surface.Window.visibility;
        Kirigami.Theme.textColor;
        glassTint.sync();
        return String(glassTint.value("Tint", "macos"));
    }
    readonly property real glassLevel: {
        surface.Window.visibility;
        glassTint.sync();
        const value = Number(glassTint.value("GlassLevel", 50));
        return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) / 100 : 0.5;
    }
    readonly property string accentHex: {
        tintName;
        const hex = String(glassTint.value("Accent", ""));
        return /^[0-9a-fA-F]{6}$/.test(hex) ? hex : "";
    }
    // The edge light, measured at 1x (the image is at 1.21x): +45 and +48
    // / 255 on the first two pixels in, then +25, +12, +9, +5: a 2 px line
    // over a glow fading to 1/e over 3 px.
    readonly property real rimLight: 0.13
    readonly property real rimWidth: 2.0
    readonly property real glowLight: 0.09
    readonly property real glowWidth: 3.0

    function luminance(c: color): real {
        return 0.299 * c.r + 0.587 * c.g + 0.114 * c.b;
    }

    ShaderEffect {
        id: shader
        anchors.fill: parent
        fragmentShader: Qt.resolvedUrl("shaders/glasssurface.frag.qsb")
        property size size: Qt.size(Math.max(1, width), Math.max(1, height))
        property real radius: surface.radius
        // Circular corners, like the blur region KWin clips the glass to.
        property real roundness: 2.0
        property vector4d tint: Qt.vector4d(surface.tint.r, surface.tint.g, surface.tint.b, surface.tintAlpha)
        property real rimLight: surface.rimLight
        property real rimWidth: surface.rimWidth
        property real glowLight: surface.glowLight
        property real glowWidth: surface.glowWidth
        property real hoverLight: surface.hovered ? 0.03 : 0

        Behavior on hoverLight {
            NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic }
        }
    }

    Rectangle {
        anchors.fill: parent
        visible: shader.status === ShaderEffect.Error
        radius: surface.radius
        color: Qt.rgba(surface.tint.r, surface.tint.g, surface.tint.b, surface.tintAlpha)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, surface.dark ? 0.24 : 0.6)
    }
}
