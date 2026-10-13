"""Reduced-transparency assets and persistent mode selection (#92)."""
import gzip
import json
import xml.etree.ElementTree as ET

import pytest

import theme_switch as switch
from theme_variants import SUFFIX, generate, opaque_svg


@pytest.mark.parametrize("mode", ["Light", "Dark"])
def test_plasma_variant_raises_surface_opacity_without_changing_shadows(repo, tmp_path, mode):
    source = repo / "src/offline/plasma-theme" / f"MacTahoeLiquidKde-{mode}"
    original = (source / "dialogs/background.svgz").read_bytes()
    generate(source, tmp_path, "plasma")
    before = ET.fromstring(gzip.decompress(original))
    after = ET.fromstring(gzip.decompress((tmp_path / "dialogs/background.svgz").read_bytes()))
    by_id = lambda root, name: next(n for n in root.iter() if n.get("id") == name)
    assert "opacity:0.96" in by_id(after, "center").get("style")
    assert ET.tostring(by_id(before, "shadow-topleft")) == ET.tostring(by_id(after, "shadow-topleft"))
    assert (source / "dialogs/background.svgz").read_bytes() == original
    assert json.loads((tmp_path / "metadata.json").read_text())["KPlugin"]["Id"].endswith(SUFFIX)


def test_svg_transform_preserves_transparent_cutouts_and_gradient_shadows():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><g id="menu-normal"><path style="fill:none;opacity:0"/><path style="fill:url(#shadow);opacity:0.2"/><path style="fill:#fff;opacity:0.6"/></g></svg>'
    nodes = list(ET.fromstring(opaque_svg(svg, "kvantum"))[0])
    assert nodes[0].get("style") == "fill:none;opacity:0"
    assert nodes[1].get("style") == "fill:url(#shadow);opacity:0.2"
    assert nodes[2].get("style") == "fill:#fff;opacity:0.96"


@pytest.mark.parametrize("name", ["mac-tahoe-liquid-kde", "mac-tahoe-liquid-kdeDark"])
def test_kvantum_variant_does_not_multiply_menu_transparency(repo, tmp_path, name):
    generate(repo / "src/offline/kvantum/mac-tahoe-liquid-kde", tmp_path, "kvantum", name)
    assert "reduce_menu_opacity=0" in (tmp_path / f"{name}{SUFFIX}.kvconfig").read_text()
    assert (tmp_path / f"{name}{SUFFIX}.svg").is_file()


@pytest.mark.parametrize("mode,rgb", [("Light", "246, 246, 246"), ("Dark", "32, 32, 32")])
def test_gtk_popups_have_a_readable_surface(repo, tmp_path, mode, rgb):
    generate(repo / "src/offline/gtk" / f"MacTahoeLiquidKde-{mode}", tmp_path, "gtk")
    css = (tmp_path / "gtk-3.0/gtk.css").read_text()
    assert "popover > contents" in css
    assert f"background-color: rgba({rgb}, 0.96)" in css


def test_transparency_is_independent_of_light_dark_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = switch._appearance_path()
    path.parent.mkdir()
    path.write_text('{"transparency":"reduced"}')
    assert switch._kvantum_theme("light") == switch.KVANTUM_THEME_LIGHT + SUFFIX
    assert switch._kvantum_theme("dark") == switch.KVANTUM_THEME_DARK + SUFFIX
    path.write_text('{"transparency":"standard"}')
    assert switch._kvantum_theme("dark") == switch.KVANTUM_THEME_DARK


def test_missing_assets_do_not_persist_a_broken_preference(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert switch.set_transparency("reduced") == 1
    assert not switch._appearance_path().exists()


def test_declarative_appearance_file_is_not_replaced(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    target = tmp_path / "declarative.json"
    target.write_text('{"transparency":"reduced"}')
    path = switch._appearance_path()
    path.parent.mkdir()
    path.symlink_to(target)
    assert switch.set_transparency("standard") == 1
    assert path.is_symlink()
    assert '"reduced"' in target.read_text()


@pytest.mark.parametrize("mode", ["Light", "Dark"])
def test_qt_renders_readable_panel_and_popup_surfaces(repo, mode):
    svg = pytest.importorskip("PyQt6.QtSvg")
    gui = pytest.importorskip("PyQt6.QtGui")
    core = pytest.importorskip("PyQt6.QtCore")
    for filename in ("widgets/panel-background.svgz", "dialogs/background.svgz"):
        data = gzip.decompress((repo / "src/offline/plasma-theme" /
                                f"MacTahoeLiquidKde-{mode}" / filename).read_bytes())
        alpha = []
        for document in (data, opaque_svg(data, "plasma")):
            renderer = svg.QSvgRenderer(document)
            image = gui.QImage(32, 32, gui.QImage.Format.Format_ARGB32)
            image.fill(0)
            painter = gui.QPainter(image)
            renderer.render(painter, "center", core.QRectF(0, 0, 32, 32))
            painter.end()
            alpha.append(image.pixelColor(16, 16).alpha())
        assert alpha[1] >= 240 and alpha[1] > alpha[0]


def test_patch_dock_subcommand_is_idempotent_and_does_not_apply_theme(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(switch, "_sync_session_env", lambda: None)
    monkeypatch.setattr(switch, "apply", lambda *a, **k: pytest.fail("full apply called"))
    path = tmp_path / "plasmashellrc"
    path.write_text("[PlasmaViews][Panel 1]\nfloating=0\npanelOpacity=0\n")
    assert switch.main(["patch-dock"]) == 0
    result = path.read_text()
    assert "floatingApplets=1" in result
    assert "panelOpacity=2" in result
    assert switch.main(["patch-dock"]) == 0
    assert path.read_text() == result


def test_surface_opacity_does_not_multiply_two_transparency_values():
    data = b'<svg xmlns="http://www.w3.org/2000/svg"><path id="center" fill="#fff" opacity="0.6" fill-opacity="0.7"/></svg>'
    node = ET.fromstring(opaque_svg(data, "plasma"))[0]
    style = dict(part.split(":") for part in node.get("style").split(";"))
    assert float(style["opacity"]) * float(style["fill-opacity"]) == 0.96


def test_preference_toggle_preserves_mode_and_other_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    for mode in ("Light", "Dark"):
        name = f"MacTahoeLiquidKde-{mode}{SUFFIX}"
        (tmp_path / "data/plasma/desktoptheme" / name).mkdir(parents=True)
        (tmp_path / ".themes" / name).mkdir(parents=True)
    for name in (switch.KVANTUM_THEME_LIGHT, switch.KVANTUM_THEME_DARK):
        (tmp_path / "config/Kvantum" / (name + SUFFIX)).mkdir(parents=True)
    path = switch._appearance_path()
    path.parent.mkdir()
    path.write_text('{"otherSetting":42}')
    applied = []
    monkeypatch.setattr(switch, "detect_mode_by_system", lambda: "dark")
    monkeypatch.setattr(switch, "_apply_unlocked", lambda mode: applied.append((mode, switch._kvantum_theme(mode))) or True)
    assert switch.set_transparency("reduced") == 0
    assert applied[-1] == ("dark", switch.KVANTUM_THEME_DARK + SUFFIX)
    assert switch.set_transparency("standard") == 0
    assert applied[-1] == ("dark", switch.KVANTUM_THEME_DARK)
    assert json.loads(path.read_text()) == {"transparency": "standard", "otherSetting": 42}
