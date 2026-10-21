import QtQuick
import Qt5Compat.GraphicalEffects

DropShadow {
    property real haloOpacity: 0.35
    readonly property color foregroundColor: main.textColor
    readonly property real luminance: 0.2126 * foregroundColor.r
        + 0.7152 * foregroundColor.g + 0.0722 * foregroundColor.b

    color: luminance < 0.5 ? Qt.rgba(1, 1, 1, haloOpacity) : Qt.rgba(0, 0, 0, haloOpacity)
    radius: 2
    samples: 9
    spread: 0
    horizontalOffset: 0
    verticalOffset: 0
}
