/*
    AquaDesktop — macOS Tahoe Downloads fan.

    Measured on a macOS Tahoe 1x capture: the files climb from the Dock
    icon on a 64 px pitch (one icon box), each on the same shallow arc
    (3 px, then 8 px off the column for the 2nd and 3rd item) and turned
    along it (~1.8 deg, ~3.6 deg), with their name in a black pill on the
    side facing the screen. The newest file sits nearest the Dock and the
    fan ends with a round "Open in Finder" button. There is no background,
    no scrolling: the fan shows what fits above the Dock.

    Adapted from plasma-downloads-stack
    (https://github.com/cromewar/plasma-downloads-stack).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Window
import org.kde.kirigami as Kirigami

Item {
    id: fan

    property var files: []
    property int extraCount: 0
    property int iconSize: 64
    property string folderPath: ""
    property bool active: false      // drives the fan-out animation
    property bool up: true           // fan climbs up (false = descends)
    property bool labelsLeft: false

    signal openFile(var url)
    signal openFolder()
    signal closeRequested()

    // The arc bows away from the labels: drift(h) = h^2 / (32 * icon box),
    // i.e. 2 px and 8 px for the 2nd and 3rd file, each file leaning along
    // half the arc's slope. Like macOS, the fan holds at most ten files.
    readonly property real pitch: iconSize
    readonly property real arcScale: iconSize * 32
    readonly property int maxFiles: 10
    readonly property real bowSign: labelsLeft ? 1 : -1
    readonly property int pad: 16
    readonly property real labelGap: 6
    readonly property real labelW: iconSize * 3

    // ---------------------------------------------------------------- canvas
    // The popup window never changes size with the number of files: the fan
    // is laid out inside a constant canvas, anchored to the measured panel
    // icon (anchorIconX / anchorIconY), so the shell never re-positions the
    // popup and the fan cannot drift.
    readonly property real canvasH: Math.max(iconSize * 6,
        (Screen.desktopAvailableHeight > 0 ? Screen.desktopAvailableHeight : 1000) * 0.82)
    readonly property real sideMax: pad + labelW + labelGap
    implicitWidth: sideMax * 2 + iconSize
    implicitHeight: canvasH
    readonly property real cH: height > 0 ? height : canvasH

    // x / y (own coordinates) of the panel icon's centre and near edge, set
    // by main.qml from real screen coordinates; -1 / NaN until known.
    property real anchorIconX: -1
    property real anchorIconY: NaN

    // Plasma aligns an applet popup with the applet's outer edge, so the
    // room on the bow side is whatever is left there; the arc shrinks to
    // fit it rather than leaving the window.
    readonly property real edgePad: 4
    readonly property real defColStart: sideMax
    readonly property real minColStart: labelsLeft ? sideMax : edgePad
    readonly property real maxColStart: implicitWidth - iconSize - (labelsLeft ? edgePad : sideMax)
    readonly property real iconColStart: (anchorIconX >= 0 && maxColStart > minColStart)
        ? Math.max(minColStart, Math.min(maxColStart, anchorIconX - iconSize / 2))
        : defColStart

    // macOS leaves ~9 px between the Dock and the nearest file.
    readonly property real panelInset: Math.round(iconSize * 0.14)
    readonly property real nearEdge: up
        ? (isNaN(anchorIconY) ? cH : Math.max(iconSize, Math.min(anchorIconY, cH))) - panelInset
        : (isNaN(anchorIconY) ? 0 : Math.max(0, Math.min(anchorIconY, cH - iconSize))) + panelInset

    // Files that fit above the Dock, keeping one slot for the button.
    readonly property int capacity: Math.min(maxFiles, Math.max(1,
        Math.floor(((up ? nearEdge : cH - nearEdge) - pad) / pitch) - 1))
    readonly property int shownCount: Math.min(files.length, capacity)
    readonly property var shownFiles: files.slice(0, shownCount)

    property int hoveredIndex: -1

    readonly property real bowRoom: labelsLeft
        ? implicitWidth - edgePad - iconColStart - iconSize
        : iconColStart - edgePad
    // The top slot is the "Open in Finder" button.
    readonly property real driftFit: Math.min(1, Math.max(0, bowRoom) / Math.max(1, drift(height_(shownCount))))

    // Distance of slot `i` from the Dock along the column.
    function height_(i: int): real {
        return i * pitch;
    }
    function drift(h: real): real {
        return h * h / arcScale;
    }
    function slotX(i: int): real {
        return iconColStart + bowSign * driftFit * drift(height_(i));
    }
    function slotY(i: int): real {
        return up ? nearEdge - iconSize - height_(i) : nearEdge + height_(i);
    }
    // Half the arc's own slope, like macOS: the fan leans, it does not spin.
    function slotRotation(i: int): real {
        const slope = driftFit * 2 * height_(i) / arcScale;
        return bowSign * (up ? 1 : -1) * Math.atan(slope) * 90 / Math.PI;
    }

    // Clicking empty space closes the fan.
    MouseArea {
        anchors.fill: parent
        onClicked: fan.closeRequested()
    }

    Repeater {
        model: fan.shownFiles
        delegate: FileTile {
            required property int index
            required property var modelData

            iconSize: fan.iconSize
            fileName: modelData.name
            fileUrl: modelData.url
            isDir: modelData.isDir
            labelWidth: fan.labelW
            gapToLabel: fan.labelGap
            labelOnLeft: fan.labelsLeft
            tileRotation: fan.slotRotation(index)

            targetX: fan.slotX(index)
            targetY: fan.slotY(index)
            collapsedX: fan.slotX(0)
            collapsedY: fan.slotY(0)

            shown: fan.active
            stagger: Math.min(index, 14) * 24
            hovered: fan.hoveredIndex === index
            z: fan.hoveredIndex === index ? 100 : (fan.shownCount - index)

            onEntered: fan.hoveredIndex = index
            onExited: if (fan.hoveredIndex === index) fan.hoveredIndex = -1
            onClicked: fan.openFile(fileUrl)
        }
    }

    // "Open in Finder": the round button that ends the fan.
    Item {
        id: openButton

        readonly property int slot: fan.shownCount
        readonly property bool hovered: buttonArea.containsMouse || labelArea.containsMouse

        width: fan.iconSize
        height: fan.iconSize
        x: fan.active ? fan.slotX(slot) : fan.slotX(0)
        y: fan.active ? fan.slotY(slot) : fan.slotY(0)
        rotation: fan.slotRotation(slot)
        opacity: fan.active ? 1 : 0
        scale: fan.active ? 1 : 0.45
        z: 50

        Behavior on x {
            SequentialAnimation {
                PauseAnimation { duration: fan.active ? Math.min(openButton.slot, 14) * 24 : 0 }
                NumberAnimation { duration: 280; easing.type: Easing.OutBack; easing.overshoot: 1.15 }
            }
        }
        Behavior on y {
            SequentialAnimation {
                PauseAnimation { duration: fan.active ? Math.min(openButton.slot, 14) * 24 : 0 }
                NumberAnimation { duration: 280; easing.type: Easing.OutBack; easing.overshoot: 1.15 }
            }
        }
        Behavior on opacity { NumberAnimation { duration: 180 } }
        Behavior on scale { NumberAnimation { duration: 130; easing.type: Easing.OutCubic } }

        // A 58 px dark disc with a light hairline ring, like macOS.
        Rectangle {
            anchors.centerIn: parent
            width: Math.round(fan.iconSize * 0.9)
            height: width
            radius: width / 2
            color: openButton.hovered ? Kirigami.Theme.highlightColor : "#121212"
            border.width: 1.5
            border.color: Qt.rgba(1, 1, 1, 0.75)
            Behavior on color { ColorAnimation { duration: 120 } }

            // Curved "go to" arrow.
            Canvas {
                id: arrow

                anchors.centerIn: parent
                width: Math.round(parent.width * 0.48)
                height: Math.round(width * 0.8)
                property color tint: openButton.hovered ? "white" : "#8c8c8c"
                onTintChanged: requestPaint()
                onPaint: {
                    const c = getContext("2d");
                    const w = width, h = height;
                    c.reset();
                    c.fillStyle = tint;
                    c.beginPath();
                    // Arrow head pointing right.
                    c.moveTo(w, h * 0.42);
                    c.lineTo(w * 0.56, 0);
                    c.lineTo(w * 0.56, h * 0.24);
                    // Shaft curving down to the bottom-left.
                    c.bezierCurveTo(w * 0.18, h * 0.24, 0, h * 0.55, 0, h);
                    c.bezierCurveTo(w * 0.16, h * 0.7, w * 0.34, h * 0.6, w * 0.56, h * 0.6);
                    c.lineTo(w * 0.56, h * 0.84);
                    c.closePath();
                    c.fill();
                }
            }
        }

        MouseArea {
            id: buttonArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: fan.openFolder()
        }

        LabelPill {
            id: buttonLabel

            text: fan.extraCount > 0 || fan.files.length > fan.shownCount
                ? i18n("%1 more in Finder", fan.files.length - fan.shownCount + fan.extraCount)
                : i18n("Open in Finder")
            highlighted: openButton.hovered
            anchors.verticalCenter: parent.verticalCenter
            x: fan.labelsLeft ? -(fan.labelGap + width) : parent.width + fan.labelGap

            MouseArea {
                id: labelArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: fan.openFolder()
            }
        }
    }
}
