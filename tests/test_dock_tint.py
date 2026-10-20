"""The glass's tint (theme_switch.apply_dock_tint): Apple's colours or none
(no veil; neutral greys the blur), the Control Center's tint or the accent
colour, denser in the frosted style, written into the installed Plasma
themes."""

import gzip
import json

import theme_switch as ts

VEIL = '<rect style="opacity:0.22;fill:#aaaaa1" id="south-center" width="12" height="12" />'


def _themes(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    paths = {}
    for name in ("MacTahoeLiquidKde-Dark", "MacTahoeLiquidKde-Light",
                 "MacTahoeLiquidKde-Dark-ReducedTransparency"):
        path = tmp_path / "data/plasma/desktoptheme" / name / "widgets/panel-background.svgz"
        path.parent.mkdir(parents=True)
        path.write_bytes(gzip.compress(f"<svg>{VEIL}</svg>".encode()))
        paths[name] = path
    return paths


def _veil(path):
    text = gzip.decompress(path.read_bytes()).decode()
    return text[text.index("style="):text.index(' id="south-center"')]


def test_macos_neutral_and_accent(tmp_path, monkeypatch):
    paths = _themes(tmp_path, monkeypatch)
    monkeypatch.setattr(ts, "glass_style", lambda: "tahoe")
    apply = ts.apply_dock_tint_unpatched
    # macOS and neutral: no veil, the effect's Dock material does the colour.
    assert apply("macos") is True
    assert _veil(paths["MacTahoeLiquidKde-Light"]) == 'style="opacity:0;fill:#aaaaa1"'
    assert apply("neutral") is False  # nothing to change
    monkeypatch.setattr(ts, "accent_color_hex", lambda: "#ff8d28")
    assert apply("accent") is True
    assert _veil(paths["MacTahoeLiquidKde-Light"]) == 'style="opacity:0.22;fill:#ff8d28"'
    # Reduced transparency keeps its own Dock.
    assert _veil(paths["MacTahoeLiquidKde-Dark-ReducedTransparency"]) == 'style="opacity:0.22;fill:#aaaaa1"'
    # The Control Center tint is gone: a saved one falls back to macOS.
    assert "control-center" not in ts.DOCK_TINTS
    apply("macos")
    assert _veil(paths["MacTahoeLiquidKde-Dark"]) == 'style="opacity:0;fill:#aaaaa1"'


def test_neutral_tint_takes_the_colour_out_of_the_glass(monkeypatch):
    monkeypatch.setattr(ts, "glass_style", lambda: "tahoe")
    for mode in ("dark", "light"):
        macos = ts.glass_preset(mode, tint="macos")
        assert macos == ts.GLASS_PRESETS[f"{mode}-tahoe"]
        neutral = ts.glass_preset(mode, tint="neutral")
        # Grey blur behind the Dock (0: the general value), menus and windows.
        assert (neutral["Saturation"], neutral["DockSaturation"]) == ("0", "0")
        assert neutral["DockContrast"] == macos["DockContrast"]
    assert ts.glass_preset("dark", "frosted", "neutral")["Saturation"] == "0"
    # The shipped presets themselves are left alone.
    assert ts.GLASS_PRESETS["dark-tahoe"]["Saturation"] == "100"


def test_frosted_style_has_its_own_veil(tmp_path, monkeypatch):
    paths = _themes(tmp_path, monkeypatch)
    ts.apply_dock_tint_unpatched("neutral", glass="frosted")
    assert _veil(paths["MacTahoeLiquidKde-Dark"]) == 'style="opacity:0.45;fill:#1e1e20"'
    assert _veil(paths["MacTahoeLiquidKde-Light"]) == 'style="opacity:0.45;fill:#f5f5f7"'
    monkeypatch.setattr(ts, "accent_color_hex", lambda: "#34c759")
    ts.apply_dock_tint_unpatched("accent", glass="frosted")
    assert _veil(paths["MacTahoeLiquidKde-Dark"]) == 'style="opacity:0.45;fill:#34c759"'


def test_accent_tint_colours_the_kvantum_menus(offline, monkeypatch):
    """Kvantum's menu frame (centre, edges, corners) mixed with the accent:
    35 % into the dark #333333, 20 % into the light white."""
    monkeypatch.setattr(ts, "accent_color_hex", lambda: "#ff8d28")
    assert ts.menu_tint_colour("mac-tahoe-liquid-kdeDark", "macos") == "#333333"
    assert ts.menu_tint_colour("mac-tahoe-liquid-kdeDark", "accent") == "#7a522f"
    assert ts.menu_tint_colour("mac-tahoe-liquid-kde", "accent") == "#ffe8d4"
    for name in ("mac-tahoe-liquid-kdeDark", "mac-tahoe-liquid-kde"):
        svg = (offline / "kvantum/mac-tahoe-liquid-kde" / f"{name}.svg").read_text()
        tinted = ts.tint_kvantum_menus(svg, "#7a522f")
        assert tinted.count("fill:#7a522f") == 3, name
        assert len(tinted) == len(svg)


def test_set_dock_tint_saves_and_reloads(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    applied, reloaded, presets = [], [], []
    monkeypatch.setattr(ts, "apply_dock_tint", lambda tint=None, glass=None: applied.append(tint) or True)
    monkeypatch.setattr(ts, "reload_plasma_theme", lambda: reloaded.append(1) or True)
    monkeypatch.setattr(ts, "current_mode", lambda: "dark")
    monkeypatch.setattr(ts, "apply_glass_preset", lambda mode: presets.append(mode) or True)
    assert ts.dock_tint() == "macos"
    cycled = []
    monkeypatch.setattr(ts, "apply_kvantum_accent", lambda: True)
    monkeypatch.setattr(ts, "cycle_widget_style_live", lambda style: cycled.append(style) or True)
    assert ts.set_dock_tint("accent") == 0
    assert ts.dock_tint() == "accent"
    assert json.loads((tmp_path / "mac-tahoe-liquid-kde/appearance.json").read_text())["dock_tint"] == "accent"
    assert applied == ["accent"] and reloaded == [1]
    # The context menus (Kvantum) follow the tint at once.
    assert cycled == ["kvantum"]
    assert ts.set_dock_tint("control-center") == 1
    # The blur follows the tint (neutral desaturates it).
    assert presets == ["dark"]
    assert ts.set_dock_tint("rainbow") == 1


def test_command_line(monkeypatch, capsys):
    monkeypatch.setattr(ts, "_sync_session_env", lambda: None)
    monkeypatch.setattr(ts, "dock_tint", lambda: "accent")
    seen = []
    monkeypatch.setattr(ts, "set_dock_tint", lambda value: seen.append(value) or 0)
    assert ts.main(["dock-tint"]) == 0 and capsys.readouterr().out.strip() == "accent"
    assert ts.main(["dock-tint", "neutral"]) == 0 and seen == ["neutral"]


def test_theme_settings_offers_the_dock_tint(offline):
    app = (offline / "theme-settings/theme_settings.py").read_text()
    assert "control-center" not in app
    assert '("neutral", _("Neutral"))' in app and '("macos", _("macOS"))' in app
    assert 'self.window.run_theme_switch(["dock-tint", tint]' in app
    # The blur warning checks the effect in use.
    assert '"better_blur_dxEnabled"' in app


def test_popovers_glass_follows_the_tint(tmp_path, monkeypatch):
    """glass.ini, read by GlassSurface.qml in every menu bar popover."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    ini = tmp_path / "mac-tahoe-liquid-kde/glass.ini"
    assert ts.write_glass_tint("neutral") is True
    assert ini.read_text() == "Tint=neutral\nAccent=\nGlassLevel=50\nStyle=tahoe\n"
    assert ts.write_glass_tint("neutral") is False  # unchanged
    monkeypatch.setattr(ts, "accent_color_hex", lambda: "#ff8d28")
    ts.write_glass_tint("accent")
    assert ini.read_text() == "Tint=accent\nAccent=ff8d28\nGlassLevel=50\nStyle=tahoe\n"
    # Every Dock tint apply writes it too.
    seen = []
    monkeypatch.setattr(ts, "write_glass_tint", lambda tint=None: seen.append(tint) or True)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    ts.apply_dock_tint_unpatched("macos")
    assert seen == ["macos"]
