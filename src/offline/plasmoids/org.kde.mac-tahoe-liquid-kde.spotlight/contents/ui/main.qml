/*
    AquaDesktop — menu bar search button.

    The Spotlight magnifier of the macOS menu bar: a symbolic icon sized and
    spaced like the system tray icons next to it, which opens Spotlight
    (SpotlightView.qml) centred under the menu bar, or KRunner when Milou's
    QML module is missing.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    Plasmoid.icon: "system-search-symbolic"
    Plasmoid.title: i18n("Search")
    // No tooltip: macOS shows none on its menu bar extras (and ours would
    // sit over this extra's own menu, which Plasma does not see as open).
    toolTipMainText: ""
    toolTipSubText: ""

    preferredRepresentation: fullRepresentation

    P5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []
        onNewData: sourceName => disconnectSource(sourceName)
    }

    // A click on the icon first deactivates (and so hides) Spotlight; that
    // same click must not open it again.
    property double popoverHiddenAt: 0

    function openSearch(): void {
        if (popover.visible) {
            popover.visible = false;
            return;
        }
        if (Date.now() - popoverHiddenAt < 300) {
            return;
        }
        if (!spotlight.item) {
            executable.connectSource("krunner");
            return;
        }
        spotlight.item.reset();
        placePopover();
        popover.visible = true;
        popover.requestActivate();
        spotlight.item.reset();
    }

    // Centred, a fifth of the way down the screen (216 px at 1080 p).
    // Transparent room above and below the glass: the Glass effect rounds
    // this window like a normal one (TopCornerRadius / BottomCornerRadius,
    // 22 px), which cut the glass's own smaller corners when the window
    // ended at its edges. A corner is only cut within that radius of both
    // edges, so vertical room is enough and the width still hugs the screen.
    readonly property int glassPad: 28

    function placePopover(): void {
        const screen = Plasmoid.containment.screenGeometry;
        popover.x = Math.round(screen.x + (screen.width - spotlight.width) / 2);
        popover.y = Math.round(screen.y + screen.height * 0.2) - glassPad;
    }

    Plasmoid.onActivated: openSearch()

    fullRepresentation: MouseArea {
        id: button

        readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical
        // A 36 px pitch with the panel's applet spacing, like the macOS menu
        // bar extras (1x Tahoe capture).
        readonly property int pitch: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.largeSpacing
            + Kirigami.Units.smallSpacing / 2

        Layout.minimumWidth: vertical ? -1 : pitch
        Layout.maximumWidth: vertical ? -1 : pitch
        Layout.minimumHeight: vertical ? pitch : -1
        Layout.maximumHeight: vertical ? pitch : -1
        Layout.fillHeight: !vertical
        Layout.fillWidth: vertical

        hoverEnabled: true
        activeFocusOnTab: true
        onClicked: root.openSearch()

        Accessible.name: Plasmoid.title
        Accessible.role: Accessible.Button

        // Like a macOS menu bar extra: no hover highlight (KRunner opens
        // in its own window, so there is no open state to show either).

        // macOS draws a 13 px magnifier; symbolic themes draw the glyph at
        // ~65% of the icon box, and standard-size rounding would snap the
        // box back to 16 px.
        Kirigami.Icon {
            anchors.centerIn: parent
            width: Math.round(Kirigami.Units.iconSizes.small * 1.2)
            roundToIconSize: false
            height: width
            source: Plasmoid.icon
            // Pure white like the Wi-Fi and Control Center glyphs (the
            // panel's text colour is a grey #dedede).
            isMask: true
            color: "white"
        }

        PlasmaCore.ToolTipArea {
            anchors.fill: parent
            mainText: root.toolTipMainText
            subText: root.toolTipSubText
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

        mainItem: Item {
            // A fixed size: the panel grows inside it (see maxHeight).
            width: spotlight.width
            height: spotlight.item ? spotlight.item.maxHeight + 2 * root.glassPad : 0

            Loader {
                id: spotlight
                y: root.glassPad
                width: item ? item.implicitWidth : 0
                height: item ? item.maxHeight : 0
                source: "SpotlightView.qml"
                focus: true
            }
            Connections {
                target: spotlight.item
                function onCloseRequested(): void {
                    popover.visible = false;
                }
                function onRunCommand(command: string): void {
                    executable.connectSource(command);
                }
                function onGlassChanged(): void {
                    if (blurLoader.item) {
                        blurLoader.item.update();
                    }
                }
            }
            // KWin blurs the desktop behind the pill, the buttons and the panel.
            Loader {
                id: blurLoader
                source: "WindowBlur.qml"
                onLoaded: item.target = spotlight
            }
            BlurSettler {
                active: popover.visible
                blur: blurLoader.item
            }
        }
    }
}
