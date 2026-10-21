import QtQuick
import QtQuick.Controls
import org.kde.kirigami as Kirigami

Item {
    id: scrollview

    property alias model: categorySwitcher.model
    property alias currentIndex: categorySwitcher.currentIndex
    implicitHeight: categorySwitcher.currentItem ? categorySwitcher.currentItem.implicitHeight : 0

    signal categorySwitched(int index)

    ListView {
        id: categorySwitcher
        spacing: main.detachedSearch ? Kirigami.Units.smallSpacing * 2.5 : 7
        orientation: ListView.Horizontal
        interactive: contentWidth > width
        boundsBehavior: Flickable.StopAtBounds
        flickDeceleration: 1500
        clip: true
        highlightResizeDuration: 0
        highlightMoveDuration: 50
        anchors.fill: parent

        delegate: CategoryPill {
            id: del
            required property var model
            required property var index
            selected: categorySwitcher.currentIndex == index
            text: model.name
            y: (categorySwitcher.height - height) / 2

            // Emit on click only: currentIndex also moves when the
            // category list rebuilds, and that must not switch views.
            onClicked: {
                categorySwitcher.currentIndex = index
                scrollview.categorySwitched(model.modelIndex)
            }
        }

        WheelHandler {
            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
            onWheel: (event) => {
                if (event.angleDelta.x !== 0) {
                    categorySwitcher.flick(event.angleDelta.x * 15, 0);
                } else if (event.angleDelta.y !== 0) {
                    categorySwitcher.flick(event.angleDelta.y * 15, 0);
                }
            }
        }
    }
}
