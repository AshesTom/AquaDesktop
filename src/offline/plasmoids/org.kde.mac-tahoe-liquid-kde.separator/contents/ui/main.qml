/*
    MacTahoe Liquid KDE — Dock separator.

    The thin vertical line macOS draws between the app icons and the
    Trash. Sized from the Dock thickness so the gap on each side matches
    the macOS Dock: ~73% of the thickness tall (75% of the glass), ~26%
    wide, #595959 on the dark Dock.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import org.kde.mac.tahoe.liquid.dockzoom

PlasmoidItem {
    id: root

    readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    Plasmoid.constraintHints: Plasmoid.CanFillArea

    preferredRepresentation: fullRepresentation

    fullRepresentation: Item {
        id: separatorItem

        readonly property real thickness: root.vertical ? width : height
        readonly property int gap: Math.max(Kirigami.Units.smallSpacing, Math.round(thickness * 0.26))

        Layout.minimumWidth: root.vertical ? -1 : gap
        Layout.maximumWidth: root.vertical ? -1 : gap
        Layout.minimumHeight: root.vertical ? gap : -1
        Layout.maximumHeight: root.vertical ? gap : -1
        Layout.fillHeight: !root.vertical
        Layout.fillWidth: root.vertical

        DockZoomTracker {
            horizontal: !root.vertical
        }

        Rectangle {
            id: line

            anchors.centerIn: parent
            // The divider keeps its size but moves aside with its magnified
            // neighbours, like the macOS Dock.
            transform: Translate {
                x: root.vertical ? 0 : DockZoom.shiftFor(line)
            }
            width: root.vertical ? Math.round(parent.thickness * 0.73) : 1
            height: root.vertical ? 1 : Math.round(parent.thickness * 0.73)
            color: Kirigami.Theme.textColor
            opacity: 0.28
        }
    }
}
