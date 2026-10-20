import QtQuick 
import org.kde.kirigami as Kirigami

Text {
    id: pill

    property bool selected: false
    signal clicked

    topPadding: main.detachedSearch ? Kirigami.Units.smallSpacing * 1.25 : 4
    bottomPadding: topPadding
    leftPadding: main.detachedSearch ? Kirigami.Units.smallSpacing * 3 : 8
    rightPadding: leftPadding
    font.family: Kirigami.Theme.defaultFont.family
    font.pointSize: main.appTextSize

    color: main.detachedSearch ? main.textColor : selected ? "#000000" : main.textColor
    opacity: main.detachedSearch ? (selected ? 1 : 0.82) : selected ? 0.8 : 0.4

   Rectangle {
        id: pillBg
        anchors.fill: parent
        anchors.centerIn: parent
        z: -1
        color: main.detachedSearch
            ? (main.isDarkTheme ? Qt.rgba(1, 1, 1, selected ? 0.18 : 0.10) : Qt.rgba(0, 0, 0, selected ? 0.14 : 0.07))
            : selected ? Qt.rgba(255, 255, 255, 0.5) : main.isDarkTheme ? Qt.rgba(255, 255, 255, 0.2) : Qt.rgba(255, 255, 255, 0.5)
        radius: main.detachedSearch ? height * 0.45 : 8
    }

    MouseArea {
        anchors.fill: pill
        onClicked: pill.clicked();
    }
}
