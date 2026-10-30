"""The glass styles and tint (theme_switch): Liquid Glass or Frosted on the
Acrylic Glass effect, the menu bar's veil, and the Dock veil written into
the installed Plasma themes: Apple's colours, neutral (grey glass) or the
accent colour, denser in the frosted style."""

import gzip
import json
import re

import theme_switch as ts

VEIL = '<rect style="opacity:0.015;fill:#ffffff" id="south-center" width="12" height="12" />'


def _themes(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    paths = {}
    for name in ("MacTahoeLiquidKde-Dark", "MacTahoeLiquidKde-Light"):
        path = tmp_path / "data/plasma/desktoptheme" / name / "widgets/panel-background.svgz"
        path.parent.mkdir(parents=True)
        path.write_bytes(gzip.compress(f"<svg>{VEIL}</svg>".encode()))
        paths[name] = path
    return paths


def _veil(path):
    text = gzip.decompress(path.read_bytes()).decode()
    return text[text.index("style="):text.index(' id="south-center"')]


def test_shipped_veil_matches_the_bundled_themes(offline):
    for theme in ("MacTahoeLiquidKde-Dark", "MacTahoeLiquidKde-Light"):
        path = offline / "plasma-theme" / theme / "widgets/panel-background.svgz"
        svg = gzip.decompress(path.read_bytes()).decode()
        assert ts._DOCK_VEIL_RE.search(svg).group(2) == ts.DOCK_VEIL_SHIPPED


def test_macos_neutral_and_accent(tmp_path, monkeypatch):
    paths = _themes(tmp_path, monkeypatch)
    apply = ts.apply_dock_tint_unpatched
    monkeypatch.setattr(ts, "glass_style", lambda: "tahoe")
    monkeypatch.setattr(ts, "accent_color_hex", lambda: "#ff8d28")
    # macOS and neutral keep the shipped veil.
    assert apply("macos") is False
    assert apply("neutral") is False
    assert apply("accent") is True
    assert _veil(paths["MacTahoeLiquidKde-Light"]) == 'style="opacity:0.22;fill:#ff8d28"'
    # Back to macOS restores the shipped veil.
    assert apply("macos") is True
    assert _veil(paths["MacTahoeLiquidKde-Dark"]) == f'style="{ts.DOCK_VEIL_SHIPPED}"'


def test_frosted_style_has_its_own_veil(tmp_path, monkeypatch):
    paths = _themes(tmp_path, monkeypatch)
    ts.apply_dock_tint_unpatched("neutral", glass="frosted")
    assert _veil(paths["MacTahoeLiquidKde-Dark"]) == 'style="opacity:0.45;fill:#1e1e20"'
    assert _veil(paths["MacTahoeLiquidKde-Light"]) == 'style="opacity:0.45;fill:#f5f5f7"'
    monkeypatch.setattr(ts, "accent_color_hex", lambda: "#34c759")
    ts.apply_dock_tint_unpatched("accent", glass="frosted")
    assert _veil(paths["MacTahoeLiquidKde-Dark"]) == 'style="opacity:0.45;fill:#34c759"'


def test_styles_rebuild_the_edition_acrylic_material(offline, monkeypatch):
    monkeypatch.setattr(ts, "default_wallpaper", lambda: "MacTahoe")
    presets = json.loads((offline / "kwin-effects/acrylic-glass/src/presets.json").read_text())
    tahoe = next(p for p in presets if p["id"] == "tahoe")
    liquid = ts.glass_preset("dark", "tahoe", "macos")
    # Liquid Glass is exactly what the installer writes.
    assert liquid["BlurStrength"] == str(tahoe["values"]["BlurStrength"])
    assert liquid["MaterialPreset"] == str(tahoe["value"])
    assert liquid["DarkGradientOverlay"] == "false"
    dark = ts.glass_preset("dark", "frosted", "macos")
    light = ts.glass_preset("light", "frosted", "macos")
    # Frosted: a deeper blur without lens, refraction or colour drift.
    assert float(dark["BlurStrength"]) > float(liquid["BlurStrength"])
    for key in ("MagnifyGlassStrength", "RefractionWidth", "RgbDriftStrength"):
        assert float(dark[key]) == 0, key
    # AquaDesktop's Better Blur DX frosted values, carried over.
    assert (dark["BlurStrength"], dark["Brightness"], light["Brightness"]) == ("11", "0.85", "1.12")
    # Both styles write the same keys: switching leaves nothing behind.
    assert dark.keys() == liquid.keys() == light.keys()
    # Every key exists in the effect's configuration.
    kcfg = (offline / "kwin-effects/acrylic-glass/src/glass.kcfg").read_text()
    for key in dark:
        assert f'<entry name="{key}"' in kcfg, key


def test_neutral_tint_takes_the_colour_out_of_the_glass(monkeypatch):
    monkeypatch.setattr(ts, "default_wallpaper", lambda: "MacGoldenGate")
    for style in ts.GLASS_STYLES:
        assert ts.glass_preset("dark", style, "neutral")["Saturation"] == "0"
        assert ts.glass_preset("dark", style, "macos")["Saturation"] != "0"
    # The baked presets the standalone switcher uses are the bundled ones.
    assert ts.glass_preset("dark", "tahoe", "macos")["DarkGradientOverlay"] == "true"


def test_glass_preset_only_while_the_effect_is_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    written = []
    monkeypatch.setattr(ts, "_kwrite", lambda *args: written.append(args) or True)
    monkeypatch.setattr(ts, "_qdbus", lambda *args: True)
    assert ts.apply_glass_preset_unpatched("dark") is False and written == []
    (tmp_path / "kwinrc").write_text("[Plugins]\nliquidglassEnabled=true\n")
    assert ts.apply_glass_preset_unpatched("dark") is True
    groups = {args[3] for args in written}
    assert groups == {"Effect-liquidglass"}


def test_style_is_saved_and_applied(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(ts, "glass_style", ts.glass_style_unpatched)
    calls = []
    monkeypatch.setattr(ts, "current_mode", lambda: "light")
    monkeypatch.setattr(ts, "apply_glass_preset", lambda mode: calls.append(("glass", mode)))
    monkeypatch.setattr(ts, "apply_top_bar_style", lambda style=None: calls.append(("bar", style)))
    monkeypatch.setattr(ts, "apply_dock_tint", lambda tint=None, glass=None: calls.append(("dock", glass)))
    assert ts.glass_style() == "tahoe"
    assert ts.set_style("frosted") == 0
    assert ts.glass_style() == "frosted"
    assert calls == [("glass", "light"), ("bar", "frosted"), ("dock", "frosted")]
    assert ts.set_style("aqua") == 1


def test_top_bar_script_carries_the_veil_only_for_tahoe():
    tahoe = ts._top_bar_script(False)
    dark = ts._top_bar_script(True, "dark")
    light = ts._top_bar_script(True, "light")
    assert ts.TOP_BAR_SCRIM in tahoe and ts.TOP_BAR_SCRIM not in dark
    # Tahoe hides Plasma's panel background; frosted shows it, so Plasma
    # asks KWin to blur behind the bar.
    assert '"enabled": false, "opacity": 0' in tahoe
    for script, mode in ((dark, "dark"), (light, "light")):
        assert '"enabled": true, "opacity": 1' in script
        colour, alpha = ts.TOP_BAR_FROSTED[mode]
        assert f'"custom": "{colour}", "alpha": {alpha}' in script
    for script in (tahoe, dark, light):
        # Panel Colorizer's blurBehind needs its compiled helper: unused.
        assert "blurBehind" not in script
        assert f'"{ts.TOP_BAR_FOREGROUND}"' in script


def test_top_bar_layer_is_valid_colorizer_json():
    for mode in ("dark", "light"):
        layer = json.loads(ts._top_bar_frosted_layer(mode))
        assert layer["backgroundColor"]["sourceType"] == 0
        assert 0 < layer["backgroundColor"]["alpha"] < 1


def test_layouts_install_the_tahoe_veil(offline):
    for relative in ("layouts/mac-tahoe.js",
                     "look-and-feel/MacTahoeLiquidKde-Light/contents/layouts/org.kde.plasma.desktop-layout.js",
                     "look-and-feel/MacTahoeLiquidKde-Dark/contents/layouts/org.kde.plasma.desktop-layout.js"):
        script = (offline / relative).read_text()
        assert f'"panel": {{ "normal": {ts.TOP_BAR_SCRIM} }}' in script, relative


def test_set_dock_tint_saves_and_reloads(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(ts, "dock_tint", ts.dock_tint_unpatched)
    applied, reloaded, presets = [], [], []
    monkeypatch.setattr(ts, "apply_dock_tint", lambda tint=None, glass=None: applied.append(tint) or True)
    monkeypatch.setattr(ts, "reload_plasma_theme", lambda: reloaded.append(1) or True)
    monkeypatch.setattr(ts, "current_mode", lambda: "dark")
    monkeypatch.setattr(ts, "apply_glass_preset", lambda mode: presets.append(mode) or True)
    assert ts.dock_tint() == "macos"
    assert ts.set_dock_tint("accent") == 0
    assert ts.dock_tint() == "accent"
    assert json.loads((tmp_path / "mac-tahoe-liquid-kde/appearance.json").read_text())["dock_tint"] == "accent"
    assert applied == ["accent"] and reloaded == [1]
    # The blur follows the tint (neutral desaturates it).
    assert presets == ["dark"]
    assert ts.set_dock_tint("rainbow") == 1


def test_command_line(monkeypatch, capsys):
    monkeypatch.setattr(ts, "_sync_session_env", lambda: None)
    monkeypatch.setattr(ts, "dock_tint", lambda: "accent")
    seen = []
    monkeypatch.setattr(ts, "set_dock_tint", lambda value: seen.append(value) or 0)
    monkeypatch.setattr(ts, "set_style", lambda value: seen.append(value) or 0)
    assert ts.main(["dock-tint"]) == 0 and capsys.readouterr().out.strip() == "accent"
    assert ts.main(["dock-tint", "neutral"]) == 0
    assert ts.main(["style"]) == 0 and capsys.readouterr().out.strip() == "tahoe"
    assert ts.main(["style", "frosted"]) == 0
    assert ts.main(["style", "aqua"]) == 1
    assert seen == ["neutral", "frosted"]


def test_theme_settings_drives_acrylic_glass(offline):
    app = (offline / "theme-settings/theme_settings.py").read_text()
    assert '("neutral", _("Neutral"))' in app and '("macos", _("macOS"))' in app
    assert 'self.window.run_theme_switch(["dock-tint", tint]' in app
    assert 'self.window.run_theme_switch(["style", style]' in app
    # The blur warning checks the effect in use.
    assert '"liquidglassEnabled"' in app
    assert "better_blur" not in app and "Better Blur" not in app
    # No reduced-transparency assets ship with this theme.
    assert '"transparency"' not in app


def test_installer_bakes_the_presets_into_the_switcher(repo):
    step = (repo / "src/scripts/steps/theme_switch.py").read_text()
    assert '"ACRYLIC_PRESETS: list = []"' in step
    assert re.search(r"^ACRYLIC_PRESETS: list = \[\]$",
                     (repo / "src/scripts/theme_switch.py").read_text(), re.M)


def test_popovers_glass_follows_the_tint(tmp_path, monkeypatch):
    """glass.ini, read by GlassSurface.qml in every menu bar popover."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(ts, "dock_tint", ts.dock_tint_unpatched)
    ini = tmp_path / "mac-tahoe-liquid-kde/glass.ini"
    assert ts.write_glass_tint("neutral") is True
    assert ini.read_text() == "Tint=neutral\nAccent=\nGlassLevel=50\n"
    assert ts.write_glass_tint("neutral") is False  # unchanged
    monkeypatch.setattr(ts, "accent_color_hex", lambda: "#ff8d28")
    ts.write_glass_tint("accent")
    assert ini.read_text() == "Tint=accent\nAccent=ff8d28\nGlassLevel=50\n"
    assert ts.set_glass_level("80") == 0
    assert ini.read_text() == "Tint=macos\nAccent=\nGlassLevel=80\n"
    assert ts.set_glass_level("101") == 1
    # Every Dock tint apply writes it too.
    seen = []
    monkeypatch.setattr(ts, "write_glass_tint", lambda tint=None: seen.append(tint) or True)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    ts.apply_dock_tint_unpatched("macos")
    assert seen == ["macos"]


def test_half_saturated_keeps_the_hue_at_half_saturation():
    import colorsys
    for mode, lightness in (("dark", 0.24), ("light", 0.86)):
        tint = ts.half_saturated("#0088ff", mode)
        rgb = [int(tint[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        hue, light, saturation = colorsys.rgb_to_hls(*rgb)
        assert abs(hue - colorsys.rgb_to_hls(0, 0x88 / 255, 1)[0]) < 0.01
        assert abs(light - lightness) < 0.01 and abs(saturation - 0.5) < 0.02


def test_frosted_follows_the_accent_half_saturated(tmp_path, monkeypatch):
    paths = _themes(tmp_path, monkeypatch)
    monkeypatch.setattr(ts, "current_accent_hex", lambda: "#34c759")
    ts.apply_dock_tint_unpatched("macos", glass="frosted")
    dark = _veil(paths["MacTahoeLiquidKde-Dark"])
    assert dark == f'style="opacity:0.45;fill:{ts.half_saturated("#34c759", "dark")}"'
    assert _veil(paths["MacTahoeLiquidKde-Light"]).endswith(
        f'fill:{ts.half_saturated("#34c759", "light")}"')
    # The bar too, a little lighter than the Dock's veil.
    script = ts._top_bar_script(True, "dark", "macos", "#34c759")
    assert f'"custom": "{ts.half_saturated("#34c759", "dark")}", "alpha": 0.3' in script
    # Neutral keeps the uncoloured frosted glass.
    assert f'"custom": "{ts.TOP_BAR_FROSTED["dark"][0]}"' in ts._top_bar_script(
        True, "dark", "neutral", "#34c759")


def test_accent_tint_reaches_the_menu_bar():
    tahoe = ts._top_bar_script(False, "dark", "accent", "#FF2D55")
    assert ts.TOP_BAR_SCRIM not in tahoe
    assert '"color": "#40ff2d55", "position": 0' in tahoe
    assert '"color": "#00ff2d55", "position": 1' in tahoe
    assert '"custom": "#FF2D55", "alpha": 0.25' in ts._top_bar_script(True, "dark", "accent", "#FF2D55")
    # Without an accent, the uncoloured bars.
    assert ts.TOP_BAR_SCRIM in ts._top_bar_script(False, "dark", "accent", "")
    layer = json.loads(ts._top_bar_scrim("accent", "#ff2d55"))
    assert len(layer["backgroundColor"]["gradient"]["stops"]) == 4


def test_wallpaper_accent_is_read_from_the_palette(monkeypatch):
    """Plasma 6.8 leaves AccentColor stale for the wallpaper's accent."""
    values = {("General", "AccentColor"): "88,111,217",
              ("Colors:Selection", "BackgroundNormal"): "49,151,74",
              ("General", "accentColorFromWallpaper"): "true"}
    monkeypatch.setattr(ts, "_kread", lambda f, g, k: values.get((g, k), ""))
    monkeypatch.setattr(ts, "accent_from_wallpaper", ts.accent_from_wallpaper_unpatched)
    assert ts.current_accent_hex() == "#31974a"
    values[("General", "accentColorFromWallpaper")] = "false"
    assert ts.current_accent_hex() == "#586fd9"


def test_accent_sync_only_acts_on_a_new_accent(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(ts, "glass_style", lambda: "frosted")
    accent = ["#34c759"]
    monkeypatch.setattr(ts, "current_accent_hex", lambda: accent[0])
    calls = []
    monkeypatch.setattr(ts, "apply_dock_tint", lambda *a, **k: calls.append("dock") or True)
    monkeypatch.setattr(ts, "reload_plasma_theme", lambda: calls.append("reload") or True)
    monkeypatch.setattr(ts, "apply_top_bar_style", lambda *a, **k: calls.append("bar") or True)
    monkeypatch.setattr(ts, "write_glass_tint", lambda *a: calls.append("ini") or True)
    assert ts.accent_sync() == 0 and calls == ["ini", "dock", "reload", "bar"]
    calls.clear()
    assert ts.accent_sync() == 0 and calls == []
    accent[0] = "#ff2d55"
    ts.accent_sync()
    assert calls == ["ini", "dock", "reload", "bar"]


def test_set_accent_writes_the_accent_key(monkeypatch):
    writes = []
    monkeypatch.setattr(ts, "_kwrite", lambda *args: writes.append(args) or True)
    monkeypatch.setattr(ts, "_have", lambda cmd: False)
    monkeypatch.setattr(ts, "accent_sync", lambda: 0)
    ts.set_accent("#ff8d28")
    assert ("--file", "kdeglobals", "--group", "General", "--key", "AccentColor",
            "255,141,40") in writes


def test_control_center_runs_accent_sync_on_palette_changes(offline):
    main = (offline / "plasmoids/org.kde.mac-tahoe-liquid-kde.controlcenter/contents/ui/main.qml").read_text()
    assert "readonly property color paletteAccent: Kirigami.Theme.highlightColor" in main
    assert 'mac-tahoe-theme-switch\\" accent-sync' in main
    for widget in ("controlcenter", "keyboard", "spotlight", "wifi"):
        accent = (offline / f"plasmoids/org.kde.mac-tahoe-liquid-kde.{widget}/contents/ui/AccentColor.qml").read_text()
        assert 'kdeglobals.value("accentColorFromWallpaper", "false")' in accent, widget
