/*
    MacTahoe Liquid KDE — Sound, the macOS menu bar item: a white speaker with 0 to 3
    waves for the volume (struck through when muted); a click opens the
    macOS sound menu (VolumeView.qml), the wheel changes the volume.
    Replaces Plasma's volume applet in the menu bar (it stays hidden in the
    tray for its shortcuts and on-screen display).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import org.kde.plasma.private.volume as PlasmaPa

PlasmoidItem {
    id: root

    readonly property var sink: PlasmaPa.PreferredDevice.sink
    readonly property real level: sink ? sink.volume / PlasmaPa.PulseAudio.NormalVolume : 0
    readonly property string glyphName: !sink || sink.muted || level <= 0 ? (sink && sink.muted ? "speaker-muted" : "speaker-0")
                                        : level < 0.34 ? "speaker-1" : level < 0.67 ? "speaker-2" : "speaker-3"

    readonly property int popoverGap: 6
    // Transparent room above and below the glass (see SoundBubble.qml).
    readonly property int glassPad: 28
    property double popoverHiddenAt: 0
    // How long the HUD stays after the last volume key, like macOS.
    readonly property int hudTimeout: 1500
    // The HUD hangs lower than the menu: 11 px under the menu bar on the
    // Tahoe capture, where the menu's glass starts 2 px under it.
    readonly property int hudDrop: 9

    Plasmoid.status: sink ? PlasmaCore.Types.ActiveStatus : PlasmaCore.Types.HiddenStatus
    Plasmoid.icon: "audio-volume-high"
    // No tooltip: macOS shows none on its menu bar extras (and ours would
    // sit over this extra's own menu, which Plasma does not see as open).
    toolTipMainText: ""
    toolTipSubText: ""

    preferredRepresentation: compactRepresentation
    fullRepresentation: Item {}

    Connections {
        target: Plasmoid
        function onActivated(): void {
            root.togglePopover();
        }
    }

    function togglePopover(): void {
        if (popover.visible) {
            popover.visible = false;
            return;
        }
        if (Date.now() - popoverHiddenAt < 300) {
            return;
        }
        hudWindow.visible = false;
        place(popover, menuBubble);
        popover.visible = true;
        popover.requestActivate();
    }

    // The HUD: shown again by every key, never while the menu is open (its
    // slider already moves).
    function showHud(): void {
        if (popover.visible || !root.sink) {
            return;
        }
        place(hudWindow, hudBubble);
        hudWindow.y += root.hudDrop;
        hudWindow.visible = true;
        hudTimer.restart();
    }

    // Centred under this extra, kept on its screen.
    function place(window: var, content: Item): void {
        const anchor = root.compactRepresentationItem;
        if (!anchor) {
            return;
        }
        const origin = anchor.mapToGlobal(0, 0);
        const screen = Plasmoid.containment.screenGeometry;
        const width = window.width > 0 ? window.width : content.width;
        let x = Math.round(origin.x + anchor.width / 2 - width / 2);
        x = Math.max(screen.x + popoverGap, Math.min(x, screen.x + screen.width - width - popoverGap));
        window.x = x;
        window.y = Math.round(origin.y + anchor.height + popoverGap) - glassPad;
    }

    Timer {
        id: hudTimer
        interval: root.hudTimeout
        onTriggered: hudWindow.visible = false
    }

    Loader {
        source: "VolumeKeys.qml"
        onLoaded: item.pressed.connect(root.showHud)
    }

    compactRepresentation: MouseArea {
        id: compact

        Layout.minimumWidth: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.smallSpacing * 2
        Layout.preferredWidth: Layout.minimumWidth
        hoverEnabled: true
        onClicked: root.togglePopover()
        onWheel: wheel => {
            if (!root.sink) {
                return;
            }
            const step = PlasmaPa.PulseAudio.NormalVolume / 20;
            const volume = root.sink.volume + (wheel.angleDelta.y > 0 ? step : -step);
            root.sink.volume = Math.max(0, Math.min(PlasmaPa.PulseAudio.NormalVolume, Math.round(volume)));
            root.sink.muted = root.sink.volume <= 0;
        }

        // Highlighted only while open or while the HUD shows, never on
        // hover, like macOS.
        Rectangle {
            anchors.centerIn: parent
            width: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.smallSpacing * 2
            height: width
            radius: Kirigami.Units.cornerRadius
            color: Qt.rgba(0.5, 0.5, 0.5, 0.25)
            visible: popover.visible || hudWindow.visible
        }

        // 18 px and pure white, like the Wi-Fi and Control Center glyphs.
        Glyph {
            anchors.centerIn: parent
            width: 18
            height: 18
            glyph: root.glyphName
            color: "white"
        }
    }

    PlasmaCore.Dialog {
        id: popover

        location: PlasmaCore.Types.Floating
        backgroundHints: PlasmaCore.Dialog.NoBackground
        type: PlasmaCore.Dialog.PopupMenu
        flags: Qt.WindowStaysOnTopHint
        hideOnWindowDeactivate: true
        visible: false
        onVisibleChanged: if (!visible) root.popoverHiddenAt = Date.now()

        mainItem: SoundBubble {
            id: menuBubble
            glassPad: root.glassPad
            shown: popover.visible
        }
    }

    // The volume HUD: an on-screen display that takes neither focus nor
    // clicks, over every window (full-screen ones included).
    PlasmaCore.Dialog {
        id: hudWindow

        location: PlasmaCore.Types.Floating
        backgroundHints: PlasmaCore.Dialog.NoBackground
        type: PlasmaCore.Dialog.OnScreenDisplay
        flags: Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        outputOnly: true
        visible: false

        mainItem: SoundBubble {
            id: hudBubble
            glassPad: root.glassPad
            hud: true
            interactive: false
            shown: hudWindow.visible
        }
    }
}
