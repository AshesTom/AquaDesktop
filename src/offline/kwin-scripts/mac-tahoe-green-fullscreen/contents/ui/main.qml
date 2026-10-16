/*
    AquaDesktop — the green traffic light enters full screen.

    On macOS the green title bar button puts the window in its own full
    screen space; double-clicking the title bar, snapping and the keyboard
    still "zoom" (maximize). KWin has no hook for a decoration button, but
    the green button asks KWin to maximize, and the cursor still sits on it
    when that happens. So a maximize requested while the cursor is over the
    green button's slot is turned into full screen instead. Any other
    maximize (title bar double-click, snap, shortcut, Global Menu "Zoom")
    is left alone.

    The slot comes from the Aurorae layout (LeftButtons=XIA): TitleEdgeLeft
    16, ButtonWidth 16, ButtonSpacing 7 put the green button at 62-78 px
    from the frame's left edge, inside the title bar. A few pixels of slack
    each way keep the yellow button and the title out of it.

    KWin's own full screen hides the title bar for good and stacks the
    window above every panel, so the menu bar could never come back. This
    is the macOS one instead: the window is kept above the panels and laid
    out with its title bar just above the screen. Pushing the cursor
    against the top edge drops it below the panels, so the menu bar shows
    over it (macOS no longer shows the window's traffic lights there). The
    bottom edge lets the Dock come up the same way. The window never moves
    or resizes on a reveal.

    Ctrl+Meta+F toggles full screen on the active window (macOS uses
    Ctrl+Cmd+F); the Global Menu's window menu has Exit Full Screen.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kwin as KWin

Item {
    id: root

    readonly property int greenLeft: 58
    readonly property int greenRight: 84
    readonly property int maximizeFull: 3

    // Windows in a full screen space: {window, restore, keepAbove,
    // borders}. Only the active one reacts to the screen edges.
    property var spaces: []
    // Frames captured when a zoom was requested from the green button.
    property var pending: []

    property var current: null
    // "hidden", "top" (menu bar and title bar shown) or "bottom" (Dock).
    property string reveal: "hidden"
    // Back to the covering state, menu bar hidden.
    function resetReveal() {
        reveal = "hidden";
    }

    function spaceOf(window) {
        return spaces.find(space => space.window === window) || null;
    }

    function rectOf(r) {
        return Qt.rect(r.x, r.y, r.width, r.height);
    }

    function bordersOf(frame, client) {
        return {
            left: client.x - frame.x,
            top: client.y - frame.y,
            right: frame.x + frame.width - client.x - client.width,
            bottom: frame.y + frame.height - client.y - client.height,
        };
    }

    function cursorOnGreenButton(window) {
        const frame = window.frameGeometry;
        const titleBar = window.clientGeometry.y - frame.y;
        const cursor = KWin.Workspace.cursorPos;
        const x = cursor.x - frame.x;
        const y = cursor.y - frame.y;
        return titleBar > 0 && x >= greenLeft && x < greenRight && y >= 0 && y < titleBar;
    }

    function screenArea(window) {
        return KWin.Workspace.clientArea(KWin.Workspace.FullScreenArea, window);
    }

    // Height of the menu bar: the strut it reserves at the top.
    function menuBarHeight(window) {
        return KWin.Workspace.clientArea(KWin.Workspace.MaximizeArea, window).y - screenArea(window).y;
    }

    // Height of the Dock on the window's screen, for the bottom reveal.
    function dockReach(window) {
        const area = screenArea(window);
        let reach = 8;
        for (const other of KWin.Workspace.stackingOrder) {
            const frame = other.frameGeometry;
            if (other.dock && Math.abs(frame.y + frame.height - (area.y + area.height)) < 2
                    && frame.height < area.height / 3) {
                reach = Math.max(reach, frame.height);
            }
        }
        return reach;
    }

    function menusOpen() {
        return KWin.Workspace.stackingOrder.some(other =>
            (other.popupWindow || other.appletPopup || other.dropdownMenu || other.popupMenu)
                && !other.minimized);
    }

    // Frame of a space: the client fills the screen and the title bar sits
    // just above it.
    function place(space) {
        const area = screenArea(space.window);
        const b = space.borders;
        space.window.frameGeometry = Qt.rect(area.x - b.left, area.y - b.top,
            area.width + b.left + b.right, area.height + b.top + b.bottom);
    }

    function enter(window, restore, borders) {
        if (spaceOf(window)) {
            return;
        }
        const space = { window: window, restore: restore, keepAbove: window.keepAbove, borders: borders };
        if (window.maximizeMode !== 0) {
            window.setMaximize(false, false);
        }
        spaces = spaces.concat([space]);
        window.keepAbove = true;
        place(space);
        if (KWin.Workspace.activeWindow === window) {
            follow(window);
        }
    }

    function leave(space, restoreGeometry) {
        spaces = spaces.filter(entry => entry !== space);
        if (current === space) {
            current = null;
            resetReveal();
        }
        space.window.keepAbove = space.keepAbove;
        if (restoreGeometry) {
            space.window.frameGeometry = space.restore;
        }
    }

    // Only the active space is kept above the panels: another window
    // brought forward (from the Dock, Alt+Tab...) shows up normally.
    function follow(active) {
        // Dialogs of the space keep it in front; the menu bar, the Dock and
        // their popups do not count as another window.
        let space = spaceOf(active);
        for (let parent = active.transientFor; !space && parent; parent = parent.transientFor) {
            space = spaceOf(parent);
        }
        if (!space && !active.normalWindow && !active.desktopWindow) {
            return;
        }
        if (space === current) {
            return;
        }
        if (current) {
            const previous = current;
            current = null;
            resetReveal();
            place(previous);
            previous.window.keepAbove = false;
        }
        if (space) {
            current = space;
            resetReveal();
            space.window.keepAbove = true;
            place(space);
        }
    }

    function setReveal(mode) {
        if (reveal === mode || !current) {
            return;
        }
        reveal = mode;
        // Below the panels, the menu bar (or the Dock) shows over the window.
        current.window.keepAbove = mode === "hidden";
    }

    function track() {
        if (!current) {
            return;
        }
        const window = current.window;
        const area = screenArea(window);
        const cursor = KWin.Workspace.cursorPos;
        const onScreen = cursor.x >= area.x && cursor.x < area.x + area.width
            && cursor.y >= area.y && cursor.y < area.y + area.height;
        if (reveal === "hidden") {
            if (onScreen && cursor.y <= area.y) {
                setReveal("top");
            } else if (onScreen && cursor.y >= area.y + area.height - 1) {
                setReveal("bottom");
            }
        } else if (reveal === "top") {
            const reach = area.y + menuBarHeight(window) + 24;
            if ((!onScreen || cursor.y > reach) && !menusOpen()) {
                setReveal("hidden");
            }
        } else if (!onScreen || cursor.y < area.y + area.height - dockReach(window) - 24) {
            setReveal("hidden");
        }
    }

    function handleMaximizeRequest(window, mode) {
        pending = pending.filter(entry => entry.window !== window);
        const space = spaceOf(window);
        if (mode === maximizeFull && !window.fullScreen && (space || window.fullScreenable)
                && cursorOnGreenButton(window)) {
            pending = pending.concat([{
                window: window,
                restore: rectOf(window.frameGeometry),
                borders: bordersOf(window.frameGeometry, window.clientGeometry),
            }]);
        } else if (space) {
            // Zoomed some other way (title bar double-click): just a window again.
            leave(space, false);
        }
    }

    function handleMaximized(window) {
        const request = pending.find(entry => entry.window === window);
        if (!request) {
            return;
        }
        pending = pending.filter(entry => entry !== request);
        if (window.maximizeMode !== maximizeFull) {
            return;
        }
        const space = spaceOf(window);
        window.setMaximize(false, false);
        if (space) {
            leave(space, true);
        } else {
            enter(window, request.restore, request.borders);
        }
    }

    function watch(window) {
        if (!window || !window.normalWindow) {
            return;
        }
        window.maximizedAboutToChange.connect(mode => root.handleMaximizeRequest(window, mode));
        window.maximizedChanged.connect(() => root.handleMaximized(window));
        window.fullScreenChanged.connect(() => {
            const space = spaceOf(window);
            if (space && window.fullScreen) {
                leave(space, false);
            }
        });
        window.interactiveMoveResizeStarted.connect(() => {
            const space = spaceOf(window);
            if (space) {
                leave(space, false);
            }
        });
        window.closed.connect(() => {
            pending = pending.filter(entry => entry.window !== window);
            const space = spaceOf(window);
            if (space) {
                leave(space, false);
            }
        });
    }

    function toggle(window) {
        if (!window) {
            return;
        }
        const space = spaceOf(window);
        if (space) {
            leave(space, true);
        } else if (window.fullScreen) {
            window.fullScreen = false;
        } else if (window.normalWindow && window.fullScreenable) {
            enter(window, rectOf(window.frameGeometry),
                bordersOf(window.frameGeometry, window.clientGeometry));
        }
    }

    Connections {
        target: KWin.Workspace
        function onWindowAdded(window) {
            root.watch(window);
        }
        function onWindowActivated(window) {
            if (window) {
                root.follow(window);
            }
        }
        function onCursorPosChanged() {
            root.track();
        }
    }

    // Menus closing do not move the cursor.
    Timer {
        interval: 120
        repeat: true
        running: root.reveal === "top"
        onTriggered: root.track()
    }

    KWin.ShortcutHandler {
        name: "MacTahoeToggleFullScreen"
        text: "AquaDesktop: Toggle Full Screen"
        sequence: "Ctrl+Meta+F"
        onActivated: root.toggle(KWin.Workspace.activeWindow)
    }

    Component.onCompleted: KWin.Workspace.stackingOrder.forEach(window => root.watch(window))
}
