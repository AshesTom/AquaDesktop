/*
    AquaDesktop — menu bar clock.

    Renders the date and time the way the macOS Tahoe menu bar does:
    one line in the system font at its normal size ("Mon 5 Oct  14:27"),
    no separators. A click opens the macOS clock panel (notifications,
    date and month, local and UTC clocks: ClockPanelView.qml). The stock Digital Clock
    scales its text to the panel height and the screen's physical DPI, so
    it can't match the menu bar's text size across machines.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    readonly property bool showDate: Plasmoid.configuration.showDate
    readonly property bool showSeconds: Plasmoid.configuration.showSeconds
    readonly property date currentDateTime: timeSource.data.Local
        ? timeSource.data.Local.DateTime : new Date()

    // macOS keeps the locale's day/month order: "Mon Oct 5" for en_US,
    // "lun. 5 oct." for fr_FR, "9月17日(水)" for Japanese and Chinese.
    readonly property string dateFormat: {
        const name = Qt.locale().name;
        if (/^(ja|zh)/.test(name)) {
            return "M月d日(ddd)";
        }
        const shortFormat = Qt.locale().dateFormat(Locale.ShortFormat);
        return /^\s*M/.test(shortFormat) ? "ddd MMM d" : "ddd d MMM";
    }

    readonly property string timeFormat: {
        const format = Qt.locale().timeFormat(Locale.ShortFormat);
        return showSeconds && format.indexOf("ss") === -1
            ? format.replace("mm", "mm:ss") : format;
    }

    readonly property string dateText: currentDateTime.toLocaleString(Qt.locale(), dateFormat)
    readonly property string timeText: currentDateTime.toLocaleString(Qt.locale(), timeFormat)

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    Plasmoid.icon: "preferences-system-time"
    Plasmoid.title: i18n("Clock")

    // No tooltip: macOS shows none on its menu bar extras (and ours would
    // sit over this extra's own menu, which Plasma does not see as open).
    toolTipMainText: ""
    toolTipSubText: ""

    P5Support.DataSource {
        id: timeSource
        engine: "time"
        connectedSources: ["Local"]
        interval: root.showSeconds ? 1000 : 60000
        intervalAlignment: root.showSeconds
            ? P5Support.Types.NoAlignment : P5Support.Types.AlignToMinute
    }

    preferredRepresentation: compactRepresentation
    // Plasma's own popup is never used (see the panel below).
    fullRepresentation: Item {}

    readonly property bool panelOpen: panel.visible
    // A click on the clock first deactivates (and so hides) the panel; that
    // same click must not open it again.
    property double panelHiddenAt: 0
    // macOS: the first bubble 34 px from the top of the screen (4 px under
    // the 30 px menu bar; the clock's own item is 4 px shorter than the
    // bar), 12 px from the screen's right edge.
    readonly property int panelGap: 8
    readonly property int panelMargin: 12
    // Transparent room above and below the glass: the Glass effect rounds
    // this window like a normal one (22 px), which would cut the bubbles'
    // corners if the window ended at their edges.
    readonly property int glassPad: 28

    function togglePanel(): void {
        if (panel.visible) {
            panel.visible = false;
            return;
        }
        if (Date.now() - panelHiddenAt < 300) {
            return;
        }
        placePanel();
        panel.visible = true;
        panel.requestActivate();
    }

    function placePanel(): void {
        const anchor = root.compactRepresentationItem;
        if (!anchor) {
            return;
        }
        const origin = anchor.mapToGlobal(0, 0);
        const screen = Plasmoid.containment.screenGeometry;
        const width = panel.width > 0 ? panel.width : panelView.implicitWidth;
        panel.x = screen.x + screen.width - width - panelMargin;
        panel.y = Math.round(origin.y + anchor.height + panelGap) - glassPad;
    }

    Connections {
        target: Plasmoid
        function onActivated(): void {
            root.togglePanel();
        }
    }

    compactRepresentation: MouseArea {
        id: compact

        readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical

        // macOS leaves ~24 px between the last menu bar extra and the
        // clock, and ~20 px between the clock and the screen edge.
        readonly property int horizontalPadding: Kirigami.Units.largeSpacing + Kirigami.Units.smallSpacing

        Layout.minimumWidth: vertical ? -1 : label.implicitWidth + horizontalPadding * 2
        Layout.maximumWidth: Layout.minimumWidth
        Layout.fillHeight: !vertical
        Layout.minimumHeight: vertical ? label.implicitHeight + Kirigami.Units.smallSpacing * 2 : -1

        hoverEnabled: true
        activeFocusOnTab: true
        acceptedButtons: Qt.LeftButton
        onClicked: root.togglePanel()

        Accessible.name: label.text
        Accessible.role: Accessible.Button

        Rectangle {
            anchors.fill: parent
            anchors.topMargin: Kirigami.Units.smallSpacing / 2
            anchors.bottomMargin: Kirigami.Units.smallSpacing / 2
            radius: Kirigami.Units.cornerRadius
            color: Qt.rgba(0.5, 0.5, 0.5, 0.25)
            // Like a macOS menu bar extra: highlighted only while open.
            visible: root.panelOpen
        }

        PlasmaComponents3.Label {
            id: label
            anchors.centerIn: parent
            // Optically centred in the 30 px bar: caps on rows 11-19, sharing
            // the menu titles' baseline.
            anchors.verticalCenterOffset: 1
            // An en space reproduces the gap macOS leaves between date and time.
            text: root.showDate ? root.dateText + " " + root.timeText : root.timeText
            font: Kirigami.Theme.defaultFont
            color: Kirigami.Theme.textColor
            textFormat: Text.PlainText
            wrapMode: Text.NoWrap
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: compact.vertical ? Text.ElideRight : Text.ElideNone
            width: compact.vertical ? compact.width : implicitWidth
        }
    }

    PlasmaCore.Dialog {
        id: panel

        // No frame of its own: each part is a glass bubble.
        location: PlasmaCore.Types.Floating
        backgroundHints: PlasmaCore.Dialog.NoBackground
        type: PlasmaCore.Dialog.PopupMenu
        flags: Qt.WindowStaysOnTopHint
        hideOnWindowDeactivate: true
        visible: false
        onVisibleChanged: if (!visible) root.panelHiddenAt = Date.now()
        onWidthChanged: if (visible) root.placePanel()

        mainItem: Item {
            width: panelView.implicitWidth
            height: panelView.implicitHeight + 2 * root.glassPad

            ClockPanelView {
                id: panelView
                y: root.glassPad
                width: implicitWidth
                height: implicitHeight
                now: root.currentDateTime
                onCloseRequested: panel.visible = false
                onHeightChanged: if (blurLoader.item) blurLoader.item.update()
            }

            // KWin blurs the desktop behind each bubble only.
            Loader {
                id: blurLoader
                source: "WindowBlur.qml"
                onLoaded: item.target = panelView
            }
            BlurSettler {
                active: panel.visible
                blur: blurLoader.item
            }
        }
    }
}
