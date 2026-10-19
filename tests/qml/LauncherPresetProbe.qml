import QtQuick
import QtQuick.Window

// Runs only in the isolated plasmoidviewer from test_launcher_presets.py.
Timer {
    id: presetProbe
    interval: 400
    running: true
    repeat: true
    property int phase: 0
    property int expectedPreset: 1
    property real inlineHeight: 0
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
    onTriggered: {
        try {
            console.log("PROBE_PHASE", phase, root.visible, kicker.launcherPreset, root.width, root.height, searchPopup.width, searchPopup.height, root.active, searchPopup.hasFocus, searchBar.textField.activeFocus);
            console.log("PROBE_GEOMETRY", root.x, root.y, searchPopup.x, searchPopup.y);
            switch (phase++) {
            case 0:
                searchPopup.title = "Launcher search role probe";
                verify(kicker.launcherPreset === expectedPreset, "edition default");
                plasmoid.configuration.launcherPreset = 1;
                plasmoid.configuration.launcherPosition = 2;
                root.visible = true;
                break;
            case 1:
                verify(root.visible, "inline panel visible");
                verify(!searchPopup.visible, "inline search has no second popup");
                verify(searchBar.parent === inlineSearchSlot, "inline field parent");
                presetProbe.inlineHeight = root.height;
                searchBar.textField.text = "terminal";
                verify(runnerModel.query === "terminal", "search reaches runner");
                searchBar.testMenuButton.testMenu.content[1].clicked();
                break;
            case 2:
                verify(root.visible && searchPopup.visible, "both detached popups visible");
                verify(searchBar.parent === detachedSearchSlot, "detached field parent");
                verify(searchBar.textField.text === "terminal", "query survives preset change");
                verify(root.height < presetProbe.inlineHeight, "no empty inline search row");
                verify(searchPopup.y + searchPopup.height < root.y, "search above app panel");
                verify(Math.abs(searchPopup.x + searchPopup.width / 2 - root.x - root.width / 2) < 2, "capsule centered");
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
