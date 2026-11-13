/*
    MacTahoe Liquid KDE — Spotlight, as on the macOS Tahoe capture (1x).

    Idle: a 448 x 56 glass pill (the magnifier, "Spotlight Search") and four
    56 px glass buttons 12 px apart: Applications, Files, Actions and
    Clipboard. Typing turns it into one 720 px glass panel: the search row,
    an inset hairline, then 44 px result rows (24 px icon, 15 px name, the
    category on the right); the current row fills with the accent colour.
    Results come from KRunner (Milou's ResultsModel), filtered to one
    runner while a button is on.

    This item uses no Plasmoid API, so it can also be rendered on its own.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.milou as Milou
import org.kde.ki18n as KI18n

Item {
    // Translations from this widget's catalog in any host: Plasma, or the
    // MacTahoe Liquid KDE shell (Quickshell has no KLocalizedContext).
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.spotlight"
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

    id: view

    // The accent itself, in Plasma as in Quickshell (see AccentColor.qml);
    // every child inherits it.
    AccentColor {
        id: kdeAccent
    }
    Binding {
        target: view.Kirigami.Theme
        property: "highlightColor"
        value: kdeAccent.value
        when: kdeAccent.valid
        restoreMode: Binding.RestoreBindingOrValue
    }

    signal closeRequested()
    signal runCommand(string command)
    // The glass shapes moved or resized (the window itself does not).
    signal glassChanged()

    readonly property bool dark: (0.299 * Kirigami.Theme.textColor.r + 0.587 * Kirigami.Theme.textColor.g
                                  + 0.114 * Kirigami.Theme.textColor.b) > 0.5
    property alias query: field.text
    readonly property bool searching: field.text.length > 0
    // The runner a button filters to ("" for all).
    property string runner: ""
    readonly property int maxRows: 8
    readonly property int rowHeight: 44
    // The panel at its tallest: the window keeps this size, so it never
    // resizes while typing (a resize makes Plasma's Dialog drop the blur).
    readonly property int maxHeight: 60 + 9 + maxRows * rowHeight + 10

    implicitWidth: 720
    implicitHeight: searching || runner.length > 0
        ? panel.height : 56

    function reset(): void {
        field.text = "";
        runner = "";
        list.currentIndex = 0;
        field.forceActiveFocus();
    }

    function runCurrent(): void {
        if (list.count === 0) {
            return;
        }
        if (results.run(results.index(Math.max(0, list.currentIndex), 0))) {
            closeRequested();
        }
    }

    Milou.ResultsModel {
        id: results
        queryString: field.text
        singleRunner: view.runner
        limit: 30
    }

    // The panel: search row and results. Idle, only the 448 px pill part of
    // it shows, with the buttons beside it.
    Rectangle {
        id: panel

        readonly property bool expanded: view.searching || view.runner.length > 0
        // GlassBlur blurs the desktop behind this shape.
        readonly property real glassRadius: radius

        onWidthChanged: view.glassChanged()
        onHeightChanged: view.glassChanged()

        width: expanded ? view.width : 448
        height: expanded ? 60 + (list.count > 0 ? 9 + Math.min(list.count, view.maxRows) * view.rowHeight + 10 : 0) : 56
        radius: expanded ? 20 : height / 2
        // The Liquid Glass face (GlassSurface.qml); KWin blurs and refracts
        // the desktop behind it.
        color: "transparent"

        GlassSurface {
            anchors.fill: parent
            z: -1
            radius: parent.radius
        }

        Kirigami.Icon {
            id: magnifier
            x: 20
            y: (Math.min(parent.height, 60) - height) / 2
            width: 22
            height: 22
            // Bundled, see main.qml.
            source: Qt.resolvedUrl("icons/SearchIcon.svg")
            color: Kirigami.Theme.textColor
            isMask: true
        }

        TextInput {
            id: field

            anchors {
                left: magnifier.right
                leftMargin: 12
                right: parent.right
                rightMargin: 20
            }
            y: (Math.min(parent.height, 60) - height) / 2
            color: Kirigami.Theme.textColor
            selectionColor: Kirigami.Theme.highlightColor
            selectedTextColor: Kirigami.Theme.highlightedTextColor
            font.pixelSize: 19
            clip: true
            focus: true
            onTextChanged: list.currentIndex = 0

            Text {
                anchors.fill: parent
                visible: field.text.length === 0
                text: view.runner.length > 0 ? i18nc("@info:placeholder", "Search %1", activeButton.label)
                    : i18nc("@info:placeholder", "Spotlight Search")
                color: Kirigami.Theme.textColor
                opacity: 0.45
                font: field.font
            }

            Keys.onPressed: event => {
                if (event.key === Qt.Key_Escape) {
                    if (field.text.length > 0 || view.runner.length > 0) {
                        view.reset();
                    } else {
                        view.closeRequested();
                    }
                    event.accepted = true;
                } else if (event.key === Qt.Key_Down) {
                    list.currentIndex = Math.min(list.count - 1, list.currentIndex + 1);
                    event.accepted = true;
                } else if (event.key === Qt.Key_Up) {
                    list.currentIndex = Math.max(0, list.currentIndex - 1);
                    event.accepted = true;
                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                    view.runCurrent();
                    event.accepted = true;
                }
            }
        }

        Rectangle {
            anchors {
                left: parent.left
                right: parent.right
                margins: 16
            }
            y: 60
            height: 1
            visible: panel.expanded && list.count > 0
            color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                           Kirigami.Theme.textColor.b, 0.15)
        }

        ListView {
            id: list

            x: 10
            y: 69
            width: parent.width - 20
            height: Math.min(count, view.maxRows) * view.rowHeight
            visible: panel.expanded
            clip: true
            model: results
            currentIndex: 0
            boundsBehavior: Flickable.StopAtBounds
            highlightMoveDuration: 0

            delegate: Rectangle {
                id: row

                required property int index
                required property var model
                readonly property bool current: ListView.isCurrentItem

                width: ListView.view.width
                height: view.rowHeight
                radius: 10
                color: current ? Kirigami.Theme.highlightColor : "transparent"

                Kirigami.Icon {
                    id: icon
                    x: 14
                    anchors.verticalCenter: parent.verticalCenter
                    width: 24
                    height: 24
                    source: row.model.decoration
                }
                Text {
                    anchors {
                        left: icon.right
                        leftMargin: 14
                        right: category.left
                        rightMargin: 12
                        verticalCenter: parent.verticalCenter
                    }
                    text: row.model.display
                    color: row.current ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                    font.pixelSize: 15
                    elide: Text.ElideRight
                }
                Text {
                    id: category
                    anchors {
                        right: parent.right
                        rightMargin: 14
                        verticalCenter: parent.verticalCenter
                    }
                    text: row.model.category || ""
                    color: row.current ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                    opacity: row.current ? 0.85 : 0.5
                    font.pixelSize: 12
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: list.currentIndex = row.index
                    onClicked: {
                        list.currentIndex = row.index;
                        view.runCurrent();
                    }
                }
            }
        }
    }

    // Applications, Files, Actions, Clipboard.
    Row {
        id: buttons

        x: 448 + 12
        spacing: 12
        visible: !panel.expanded

        Repeater {
            model: [
                {glyph: "view-app-grid-symbolic", runner: "krunner_services",
                 label: i18nc("@action:button Spotlight", "Applications")},
                {glyph: "folder-symbolic", runner: "baloosearch",
                 label: i18nc("@action:button Spotlight", "Files")},
                {glyph: "view-list-symbolic", runner: "krunner_systemsettings",
                 label: i18nc("@action:button Spotlight", "Actions")},
                {glyph: "edit-paste-symbolic", runner: "",
                 label: i18nc("@action:button Spotlight", "Clipboard")},
            ]
            delegate: Rectangle {
                id: button

                required property var modelData
                readonly property real glassRadius: radius

                width: 56
                height: 56
                radius: 28
                color: hover.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent"

                GlassSurface {
                    anchors.fill: parent
                    z: -1
                    radius: parent.radius
                }

                Kirigami.Icon {
                    anchors.centerIn: parent
                    width: 22
                    height: 22
                    source: button.modelData.glyph
                    color: Kirigami.Theme.textColor
                    isMask: true
                }
                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        if (button.modelData.runner.length > 0) {
                            activeButton.label = button.modelData.label;
                            view.runner = button.modelData.runner;
                            field.forceActiveFocus();
                        } else {
                            // Klipper's history, as Plasma's clipboard shortcut shows it.
                            view.closeRequested();
                            view.runCommand("qdbus6 org.kde.klipper /klipper org.kde.klipper.klipper.showKlipperPopupMenu"
                                            + " || qdbus org.kde.klipper /klipper org.kde.klipper.klipper.showKlipperPopupMenu");
                        }
                    }
                }
            }
        }
    }

    QtObject {
        id: activeButton
        property string label: ""
    }
}
