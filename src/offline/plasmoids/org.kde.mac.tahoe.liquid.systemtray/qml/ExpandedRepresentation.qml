/*
    SPDX-FileCopyrightText: 2016 Marco Martin <mart@kde.org>
    SPDX-FileCopyrightText: 2020 Nate Graham <nate@kde.org>

    SPDX-License-Identifier: LGPL-2.0-or-later
*/
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.plasmoid

Item {
    id: popup

    // MacTahoe Liquid KDE: the other items as a 280 px macOS menu, as tall as its
    // rows; an open applet gets Plasma's usual room.
    readonly property bool menuMode: !systemTrayState.activeApplet
    readonly property int menuHeight: Math.min(Kirigami.Units.gridUnit * 30,
        hiddenItemsView.layout.itemCount * 28 + settingsRow.height + 9)
    Layout.minimumWidth: menuMode ? 280 : Kirigami.Units.gridUnit * 24
    Layout.preferredWidth: Layout.minimumWidth
    Layout.minimumHeight: menuMode ? menuHeight : Kirigami.Units.gridUnit * 24
    Layout.preferredHeight: Layout.minimumHeight
    Layout.maximumWidth: menuMode ? 280 : -1
    Layout.maximumHeight: menuMode ? menuHeight : -1

    property alias hiddenLayout: hiddenItemsView.layout
    property alias plasmoidContainer: container

    // Header
    PlasmaExtras.PlasmoidHeading {
        id: plasmoidHeading
        visible: !popup.menuMode
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
        }
        height: trayHeading.height + bottomPadding + container.headingHeight
        Behavior on height {
            NumberAnimation { duration: Kirigami.Units.shortDuration / 2; easing.type: Easing.InOutQuad }
        }
    }

    // Main content layout
    ColumnLayout {
        id: expandedRepresentation
        anchors.fill: parent
        // TODO: remove this so the scrollview fully touches the header;
        // add top padding internally
        spacing: popup.menuMode ? 4 : plasmoidHeading.bottomPadding

        // Header content layout
        RowLayout {
            id: trayHeading
            Layout.fillWidth: true
            // No title row over the menu (macOS menus have none).
            visible: !popup.menuMode

            PlasmaComponents.ToolButton {
                id: backButton
                visible: systemTrayState.activeApplet && systemTrayState.activeApplet.expanded && (popup.hiddenLayout.itemCount > 0)
                icon.name: mirrored ? "go-previous-symbolic-rtl" : "go-previous-symbolic"

                display: PlasmaComponents.AbstractButton.IconOnly
                text: i18nc("@action:button", "Go Back")

                KeyNavigation.down: hiddenItemsView.visible ? popup.hiddenLayout : container

                onClicked: if (typeof systemTrayState.activeApplet?.backAction !== "undefined" && systemTrayState.activeApplet.backAction.enabled) {
                    systemTrayState.activeApplet?.backAction.trigger()
                } else {
                    systemTrayState.setActiveApplet(null)
                }
            }

            Kirigami.Heading {
                Layout.fillWidth: true
                leftPadding: systemTrayState.activeApplet ? 0 : Kirigami.Units.largeSpacing

                level: 1
                text: systemTrayState.activeApplet ? systemTrayState.activeApplet.plasmoid.title : i18n("Status and Notifications")
                maximumLineCount: 1
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }

            Repeater {
                id: primaryActionButtons

                model: {
                    if (actionsButton.applet === null) {
                        return [];
                    }
                    return actionsButton.applet.Plasmoid.contextualActions.filter(action => {
                        return !action.isSeparator && action.priority === PlasmaCore.Action.HighPriority;
                    });
                }

                delegate: PlasmaComponents.ToolButton {
                    id: actionButton
                    required property int index
                    required property PlasmaCore.Action modelData
                    // We cannot use `action` as it is already a QQuickAction property of the button
                    property PlasmaCore.Action qAction: modelData

                    visible: qAction && qAction.visible

                    // NOTE: it needs an IconItem because QtQuickControls2 buttons cannot load QIcons as their icon
                    contentItem: Kirigami.Icon {
                        anchors.centerIn: parent
                        active: actionButton.hovered
                        implicitWidth: Kirigami.Units.iconSizes.smallMedium
                        implicitHeight: implicitWidth
                        source: actionButton.qAction ? actionButton.qAction.icon.name : ""
                    }

                    enabled: qAction && qAction.enabled
                    checkable: qAction && qAction.checkable
                    checked: qAction && qAction.checked
                    display: PlasmaComponents.AbstractButton.IconOnly
                    text: qAction ? qAction.text : ""

                    KeyNavigation.down: backButton.KeyNavigation.down
                    KeyNavigation.left: (index > 0) ? primaryActionButtons.itemAt(index - 1) : backButton
                    KeyNavigation.right: (index < primaryActionButtons.count - 1) ? primaryActionButtons.itemAt(index + 1) :
                                                            actionsButton.visible ? actionsButton : actionsButton.KeyNavigation.right

                    PlasmaComponents.ToolTip {
                        text: actionButton.text
                    }

                    onClicked: {
                        if (qAction) {
                            qAction.trigger();
                        }
                    }
                }
            }

            PlasmaComponents.ToolButton {
                id: actionsButton
                visible: visibleActions > 0
                enabled: visibleActions > 1 || (singleAction && singleAction.enabled)
                checked: visibleActions > 1 ? configMenu.status !== PlasmaExtras.Menu.Closed : singleAction && singleAction.checked
                property QtObject applet: systemTrayState.activeApplet || root
                property int visibleActions: actions.length
                property PlasmaCore.Action singleAction: visibleActions === 1 && menuItemFactory.object ? menuItemFactory.object.action : null

                readonly property var actions: {
                    if (!applet) {
                        return [];
                    }

                    return applet.plasmoid.contextualActions
                        .filter(action => {
                            return action.visible &&
                            action.priority === PlasmaCore.Action.NormalPriority &&
                            action !== applet.plasmoid.internalAction("configure");
                        })
                        // squash separators
                        .reduce((dstActions, action, i, srcActions) => {
                            if (!action.isSeparator) {
                                const prevAction = srcActions[i - 1];
                                if (prevAction?.isSeparator && dstActions.length > 0) {
                                    dstActions.push(prevAction);
                                }
                                dstActions.push(action);
                            }
                            return dstActions;
                        }, []);
                }

                icon.name: "application-menu"
                checkable: visibleActions > 1 || (singleAction && singleAction.checkable)
                contentItem.opacity: visibleActions > 1

                display: PlasmaComponents.AbstractButton.IconOnly
                text: actionsButton.singleAction ? actionsButton.singleAction.text : i18n("More actions")

                Accessible.role: actionsButton.singleAction ? Accessible.Button : Accessible.ButtonMenu

                KeyNavigation.down: backButton.KeyNavigation.down
                KeyNavigation.right: configureButton.visible ? configureButton : configureButton.KeyNavigation.right

                // NOTE: it needs a Kirigami.Icon because QtQuickControls2 buttons cannot load QIcons as their icon
                Kirigami.Icon {
                    parent: actionsButton
                    anchors.centerIn: parent
                    active: actionsButton.hovered
                    implicitWidth: Kirigami.Units.iconSizes.smallMedium
                    implicitHeight: implicitWidth
                    source: actionsButton.singleAction !== null ? actionsButton.singleAction.icon.name : ""
                    visible: actionsButton.singleAction
                }
                onToggled: {
                    if (visibleActions > 1) {
                        if (checked) {
                            configMenu.openRelative();
                        } else {
                            configMenu.close();
                        }
                    }
                }
                onClicked: {
                    if (singleAction) {
                        singleAction.trigger();
                    }
                }
                PlasmaComponents.ToolTip {
                    text: actionsButton.text
                }
                PlasmaExtras.Menu {
                    id: configMenu
                    visualParent: actionsButton
                    placement: PlasmaExtras.Menu.BottomPosedLeftAlignedPopup
                }

                Instantiator {
                    id: menuItemFactory

                    model: actionsButton.actions

                    delegate: PlasmaExtras.MenuItem {
                        id: menuItem
                        required property PlasmaCore.Action modelData
                        action: modelData
                    }

                    onObjectAdded: (index, object) => {
                        configMenu.addMenuItem(object);
                    }

                    onObjectRemoved: (index, object) => {
                        configMenu.removeMenuItem(object)
                    }
                }
            }
            PlasmaComponents.ToolButton {
                id: configureButton
                icon.name: "configure"
                visible: actionsButton.applet && actionsButton.applet.plasmoid.internalAction("configure")

                display: PlasmaComponents.AbstractButton.IconOnly
                text: actionsButton.applet?.plasmoid.internalAction("configure").text ?? ""

                KeyNavigation.down: backButton.KeyNavigation.down
                KeyNavigation.left: actionsButton.visible ? actionsButton : actionsButton.KeyNavigation.left
                KeyNavigation.right: pinButton

                PlasmaComponents.ToolTip {
                    text: parent.visible ? parent.text : ""
                }
                onClicked: actionsButton.applet.plasmoid.internalAction("configure").trigger();
            }

            PlasmaComponents.ToolButton {
                id: pinButton
                // macOS menus close when clicked away.
                visible: false
                checkable: true
                checked: Plasmoid.configuration.pin
                onToggled: Plasmoid.configuration.pin = checked
                icon.name: "window-pin"

                display: PlasmaComponents.AbstractButton.IconOnly
                text: i18n("Keep Open")

                KeyNavigation.down: backButton.KeyNavigation.down
                KeyNavigation.left: configureButton.visible ? configureButton : configureButton.KeyNavigation.left
                KeyNavigation.tab: hiddenItemsView.visible ? hiddenItemsView.layout : container.currentItem?.nextItemInFocusChain() ?? null

                PlasmaComponents.ToolTip {
                    text: parent.text
                }
            }
        }

        // Grid view of all available items
        HiddenItemsView {
            id: hiddenItemsView
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !systemTrayState.activeApplet

            KeyNavigation.up: pinButton

            onVisibleChanged: {
                if (visible) {
                    layout.forceActiveFocus();
                    systemTrayState.oldVisualIndex = systemTrayState.newVisualIndex = -1;
                }
            }
        }

        // A hairline, then the tray's settings, as a macOS menu ends.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            visible: popup.menuMode
            color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                           Kirigami.Theme.textColor.b, 0.15)
        }
        Rectangle {
            id: settingsRow
            Layout.fillWidth: true
            Layout.preferredHeight: 28
            visible: popup.menuMode
            radius: 6
            color: settingsArea.containsMouse ? Kirigami.Theme.highlightColor : "transparent"
            PlasmaComponents.Label {
                x: 8
                anchors.verticalCenter: parent.verticalCenter
                text: i18nc("@action:button", "Status Items Settings…")
                font.pixelSize: 13
                color: settingsArea.containsMouse ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
            }
            MouseArea {
                id: settingsArea
                anchors.fill: parent
                hoverEnabled: true
                onClicked: {
                    systemTrayState.expanded = false;
                    Plasmoid.internalAction("configure").trigger();
                }
            }
        }

        // Container for currently visible item
        PlasmoidPopupsContainer {
            id: container
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: systemTrayState.activeApplet

            // We need to add margin on the top so it matches the dialog's own margin
            Layout.topMargin: mergeHeadings ? 0 : dialog.topPadding

            KeyNavigation.up: pinButton
            KeyNavigation.backtab: pinButton

            onVisibleChanged: {
                if (visible) {
                    forceActiveFocus();
                }
            }
        }
    }

    // Footer
    PlasmaExtras.PlasmoidHeading {
        id: plasmoidFooter
        position: PlasmaComponents.ToolBar.Footer
        anchors {
            bottom: parent.bottom
            left: parent.left
            right: parent.right
        }
        visible: container.appletHasFooter
        height: container.footerHeight
        // So that it doesn't appear over the content view, which results in
        // the footer controls being inaccessible
        z: -9999
    }
}
