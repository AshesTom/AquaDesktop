"""Kvantum: the Finder pass (AquaDesktop).

Measured on Finder (macOS Tahoe, 1x): opaque #1E1E1E content beside a
lighter glass sidebar, no toolbar band (title bar and toolbar in the
content's colour), toolbar buttons grouped in capsules, capsule push
buttons / fields / tabs, thin overlay scroll bars and plain check marks in
menus.
"""

import configparser
import re
from pathlib import Path

import pytest

KV = Path(__file__).resolve().parent.parent / "src/offline/kvantum/mac-tahoe-liquid-kde"
THEMES = ("mac-tahoe-liquid-kdeDark", "mac-tahoe-liquid-kde")


def _cfg(name):
    cfg = configparser.ConfigParser(strict=False, interpolation=None)
    cfg.optionxform = str
    cfg.read(KV / f"{name}.kvconfig")
    return cfg


def _element(svg, id_):
    m = re.search(rf'<[^<>]*\bid="{re.escape(id_)}"[^<>]*>', svg)
    return m.group(0) if m else None


@pytest.mark.parametrize("name", THEMES)
def test_controls_are_capsules(name):
    cfg = _cfg(name)
    for section in ("PanelButtonCommand", "ToolbarButton", "Tab", "ScrollbarSlider"):
        assert int(cfg[section]["frame.expansion"]) >= 64, section
    general = cfg["%General"]
    assert general["group_toolbar_buttons"] == "true"
    assert general["transient_scrollbar"] == "true"
    assert int(general["scroll_width"]) <= 10


@pytest.mark.parametrize("name,base,accent", [
    ("mac-tahoe-liquid-kdeDark", "#1E1E1E", "#0091FF"),
    ("mac-tahoe-liquid-kde", "#FFFFFF", "#0088FF"),
])
def test_content_is_opaque_and_the_window_is_glass(name, base, accent):
    colors = _cfg(name)["GeneralColors"]
    assert colors["base.color"] == base
    assert colors["highlight.color"] == accent
    window = colors["window.color"]
    assert len(window) == 9 and window[-2:] != "FF"  # translucent sidebar


def _fill(svg, id_):
    tag = _element(svg, id_)
    assert tag is not None, id_
    return re.search(r"fill:(#[0-9a-fA-F]{6})", tag).group(1).upper()


@pytest.mark.parametrize("name,mode,header", [
    ("mac-tahoe-liquid-kdeDark", "Dark", "30,30,30"),
    ("mac-tahoe-liquid-kde", "Light", "255,255,255"),
])
def test_title_bar_and_toolbar_take_the_content_colour(name, mode, header):
    # Tahoe draws no toolbar band: the title bar, toolbar and menu bar of an
    # active window are the content's colour (#21212D on the dark Finder
    # capture, its wallpaper tint aside), only the capsules stand out.
    base = _cfg(name)["GeneralColors"]["base.color"].upper()
    svg = (KV / f"{name}.svg").read_text()
    for id_ in ("toolbar-normal", "toolbar-normal-top", "menubar-normal"):
        assert _fill(svg, id_) == base, id_
    offline = KV.parent.parent
    deco = (offline / f"aurorae/MacTahoeLiquidKde-{mode}/decoration.svg").read_text()
    assert _fill(deco, "decoration-center") == base
    # Kirigami headers (System Settings) sit under the same title bar.
    scheme = configparser.ConfigParser(strict=False, interpolation=None)
    scheme.read(offline / f"color-schemes/MacTahoeLiquidKde{mode}.colors")
    assert scheme["Colors:Header"]["BackgroundNormal"] == header
    assert "#{:02X}{:02X}{:02X}".format(*map(int, header.split(","))) == base


@pytest.mark.parametrize("name", THEMES)
def test_menu_checks_are_plain_check_marks(name):
    svg = (KV / f"{name}.svg").read_text()
    for kind in ("checkbox", "radio"):
        assert svg.count(f'id="menu-{kind}-checked-normal"') == 1
        group = re.search(rf'<g id="menu-{kind}-checked-normal">(.*?)</g>', svg).group(1)
        assert "stroke-linecap:round" in group and "fill:none" in group
        # Unchecked items draw nothing.
        empty = re.search(rf'<g id="menu-{kind}-normal">(.*?)</g>', svg).group(1)
        assert "opacity:0" in empty and "<path" not in empty


def test_light_default_button_has_no_corner_indicator():
    svg = (KV / "mac-tahoe-liquid-kde.svg").read_text()
    assert _element(svg, "button-default-indicator") is None
    assert "fill:#0088ff" in _element(svg, "button-default")
    assert _element(svg, "tbutton-normal-topleft") is not None
