/*
    MacTahoe Liquid KDE — the notifications at the top of the clock panel: Plasma's
    notification history, newest first, as macOS glass bubbles (app icon,
    bold title, body, time). A click runs the notification's default
    action; the close button shows on hover. Loaded by ClockPanelView.qml,
    so a missing notificationmanager module only shows "No Notifications".

    SPDX-License-Identifier: GPL-3.0-or-later
*/
pragma ComponentBehavior: Bound

import QtQuick

import org.kde.kirigami as Kirigami
import org.kde.notificationmanager as NotificationManager

Column {
    id: list

    // The model has no count property: the bubbles shown.
    readonly property int count: bubbles.count

    signal closeRequested()

    spacing: 8

    NotificationManager.Notifications {
        id: notifications
        showExpired: true
        showDismissed: false
        showJobs: false
        groupMode: NotificationManager.Notifications.GroupDisabled
        sortMode: NotificationManager.Notifications.SortByDate
        limit: 4
    }

    Repeater {
        id: bubbles
        model: notifications

        delegate: GlassCard {
            id: bubble

            required property int index
            required property var model

            width: list.width
            height: Math.max(64, texts.implicitHeight + 24)
            hovered: hover.hovered

            HoverHandler {
                id: hover
            }
            TapHandler {
                onTapped: {
                    notifications.invokeDefaultAction(notifications.index(bubble.index, 0));
                    list.closeRequested();
                }
            }

            Kirigami.Icon {
                x: 14
                anchors.verticalCenter: parent.verticalCenter
                width: 32
                height: 32
                source: bubble.model.applicationIconName || bubble.model.iconName
                        || "preferences-desktop-notification-bell"
            }

            Column {
                id: texts
                x: 56
                y: 12
                width: parent.width - x - 14
                spacing: 1

                Item {
                    width: parent.width
                    height: title.implicitHeight
                    Text {
                        id: title
                        width: parent.width - time.implicitWidth - 8
                        text: bubble.model.summary || bubble.model.applicationName || ""
                        color: Kirigami.Theme.textColor
                        font.pixelSize: 13
                        font.weight: Font.Bold
                        elide: Text.ElideRight
                    }
                    Text {
                        id: time
                        anchors.right: parent.right
                        anchors.baseline: title.baseline
                        text: bubble.model.created ? Qt.formatTime(bubble.model.created,
                                                                   Qt.locale().timeFormat(Locale.ShortFormat)) : ""
                        color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                       Kirigami.Theme.textColor.b, 0.55)
                        font.pixelSize: 11
                        visible: !hover.hovered
                    }
                }
                Text {
                    width: parent.width
                    visible: text.length > 0
                    text: bubble.model.body || ""
                    textFormat: Text.StyledText
                    color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                   Kirigami.Theme.textColor.b, 0.85)
                    font.pixelSize: 13
                    wrapMode: Text.Wrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
            }

            // macOS: a round close button by the corner, on hover (inside the
            // bubble: the window takes clicks on the glass only).
            Rectangle {
                visible: hover.hovered
                z: 2
                x: 4
                y: 4
                width: 20
                height: 20
                radius: 10
                color: bubble.dark ? Qt.rgba(0.25, 0.25, 0.27, 0.95) : Qt.rgba(0.95, 0.95, 0.96, 0.95)
                border.width: 1
                border.color: Qt.rgba(1, 1, 1, bubble.dark ? 0.2 : 0.7)
                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    color: Kirigami.Theme.textColor
                    font.pixelSize: 10
                }
                TapHandler {
                    onTapped: notifications.close(notifications.index(bubble.index, 0))
                }
            }
        }
    }
}
