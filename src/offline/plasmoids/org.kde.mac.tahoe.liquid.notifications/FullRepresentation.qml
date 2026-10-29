/*
    SPDX-FileCopyrightText: 2018-2019 Kai Uwe Broulik <kde@privat.broulik.de>
    SPDX-FileCopyrightText: 2026 MacTahoe Liquid KDE contributors

    SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/

/*
    MacTahoe Liquid KDE — the notification history as macOS Tahoe's Notification
    Center, laid out after NextKde's history: no panel behind it, every
    notification its own glass card (24 px corners, no drawn border), the
    Do Not Disturb row a glass card on top. Notifications are grouped by
    app; a collapsed group is a stack, its newest card with up to two
    cards peeking under it, and a click expands it into one card per
    notification under a row with the app's name, "Show Fewer" and a
    button closing the group. Every card and pill declares `glassRadius`,
    so GlassBlur (main.qml) blurs the desktop behind each one on its own.
*/

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.extras as PlasmaExtras
import org.kde.kirigami as Kirigami

import org.kde.coreaddons as KCoreAddons

import org.kde.notificationmanager as NotificationManager
import plasma.applet.org.kde.mac.tahoe.liquid.notifications as Notifications

import "delegates" as Delegates
import "components" as Components

Item {
    id: fullRepresentationRoot

    // TODO these should be configurable in the future
    readonly property int dndMorningHour: 6
    readonly property int dndEveningHour: 20
    required property PlasmoidItem appletInterface
    required property NotificationManager.Settings notificationSettings
    required property PlasmaCore.Action clearHistoryAction
    required property NotificationManager.Notifications historyModel

    // The history's window is on screen.
    property bool shown: false
    // The tallest the history may grow: the screen's room under the menu bar.
    property int maximumHeight: Kirigami.Units.gridUnit * 40

    // 356 px wide like the clock panel, cards 8 px apart; a collapsed
    // group's cards peek 6 px under its newest one, 8 px narrower per side
    // each (NextKde's stack).
    readonly property int cardSpacing: 8
    readonly property int stackStep: 6
    readonly property int stackInset: 8
    // White content on dark glass.
    readonly property bool dark: (0.299 * Kirigami.Theme.textColor.r + 0.587 * Kirigami.Theme.textColor.g
                                  + 0.114 * Kirigami.Theme.textColor.b) > 0.5

    // A glass shape moved, appeared or went away: GlassBlur asks KWin again.
    signal glassChanged()

    implicitWidth: 356
    implicitHeight: Math.min(maximumHeight, headerCard.height + cardSpacing
        + (list.count > 0 ? list.contentHeight : emptyCard.height))

    onHeightChanged: glassChanged()
    onShownChanged: {
        if (shown) {
            list.positionViewAtBeginning();
            list.currentIndex = -1;
            for (let i = 0; i < fullRepresentationRoot.historyModel.count; i++)  {
                let rowIdx = fullRepresentationRoot.historyModel.index(i, 0);
                fullRepresentationRoot.historyModel.setData(rowIdx, true, NotificationManager.Notifications.ReadRole);
            }
        }
        glassChanged();
    }

    Keys.onDownPressed: dndCheck.forceActiveFocus(Qt.TabFocusReason);

    // A round button on the glass: the cards' close, configure and restore
    // buttons, and the group row's buttons.
    component RoundButton: Rectangle {
        id: roundButton

        property string iconName
        property string glyph
        property string toolTip
        signal clicked()

        width: 20
        height: 20
        radius: width / 2
        color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                       Kirigami.Theme.backgroundColor.b, 0.95)
        border.width: 1
        border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                              Kirigami.Theme.textColor.b, 0.18)

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -1
            visible: roundButton.glyph !== ""
            text: roundButton.glyph
            color: Kirigami.Theme.textColor
            opacity: roundButtonArea.pressed ? 0.5 : 0.8
            font.pixelSize: 15
            font.weight: Font.DemiBold
        }
        Kirigami.Icon {
            anchors.centerIn: parent
            width: 14
            height: 14
            visible: roundButton.iconName !== ""
            source: roundButton.iconName
            opacity: roundButtonArea.pressed ? 0.5 : 0.8
        }
        MouseArea {
            id: roundButtonArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: roundButton.clicked()
        }
        PlasmaComponents3.ToolTip {
            text: roundButton.toolTip
            visible: roundButtonArea.containsMouse && text !== ""
        }

        Accessible.role: Accessible.Button
        Accessible.name: toolTip
        Accessible.onPressAction: clicked()
    }

    // Do Not Disturb, its end, and Clear All / Configure.
    Components.GlassCard {
        id: headerCard
        width: parent.width
        height: header.implicitHeight + 2 * 8
        onHeightChanged: fullRepresentationRoot.glassChanged()

        ColumnLayout {
            id: header
            anchors {
                left: parent.left
                right: parent.right
                verticalCenter: parent.verticalCenter
                leftMargin: 12
                rightMargin: 8
            }
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                spacing: 0

                PlasmaComponents3.Switch {
                    id: dndCheck
                    enabled: NotificationManager.Server.valid
                    text: i18nd("plasma_applet_org.kde.plasma.notifications", "Do not disturb")
                    icon.name: "notifications-disabled"
                    checkable: true
                    checked: Notifications.Globals.inhibited

                    Accessible.onPressAction: if (Notifications.Globals.inhibited) {
                        Notifications.Globals.revokeInhibitions();
                    } else {
                        let date = new Date();
                        date.setFullYear(date.getFullYear() + 1);
                        fullRepresentationRoot.notificationSettings.notificationsInhibitedUntil = date;
                        fullRepresentationRoot.notificationSettings.save();
                    }
                    KeyNavigation.down: list
                    KeyNavigation.tab: list

                    // Let the menu open on press
                    onPressed: {
                        if (!Notifications.Globals.inhibited) {
                            dndMenu.date = new Date();
                            // shows ontop of CheckBox to hide the fact that it's unchecked
                            // until you actually select something :)
                            dndMenu.open(0, 0);
                        }
                    }
                    // but disable only on click
                    onClicked: {
                        if (Notifications.Globals.inhibited) {
                            Notifications.Globals.revokeInhibitions();
                        }
                    }


                    PlasmaExtras.ModelContextMenu {
                        id: dndMenu
                        property date date
                        visualParent: dndCheck

                        onClicked: {
                            fullRepresentationRoot.notificationSettings.notificationsInhibitedUntil = model.date;
                            fullRepresentationRoot.notificationSettings.save();
                        }

                        model: {
                            var model = [];

                            // For 1 hour
                            var d = dndMenu.date;
                            d.setHours(d.getHours() + 1);
                            d.setSeconds(0);
                            model.push({date: d, text: i18nd("plasma_applet_org.kde.plasma.notifications", "For 1 hour")});

                            d = dndMenu.date;
                            d.setHours(d.getHours() + 4);
                            d.setSeconds(0);
                            model.push({date: d, text: i18nd("plasma_applet_org.kde.plasma.notifications", "For 4 hours")});

                            // Until this evening
                            if (dndMenu.date.getHours() < fullRepresentationRoot.dndEveningHour) {
                                d = dndMenu.date;
                                // TODO make the user's preferred time schedule configurable
                                d.setHours(fullRepresentationRoot.dndEveningHour);
                                d.setMinutes(0);
                                d.setSeconds(0);
                                model.push({date: d, text: i18nd("plasma_applet_org.kde.plasma.notifications", "Until this evening")});
                            }

                            // Until next morning
                            if (dndMenu.date.getHours() > fullRepresentationRoot.dndMorningHour) {
                                d = dndMenu.date;
                                d.setDate(d.getDate() + 1);
                                d.setHours(fullRepresentationRoot.dndMorningHour);
                                d.setMinutes(0);
                                d.setSeconds(0);
                                model.push({date: d, text: i18nd("plasma_applet_org.kde.plasma.notifications", "Until tomorrow morning")});
                            }

                            // Until Monday
                            // show Friday and Saturday, Sunday is "0" but for that you can use "until tomorrow morning"
                            if (dndMenu.date.getDay() >= 5) {
                                d = dndMenu.date;
                                d.setHours(fullRepresentationRoot.dndMorningHour);
                                // wraps around if necessary
                                d.setDate(d.getDate() + (7 - d.getDay() + 1));
                                d.setMinutes(0);
                                d.setSeconds(0);
                                model.push({date: d, text: i18nd("plasma_applet_org.kde.plasma.notifications", "Until Monday")});
                            }

                            // Until "turned off"
                            d = dndMenu.date;
                            // Just set it to one year in the future so we don't need yet another "do not disturb enabled" property
                            d.setFullYear(d.getFullYear() + 1);
                            model.push({date: d, text: i18nd("plasma_applet_org.kde.plasma.notifications", "Until manually disabled")});

                            return model;
                        }
                    }
                }
                Item {
                    Layout.fillWidth: true
                }

                PlasmaComponents3.ToolButton {
                    Accessible.name: fullRepresentationRoot.clearHistoryAction.text
                    icon.name: "edit-clear-history"
                    enabled: fullRepresentationRoot.clearHistoryAction.visible
                    onClicked: fullRepresentationRoot.clearHistoryAction.trigger()

                    PlasmaComponents3.ToolTip {
                        text: parent.Accessible.name
                    }
                }

                // The tray's heading had it: the history has its own window.
                PlasmaComponents3.ToolButton {
                    readonly property PlasmaCore.Action configureAction: Plasmoid.internalAction("configure")
                    visible: configureAction !== null && configureAction.visible
                    Accessible.name: configureAction ? configureAction.text.replace("&", "") : ""
                    icon.name: "configure"
                    onClicked: {
                        fullRepresentationRoot.appletInterface.closePlasmoid();
                        configureAction.trigger();
                    }

                    PlasmaComponents3.ToolTip {
                        text: parent.Accessible.name
                    }
                }
            }

            PlasmaExtras.DescriptiveLabel {
                Layout.leftMargin: dndCheck.mirrored ? 0 : dndCheck.indicator.width + 2 * dndCheck.spacing + Kirigami.Units.iconSizes.smallMedium
                Layout.rightMargin: dndCheck.mirrored ? dndCheck.indicator.width + 2 * dndCheck.spacing + Kirigami.Units.iconSizes.smallMedium : 0
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                text: {
                    if (!Notifications.Globals.inhibited) {
                        return "";
                    }

                    var inhibitedUntil = fullRepresentationRoot.notificationSettings.notificationsInhibitedUntil;
                    var inhibitedUntilTime = inhibitedUntil.getTime();
                    var inhibitedByApp = fullRepresentationRoot.notificationSettings.notificationsInhibitedByApplication;
                    var inhibitedByMirroredScreens = fullRepresentationRoot.notificationSettings.inhibitNotificationsWhenScreensMirrored
                                                        && fullRepresentationRoot.notificationSettings.screensMirrored;
                    var inhibitedByFullscreen = fullRepresentationRoot.notificationSettings.inhibitNotificationsWhenFullscreen
                                                        && fullRepresentationRoot.notificationSettings.fullscreenFocused;
                    var dateNow = Date.now();

                    var sections = [];

                    // Show until time if valid but not if too far int he future
                    if (!isNaN(inhibitedUntilTime) && inhibitedUntilTime - dateNow > 0 &&
                        inhibitedUntilTime - dateNow < 100 * 24 * 60 * 60 * 1000 /* 1 year*/) {
                        const endTime = KCoreAddons.Format.formatRelativeDateTime(inhibitedUntil, Locale.ShortFormat);
                        const lowercaseEndTime = endTime[0] + endTime.slice(1);
                        sections.push(i18ndc("plasma_applet_org.kde.plasma.notifications", "Do not disturb until date", "Automatically ends: %1", lowercaseEndTime));
                    }

                    if (inhibitedByApp) {
                        var inhibitionAppNames = fullRepresentationRoot.notificationSettings.notificationInhibitionApplications;
                        var inhibitionAppReasons = fullRepresentationRoot.notificationSettings.notificationInhibitionReasons;

                        for (var i = 0, length = inhibitionAppNames.length; i < length; ++i) {
                            var name = inhibitionAppNames[i];
                            var reason = inhibitionAppReasons[i];

                            if (reason) {
                                sections.push(i18ndc("plasma_applet_org.kde.plasma.notifications", "Do not disturb until app has finished (reason)", "While %1 is active (%2)", name, reason));
                            } else {
                                sections.push(i18ndc("plasma_applet_org.kde.plasma.notifications", "Do not disturb until app has finished", "While %1 is active", name));
                            }
                        }
                    }

                    if (inhibitedByMirroredScreens) {
                        sections.push(i18ndc("plasma_applet_org.kde.plasma.notifications", "Do not disturb because external mirrored screens connected", "Screens are mirrored"))
                    }

                    if (inhibitedByFullscreen) {
                        sections.push(i18ndc("plasma_applet_org.kde.plasma.notifications", "Do not disturb because fullscreen app is focused", "Fullscreen app is focused"))
                    }

                    return sections.join(" · ");
                }
                visible: text !== ""
            }
        }
    }

    // Nothing to show: one pill, like the clock panel's "No Notifications".
    Components.GlassCard {
        id: emptyCard

        // Checking valid to avoid creating ServerInfo object if everything is alright
        readonly property NotificationManager.ServerInfo currentOwner: NotificationManager.Server.valid ? null : NotificationManager.Server.currentOwner

        y: headerCard.height + fullRepresentationRoot.cardSpacing
        width: parent.width
        height: Math.max(46, emptyText.implicitHeight + 2 * 12)
        visible: list.count === 0
        onVisibleChanged: fullRepresentationRoot.glassChanged()

        ColumnLayout {
            id: emptyText
            anchors {
                left: parent.left
                right: parent.right
                verticalCenter: parent.verticalCenter
                leftMargin: 16
                rightMargin: 16
            }
            spacing: 2

            PlasmaComponents3.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                textFormat: Text.PlainText
                font.weight: Font.DemiBold
                text: NotificationManager.Server.valid
                    ? i18nd("plasma_applet_org.kde.plasma.notifications", "No unread notifications")
                    : i18nd("plasma_applet_org.kde.plasma.notifications", "Notification service not available")
            }
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                textFormat: Text.PlainText
                opacity: 0.7
                visible: text !== ""
                text: emptyCard.currentOwner && emptyCard.currentOwner.vendor && emptyCard.currentOwner.name
                    ? i18ndc("plasma_applet_org.kde.plasma.notifications", "Vendor and product name", "Notifications are currently provided by '%1 %2'", emptyCard.currentOwner.vendor, emptyCard.currentOwner.name)
                    : ""
            }
        }
    }

    PlasmaComponents3.ScrollView {
        id: scrollView
        y: headerCard.height + fullRepresentationRoot.cardSpacing
        width: parent.width
        height: Math.max(0, parent.height - y)
        background: null
        focus: true
        // macOS overlays its scroll bars; ours would sit beside the cards,
        // off the glass, where the window takes no clicks.
        QQC2.ScrollBar.vertical.policy: QQC2.ScrollBar.AlwaysOff
        QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff

        contentItem: ListView {
            id: list
            width: scrollView.availableWidth
            clip: true
            focus: true
            model: fullRepresentationRoot.shown ? fullRepresentationRoot.historyModel : null
            currentIndex: -1

            // Each row keeps its own gap below (a collapsed group's hidden
            // heading has none).
            spacing: 0

            onContentYChanged: fullRepresentationRoot.glassChanged()
            onContentHeightChanged: fullRepresentationRoot.glassChanged()
            onCountChanged: fullRepresentationRoot.glassChanged()

            KeyNavigation.up: dndCheck

            Keys.onDeletePressed: {
                var idx = fullRepresentationRoot.historyModel.index(currentIndex, 0);
                if (fullRepresentationRoot.historyModel.data(idx, NotificationManager.Notifications.ClosableRole)) {
                    fullRepresentationRoot.historyModel.close(idx);
                    // TODO would be nice to stay inside the current group when deleting an item
                }
            }
            Keys.onEnterPressed: event => { Keys.returnPressed(event) }
            Keys.onReturnPressed: {
                // Trigger default action, if any
                var idx = fullRepresentationRoot.historyModel.index(currentIndex, 0);
                if (fullRepresentationRoot.historyModel.data(idx, NotificationManager.Notifications.HasDefaultActionRole)) {
                    fullRepresentationRoot.historyModel.invokeDefaultAction(idx);
                    return;
                }

                // Trigger thumbnail URL if there's one
                var urls = fullRepresentationRoot.historyModel.data(idx, NotificationManager.Notifications.UrlsRole);
                if (urls && urls.length === 1) {
                    Qt.openUrlExternally(urls[0]);
                    return;
                }

                // TODO for finished jobs trigger "Open" or "Open Containing Folder" action
            }
            Keys.onLeftPressed: setGroupExpanded(currentIndex, LayoutMirroring.enabled)
            Keys.onRightPressed: setGroupExpanded(currentIndex, !LayoutMirroring.enabled)

            Keys.onPressed: event => {
                switch (event.key) {
                case Qt.Key_Home:
                    currentIndex = 0;
                    break;
                case Qt.Key_End:
                    currentIndex = count - 1;
                    break;
                }
            }

            function setGroupExpanded(row, expanded) {
                var rowIdx = fullRepresentationRoot.historyModel.index(row, 0);
                var persistentRowIdx = fullRepresentationRoot.historyModel.makePersistentModelIndex(rowIdx);
                var persistentGroupIdx = fullRepresentationRoot.historyModel.makePersistentModelIndex(fullRepresentationRoot.historyModel.groupIndex(rowIdx));

                fullRepresentationRoot.historyModel.setData(rowIdx, expanded, NotificationManager.Notifications.IsGroupExpandedRole);

                // If the current item went away when the group collapsed, scroll to the group heading
                if (!persistentRowIdx || !persistentRowIdx.valid) {
                    if (persistentGroupIdx && persistentGroupIdx.valid) {
                        list.positionViewAtIndex(persistentGroupIdx.row, ListView.Contain);
                        // When closed via keyboard, also set a sane current index
                        if (list.currentIndex > -1) {
                            list.currentIndex = persistentGroupIdx.row;
                        }
                    }
                }
            }
            // The keyboard focus is a ring on the card itself.
            highlight: null

            // No separator between apps: every card is its own bubble.
            // Rows still know their app, for the group's last card.
            section {
                property: "desktopEntry"
                criteria: ViewSection.FullString
            }

            delegate: DraggableDelegate {
                id: delegate
                width: ListView.view.width
                leftPadding: 0
                rightPadding: 0
                opacity: 0

                required property int index
                required property var model

                required property bool isGroup
                required property bool isInGroup
                required property int type
                required property bool hasDefaultAction
                required property list<string> actionLabels
                required property string configureActionLabel
                required property bool hasReplyAction
                required property string applicationName
                required property string applicationIconName
                required property string originName
                required property date updated
                required property date created
                required property bool configurable
                required property bool dismissable
                required property bool dismissed
                required property bool closable
                required property string summary
                required property string body
                required property var image
                required property string iconName
                required property list<url> urls
                required property string defaultActionLabel
                required property int jobState
                required property int percentage
                required property string jobError
                required property bool suspendable
                required property bool killable
                required property QtObject jobDetails
                required property list<string> actionNames
                required property bool resident
                required property bool isGroupExpanded
                required property int groupChildrenCount
                required property int expandedGroupChildrenCount

                // A collapsed group: its heading row is hidden and its
                // newest notification is the front of a stack.
                readonly property bool stacked: isInGroup && !isGroupExpanded
                readonly property int stackDepth: stacked ? Math.max(0, Math.min(2, groupChildrenCount - 1)) : 0

                onOpacityChanged: fullRepresentationRoot.glassChanged()
                onHeightChanged: fullRepresentationRoot.glassChanged()

                // NOTE: The following animations replace the Transitions in the ListView
                // because they don't work when the items change size during the animation
                // (showing/hiding the show more/show less button) in that case they will
                // animate to a wrong position and stay there
                // see https://bugs.kde.org/show_bug.cgi?id=427894 and QTBUG-110366
                property real oldY: -1
                property int oldListCount: -1
                onYChanged: {
                    if (oldY < 0 || oldListCount === list.count) {
                        oldY = y;
                        return;
                    }
                    traslAnim.from = oldY - y;
                    //traslAnim.running = true;
                    traslAnim.restart()
                    oldY = y;
                    oldListCount = list.count;
                }
                transform: Translate {
                    id: transl
                    onYChanged: fullRepresentationRoot.glassChanged()
                }
                NumberAnimation {
                    id: traslAnim
                    target: transl
                    properties: "y"
                    to: 0
                    duration: Kirigami.Units.longDuration
                }

                ListView.onAdd: appearAnim.restart();
                Component.onCompleted: {
                    Qt.callLater(() => {
                        if (!appearAnim.running) {
                            opacity = 1;
                        }
                    });
                    oldListCount = list.count;
                }

                SequentialAnimation {
                    id: appearAnim
                    PropertyAction { target: delegate; property: "opacity"; value: 0 }
                    PauseAnimation { duration: Kirigami.Units.longDuration}
                    NumberAnimation {
                        target: delegate
                        property: "opacity"
                        from: 0
                        to: 1
                        duration: Kirigami.Units.longDuration
                    }
                }

                draggable: !delegate.isGroup && delegate.type != NotificationManager.Notifications.JobType

                onDismissRequested: fullRepresentationRoot.historyModel.close(fullRepresentationRoot.historyModel.index(index, 0));

                contentItem: Loader {
                    id: delegateLoader

                    // A collapsed group's heading takes no room.
                    active: !delegate.isGroup || delegate.isGroupExpanded
                    sourceComponent: delegate.isGroup ? groupDelegate : cardDelegate

                    // Closes the notification, or the whole group from the
                    // front of a stack (macOS clears the stack).
                    function closeCard() {
                        if (delegate.stacked) {
                            const rowIdx = fullRepresentationRoot.historyModel.index(delegate.index, 0);
                            fullRepresentationRoot.historyModel.close(fullRepresentationRoot.historyModel.groupIndex(rowIdx));
                        } else {
                            delegate.close();
                        }
                    }

                    readonly property Components.ModelInterface modelInterface: Components.ModelInterface {
                        index: delegate.index
                        notificationType: delegate.type

                        hasSomeActions: (delegate.hasDefaultAction || false) || (delegate.actionLabels || []).length > 0 || (delegate.configureActionLabel || "").length > 0 || (delegate.hasReplyAction || false)
                        hasReplyAction: delegate.hasReplyAction || false

                        inGroup: delegate.isInGroup
                        inHistory: true

                        applicationName: delegate.applicationName
                        applicationIconSource: delegate.applicationIconName
                        originName: delegate.originName || ""

                        time: isNaN(delegate.updated) ? delegate.created : delegate.updated

                        // configure button on every single notifications is bit overwhelming
                        configurable: !inGroup && delegate.configurable

                        dismissable: delegate.dismissable
                            && delegate.dismissed
                            // TODO would be nice to be able to undismiss jobs even when they autohide
                            && fullRepresentationRoot.notificationSettings.permanentJobPopups
                        dismissed: delegate.dismissed || false
                        closable: delegate.closable

                        summary: delegate.summary
                        body: delegate.body || ""
                        icon: delegate.image || delegate.iconName

                        urls: delegate.urls || []

                        defaultActionLabel: delegate.defaultActionLabel || i18ndc("plasma_applet_org.kde.plasma.notifications", "@action:button", "View")

                        // In the popup the default action is triggered by clicking on the popup
                        // however in the list this is undesirable, so instead show a clickable button
                        // in case you have a non-expired notification in history (do not disturb mode)
                        // unless it has the same label as an action
                        addDefaultAction: (delegate.hasDefaultAction && (delegate.actionLabels || []).indexOf(delegate.defaultActionLabel || i18ndc("plasma_applet_org.kde.plasma.notifications", "@action:button", "View")) === -1) ? true : false

                        jobState: delegate.jobState || 0
                        percentage: delegate.percentage || 0
                        jobError: delegate.jobError || 0
                        suspendable: !!delegate.suspendable
                        killable: !!delegate.killable
                        jobDetails: delegate.jobDetails || null

                        configureActionLabel: delegate.configureActionLabel || ""

                        actionNames: delegate.actionNames || []
                        actionLabels: delegate.actionLabels || []

                        onCloseClicked: delegate.close()

                        onDismissClicked: {
                            delegate.model.dismissed = false;
                            fullRepresentationRoot.appletInterface.closePlasmoid();
                        }
                        onConfigureClicked: fullRepresentationRoot.historyModel.configure(fullRepresentationRoot.historyModel.index(index, 0))

                        onActionInvoked: actionName => {
                            // We close any non-resident notification (even those that still may have some actions)
                            // because the assumption is that once the notification has been interacted with, it may
                            // safely lose interaction capabilities (since the user is now likely in the app itself).
                            //
                            // The alternative to this would have the downside that notifications whose apps have been
                            // closed will keep their buttons in the notification history. This way, invoking an action
                            // will make the notification actually disappear (as is common on other operating systems).
                            const behavior = delegate.resident ? NotificationManager.Notifications.None : NotificationManager.Notifications.Close;

                            if (actionName === "default") {
                                fullRepresentationRoot.historyModel.invokeDefaultAction(fullRepresentationRoot.historyModel.index(index, 0), behavior);
                            } else {
                                fullRepresentationRoot.historyModel.invokeAction(fullRepresentationRoot.historyModel.index(index, 0), actionName, behavior);
                            }
                        }
                        onOpenUrl: url => {
                            Qt.openUrlExternally(url);
                            delegateLoader.expire();
                        }
                        onFileActionInvoked: action => {
                            if (action.objectName === "movetotrash" || action.objectName === "deletefile") {
                                delegate.close();
                            } else {
                                delegateLoader.expire();
                            }
                        }
                        onReplied: text => {
                            const behavior = delegate.resident ? NotificationManager.Notifications.None : NotificationManager.Notifications.Close;
                            fullRepresentationRoot.historyModel.reply(fullRepresentationRoot.historyModel.index(index, 0), text, behavior);
                        }

                        onSuspendJobClicked: fullRepresentationRoot.historyModel.suspendJob(fullRepresentationRoot.historyModel.index(index, 0))
                        onResumeJobClicked: fullRepresentationRoot.historyModel.resumeJob(fullRepresentationRoot.historyModel.index(index, 0))
                        onKillJobClicked: fullRepresentationRoot.historyModel.killJob(fullRepresentationRoot.historyModel.index(index, 0))
                    }

                    function expire() {
                        if (delegate.resident) {
                            delegate.model.expired = true;
                        } else {
                            fullRepresentationRoot.historyModel.expire(fullRepresentationRoot.historyModel.index(delegate.index, 0));
                        }
                    }

                    Component {
                        id: groupDelegate

                        // The expanded group's row: the app, "Show Fewer"
                        // and the group's buttons, each a glass pill.
                        Item {
                            implicitHeight: 28 + fullRepresentationRoot.cardSpacing

                            Components.GlassCard {
                                height: 28
                                width: Math.min(appRow.implicitWidth + 20, parent.width - groupButtons.width - fullRepresentationRoot.cardSpacing)
                                radius: height / 2

                                RowLayout {
                                    id: appRow
                                    x: 10
                                    width: parent.width - 20
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: Kirigami.Units.smallSpacing

                                    Kirigami.Icon {
                                        Layout.preferredWidth: 16
                                        Layout.preferredHeight: 16
                                        source: delegate.applicationIconName
                                        visible: valid
                                    }
                                    PlasmaComponents3.Label {
                                        Layout.fillWidth: true
                                        textFormat: Text.PlainText
                                        elide: Text.ElideRight
                                        font.weight: Font.Bold
                                        text: delegate.applicationName + (delegate.originName ? " · " + delegate.originName : "")
                                    }
                                }
                            }

                            Row {
                                id: groupButtons
                                anchors.right: parent.right
                                height: 28
                                spacing: 6

                                Components.GlassCard {
                                    width: showFewerLabel.implicitWidth + 24
                                    height: 28
                                    radius: height / 2
                                    hovered: showFewerHover.hovered

                                    PlasmaComponents3.Label {
                                        id: showFewerLabel
                                        anchors.centerIn: parent
                                        textFormat: Text.PlainText
                                        text: i18nd("plasma_applet_org.kde.plasma.notifications", "Show Fewer")
                                    }
                                    HoverHandler {
                                        id: showFewerHover
                                    }
                                    TapHandler {
                                        onTapped: list.setGroupExpanded(delegate.index, false)
                                    }

                                    Accessible.role: Accessible.Button
                                    Accessible.name: showFewerLabel.text
                                    Accessible.onPressAction: list.setGroupExpanded(delegate.index, false)
                                }

                                Components.GlassCard {
                                    width: 28
                                    height: 28
                                    radius: height / 2
                                    visible: delegate.configurable

                                    RoundButton {
                                        anchors.centerIn: parent
                                        color: "transparent"
                                        border.width: 0
                                        iconName: "configure"
                                        toolTip: delegate.configureActionLabel || i18nd("plasma_applet_org.kde.plasma.notifications", "Configure")
                                        onClicked: fullRepresentationRoot.historyModel.configure(fullRepresentationRoot.historyModel.index(delegate.index, 0))
                                    }
                                }

                                Components.GlassCard {
                                    width: 28
                                    height: 28
                                    radius: height / 2
                                    visible: delegate.closable

                                    RoundButton {
                                        anchors.centerIn: parent
                                        color: "transparent"
                                        border.width: 0
                                        glyph: "×"
                                        toolTip: i18nd("plasma_applet_org.kde.plasma.notifications", "Close Group")
                                        onClicked: fullRepresentationRoot.historyModel.close(fullRepresentationRoot.historyModel.index(delegate.index, 0))
                                    }
                                }
                            }
                        }
                    }

                    Component {
                        id: cardDelegate

                        Item {
                            id: cardRow
                            // Named here: inside the Repeater, `delegate` is its own property.
                            readonly property int stackDepth: delegate.stackDepth

                            implicitHeight: card.height + stackDepth * fullRepresentationRoot.stackStep
                                + fullRepresentationRoot.cardSpacing

                            // The stack's other cards, under the front one:
                            // nothing of them is painted above its bottom
                            // edge, so they never show through the glass.
                            Item {
                                y: card.height
                                width: parent.width
                                height: cardRow.stackDepth * fullRepresentationRoot.stackStep
                                clip: true

                                Repeater {
                                    model: cardRow.stackDepth

                                    delegate: Rectangle {
                                        required property int index
                                        z: -index
                                        x: (index + 1) * fullRepresentationRoot.stackInset
                                        y: (index + 1) * fullRepresentationRoot.stackStep - height
                                        width: parent.width - 2 * x
                                        height: card.height
                                        radius: card.radius
                                        color: fullRepresentationRoot.dark
                                            ? (index === 0 ? Qt.rgba(0.26, 0.27, 0.29, 0.9) : Qt.rgba(0.23, 0.24, 0.26, 0.85))
                                            : (index === 0 ? Qt.rgba(0.84, 0.84, 0.85, 0.9) : Qt.rgba(0.78, 0.78, 0.79, 0.85))
                                    }
                                }
                            }

                            Components.GlassCard {
                                id: card
                                width: parent.width
                                height: notification.implicitHeight
                                hovered: cardHover.hovered

                                // What the card's hover buttons offer.
                                readonly property bool canConfigure: delegate.configurable && !delegate.isInGroup
                                readonly property bool canRestore: delegateLoader.modelInterface.dismissable

                                HoverHandler {
                                    id: cardHover
                                }

                                Delegates.DelegateHistory {
                                    id: notification
                                    width: parent.width
                                    modelInterface: delegateLoader.modelInterface
                                    showAge: !cardHover.hovered || !(card.canConfigure || card.canRestore)
                                }

                                // A stack opens on a click anywhere but its buttons.
                                MouseArea {
                                    anchors.fill: parent
                                    visible: delegate.stacked && delegate.stackDepth > 0
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: list.setGroupExpanded(delegate.index, true)
                                    Accessible.role: Accessible.Button
                                    Accessible.name: i18ndc("plasma_applet_org.kde.plasma.notifications", "Expand to show n more notifications",
                                                            "Show %1 More", delegate.groupChildrenCount - delegate.expandedGroupChildrenCount)
                                }

                                // Keyboard focus.
                                Rectangle {
                                    anchors.fill: parent
                                    radius: card.radius
                                    color: "transparent"
                                    border.width: 2
                                    border.color: Kirigami.Theme.highlightColor
                                    visible: delegate.ListView.isCurrentItem && list.activeFocus
                                }

                                // macOS: a round close button by the top-left
                                // corner while hovered (as on the banners).
                                RoundButton {
                                    x: 6
                                    y: 6
                                    z: 10
                                    visible: delegateLoader.modelInterface.closable && cardHover.hovered
                                    glyph: "×"
                                    toolTip: delegate.stacked && delegate.stackDepth > 0
                                        ? i18nd("plasma_applet_org.kde.plasma.notifications", "Close Group")
                                        : i18nd("plasma_applet_org.kde.plasma.notifications", "Close")
                                    onClicked: delegateLoader.closeCard()
                                }

                                Row {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 10
                                    y: 10
                                    z: 10
                                    spacing: 6
                                    visible: cardHover.hovered

                                    RoundButton {
                                        visible: card.canRestore
                                        iconName: delegateLoader.modelInterface.dismissed ? "window-restore" : "window-minimize"
                                        toolTip: delegateLoader.modelInterface.dismissed
                                            ? i18ndc("plasma_applet_org.kde.plasma.notifications", "Opposite of minimize", "Restore")
                                            : i18nd("plasma_applet_org.kde.plasma.notifications", "Minimize")
                                        onClicked: delegateLoader.modelInterface.dismissClicked()
                                    }
                                    RoundButton {
                                        visible: card.canConfigure
                                        iconName: "configure"
                                        toolTip: delegateLoader.modelInterface.configureActionLabel || i18nd("plasma_applet_org.kde.plasma.notifications", "Configure")
                                        onClicked: delegateLoader.modelInterface.configureClicked()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
