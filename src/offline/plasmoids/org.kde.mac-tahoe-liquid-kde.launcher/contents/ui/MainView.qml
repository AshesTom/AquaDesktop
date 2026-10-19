import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components 3.0 as PlasmaComponents
import org.kde.coreaddons as KCoreAddons

import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami
import org.kde.mac.tahoe.launcher as Tahoe

import "js/colorType.js" as ColorType

Item {
	id: main
	property bool searching: (searchBar.textField.text != "")
	readonly property bool detachedSearch: kicker.launcherPreset === 2
	readonly property real searchPopupHeight: searchPopup.height
	readonly property real searchPopupGap: Kirigami.Units.largeSpacing * 2
	readonly property bool searchPopupActive: searchPopup.visible && searchPopup.hasFocus
	readonly property bool menuOpen: searchBar.menuOpen

	function focusSearch() {
		if (detachedSearch) {
			searchPopup.activate();
		} else {
			root.requestActivate();
		}
		searchBar.textField.forceActiveFocus(Qt.PopupFocusReason);
	}

	onDetachedSearchChanged: {
		Qt.callLater(function() {
			root.reposition();
			if (root.visible) {
				focusSearch();
			}
		});
	}
	onSearchPopupHeightChanged: root.reposition()
	onMenuOpenChanged: {
		if (!menuOpen && root.visible) {
			root.checkDismissal();
		}
	}

	Tahoe.LauncherSearchPopup {
		id: searchPopup
		objectName: "launcherSearchPopup"
		visualParent: root.contentItem
		popupDirection: Qt.TopEdge
		margin: main.searchPopupGap
		transientParent: root
		visible: root.visible && main.detachedSearch
		hideOnWindowDeactivate: false
		width: Math.max(Kirigami.Units.gridUnit * 16, main.width * 0.62) + leftPadding + rightPadding
		height: Math.max(Kirigami.Units.gridUnit * 3, 56) + topPadding + bottomPadding
		x: root.x + (root.width - width) / 2
		y: root.y - height - main.searchPopupGap
		onHasFocusChanged: root.checkDismissal()

		mainItem: FocusScope {
			id: detachedSearchSlot
		}
	}

	readonly property color textColor: isDarkTheme ? Kirigami.Theme.textColor : "#555555"
	readonly property string textFont: Kirigami.Theme.defaultFont.family
	readonly property real textSize: Kirigami.Theme.defaultFont.pointSize
	readonly property color bgColor: Kirigami.Theme.backgroundColor
	readonly property color highlightColor: Kirigami.Theme.highlightColor
	readonly property color highlightedTextColor: Kirigami.Theme.highlightedTextColor
	readonly property bool isTop: plasmoid.location == PlasmaCore.Types.TopEdge & plasmoid.configuration.launcherPosition != 2 & !plasmoid.configuration.floating

	property bool isDarkTheme: ColorType.isDark(bgColor)
	property color contrastBgColor: isDarkTheme ? Qt.rgba(255, 255, 255, 0.15) : Qt.rgba(0, 0, 0, 0.1)
	property color dimmedTextColor: Qt.rgba(textColor.r, textColor.g, textColor.b, 0.7)

	function reload() {
		searchBar.textField.clear()
		appList.reset()
	}
	function reset(){
		searchBar.textField.clear()
		appList.reset()
	}

	ColumnLayout {

		anchors.top: parent.top
		anchors.left: parent.left
		anchors.right: parent.right
		anchors.bottom: parent.bottom

		spacing: 0

		Item {
			id: inlineSearchSlot
			visible: !main.detachedSearch
			Layout.fillWidth: true
			Layout.preferredHeight: 40
			Layout.maximumHeight: Layout.preferredHeight
			Layout.rightMargin: fs.innerPadding

			SearchBar {
				id: searchBar
				parent: main.detachedSearch ? detachedSearchSlot : inlineSearchSlot
				anchors.fill: parent
				showMenuButton: true
				Keys.priority: Keys.AfterItem
				Keys.forwardTo: searching ? searchList : appList.viewItem
			}
		}

		Rectangle {
			visible: !main.detachedSearch
			Layout.fillWidth: true
			Layout.rightMargin: fs.innerPadding
			Layout.topMargin: 6
			Layout.bottomMargin: 6
			height: 1.5
			color: main.contrastBgColor
		}

		AllAppsList{
			id: appList
			state: "visible"
			Layout.fillHeight: true
			Layout.fillWidth: true

			Keys.priority: Keys.AfterItem
			Keys.forwardTo: searchBar.textField

			visible: opacity > 0
			states: [
				State {
					name: "visible"; when: (!searching)
					PropertyChanges { target: appList; opacity: 1.0 }
				},
				State {
					name: "hidden"; when: (searching)
					PropertyChanges { target: appList; opacity: 0.0}
				}
			]
			transitions: [
				Transition {
					to: "visible"
					PropertyAnimation {properties: 'opacity'; duration: 100; easing.type: Easing.OutQuart}
				},
				Transition {
					to: "hidden"
					PropertyAnimation {properties: 'opacity'; duration: 100; easing.type: Easing.OutQuart}
				}
			]
		}

		SearchList {
			id: searchList
			state: "hidden"
			visible: opacity > 0

			Layout.fillWidth: true
			Layout.fillHeight: true

			states: [
				State {
					name: "visible"; when: (searching)
					PropertyChanges { target: searchList; opacity: 1.0 }
				},
				State {
					name: "hidden"; when: (!searching)
					PropertyChanges { target: searchList; opacity: 0.0}
				}
			]
			transitions: [
				Transition {
					to: "visible"
					PropertyAnimation {properties: 'opacity'; duration: 100; easing.type: Easing.OutQuart}
				},
				Transition {
					to: "hidden"
					PropertyAnimation {properties: 'opacity'; duration: 100; easing.type: Easing.OutQuart}
				}
			]

			Keys.priority: Keys.AfterItem
			Keys.forwardTo: searchBar.textField
		}
	}
}
