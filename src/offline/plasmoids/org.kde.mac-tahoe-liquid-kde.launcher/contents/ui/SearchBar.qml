import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import org.kde.kirigami as Kirigami

RowLayout {
	spacing: Kirigami.Units.smallSpacing

    property alias textField: textField
    property alias showMenuButton: menuButton.visible
    readonly property bool menuOpen: menuButton.menuOpen

    Kirigami.Icon {
        id: searchIcon
        Layout.rightMargin: 0
        Layout.preferredWidth: main.detachedSearch ? Kirigami.Units.gridUnit * 2 : Kirigami.Units.iconSizes.medium
        Layout.preferredHeight: Layout.preferredWidth
        source: Qt.resolvedUrl('icons/AppsIcon.svg')
        isMask: true
        color: main.dimmedTextColor
    }

    TextField {
        id: textField
        Layout.fillHeight: true
        Layout.fillWidth: true
        font.family: Kirigami.Theme.defaultFont.family
        font.pointSize: main.textSize * (main.detachedSearch ? 2 : 1)
        font.weight: Kirigami.Theme.defaultFont.weight
        color: main.textColor

        placeholderText: i18n("Apps")
        placeholderTextColor: main.dimmedTextColor
        background: Rectangle{
            color: "transparent"
        }
        focus: true
        onTextChanged: {
            textField.forceActiveFocus(Qt.ShortcutFocusReason)
            runnerModel.query = text;   
        }

        Keys.onPressed: event => {
            if (event.key == Qt.Key_Escape) {
                event.accepted = true;
                if (searching) {
                    clear();
                } else {
                    root.toggle()
                }
            }

        }
    }

    MenuButton {
        id: menuButton
        Layout.alignment: Qt.AlignVCenter
    }
}
