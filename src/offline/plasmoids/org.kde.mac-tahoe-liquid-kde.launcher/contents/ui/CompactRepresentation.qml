import QtQuick 2.15
import QtQuick.Layouts 1.15

import org.kde.plasma.plasmoid 2.0
import org.kde.plasma.core as PlasmaCore

import org.kde.kirigami as Kirigami
import org.kde.mac.tahoe.launcher as NativeLauncher
import org.kde.mac.tahoe.liquid.dockzoom

NativeLauncher.DockIcon {
    id: root

    readonly property bool useCustomButtonImage: (Plasmoid.configuration.useCustomButtonImage && Plasmoid.configuration.customButtonImage.length != 0)

    NativeLauncher.IconThemeWatcher {
        onChanged: {
            root.source = "";
            root.source = Qt.binding(() => root.useCustomButtonImage
                ? Plasmoid.configuration.customButtonImage : Plasmoid.configuration.icon);
        }
    }

    inPanel: Plasmoid.formFactor === PlasmaCore.Types.Horizontal
        || Plasmoid.formFactor === PlasmaCore.Types.Vertical
    location: Plasmoid.location
    source: useCustomButtonImage ? Plasmoid.configuration.customButtonImage : Plasmoid.configuration.icon
    active: mouseArea.containsMouse
    // The horizontal Dock magnifies the whole Dock instead (DockZoom); the
    // button and its click target move together.
    readonly property bool horizontalDock: Plasmoid.formFactor === PlasmaCore.Types.Horizontal
    hovered: mouseArea.containsMouse && !horizontalDock
    transform: [
        Scale {
            origin.x: root.width / 2
            origin.y: root.height
            xScale: root.horizontalDock ? DockZoom.scaleFor(root) : 1
            yScale: xScale
        },
        Translate {
            x: root.horizontalDock ? DockZoom.shiftFor(root) : 0
        }
    ]

    DockZoomTracker {
        horizontal: root.horizontalDock
    }

    MouseArea
    {
        id: mouseArea

        anchors.fill: parent

        hoverEnabled: true

        onClicked: kicker.toggleDash()
    }
}
