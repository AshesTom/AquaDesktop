import QtQuick 2.15
import QtQuick.Layouts 1.15

import org.kde.plasma.plasmoid 2.0
import org.kde.plasma.core as PlasmaCore

import org.kde.kirigami as Kirigami
import org.kde.mac.tahoe.liquid.dockzoom

Item {
    id: root

    readonly property bool useCustomButtonImage: (Plasmoid.configuration.useCustomButtonImage && Plasmoid.configuration.customButtonImage.length != 0)

    // Same proportions as the Dock task icons (see the task manager's
    // LayoutMetrics.js): 68.5% of the thickness, 16% below the top edge, in a
    // slot that leaves the panel's applet spacing out of the icon gap.
    readonly property bool dockLayout: Plasmoid.formFactor === PlasmaCore.Types.Horizontal
    // Hidden from the Dock: the pinned "Apps" launcher stands in for it.
    readonly property bool hiddenInDock: dockLayout && Plasmoid.configuration.hiddenInDock
    readonly property int dockIconSize: Math.round(height * 0.685)

    // The Launcher starts the Dock, so it widens the glass on its leading
    // side while the Dock magnifies (see DockZoom); its icon stays on the
    // trailing side, next to the apps.
    readonly property int dockBaseWidth: Math.round(height * 0.75) - Kirigami.Units.smallSpacing
    Layout.minimumWidth: hiddenInDock ? 0 : dockLayout ? dockBaseWidth + DockZoom.growthFor(root) : -1
    Layout.maximumWidth: dockLayout ? Layout.minimumWidth : -1
    visible: !hiddenInDock

    function updateGrowthOwner(): void {
        if (dockLayout && !hiddenInDock) {
            DockZoom.registerGrowthOwner(root, dockBaseWidth, true);
        } else {
            DockZoom.unregisterGrowthOwner(root);
        }
    }
    onDockBaseWidthChanged: updateGrowthOwner()
    onDockLayoutChanged: updateGrowthOwner()
    onHiddenInDockChanged: updateGrowthOwner()
    Component.onDestruction: DockZoom.unregisterGrowthOwner(root)

    DockZoomTracker {
        horizontal: root.dockLayout
    }

    // Icon and click target magnify together (see DockZoomSlot).
    DockZoomSlot {
        id: slot

        horizontal: root.dockLayout
        x: root.dockLayout ? root.width - root.dockBaseWidth : 0
        width: root.dockLayout ? root.dockBaseWidth : root.width
        height: root.height

        Kirigami.Icon {
            id: buttonIcon

            readonly property real scaleFactor: Plasmoid.configuration.activationIndicator ? 0.65 : 1

            readonly property real size: root.dockLayout ? Math.round(root.dockIconSize * scaleFactor) : parent.width * scaleFactor
            readonly property real tall: root.dockLayout ? size : parent.height * scaleFactor
            // Rasterized larger while the Dock magnifies (see DockZoomSlot.raster;
            // 1 with an older dockzoom module).
            width: size * (slot.raster || 1)
            height: tall * (slot.raster || 1)
            scale: 1 / (slot.raster || 1)
            transformOrigin: Item.TopLeft
            x: Math.round((parent.width - size) / 2)
            y: root.dockLayout ? Math.round(root.height * 0.16 + (root.dockIconSize - tall) / 2)
                               : Math.round((parent.height - tall) / 2)
            roundToIconSize: !root.dockLayout

            source: useCustomButtonImage ? Plasmoid.configuration.customButtonImage : Plasmoid.configuration.icon

            active: mouseArea.containsMouse

            smooth: true
        }

        MouseArea {
            id: mouseArea

            anchors.fill: parent

            hoverEnabled: true

            onClicked: kicker.toggleDash()
        }
    }

    Component.onCompleted: {
        updateGrowthOwner();
    }
}
