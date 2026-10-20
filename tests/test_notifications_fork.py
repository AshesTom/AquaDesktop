"""Plasma's notifications applet, forked for macOS Tahoe banners."""

import json
import re

ROOT = "plasmoids/org.kde.mac.tahoe.liquid.notifications"
LAYOUTS = (
    "layouts/mac-tahoe.js",
    "look-and-feel/MacTahoeLiquidKde-Dark/contents/layouts/org.kde.plasma.desktop-layout.js",
    "look-and-feel/MacTahoeLiquidKde-Light/contents/layouts/org.kde.plasma.desktop-layout.js",
)


def test_fork_identity_and_provenance(offline):
    root = offline / ROOT
    meta = json.loads((root / "metadata.json").read_text())
    assert meta["KPlugin"]["Id"] == "org.kde.mac.tahoe.liquid.notifications"
    assert "plasma_add_applet(org.kde.mac.tahoe.liquid.notifications" in (root / "CMakeLists.txt").read_text()
    assert meta["X-Plasma-Provides"] == ["org.kde.plasma.notifications"]
    # The layout swaps it in; it must not show up next to the stock applet.
    assert meta["KPlugin"]["EnabledByDefault"] is False
    upstream = (root / "UPSTREAM.md").read_text()
    assert "v6.7.5" in upstream and "applets/notifications" in upstream
    assert (root / "protocols/plasma-shell.xml").is_file()
    cmake = (root / "CMakeLists.txt").read_text()
    assert "protocols/plasma-shell.xml" in cmake
    assert 'TRANSLATION_DOMAIN="plasma_applet_org.kde.plasma.notifications"' in cmake


def test_qml_uses_the_fork_module_and_plasma_catalog(offline):
    for path in (offline / ROOT).rglob("*.qml"):
        text = path.read_text()
        assert "plasma.applet.org.kde.plasma.notifications" not in text, path
        assert not re.search(r"\bi18n(?:c|p|cp)?\(", text), path


def test_banner_geometry_matches_macos(offline):
    globals_qml = (offline / ROOT / "global/Globals.qml").read_text()
    assert "property int popupWidth: 344" in globals_qml
    assert "property int popupEdgeDistance: 10" in globals_qml
    assert "property int popupTopDistance: 15" in globals_qml
    assert "property int popupSpacing: 6" in globals_qml
    assert "y += popupTopDistance;" in globals_qml
    popup = (offline / ROOT / "NotificationPopup.qml").read_text()
    assert "readonly property int maximumContentWidth: minimumContentWidth" in popup


def test_banner_layout_matches_macos(offline):
    delegate = (offline / ROOT / "delegates/DelegatePopup.qml").read_text()
    # No header row and no timeout bar.
    assert "NotificationHeader" not in delegate
    assert "completionFraction" not in delegate
    # 32 px app icon on the left, 13 px insets, bold 13 px title.
    assert "Layout.column: 0" in delegate and "Layout.preferredWidth: 32" in delegate
    assert "source: modelInterface.icon || modelInterface.applicationIconSource" in delegate
    assert "columnSpacing: 13" in delegate
    assert "readonly property int edgeInset: 13" in delegate
    assert "font.weight: Font.Bold" in delegate
    # A close button on hover.
    assert "delegateRoot.modelInterface.closeClicked()" in delegate
    assert "hover.hovered" in delegate


def test_layouts_swap_the_stock_applet_for_the_fork(offline):
    for layout in LAYOUTS:
        text = (offline / layout).read_text()
        extra = re.search(r'writeConfig\("extraItems", "([^"]+)"\)', text).group(1).split(",")
        known = re.search(r'writeConfig\("knownItems", "([^"]+)"\)', text).group(1).split(",")
        hidden = re.search(r'writeConfig\("hiddenItems", "([^"]+)"\)', text).group(1).split(",")
        assert "org.kde.mac.tahoe.liquid.notifications" in extra
        assert "org.kde.plasma.notifications" not in extra
        assert "org.kde.plasma.notifications" in known
        assert "org.kde.mac.tahoe.liquid.notifications" in hidden


