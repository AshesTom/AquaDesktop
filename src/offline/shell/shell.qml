/*
    AquaDesktop shell — the menu bar drawn by Quickshell: the reference the
    Plasma menu bar's plasmoids are styled after. Not installed; run it with
    `qs -p <this dir>` in a nested KWin to compare (the full Quickshell
    session was dropped: Plasma stays the shell).

    Per screen: the menu bar and its popovers (Control Center, Wi-Fi,
    Spotlight), which reuse the plasmoids' views (views/, the same QML as
    in the Plasma session). One popover is open at a time; a click anywhere
    else closes it, as on macOS.

    Commands: `qs -p <this dir> ipc call shell toggle spotlight` (also
    controlcenter, wifi), `... ipc call shell search <text>`,
    `... ipc call shell menu <index>`, `... ipc call shell close`.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
//@ pragma UseQApplication
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import org.kde.kirigami as Kirigami
import "views/controlcenter" as CC
import "views/wifi" as Wifi
import "views/spotlight" as Spot

ShellRoot {
    id: shell

    // The popover open on any screen ("" for none) and the screen it is on.
    property string openPopover: ""
    property var popoverScreen: null

    function toggle(name: string, screen: var, centerX: real): void {
        if (openPopover === name && popoverScreen === screen) {
            openPopover = "";
            return;
        }
        popoverScreen = screen;
        openPopover = name;
        lastCenter = centerX;
    }
    property real lastCenter: 0
    // Typed into Spotlight when it opens (the `search` command).
    property string pendingQuery: ""

    IpcHandler {
        target: "shell"

        function toggle(name: string): void {
            const screen = Quickshell.screens[0];
            const center = name === "spotlight" ? screen.width / 2 : screen.width - 60;
            shell.toggle(name, screen, center);
        }
        function close(): void {
            shell.openPopover = "";
        }
        // Menu `index` of the menu bar (-3 Apple, -2 app name, else a
        // title of the active app; checking captures).
        function menu(index: int): void {
            if (shell.bars.length > 0) {
                shell.bars[0].openMenu(index);
            }
        }
        // Spotlight, already searching for `text`.
        function search(text: string): void {
            shell.pendingQuery = text;
            toggle("spotlight");
        }
    }

    property var bars: []

    Variants {
        model: Quickshell.screens

        delegate: Scope {
            id: screenScope

            required property ShellScreen modelData
            readonly property bool here: shell.popoverScreen === modelData
            readonly property string open: here ? shell.openPopover : ""
            readonly property bool dark: (0.299 * Kirigami.Theme.textColor.r + 0.587 * Kirigami.Theme.textColor.g
                                          + 0.114 * Kirigami.Theme.textColor.b) > 0.5

            function placeX(width: real): int {
                const x = shell.lastCenter - width / 2;
                return Math.round(Math.max(6, Math.min(x, modelData.width - width - 6)));
            }

            MenuBar {
                id: bar
                screen: screenScope.modelData
                openPopover: screenScope.open
                Component.onCompleted: shell.bars = shell.bars.concat([bar])
                onToggleRequested: (name, centerX) => shell.toggle(name, screenScope.modelData, centerX)
            }

            // Below the popovers, over everything else: a click outside the
            // open popover closes it (and is not passed on, as on macOS).
            PanelWindow {
                screen: screenScope.modelData
                visible: screenScope.open !== ""
                anchors { top: true; bottom: true; left: true; right: true }
                margins.top: bar.barHeight
                exclusionMode: ExclusionMode.Ignore
                color: "transparent"
                WlrLayershell.layer: WlrLayer.Top
                WlrLayershell.namespace: "dock"
                MouseArea {
                    anchors.fill: parent
                    onPressed: shell.openPopover = ""
                }
            }

            Popover {
                screen: screenScope.modelData
                view: controlCenter
                visible: screenScope.open === "controlcenter"
                popoverY: bar.barHeight + 6
                popoverX: screenScope.placeX(controlCenter.width)
                CC.ControlCenterView {
                    id: controlCenter
                    width: implicitWidth
                    height: implicitHeight
                    showEditControls: true
                    onRunCommand: command => Quickshell.execDetached(["sh", "-c", command])
                    onCloseRequested: shell.openPopover = ""
                }
            }

            Popover {
                screen: screenScope.modelData
                view: wifiFrame
                visible: screenScope.open === "wifi"
                popoverY: bar.barHeight + 6
                popoverX: screenScope.placeX(wifiFrame.width)
                // The Wi-Fi menu is one glass panel with 16 px padding.
                Rectangle {
                    id: wifiFrame
                    readonly property real glassRadius: radius
                    width: wifiView.implicitWidth + 32
                    height: wifiView.implicitHeight + 28
                    radius: 14
                    color: screenScope.dark ? Qt.rgba(1, 1, 1, 0.0) : Qt.rgba(0.98, 0.98, 0.99, 0.62)
                    border.width: 1
                    border.color: Qt.rgba(1, 1, 1, screenScope.dark ? 0.16 : 0.6)
                    Wifi.WifiView {
                        id: wifiView
                        x: 16
                        y: 14
                        width: implicitWidth
                        height: implicitHeight
                        onCloseRequested: shell.openPopover = ""
                    }
                }
            }

            Popover {
                id: spotlightPopover
                screen: screenScope.modelData
                view: spotlight
                takesKeyboard: true
                visible: screenScope.open === "spotlight"
                // Centred, a fifth of the way down the screen.
                popoverY: Math.round(screenScope.modelData.height * 0.2)
                popoverX: Math.round((screenScope.modelData.width - spotlight.width) / 2)
                onVisibleChanged: {
                    if (visible) {
                        spotlight.reset();
                        spotlight.query = shell.pendingQuery;
                        shell.pendingQuery = "";
                    }
                }
                Spot.SpotlightView {
                    id: spotlight
                    width: implicitWidth
                    height: maxHeight
                    onRunCommand: command => Quickshell.execDetached(["sh", "-c", command])
                    onCloseRequested: shell.openPopover = ""
                    onGlassChanged: spotlightPopover.refreshGlass()
                }
            }
        }
    }
}
