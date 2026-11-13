/*
    MacTahoe Liquid KDE — the panel the menu bar clock opens, as on macOS Tahoe
    (measured on the reference capture, 1x): a 356 px column of glass
    bubbles under the menu bar.

    - The notifications (NotificationList.qml), or a 46 px "No
      Notifications" pill.
    - 18 px below, the date card (168 px): the weekday in red capitals and
      the day in large thin figures on the left, "No events today" under
      them; the month grid on the right (red month name, narrow weekday
      initials, days on a 25 x 18 px pitch, today in a red disc).
    - 12 px below, two 170 px clocks: Local and UTC (with its offset).

    No Plasmoid API here, so the view also works outside Plasma.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
pragma ComponentBehavior: Bound

import QtQuick

import org.kde.kirigami as Kirigami
import org.kde.ki18n as KI18n

Item {
    // Translations from this widget's catalog in any host.
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.clock"
    }
    function i18n(text, arg1) {
        return arg1 === undefined ? widgetI18n.i18n(text) : widgetI18n.i18n(text, arg1);
    }

    id: view

    // The current time (the plasmoid's time source, minute precision).
    property date now: new Date()

    signal closeRequested()

    // macOS system red (dark), the weekday, month and today.
    readonly property color red: "#ff453a"
    readonly property color dim: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                         Kirigami.Theme.textColor.b, 0.55)
    readonly property color soft: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                          Kirigami.Theme.textColor.b, 0.85)

    implicitWidth: 356
    implicitHeight: clocks.y + clocks.height

    function timeText(date: date): string {
        return date.toLocaleTimeString(Qt.locale(), Qt.locale().timeFormat(Locale.ShortFormat)
                                       .replace(/\s*(AP|ap|A|a)\s*/, ""));
    }

    // ── Notifications ────────────────────────────────────────────────
    Loader {
        id: notificationsLoader
        width: parent.width
        source: "NotificationList.qml"
        onLoaded: item.closeRequested.connect(view.closeRequested)
    }
    readonly property bool hasNotifications: notificationsLoader.item !== null && notificationsLoader.item.count > 0

    GlassCard {
        id: emptyPill
        visible: !view.hasNotifications
        width: parent.width
        height: 46
        radius: 23
        Text {
            anchors.centerIn: parent
            text: view.i18n("No Notifications")
            color: view.soft
            font.pixelSize: 13
        }
    }

    // ── Date and month ───────────────────────────────────────────────
    GlassCard {
        id: dateCard

        readonly property date day: new Date(view.now.getFullYear(), view.now.getMonth(), view.now.getDate())
        // The month grid: the first cell is the week's first day on or
        // before the 1st (the locale's first day of the week).
        readonly property int firstDay: Qt.locale().firstDayOfWeek
        readonly property int lead: (new Date(day.getFullYear(), day.getMonth(), 1).getDay() - firstDay + 7) % 7
        readonly property int daysInMonth: new Date(day.getFullYear(), day.getMonth() + 1, 0).getDate()

        y: (view.hasNotifications ? notificationsLoader.height : emptyPill.height) + 18
        width: parent.width
        height: 168

        Text {
            x: 18
            y: 18
            text: Qt.locale().standaloneDayName(dateCard.day.getDay(), Locale.LongFormat).toUpperCase()
            color: view.red
            font.pixelSize: 12
            font.weight: Font.Bold
        }
        Text {
            x: 16
            y: 34
            text: dateCard.day.getDate()
            color: Kirigami.Theme.textColor
            font.pixelSize: 56
            font.weight: Font.Light
        }
        Text {
            x: 18
            y: 126
            text: view.i18n("No events today")
            color: view.soft
            font.pixelSize: 13
        }

        Text {
            x: 165
            y: 12
            text: Qt.locale().standaloneMonthName(dateCard.day.getMonth(), Locale.LongFormat).toUpperCase()
            color: view.red
            font.pixelSize: 12
            font.weight: Font.Bold
        }
        Repeater {
            model: 7
            delegate: Text {
                required property int index
                x: 176 + index * 25 - width / 2
                y: 45 - height / 2
                text: Qt.locale().standaloneDayName((dateCard.firstDay + index) % 7, Locale.NarrowFormat)
                color: view.dim
                font.pixelSize: 10
            }
        }
        Repeater {
            model: dateCard.daysInMonth
            delegate: Item {
                required property int index
                readonly property int cell: dateCard.lead + index
                readonly property bool today: index + 1 === dateCard.day.getDate()
                x: 176 + (cell % 7) * 25 - width / 2
                y: 65 + Math.floor(cell / 7) * 18 - height / 2
                width: 18
                height: 18
                Rectangle {
                    anchors.fill: parent
                    radius: width / 2
                    color: view.red
                    visible: parent.today
                }
                Text {
                    anchors.centerIn: parent
                    text: parent.index + 1
                    color: parent.today ? "white" : Kirigami.Theme.textColor
                    font.pixelSize: 11
                    font.weight: Font.Medium
                }
            }
        }
    }

    // ── Clocks ───────────────────────────────────────────────────────
    Row {
        id: clocks
        y: dateCard.y + dateCard.height + 12
        spacing: 12

        WorldClock {
            label: view.i18n("Local")
            time: view.timeText(view.now)
            detail: view.now.toLocaleDateString(Qt.locale(), "ddd d")
        }
        WorldClock {
            // UTC wall time, read through the local formatter.
            readonly property date utc: new Date(view.now.getTime() + view.now.getTimezoneOffset() * 60000)
            // UTC relative to here, like macOS' "-10h".
            readonly property int offset: Math.round(view.now.getTimezoneOffset() / 60)
            label: "UTC"
            time: view.timeText(utc)
            detail: (offset >= 0 ? "+" : "−") + Math.abs(offset) + "h"
        }
    }

    component WorldClock: GlassCard {
        id: worldClock

        property string label
        property string time
        property string detail

        width: (view.width - 12) / 2
        height: 170

        Text {
            x: 16
            y: 14
            text: worldClock.label
            color: view.soft
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.top
            anchors.verticalCenterOffset: 76
            text: worldClock.time
            color: Kirigami.Theme.textColor
            font.pixelSize: 44
            font.weight: Font.Medium
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.top
            anchors.verticalCenterOffset: 122
            text: worldClock.detail
            color: view.dim
            font.pixelSize: 12
        }
    }
}