def test_plasmoids_step_builds_and_installs_the_fork():
    from steps import plasmoids
    artifacts = [str(p) for p in plasmoids.build_artifacts()]
    assert any(p.endswith("org.kde.mac.tahoe.liquid.notifications.so") for p in artifacts)
    assert "qt6-waylandclient-cmake:qt6-wayland" in plasmoids.deps()


def test_waylandclient_token_maps_on_every_family():
    import distro
    row = distro._PACKAGE_MAP["qt6-waylandclient-cmake"]
    for family in ("arch", "debian", "ubuntu", "fedora", "opensuse", "gentoo"):
        assert row[family]


def test_history_is_a_frameless_window_of_glass_cards(offline):
    """The Notification Center, after NextKde's history: its own frameless
    window (the tray's popup always draws a frame and a shadow), each card
    and pill a glass bubble GlassBlur blurs on its own."""
    root = offline / ROOT
    main = (root / "main.qml").read_text()
    assert "preferredRepresentation: compactRepresentation" in main
    assert "fullRepresentation: Item {}" in main
    assert "backgroundHints: PlasmaCore.Dialog.NoBackground" in main
    assert 'source: "components/WindowBlur.qml"' in main
    assert "onLoaded: item.target = historyView" in main
    assert "onGlassChanged: if (blurLoader.item) blurLoader.item.update()" in main
    # A group is a stack until clicked.
    assert "groupLimit: 1" in main and "expandUnread: false" in main
    blur = (root / "components/WindowBlur.qml").read_text()
    assert "import org.kde.mac.tahoe.liquid.glass as Glass" in blur
    # Only WindowBlur.qml needs the compiled module: without it the Loader
    # loses the blur, never the history.
    for path in root.rglob("*.qml"):
        if path.name != "WindowBlur.qml":
            assert "org.kde.mac.tahoe.liquid.glass" not in path.read_text(), path

    card = (root / "components/GlassCard.qml").read_text()
    assert "property real radius: 24" in card
    assert "readonly property real glassRadius: radius" in card
    assert "GlassSurface {" in card and "border.width" not in card

    full = (root / "FullRepresentation.qml").read_text()
    assert "PlasmoidHeading" not in full and "widgets/line" not in full
    assert "implicitWidth: 356" in full
    assert "readonly property int cardSpacing: 8" in full
    assert "readonly property int stackStep: 6" in full
    assert full.count("Components.GlassCard {") >= 6
    assert "historyModel.groupIndex(rowIdx)" in full
    assert "signal glassChanged()" in full
    assert "QQC2.ScrollBar.AlwaysOff" in full

    grouped = (root / "delegates/DelegateHistoryGrouped.qml").read_text()
    assert "DelegateHistory {" in grouped
    history = (root / "delegates/DelegateHistory.qml").read_text()
    assert "Layout.preferredWidth: 32" in history and "font.weight: Font.Bold" in history

    cmake = (root / "CMakeLists.txt").read_text()
    for name in ("GlassCard", "GlassSurface", "WindowBlur", "BlurSettler"):
        assert f"components/{name}.qml" in cmake
    assert "RESOURCES components/shaders/glasssurface.frag.qsb" in cmake


def test_history_glass_face_is_the_popovers_copy(offline):
    clock = offline / "plasmoids/org.kde.mac-tahoe-liquid-kde.clock/contents/ui"
    ours = offline / ROOT / "components"
    for name in ("GlassSurface.qml", "BlurSettler.qml", "shaders/glasssurface.frag",
                 "shaders/glasssurface.frag.qsb"):
        assert (ours / name).read_bytes() == (clock / name).read_bytes(), name


def test_glass_blur_cuts_shapes_to_clipping_items_and_returns_the_mask(offline):
    cpp = (offline / "qml/org.kde.mac.tahoe.liquid.glass/glassblur.cpp").read_text()
    # A card scrolled half out of the history's list is blurred (and takes
    # clicks) only where it shows.
    assert "if (item->clip())" in cpp and "shape &= itemClip.toAlignedRect();" in cpp
    # The window's input mask goes back to the whole window with the glass.
    assert "m_window->setMask(QRegion());" in cpp
