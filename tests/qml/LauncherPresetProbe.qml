import QtQuick
import QtQuick.Window
import org.kde.kirigami as Kirigami

// Runs only in the isolated plasmoidviewer from test_launcher_presets.py.
Timer {
    id: presetProbe
    interval: 400
    running: true
    repeat: true
    property int phase: -2
    property int expectedPreset: 1
    property real inlineHeight: 0
    property real inlineWidth: 0
    property size initialPopupSize
    property color originalForeground: "transparent"
    property Window outsideProbe: Window {
        width: 100
        height: 100
        transientParent: null
    }
    function verify(condition, label) {
        if (!condition) {
            throw new Error(label);
        }
    }
    function verifyCapsulePosition() {
        verify(searchPopup.y + searchPopup.height < root.y, "search above app panel");
        verify(Math.abs(searchPopup.x + searchPopup.width / 2 - root.x - root.width / 2) < 2, "capsule centered");
    }
    function findIcon(item) {
        if (item instanceof Kirigami.Icon) {
            return item;
        }
        for (const child of item.children) {
            const icon = findIcon(child);
            if (icon) {
                return icon;
            }
        }
        return null;
    }
    function verifyOptionsIcon(search) {
        const icon = findIcon(search.testMenuButton.testButton.contentItem);
        verify(icon !== null && icon.valid, "options icon loaded");
        verify(icon.Kirigami.Theme.textColor === search.textField.color, "options icon follows the search foreground");
    }
    onTriggered: {
        try {
            console.log("PROBE_PHASE", phase, root.visible, kicker.launcherPreset, root.width, root.height, searchPopup.width, searchPopup.height, root.active, main.popupHasFocus, searchBar.textField.activeFocus);
            console.log("PROBE_GEOMETRY", root.x, root.y, searchPopup.x, searchPopup.y);
            switch (phase++) {
            case -2:
                root.visible = true;
                break;
            case -1:
                initialPopupSize = Qt.size(root.width, root.height);
                root.visible = false;
                break;
            case 0:
                root.title = "Launcher app role probe";
                searchPopup.title = "Launcher search role probe";
                verify(kicker.launcherPreset === expectedPreset, "edition default");
                plasmoid.configuration.launcherPreset = 1;
                plasmoid.configuration.launcherPosition = 2;
                root.visible = true;
                break;
            case 1:
                verify(root.visible, "inline panel visible");
                verify(main.textColor === glassPalette.Kirigami.Theme.textColor, "labels follow the system complementary foreground");
                verify(!searchPopup.visible, "inline search has no second popup");
                verify(searchBar.parent === inlineSearchSlot, "inline field parent");
                verifyOptionsIcon(searchBar);
                presetProbe.inlineHeight = root.height;
                presetProbe.inlineWidth = root.width;
                // Exercise native geometry feedback before changing presets.
                root.width += 80;
                root.height += 60;
                searchBar.textField.text = "terminal";
                verify(runnerModel.query === "terminal", "search reaches runner");
                searchBar.testMenuButton.testMenu.content[1].clicked();
                break;
            case 2:
                verify(root.visible && searchPopup.visible, "both detached popups visible");
                verify(root.width !== presetProbe.inlineWidth, "Golden Gate applies its own width");
                if (expectedPreset === 2) {
                    verify(root.width === initialPopupSize.width && root.height === initialPopupSize.height,
                           "Golden Gate restores its initial size after switching presets");
                }
                verify(searchBar.parent === detachedSearchSlot, "detached field parent");
                verifyOptionsIcon(searchBar);
                verify(searchBar.textField.text === "terminal", "query survives preset change");
                verify(root.height < presetProbe.inlineHeight, "no empty inline search row");
                verifyCapsulePosition();
                searchBar.testMenuButton.testMenu.content[3].clicked();
                verify(plasmoid.configuration.showAllAppsInList, "list option works");
                searchBar.testMenuButton.testMenu.openRelative();
                break;
            case 3:
                verify(root.visible && searchPopup.visible && main.menuOpen, "options menu keeps popups open");
                searchBar.testMenuButton.testMenu.content[0].clicked();
                searchBar.testMenuButton.testMenu.close();
                break;
            case 4:
                verify(root.visible && !searchPopup.visible, "switch back hides capsule");
                verify(searchBar.parent === inlineSearchSlot, "field returns inside panel");
                verify(root.height === presetProbe.inlineHeight, "inline height restored");
                verify(root.width === presetProbe.inlineWidth, "Tahoe applies its own width");
                verify(searchBar.textField.text === "terminal", "query survives round trip");
                plasmoid.configuration.launcherPreset = 2;
                break;
            case 5:
                outsideProbe.show();
                outsideProbe.requestActivate();
                break;
            case 6:
                verify(!root.visible && !searchPopup.visible && searchBar.textField.text === "", "outside focus closes both popups and resets query");
                outsideProbe.close();
                plasmoid.configuration.showAllAppsInList = false;
                plasmoid.configuration.showAllAppsInGrid = true;
                root.visible = true;
                break;
            case 7:
                verify(root.columns === 7, "Golden Gate starts with seven columns");
                verify(searchBar.textField.font.pointSize > main.appTextSize, "search text has its own hierarchy");
                const view = appList.viewItem;
                console.log("PROBE_CATEGORIES", JSON.stringify(appList.appsCategoriesList),
                            appList.selectedModelIndex, appList.selectedIsAllApps, globalFavorites.count);
                verify(view.headerItem !== null, "favorites row shown above all apps");
                verify(view.headerItem.favoritesView.count === 7, "favorites limited to one row");
                verify(view.contentY <= view.headerItem.y, "opening shows the favorites header");
                plasmoid.configuration.goldenGateColumns = 6;
                break;
            case 8:
                verify(appList.viewItem.headerItem.favoritesView.count === 6, "favorites follow the column setting");
                verifyCapsulePosition();
                root.x += 40;
                root.y += 30;
                break;
            case 9:
                verifyCapsulePosition();
                originalForeground = glassPalette.Kirigami.Theme.textColor;
                glassPalette.Kirigami.Theme.textColor = "#182838";
                break;
            case 10:
                verifyOptionsIcon(inlineSearchBar);
                verifyOptionsIcon(detachedSearchBar);
                glassPalette.Kirigami.Theme.textColor = "#e8d8c8";
                break;
            case 11:
                verifyOptionsIcon(inlineSearchBar);
                verifyOptionsIcon(detachedSearchBar);
                glassPalette.Kirigami.Theme.textColor = originalForeground;
                root.visible = false;
                // Plasma's panel/desktop can share a transient chain with the
                // launcher. QWindow.active stays true when that parent takes focus.
                outsideProbe.show();
                root.transientParent = outsideProbe;
                plasmoid.configuration.launcherPreset = 1;
                root.visible = true;
                break;
            case 12:
                verify(root.visible, "inline popup stays open with a transient parent");
                outsideProbe.requestActivate();
                break;
            case 13:
                verify(!root.visible, "focusing the parent closes the inline launcher");
                plasmoid.configuration.launcherPreset = 2;
                root.visible = true;
                break;
            case 14:
                verify(root.visible && searchPopup.visible, "detached popups reopen with a transient parent");
                root.requestActivate();
                break;
            case 15:
                verify(root.visible && searchPopup.visible, "moving focus to app panel keeps both popups open");
                main.focusSearch();
                break;
            case 16:
                verify(root.visible && searchPopup.visible, "moving focus to search keeps both popups open");
                const app = appList.viewItem.currentItem;
                verify(app !== null, "app available for its context menu");
                app.openActionMenu(app, 10, 10);
                break;
            case 17:
                verify(root.visible && searchPopup.visible && appList.viewItem.currentItem.testActionMenu.opened,
                       "app context menu keeps both popups open");
                appList.viewItem.currentItem.testActionMenu.menu.close();
                break;
            case 18:
                outsideProbe.requestActivate();
                break;
            case 19:
                verify(!root.visible && !searchPopup.visible, "focusing the parent closes both detached popups");
                console.log("LAUNCHER_PROBE_OK");
                stop();
                break;
            }
        } catch (error) {
            console.log("LAUNCHER_PROBE_FAILED", error.message);
            stop();
        }
    }
}
