"""macOS controls for Qt Quick / Kirigami apps (org.kde.mactahoe)."""

STYLE = "qml/org.kde.mactahoe"


def test_style_inherits_org_kde_desktop(offline):
    qmldir = (offline / STYLE / "qmldir").read_text().splitlines()
    assert qmldir[0] == "module org.kde.mactahoe"
    assert "import org.kde.desktop auto" in qmldir
    for control in ("ItemDelegate", "Menu", "MenuItem", "Switch", "SwitchDelegate"):
        assert f"{control} 1.0 {control}.qml" in qmldir
        source = (offline / STYLE / f"{control}.qml").read_text()
        assert f"Desktop.{control} {{" in source


def test_rows_and_switches_follow_macos(offline):
    row = (offline / STYLE / "ItemDelegate.qml").read_text()
    assert "radius: 6" in row and "Kirigami.Theme.highlightColor" in row
    assert "hovered" not in row  # no hover highlight, like macOS
    switch = (offline / STYLE / "MacSwitchIndicator.qml").read_text()
    assert "implicitWidth: 36" in switch and "implicitHeight: 16" in switch
    assert "width: 22" in switch  # Tahoe's capsule knob


def test_kirigami_platform_is_a_symlink_and_env_is_guarded(tmp_path):
    from steps import _qqc2_style
    script = _qqc2_style.env_script(tmp_path / "qmldir", tmp_path / "org.kde.mactahoe.so")
    assert script.startswith(_qqc2_style.ENV_MARKER)
    assert "export QT_QUICK_CONTROLS_STYLE=org.kde.mactahoe" in script
    assert f"[ -f '{tmp_path / 'qmldir'}' ] && [ -e '{tmp_path / 'org.kde.mactahoe.so'}' ]" in script
    import inspect
    code = inspect.getsource(_qqc2_style.install)
    assert "link.symlink_to(_BASE_PLUGIN)" in code
    assert "shutil.copy" not in code


def test_menus_show_no_icons_like_macos(offline, src):
    """macOS menus show the label and the right-aligned shortcut, no icon:
    Qt Quick menus through this style, QWidget (and, through kded's
    gtkconfig, GTK) menus through kdeglobals."""
    item = (offline / STYLE / "MenuItem.qml").read_text()
    assert "Kirigami.Icon {" not in item
    assert "itemShortcut.nativeText" in item
    # Items Menu builds for plain Actions must use this MenuItem too.
    assert "delegate: MenuItem {}" in (offline / STYLE / "Menu.qml").read_text()
    kvantum = (src / "scripts/steps/kvantum.py").read_text()
    assert 'MENU_ICONS_KEY = "ShowIconsInMenuItems"' in kvantum
    assert '"--key", MENU_ICONS_KEY, "false"' in kvantum
    assert '"--key", MENU_ICONS_KEY, "--delete"' in kvantum
