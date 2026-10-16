/*
    AquaDesktop — the Shut Down / Restart / Log Out confirmation, drawn as a
    macOS Tahoe alert instead of Breeze's full-screen black page: a glass
    card centred on the desktop (no dimming), the Mac's icon at the top
    left, a bold question, the 60 s countdown, then capsule buttons with
    the action in the accent colour. Esc cancels, Return confirms.

    ksmserver-logout-greeter loads this file (the package's
    "logoutmainscript") with one view per screen and gives it these
    context properties: screenGeometry, sdtype, ShutdownType (a map of the
    ShutdownType* values), maysd, canLogout, spdMethods,
    softwareUpdatePending, rebootToFirmwareSetup, rebootToBootLoaderMenu,
    rebootToBootLoaderEntry and isUefi. It listens to the signals below.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.private.sessions

Item {
    id: root
    width: screenGeometry.width
    height: screenGeometry.height

    signal logoutRequested()
    signal haltRequested()
    signal haltUpdateRequested()
    signal suspendRequested(int spdMethod)
    signal rebootRequested()
    signal rebootRequested2(int opt)
    signal rebootUpdateRequested()
    signal cancelRequested()
    signal lockScreenRequested()
    signal cancelSoftwareUpdateRequested()

    // macOS waits a minute before it acts on its own.
    property int remainingTime: 60

    readonly property bool showAllOptions: sdtype === ShutdownType.ShutdownTypeDefault
    readonly property bool isHalt: sdtype === ShutdownType.ShutdownTypeHalt
    readonly property bool isReboot: sdtype === ShutdownType.ShutdownTypeReboot
    readonly property bool isLogout: !showAllOptions && !isHalt && !isReboot
    readonly property bool dark: Kirigami.Theme.backgroundColor.hslLightness < 0.5
    readonly property color accent: accentColor.valid ? accentColor.value : Kirigami.Theme.highlightColor

    function act() {
        if (isReboot) {
            softwareUpdatePending ? rebootUpdateRequested() : rebootRequested();
        } else if (isHalt || showAllOptions) {
            softwareUpdatePending ? haltUpdateRequested() : haltRequested();
        } else {
            logoutRequested();
        }
    }

    onRemainingTimeChanged: {
        if (remainingTime <= 0) {
            act();
        }
    }

    Timer {
        running: !root.showAllOptions
        repeat: true
        interval: 1000
        onTriggered: root.remainingTime--
    }

    Shortcut {
        sequence: "Escape"
        onActivated: root.cancelRequested()
    }
    Shortcut {
        sequences: ["Return", "Enter"]
        onActivated: root.act()
    }

    AccentColor {
        id: accentColor
    }

    // For the "other users are logged in" warning.
    SessionsModel {
        id: otherSessions
        includeUnusedSessions: false
        includeOwnSession: false
    }

    // The alert's soft shadow, drawn with plain rounded rectangles: a
    // shader effect draws nothing on a GPU-less session, and the alert
    // must show wherever the greeter runs.
    Repeater {
        model: 8
        delegate: Rectangle {
            required property int index
            readonly property real spread: (index + 1) * 3
            x: alert.x - spread
            y: alert.y - spread + 10
            width: alert.width + spread * 2
            height: alert.height + spread * 2
            radius: alert.radius + spread
            color: Qt.rgba(0, 0, 0, (root.dark ? 0.07 : 0.035) * (1 - index / 8))
        }
    }

    Rectangle {
        id: alert

        // GlassBlur blurs behind every item declaring a glassRadius.
        readonly property real glassRadius: radius

        anchors.centerIn: parent
        width: 300
        height: content.implicitHeight + 40
        radius: 26
        color: root.dark ? Qt.rgba(0.16, 0.16, 0.17, 0.90) : Qt.rgba(0.97, 0.97, 0.97, 0.90)
        border.width: 1
        border.color: root.dark ? Qt.rgba(1, 1, 1, 0.14) : Qt.rgba(1, 1, 1, 0.65)

        Kirigami.Theme.inherit: false
        Kirigami.Theme.colorSet: Kirigami.Theme.Window

        // Clicks on the card never reach the desktop behind it.
        MouseArea {
            anchors.fill: parent
        }

        ColumnLayout {
            id: content
            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
                margins: 20
            }
            spacing: 0

            Kirigami.Icon {
                Layout.preferredWidth: 64
                Layout.preferredHeight: 64
                source: "computer"
                fallback: "system-shutdown"
            }

            Text {
                Layout.fillWidth: true
                Layout.topMargin: 12
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                font.family: Kirigami.Theme.defaultFont.family
                font.pointSize: Kirigami.Theme.defaultFont.pointSize
                font.weight: Font.Bold
                color: Kirigami.Theme.textColor
                renderType: Text.NativeRendering
                text: {
                    if (root.isReboot) {
                        return i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Are you sure you want to restart your computer now?");
                    }
                    if (root.isLogout) {
                        return i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Are you sure you want to quit all applications and log out now?");
                    }
                    return i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Are you sure you want to shut down your computer now?");
                }
            }

            Repeater {
                model: {
                    const lines = [];
                    if (!root.showAllOptions) {
                        if (root.isReboot) {
                            lines.push(i18ndp("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde",
                                "If you do nothing, the computer will restart automatically in 1 second.",
                                "If you do nothing, the computer will restart automatically in %1 seconds.", root.remainingTime));
                        } else if (root.isLogout) {
                            lines.push(i18ndp("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde",
                                "If you do nothing, you will be logged out automatically in 1 second.",
                                "If you do nothing, you will be logged out automatically in %1 seconds.", root.remainingTime));
                        } else {
                            lines.push(i18ndp("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde",
                                "If you do nothing, the computer will shut down automatically in 1 second.",
                                "If you do nothing, the computer will shut down automatically in %1 seconds.", root.remainingTime));
                        }
                    }
                    if (otherSessions.count > 0 && !root.isLogout) {
                        lines.push(i18ndp("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde",
                            "Another user is logged in and may lose unsaved work.",
                            "%1 other users are logged in and may lose unsaved work.", otherSessions.count));
                    }
                    if (root.isReboot || root.showAllOptions) {
                        if (rebootToFirmwareSetup) {
                            lines.push(isUefi
                                ? i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "When restarted, the computer will enter UEFI firmware settings.")
                                : i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "When restarted, the computer will enter the firmware setup screen."));
                        }
                        if (rebootToBootLoaderMenu) {
                            lines.push(i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "When restarted, the computer will enter the boot loader menu."));
                        }
                        if (rebootToBootLoaderEntry) {
                            lines.push(i18ndc("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "%1 is a boot loader entry", "When restarted, the computer will switch to %1.", rebootToBootLoaderEntry));
                        }
                    }
                    return lines;
                }
                delegate: Text {
                    required property string modelData
                    Layout.fillWidth: true
                    Layout.topMargin: 6
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    font: Kirigami.Theme.smallFont
                    color: Kirigami.Theme.textColor
                    renderType: Text.NativeRendering
                    text: modelData
                }
            }

            // Two buttons side by side; more stack up, the action first.
            GridLayout {
                id: buttons
                Layout.fillWidth: true
                Layout.topMargin: 20
                columns: visibleChildren.length > 2 ? 1 : 2
                rowSpacing: 8
                columnSpacing: 8
                layoutDirection: Qt.RightToLeft

                AlertButton {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    isDefault: true
                    dark: root.dark
                    accent: root.accent
                    text: {
                        if (root.isReboot) {
                            return softwareUpdatePending
                                ? i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Update and Restart")
                                : i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Restart");
                        }
                        if (root.isLogout) {
                            return i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Log Out");
                        }
                        return softwareUpdatePending
                            ? i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Update and Shut Down")
                            : i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Shut Down");
                    }
                    visible: root.isLogout ? canLogout : maysd
                    onClicked: root.act()
                }
                // With updates pending, the same action without them.
                AlertButton {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    dark: root.dark
                    text: root.isReboot
                        ? i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Restart Without Updating")
                        : i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Shut Down Without Updating")
                    visible: maysd && softwareUpdatePending && !root.isLogout
                    onClicked: root.isReboot ? root.rebootRequested() : root.haltRequested()
                }
                // The power key's alert also offers Restart, Sleep and Log Out.
                AlertButton {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    dark: root.dark
                    text: i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Restart")
                    visible: root.showAllOptions && maysd
                    onClicked: root.rebootRequested()
                }
                AlertButton {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    dark: root.dark
                    text: i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Sleep")
                    visible: root.showAllOptions && !!spdMethods.SuspendState
                    onClicked: root.suspendRequested(2)
                }
                AlertButton {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    dark: root.dark
                    text: i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Log Out")
                    visible: root.showAllOptions && canLogout
                    onClicked: root.logoutRequested()
                }
                AlertButton {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    dark: root.dark
                    text: i18nd("plasma_lookandfeel_org.kde.mac-tahoe-liquid-kde", "Cancel")
                    onClicked: root.cancelRequested()
                }
            }
        }
    }

    // Blur behind the card only; without the compiled module the card
    // keeps its own fill.
    Loader {
        source: "WindowBlur.qml"
        onLoaded: item.target = root
    }
}
