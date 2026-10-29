/*
    SPDX-FileCopyrightText: 2018-2019 Kai Uwe Broulik <kde@privat.broulik.de>

    SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/
pragma ComponentBehavior: Bound

import QtQuick
import QtQml

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kquickcontrolsaddons // For KCMShell
import org.kde.kirigami as Kirigami

import org.kde.coreaddons as KCoreAddons
import org.kde.kcmutils as KCMUtils
import org.kde.config as KConfig

import org.kde.notificationmanager as NotificationManager

import plasma.applet.org.kde.mac.tahoe.liquid.notifications as Notifications

import "components" as Components

PlasmoidItem {
    id: root

    readonly property int unreadCount: Math.min(99, historyModel.unreadNotificationsCount)

    readonly property bool inhibitedOrBroken: Notifications.Globals.inhibited || !NotificationManager.Server.valid

    readonly property bool inPanel: (Plasmoid.location === PlasmaCore.Types.TopEdge
        || Plasmoid.location === PlasmaCore.Types.RightEdge
        || Plasmoid.location === PlasmaCore.Types.BottomEdge
        || Plasmoid.location === PlasmaCore.Types.LeftEdge)

    readonly property int effectiveStatus: historyModel.activeJobsCount > 0
                     || historyModel.unreadNotificationsCount > 0
                     || historyModel.dismissedResidentNotificationsCount > 0
                     || Notifications.Globals.inhibited ? PlasmaCore.Types.ActiveStatus
                                          : PlasmaCore.Types.PassiveStatus
    onEffectiveStatusChanged: {
        if (effectiveStatus === PlasmaCore.Types.PassiveStatus) {
            // HACK System Tray only lets applets self-hide when in Active state
            // When we clear the notifications, the status is updated right away
            // as a result of model signals, and when we then try to collapse
            // the popup isn't hidden.
            Qt.callLater(function() {
                Plasmoid.status = effectiveStatus;
            });
        } else {
            Plasmoid.status = effectiveStatus;
        }
    }

    Plasmoid.status: effectiveStatus

    toolTipSubText: {
        var lines = [];

        if (jobAggregator.count > 0) {
            let description = i18ndp("plasma_applet_org.kde.plasma.notifications", "%1 running job", "%1 running jobs", jobAggregator.count);

            if (jobAggregator.summary) {
                if (jobAggregator.percentage > 0) {
                    description = i18ndc("plasma_applet_org.kde.plasma.notifications", "Job title (percentage)", "%1 (%2%)", jobAggregator.summary, jobAggregator.percentage);
                } else {
                    description = jobAggregator.summary;
                }
            } else if (jobAggregator.percentage > 0) {
                description = i18ndp("plasma_applet_org.kde.plasma.notifications", "%1 running job (%2%)", "%1 running jobs (%2%)", jobAggregator.count, jobAggregator.percentage);
            }

            lines.push(description);
        }

        if (!NotificationManager.Server.valid) {
            lines.push(i18nd("plasma_applet_org.kde.plasma.notifications", "Notification service not available"));
        } else {
            // Any notification that is newer than "lastRead" is "unread"
            // since it doesn't know the popup is on screen which makes the user see it
            var actualUnread = historyModel.unreadNotificationsCount - Notifications.Globals.popupNotificationsModel.activeNotificationsCount;
            if (actualUnread > 0) {
                lines.push(i18ndp("plasma_applet_org.kde.plasma.notifications", "%1 unread notification", "%1 unread notifications", actualUnread));
            }

            const dismissedResidents = historyModel.dismissedResidentNotificationsCount;
            if (dismissedResidents > 0) {
                lines.push(i18ndp("plasma_applet_org.kde.plasma.notifications", "%1 active notification", "%1 active notifications", dismissedResidents));
            }

            if (Notifications.Globals.inhibited) {
                var inhibitedUntil = notificationSettings.notificationsInhibitedUntil
                var inhibitedUntilTime = inhibitedUntil.getTime();
                var inhibitedUntilValid = !isNaN(inhibitedUntilTime);
                var dateNow = Date.now();

                // Show until time if valid but not if too far in the future
                // TODO check app inhibition, too
                if (inhibitedUntilValid && inhibitedUntilTime - dateNow > 0
                        && inhibitedUntilTime - dateNow < 100 * 24 * 60 * 60 * 1000 /* 100 days*/) {
                        lines.push(i18nd("plasma_applet_org.kde.plasma.notifications", "Do not disturb until %1; middle-click to exit now",
                                     KCoreAddons.Format.formatRelativeDateTime(inhibitedUntil, Locale.ShortFormat)));
                } else {
                    lines.push(i18nd("plasma_applet_org.kde.plasma.notifications", "Do not disturb mode active; middle-click to exit"));
                }
            } else {
                if (lines.length === 0) {
                    lines.push(i18nd("plasma_applet_org.kde.plasma.notifications", "No unread notifications"));
                }
                lines.push(i18nd("plasma_applet_org.kde.plasma.notifications", "Middle-click to enter do not disturb mode"));
            }
        }

        return lines.join("\n");
    }

    // Even though the actual icon is drawn with custom code in CompactRepresentation,
    // set the icon property here anyway because it's useful in other contexts
    Plasmoid.icon: {
        let iconName;
        if (root.inhibitedOrBroken) {
            iconName = "notifications-disabled";
        } else if (root.unreadCount > 0) {
            iconName = "notification-active";
        } else {
            iconName = "notification-inactive"
        }
        // "active jobs" state not included here since that requires custom painting,
        // and not just a simple icon

        if (inPanel) {
            return symbolicizeIconName(iconName);
        }

        return iconName;
    }

    // MacTahoe Liquid KDE: the history is a window of its own (`history` below),
    // never Plasma's applet popup or the tray's: those draw a frame and a
    // shadow around the whole popup, where macOS shows separate glass cards.
    preferredRepresentation: compactRepresentation
    fullRepresentation: Item {}

    // Every way of opening the history (a click on the icon or on its tray
    // menu row, the global shortcut) sets `expanded`: open the window
    // instead.
    onExpandedChanged: expanded => {
        if (expanded) {
            Qt.callLater(() => {
                root.expanded = false;
            });
            root.toggleHistory();
        }
    }

    // macOS: under the menu bar, 12 px from the screen's right edge, like
    // the clock panel.
    readonly property int historyGap: 8
    readonly property int historyMargin: 12
    // Transparent room above and below the glass: the Glass effect rounds
    // this window like a normal one (22 px), which would cut the cards'
    // corners if the window ended at their edges.
    readonly property int glassPad: 28
    // A click on the icon first deactivates (and so hides) the history;
    // that same click must not open it again.
    property double historyHiddenAt: 0

    readonly property rect historyScreenRect: {
        const rect = Notifications.Globals.screenRect;
        if (rect.width > 0 && rect.height > 0) {
            return rect;
        }
        return Plasmoid.containment ? Plasmoid.containment.screenGeometry : Qt.rect(0, 0, 0, 0);
    }

    function toggleHistory(): void {
        if (history.visible) {
            history.visible = false;
            return;
        }
        if (Date.now() - historyHiddenAt < 300) {
            return;
        }
        placeHistory();
        history.visible = true;
        history.requestActivate();
    }

    function placeHistory(): void {
        const rect = root.historyScreenRect;
        const width = history.width > 0 ? history.width : historyView.implicitWidth;
        history.x = Math.round(rect.x + rect.width - width - historyMargin);
        history.y = Math.round(rect.y + historyGap) - glassPad;
    }

    compactRepresentation: CompactRepresentation {
        activeCount: Notifications.Globals.popupNotificationsModel.activeNotificationsCount
        unreadCount: root.unreadCount

        jobsCount: historyModel.activeJobsCount
        jobsPercentage: historyModel.jobsPercentage

        inhibited: root.inhibitedOrBroken
    }

    PlasmaCore.Dialog {
        id: history

        // No frame of its own: every card is a glass bubble.
        location: PlasmaCore.Types.Floating
        backgroundHints: PlasmaCore.Dialog.NoBackground
        type: PlasmaCore.Dialog.PopupMenu
        flags: Qt.WindowStaysOnTopHint
        hideOnWindowDeactivate: true
        visible: false
        onWidthChanged: if (visible) root.placeHistory()
        onVisibleChanged: {
            if (visible) {
                Notifications.Globals.popupNotificationsModel.hideInhibitionSummary();
            } else {
                root.historyHiddenAt = Date.now();
                historyModel.lastRead = undefined; // reset to now
                historyModel.collapseAllGroups();
            }
        }

        mainItem: Item {
            width: historyView.implicitWidth
            height: historyView.implicitHeight + 2 * root.glassPad

            Keys.onEscapePressed: history.visible = false

            FullRepresentation {
                id: historyView
                y: root.glassPad
                width: implicitWidth
                height: implicitHeight
                focus: true
                appletInterface: root
                notificationSettings: notificationSettings
                clearHistoryAction: clearHistory
                historyModel: historyModel
                shown: history.visible
                maximumHeight: Math.max(Kirigami.Units.gridUnit * 12,
                                        root.historyScreenRect.height - root.historyGap - root.historyMargin)
                onGlassChanged: if (blurLoader.item) blurLoader.item.update()
            }

            // KWin blurs the desktop behind each card only.
            Loader {
                id: blurLoader
                source: "components/WindowBlur.qml"
                onLoaded: item.target = historyView
            }
            Components.BlurSettler {
                active: history.visible
                blur: blurLoader.item
            }
        }
    }

    NotificationManager.Settings {
        id: notificationSettings
    }

    NotificationManager.Notifications {
        id: historyModel
        showExpired: true
        showDismissed: true
        showJobs: notificationSettings.jobsInNotifications
        sortMode: NotificationManager.Notifications.SortByDate
        groupMode: NotificationManager.Notifications.GroupApplicationsFlat
        // MacTahoe Liquid KDE: a group is a macOS stack, its newest notification in
        // front, until a click expands it.
        groupLimit: 1
        expandUnread: false
        ignoreBlacklistDuringInhibition: true
        blacklistedDesktopEntries: notificationSettings.historyBlacklistedApplications
        blacklistedNotifyRcNames: notificationSettings.historyBlacklistedServices
        urgencies: {
            var urgencies = NotificationManager.Notifications.CriticalUrgency
                          | NotificationManager.Notifications.NormalUrgency;
            if (notificationSettings.lowPriorityHistory) {
                urgencies |= NotificationManager.Notifications.LowUrgency;
            }
            return urgencies;
        }

        onCountChanged: {
            if (count === 0) {
                root.closePlasmoid();
            }
        }
    }

    Notifications.JobAggregator {
        id: jobAggregator
        sourceModel: NotificationManager.Notifications {
            id: jobAggregatorModel
            showExpired: historyModel.showExpired
            showDismissed: historyModel.showDismissed
            showJobs: historyModel.showJobs
            showNotifications: false
            blacklistedDesktopEntries: historyModel.blacklistedDesktopEntries
            blacklistedNotifyRcNames: historyModel.blacklistedNotifyRcNames
            urgencies: historyModel.urgencies
        }
    }

    function closePlasmoid() {
        history.visible = false;
    }

    function clearNotificationHistoryAndShowOsd() {
        if (historyModel.expiredNotificationsCount > 0 || historyModel.activeNotificationsCount > 0) {
            historyModel.clear(NotificationManager.Notifications.ClearExpired);
            Notifications.Globals.shortcuts.showNotificationsHistoryCleaned();
        }
    }

    function action_configure() {
        KCMUtils.KCMLauncher.openSystemSettings("kcm_notifications");
    }

    function symbolicizeIconName(iconName) {
        const symbolicSuffix = "-symbolic";
        if (iconName.endsWith(symbolicSuffix)) {
            return iconName;
        }

        return iconName + symbolicSuffix;
    }

    Plasmoid.contextualActions: [
        PlasmaCore.Action {
            id: clearHistory
            text: i18nd("plasma_applet_org.kde.plasma.notifications", "Clear All Notifications")
            icon.name: "edit-clear-history"
            visible: historyModel.expiredNotificationsCount > 0
            onTriggered: {
                historyModel.clear(NotificationManager.Notifications.ClearExpired);
                // clear is async,
                historyModel.countChanged.connect(closeWhenCleared)
            }
            function closeWhenCleared() {
                if (historyModel.count === 0) {
                    root.closePlasmoid();
                }
                historyModel.countChanged.disconnect(closeWhenCleared)
            }
        }
    ]

    PlasmaCore.Action {
        id: configureAction
        text: i18nd("plasma_applet_org.kde.plasma.notifications", "&Configure Event Notifications and Actions…")
        icon.name: "configure"
        visible: KConfig.KAuthorized.authorizeControlModule("kcm_notifications");
        onTriggered: KCMUtils.KCMLauncher.openSystemSettings("kcm_notifications");
    }

    Component.onCompleted: {
        Notifications.Globals.adopt(root);

        // The applet's config window has nothing in it, so let's make the header's
        // "Configure" button open the KCM instead, like we do in the Bluetooth
        // and Networks applets
        Plasmoid.setInternalAction("configure", configureAction)
    }
    Component.onDestruction: {
        Notifications.Globals.forget(root);
    }

    Connections {
        target: Notifications.Globals.popupNotificationsModel

        // The user requested to show the notifications popup, probably by 
        // clicking the "Missed Notifications in Do Not Disturb" notification.
        function onShowNotificationsRequested(): void {
            if (!history.visible) {
                root.toggleHistory();
            }
        }
    }
}
