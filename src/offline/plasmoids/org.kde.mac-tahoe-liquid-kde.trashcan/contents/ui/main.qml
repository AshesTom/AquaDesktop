/*
    Fork: MacTahoe Liquid KDE — adds configurable empty/full icons.
    Replaces compiled C++ backend with shell commands so no build step
    is needed.

    SPDX-License-Identifier: GPL-2.0-or-later
*/
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.extras as PlasmaExtras
import org.kde.draganddrop as DragDrop
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasma5support as P5Support
import org.kde.mac.tahoe.launcher as NativeLauncher
import org.kde.mac.tahoe.liquid.dockzoom

PlasmoidItem {
    id: root

    readonly property bool inPanel: (Plasmoid.location === PlasmaCore.Types.TopEdge
        || Plasmoid.location === PlasmaCore.Types.RightEdge
        || Plasmoid.location === PlasmaCore.Types.BottomEdge
        || Plasmoid.location === PlasmaCore.Types.LeftEdge)

    readonly property string cfgEmptyIcon: Plasmoid.configuration.emptyIcon || "user-trash"
    readonly property string cfgFullIcon: Plasmoid.configuration.fullIcon || "user-trash-full"

    property int trashCount: 0
    readonly property bool hasContents: trashCount > 0
    property bool emptying: false
    property bool containsAcceptableDrag: false

    Plasmoid.title: i18n("Trash")
    toolTipSubText: {
        if (emptying) {
            return "Emptying\u2026";
        } else if (hasContents) {
            return trashCount === 1 ? "One item" : trashCount + " items";
        }
        return "Empty";
    }

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    // In the Dock, take the full thickness so the icon can use the same
    // macOS proportions as the task icons (see the task manager's
    // LayoutMetrics.js): 68.5% of the thickness, 16% below the top edge.
    readonly property bool dockLayout: inPanel && Plasmoid.formFactor === PlasmaCore.Types.Horizontal
    Plasmoid.constraintHints: dockLayout ? Plasmoid.CanFillArea : Plasmoid.NoHint
    Plasmoid.icon: hasContents ? cfgFullIcon : cfgEmptyIcon
    Plasmoid.status: hasContents ? PlasmaCore.Types.ActiveStatus
                                : PlasmaCore.Types.PassiveStatus
    Plasmoid.busy: emptying

    Plasmoid.onActivated: Qt.openUrlExternally("trash:/")

    // trash monitoring (polls every 3 s)
    P5Support.DataSource {
        id: trashMonitor
        engine: "executable"
        connectedSources: [cmd]
        interval: 3000

        readonly property string cmd:
            "ls -1A \"$HOME/.local/share/Trash/files/\" 2>/dev/null | wc -l"

        onNewData: (sourceName, data) => {
            if (sourceName === cmd) {
                let n = parseInt(data["stdout"]) || 0;
                if (n !== root.trashCount) {
                    root.trashCount = n;
                }
                if (root.emptying && n === 0) {
                    root.emptying = false;
                }
            }
        }
    }

    // command runner
    P5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []

        onNewData: (sourceName, data) => {
            disconnectSource(sourceName);
        }

        function exec(cmd: string): void {
            connectSource(cmd);
        }
    }

    // keyboard
    Keys.onPressed: event => {
        switch (event.key) {
        case Qt.Key_Space:
        case Qt.Key_Enter:
        case Qt.Key_Return:
        case Qt.Key_Select:
            Plasmoid.activated();
            break;
        }
    }
    Accessible.name: Plasmoid.title
    Accessible.description: toolTipSubText
    Accessible.role: Accessible.Button

    // context menu
    Plasmoid.contextualActions: [
        PlasmaCore.Action {
            text: i18n("Open")
            icon.name: "document-open-symbolic"
            onTriggered: Plasmoid.activated()
        },
        PlasmaCore.Action {
            text: i18n("Empty Trash")
            icon.name: "trash-empty-symbolic"
            enabled: root.hasContents && !root.emptying
            onTriggered: {
                root.emptying = true;
                executable.exec(
                    "kdialog --warningyesno 'Permanently delete all items in the trash?' "
                    + "--title 'Empty Trash' && ktrash6 --empty "
                    + "|| true"
                );
            }
        }
    ]

    // representation
    preferredRepresentation: fullRepresentation
    fullRepresentation: MouseArea {
        id: mouseArea

        activeFocusOnTab: true
        // In the Dock, clicks and hover go to the magnified slot below, so
        // they land where the Trash is drawn.
        hoverEnabled: !root.dockLayout
        acceptedButtons: root.dockLayout ? Qt.NoButton : Qt.LeftButton

        // The Trash ends the Dock, so it widens the glass while the Dock
        // magnifies (see DockZoom); its icon stays on the leading side.
        readonly property int dockBaseWidth: Math.round(height * 0.75) - Kirigami.Units.smallSpacing
        Layout.minimumWidth: root.dockLayout ? dockBaseWidth + DockZoom.growthFor(mouseArea) : -1
        Layout.maximumWidth: root.dockLayout ? Layout.minimumWidth : -1

        function updateGrowthOwner(): void {
            if (root.dockLayout) {
                DockZoom.registerGrowthOwner(mouseArea, dockBaseWidth);
            } else {
                DockZoom.unregisterGrowthOwner(mouseArea);
            }
        }
        onDockBaseWidthChanged: updateGrowthOwner()
        Component.onCompleted: updateGrowthOwner()
        Component.onDestruction: DockZoom.unregisterGrowthOwner(mouseArea)

        onClicked: Plasmoid.activated()

        DockZoomTracker {
            horizontal: root.dockLayout
        }

        DragDrop.DropArea {
            anchors.fill: parent
            preventStealing: true

            onDragEnter: event => {
                let dominated = false;
                for (let i = 0; i < event.mimeData.urls.length; i++) {
                    if (event.mimeData.urls[i].toString().startsWith("file://")) {
                        dominated = true;
                        break;
                    }
                }
                root.containsAcceptableDrag = dominated;
                if (!dominated) {
                    // DropArea defaults to accepting a drag unless told
                    // otherwise — without this, non-file drags (plain
                    // text, a browser URL) keep this DropArea as their
                    // accepted target instead of passing through to
                    // whatever's behind the trash icon.
                    event.ignore();
                }
            }
            onDragLeave: root.containsAcceptableDrag = false

            onDrop: event => {
                root.containsAcceptableDrag = false;

                let paths = [];
                for (let i = 0; i < event.mimeData.urls.length; i++) {
                    let url = event.mimeData.urls[i].toString();
                    if (url.startsWith("file://")) {
                        let path = decodeURIComponent(url.substring(7));
                        paths.push("'" + path.replace(/'/g, "'\\''") + "'");
                    }
                }

                if (paths.length > 0) {
                    executable.exec("gio trash " + paths.join(" "));
                    event.accept(Qt.MoveAction);
                } else {
                    event.accept(Qt.IgnoreAction);
                }
            }
        }

        Kirigami.Icon {
            id: trashIcon
            NativeLauncher.IconThemeWatcher {
                onChanged: {
                    trashIcon.source = "";
                    trashIcon.source = Qt.binding(() => Plasmoid.icon);
                }
            }
            source: Plasmoid.icon
            visible: !root.dockLayout
            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
                bottom: root.inPanel ? parent.bottom : text.top
            }
            active: mouseArea.containsMouse || root.containsAcceptableDrag
        }

        DockZoomSlot {
            id: dockSlot

            horizontal: root.dockLayout
            visible: root.dockLayout
            width: mouseArea.dockBaseWidth
            height: mouseArea.height

            Kirigami.Icon {
                id: dockIcon
                NativeLauncher.IconThemeWatcher {
                    onChanged: {
                        dockIcon.source = "";
                        dockIcon.source = Qt.binding(() => Plasmoid.icon);
                    }
                }
                source: Plasmoid.icon
                readonly property real size: Math.round(dockSlot.height * 0.685)
                width: size * (dockSlot.raster || 1)
                height: width
                scale: 1 / (dockSlot.raster || 1)
                transformOrigin: Item.TopLeft
                x: Math.round((dockSlot.width - size) / 2)
                y: Math.round(dockSlot.height * 0.16)
                roundToIconSize: false
                active: dockHit.containsMouse || root.containsAcceptableDrag
            }

            MouseArea {
                id: dockHit
                anchors.fill: parent
                hoverEnabled: true
                onClicked: Plasmoid.activated()
            }
        }

        PlasmaExtras.ShadowedLabel {
            id: text
            anchors {
                horizontalCenter: parent.horizontalCenter
                bottom: parent.bottom
            }
            width: Math.round(text.implicitWidth + Kirigami.Units.smallSpacing)
            text: Plasmoid.title + "\n" + root.toolTipSubText
            horizontalAlignment: Text.AlignHCenter
            visible: !root.inPanel
        }

        PlasmaCore.ToolTipArea {
            // Follows the magnified slot in the Dock.
            parent: root.dockLayout ? dockSlot : mouseArea
            anchors.fill: parent
            mainText: Plasmoid.title
            subText: root.toolTipSubText
        }
    }
}
