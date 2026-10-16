"""The Better Blur DX KWin effect, installed by the ``acrylic_glass``
feature: the bundled copy and its local changes, the per-mode glass, and
the migration away from Glass and Acrylic Glass."""

import re

import pytest

GLASS = "kwin-effects/better-blur-dx"


def test_bundled_copy_is_pinned_and_documented(offline):
    upstream = (offline / GLASS / "UPSTREAM.md").read_text()
    assert "https://github.com/xarblu/kwin-effects-better-blur-dx" in upstream
    assert "811bce88af12b15be01d1b388dc5174451450362" in upstream
    assert (offline / GLASS / "LICENSE").read_text().lstrip().startswith(
        "GNU GENERAL PUBLIC LICENSE")
    for gone in ("kwin-effects/acrylic-glass", "kwin-effects/glass"):
        assert not (offline / gone).exists()
    # Upstream's build.sh runs "sudo make install": not bundled.
    assert not (offline / GLASS / "build.sh").exists()


def test_local_changes_are_the_documented_two(offline):
    """Docks' own blur strength and refraction kept to docks, each marked
    "AquaDesktop" in the source."""
    kcfg = (offline / GLASS / "src/blur.kcfg").read_text()
    for key in ("DockBlurStrength", "DockBrightness", "DockContrast", "DockSaturation",
                "RefractionDocksOnly"):
        assert f'<entry name="{key}"' in kcfg, key
    cpp = (offline / GLASS / "src/blur.cpp").read_text()
    assert "const bool dockBlur = w->isDock() && m_dockIterationCount > 0;" in cpp
    assert "const bool refract = !m_refractionDocksOnly || w->isDock();" in cpp
    assert "if (!refract || !m_refractionPass->pushShader())" in cpp
    # Only blur(), the Dock's own pipeline, uses the window's strength.
    blur = cpp[cpp.index("void BlurEffect::blur("):]
    blur = blur[:blur.index("\n}\n")]
    assert "m_iterationCount" not in blur.replace("? m_dockIterationCount : m_iterationCount", "")
    assert "float(m_offset)" not in blur
    # The upstream shaders and refraction pass are untouched.
    for name in ("src/shaders/refraction.frag", "src/refraction_pass.cpp"):
        assert "AquaDesktop" not in (offline / GLASS / name).read_text(), name


def test_plasma_popups_and_vms_are_never_force_blurred():
    """plasmashell keeps only the region it asks for (the Dock's Downloads
    fan, the Control Center's room around its bubbles stay clear); menus
    and docks are never force-blurred; VirtualBox VMs never, whatever the
    case of their class (#90)."""
    from steps import acrylic_glass as step
    shared = dict(step._SHARED)
    assert (shared["BlurMatching"], shared["BlurNonMatching"]) == ("false", "true")
    assert (shared["BlurMenus"], shared["BlurDocks"]) == ("false", "false")
    deny = shared["WindowClasses"].split("\n")
    assert "plasmashell" in deny
    assert "/(?i)^VirtualBoxVM$/" in deny


def test_default_deny_list_survives():
    from steps import acrylic_glass as step
    deny = set(dict(step._SHARED)["WindowClasses"].split("\n"))
    assert {"cairo-dock", "kwin_wayland", "linux-wallpaperengine", "xembedsniproxy"} <= deny


def test_presets_tahoe_glass_and_frosted():
    import theme_switch as ts
    assert ts.GLASS_EFFECT == "better_blur_dx" and ts.GLASS_GROUP == "Effect-better-blur-dx"
    presets = ts.GLASS_PRESETS
    assert set(presets) == {"dark-tahoe", "light-tahoe", "dark-frosted", "light-frosted"}
    # Every preset sets the same keys: switching styles leaves nothing behind.
    assert len({tuple(sorted(p)) for p in presets.values()}) == 1
    for p in presets.values():
        assert "__" not in "".join(p.values())
        assert p["NoiseStrength"] == "0" and p["RefractionDocksOnly"] == "true"
    # Tahoe: in light mode the Dock nearly clear (strength 1, Apple's ~1 px)
    # under the effect's radial lens at its edges; popovers and windows
    # heavily blurred.
    tahoe = presets["light-tahoe"]
    assert (tahoe["BlurStrength"], tahoe["DockBlurStrength"]) == ("5", "1")
    assert (tahoe["RefractionStrength"], tahoe["RefractionMode"]) == ("30", "1")
    assert (tahoe["RefractionEdgeSize"], tahoe["RefractionNormalPow"]) == ("1", "4")
    assert (tahoe["Brightness"], tahoe["Saturation"]) == ("100", "100")
    # The Dock's material, fitted on two Apple captures over their bare
    # wallpapers: contrast 0.68, saturation 1.35, brightness 1.04.
    assert (tahoe["DockContrast"], tahoe["DockSaturation"], tahoe["DockBrightness"]) == ("68", "135", "104")
    # Dark mode: Apple's dark Dock, fitted on a macOS dark capture over its
    # bare wallpaper: a light blur (sigma 3-4 px, the desktop stays
    # readable through the glass) and kept dark.
    dark = presets["dark-tahoe"]
    # A soft lens over a wider band: no second contour inside the rim.
    assert dark == {**tahoe, "DockBlurStrength": "2", "DockContrast": "84",
                    "DockSaturation": "133", "DockBrightness": "87",
                    "RefractionStrength": "15", "RefractionEdgeSize": "2",
                    "RefractionNormalPow": "2"}
    # Frosted, measured on a macOS dark Dock: dimmed to 85 %, strong blur,
    # no refraction, the Dock blurred like the rest.
    frosted = presets["dark-frosted"]
    assert (frosted["Brightness"], frosted["BlurStrength"]) == ("85", "11")
    assert (frosted["RefractionStrength"], frosted["DockBlurStrength"]) == ("0", "0")
    assert int(tahoe["BlurStrength"]) < int(frosted["BlurStrength"])
    assert ts._OWN_COMPILED_EFFECTS == ("better_blur_dx",)


@pytest.mark.parametrize("enabled", [True, False])
def test_theme_switch_writes_the_mode_preset_only_while_enabled(
        monkeypatch, tmp_path, enabled):
    import theme_switch as ts
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    kwinrc = tmp_path / "kwinrc"
    kwinrc.write_text(f"[Plugins]\nbetter_blur_dxEnabled={'true' if enabled else 'false'}\n")
    monkeypatch.setattr(ts, "_kwinrc_path", lambda: kwinrc)
    writes, calls = [], []
    monkeypatch.setattr(ts, "_kwrite", lambda *a: writes.append(a) or True)
    monkeypatch.setattr(ts, "_qdbus", lambda *a: calls.append(a) or True)

    assert ts.apply_glass_preset("light") is enabled
    if enabled:
        written = {a[a.index("--key") + 1]: a[-1] for a in writes}
        assert all(a[3] == "Effect-better-blur-dx" for a in writes)
        # Tahoe is the default style, macOS the default tint.
        assert written == ts.GLASS_PRESETS["light-tahoe"]
        assert calls == [("org.kde.KWin", "/Effects",
                          "org.kde.kwin.Effects.reconfigureEffect", "better_blur_dx")]
    else:
        assert writes == [] and calls == []


def test_install_replaces_glass_and_acrylic_glass(monkeypatch, tmp_path):
    import theme_switch as ts
    from steps import acrylic_glass as step

    plugins = tmp_path / "plugins"
    build = tmp_path / "build"
    for so in ("src/better_blur_dx.so", "src/kcm/kwin_better_blur_dx_config.so"):
        (build / so).parent.mkdir(parents=True, exist_ok=True)
        (build / so).write_bytes(b"so")
    old_files = [so for _effect, _group, files in step._REPLACED_EFFECTS for so in files]
    for so in old_files:
        (plugins / so).parent.mkdir(parents=True, exist_ok=True)
        (plugins / so).write_bytes(b"old")
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    kwinrc = home / ".config/kwinrc"
    kwinrc.write_text("[Effect-blurplus]\nBlurStrength=4\n\n[Effect-liquidglass]\nBlurStrength=3.5\n\n"
                      "[Plugins]\nglassEnabled=true\nliquidglassEnabled=true\n")

    writes, installed, removed = [], [], []
    monkeypatch.setattr(step, "BUILD", build)
    monkeypatch.setattr(step, "HOME", home)
    monkeypatch.setattr(step, "_plugin_dir", lambda: plugins)
    monkeypatch.setattr(step, "kw_write", lambda *a: writes.append(a) or True)
    monkeypatch.setattr(step, "qdbus_call", lambda *a: True)
    monkeypatch.setattr(step, "sudo_install_file",
                        lambda src, dest, label: installed.append(dest) or True)
    monkeypatch.setattr(step, "sudo_remove",
                        lambda path, label: removed.append(path) or True)
    monkeypatch.setattr(step, "_install_corner_defaults", lambda: None)
    monkeypatch.setattr(step, "_kwin_has_effect", lambda effect: True)
    monkeypatch.setattr(step, "theme_mode", lambda: "dark")
    monkeypatch.setattr(step, "glass_preset", lambda mode: ts.glass_preset(mode, "frosted", "macos"))
    monkeypatch.setattr(step.time, "sleep", lambda _s: None)
    for name in ("ok", "info", "warn"):
        monkeypatch.setattr(step, name, lambda *_a: None)

    step.install()

    assert plugins / "kwin/effects/plugins/better_blur_dx.so" in installed
    assert plugins / "kwin/effects/configs/kwin_better_blur_dx_config.so" in installed
    assert {plugins / so for so in old_files} <= set(removed)
    text = kwinrc.read_text()
    assert "[Effect-liquidglass]" not in text and "[Effect-blurplus]" not in text
    flat = [(a[3], a[5], a[6]) for a in writes]
    assert ("Plugins", "liquidglassEnabled", "false") in flat
    assert ("Plugins", "glassEnabled", "false") in flat
    assert ("Effect-better-blur-dx", "BlurDecorations", "true") in flat
    # The frosted style, as chosen.
    assert ("Effect-better-blur-dx", "BlurStrength", "11") in flat
    assert ("Effect-better-blur-dx", "RefractionStrength", "0") in flat
    # Enabled last, once everything is in place.
    assert flat[-1] == ("Plugins", "better_blur_dxEnabled", "true")


def test_glass_style_is_chosen_in_the_switcher(monkeypatch, tmp_path):
    """tahoe by default, frosted on request; `mac-tahoe-theme-switch style`
    switches the blur and the menu bar together."""
    import theme_switch as ts
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert ts.glass_style() == "tahoe"
    assert ts.glass_preset_name("dark") == "dark-tahoe"
    applied, bars = [], []
    monkeypatch.setattr(ts, "_sync_session_env", lambda: None)
    monkeypatch.setattr(ts, "current_mode", lambda: "light")
    monkeypatch.setattr(ts, "apply_glass_preset", applied.append)
    monkeypatch.setattr(ts, "apply_top_bar_style", bars.append)

    assert ts.main(["style", "frosted"]) == 0
    assert (tmp_path / "mac-tahoe-liquid-kde/glass-style").read_text() == "frosted\n"
    assert ts.glass_preset_name("light") == "light-frosted"
    assert ts.main(["style", "glass"]) == 1
    assert ts.glass_style() == "frosted"
    assert ts.main(["style", "tahoe"]) == 0
    assert applied == ["light", "light"]
    assert bars == ["frosted", "tahoe"]


@pytest.mark.parametrize("frosted", [True, False])
def test_menu_bar_background_follows_the_style(frosted):
    """Frosted gives the menu bar its translucent background back through
    its Panel Colorizer, Tahoe hides it again; nothing else the user set in
    the Colorizer changes."""
    import theme_switch as ts
    script = ts._top_bar_script(frosted)
    assert 'panel.location !== "top"' in script
    assert 'panel.widgets("luisbocanegra.panel.colorizer")' in script
    assert "settings.nativePanel.background = " in script
    assert ('"enabled": true, "opacity": 1' in script) is frosted
    assert ('"enabled": false, "opacity": 0' in script) is (not frosted)
    assert "JSON.parse(widget.readConfig(" in script


def test_layout_reinstall_keeps_a_frosted_menu_bar(monkeypatch):
    from steps import layout
    sent = []
    monkeypatch.setattr(layout, "_evaluate_layout_script", lambda s: sent.append(s) or True)
    monkeypatch.setattr(layout, "ok", lambda *_a: None)
    import theme_switch
    monkeypatch.setattr(theme_switch, "glass_style", lambda: "tahoe")
    layout._restore_top_bar_style()
    assert sent == []
    monkeypatch.setattr(theme_switch, "glass_style", lambda: "frosted")
    layout._restore_top_bar_style()
    assert sent == [theme_switch._top_bar_script(True)]


@pytest.mark.parametrize("theme", ["Dark", "Light"])
@pytest.mark.parametrize("name", ["gtk.css", "gtk-dark.css", "gtk-Dark.css", "gtk-Light.css"])
def test_gtk4_traffic_lights_show_glyphs_together(offline, theme, name):
    """macOS shows every light's glyph while the pointer is over any of
    them: GTK4 sets :hover on ancestors, so the hover images key on the
    window controls box, not on each button."""
    css = (offline / f"gtk/MacTahoeLiquidKde-{theme}/gtk-4.0/{name}").read_text()
    for button in ("close", "minimize", "maximize"):
        assert f"headerbar windowcontrols:hover button.{button} {{" in css
        assert f"headerbar windowcontrols:hover button.{button}:backdrop {{" in css
        assert f"headerbar windowcontrols button.{button}:hover {{" not in css


@pytest.mark.parametrize("theme", ["Dark", "Light"])
def test_dock_background_adds_no_veil(offline, theme):
    """The Dock draws no fill of its own: its lift is the blur effect's
    (DockBrightness / DockContrast), since a veil over the blur cannot
    brighten the desktop the way Apple's Dock does. The hint keeps any veil
    seamless (the centre is painted under the whole frame and cut by the
    rounded mask)."""
    import gzip
    svg = gzip.decompress((offline / f"plasma-theme/MacTahoeLiquidKde-{theme}"
                           "/widgets/panel-background.svgz").read_bytes()).decode()
    i = svg.index('id="south-center"')
    element = svg[svg.rindex("<rect", 0, i):svg.index("/>", i)]
    assert 'style="opacity:0;' in element
    assert 'id="south-hint-compose-over-border"' in svg
    assert "-veil" not in svg


@pytest.mark.parametrize("theme", ["Dark", "Light"])
def test_dock_background_is_glass_only_with_a_real_mask(offline, theme):
    """The Dock (a bottom panel) draws panel-background's south-* elements:
    their edges draw only a 1 px rim, so the Dock body is the Glass effect.
    KSvg then needs mask-south-* elements: without them it derives the blur
    mask from the drawn (invisible) edges, the mask is empty and Plasma
    blurs the whole panel window, magnification headroom included."""
    import gzip
    svg = gzip.decompress((offline / f"plasma-theme/MacTahoeLiquidKde-{theme}"
                           "/widgets/panel-background.svgz").read_bytes()).decode()
    # The edges draw the rim measured on Apple's Dock. Light (Spotlight
    # capture): a 1 px dark hairline (8 % black) on the outer pixel, then a
    # 1 px light line, 29 % white at the top, 27 % at the bottom, 22 % on
    # the sides. Dark (dark Dock capture): only a light outer pixel, 15 %
    # at the top, 18 % at the bottom, 12 % on the sides, 6 % in the corners
    # (Apple's fades out along them).
    top = re.search(r'id="south-top".*?</(?:svg:)?g>', svg, re.S).group(0)
    bottom = re.search(r'id="south-bottom".*?</(?:svg:)?g>', svg, re.S).group(0)
    left = re.search(r'id="south-left".*?</(?:svg:)?g>', svg, re.S).group(0)
    rims = ("0.29", "0.27", "0.22") if theme == "Light" else ("0.15", "0.18", "0.12")
    for edge, rim in zip((top, bottom, left), rims):
        assert ("fill:#000000;fill-opacity:0.08" in edge) == (theme == "Light")
        assert f"fill:#ffffff;fill-opacity:{rim}" in edge
    for part in ("topleft", "topright", "bottomleft", "bottomright"):
        corner = re.search(r'id="south-%s".*?</(?:svg:)?g>' % part, svg, re.S).group(0)
        assert "stroke-width:1" in corner and "fill:none" in corner, part
    for part in ("center", "top", "bottom", "left", "right",
                 "topleft", "topright", "bottomleft", "bottomright"):
        assert f'id="mask-south-{part}"' in svg, part


@pytest.mark.parametrize("theme", ["Dark", "Light"])
def test_dock_corners_match_the_lens_radius(offline, theme):
    """The Dock rim, its blur mask and the lens' corner radius share one
    radius."""
    import gzip
    import theme_switch as ts

    radius = int(ts.GLASS_PRESETS["dark-tahoe"]["RefractionCornerRadius"])
    svg = gzip.decompress((offline / f"plasma-theme/MacTahoeLiquidKde-{theme}"
                           "/widgets/panel-background.svgz").read_bytes()).decode()
    for prefix in ("south-", "mask-south-"):
        corner = re.search(r'id="%stopleft".*?</(?:svg:)?g>' % prefix, svg, re.S).group(0)
        assert f'width="{radius}" height="{radius}"' in corner, prefix


@pytest.mark.parametrize("current, written", [
    ("__absent__", "22"),   # never set
    ("14", None),           # user tuning is kept (#89)
    ("", None),             # an explicitly empty value is kept too
])
def test_window_radius_is_seeded_only_when_absent(monkeypatch, current, written):
    from types import SimpleNamespace
    from steps import acrylic_glass as step

    writes = []

    def read(cmd, **_kw):
        sentinel = cmd[cmd.index("--default") + 1]
        return SimpleNamespace(returncode=0,
                               stdout=(sentinel if current == "__absent__" else current) + "\n")

    monkeypatch.setattr(step, "have", lambda _tool: True)
    monkeypatch.setattr(step, "run_user", read)
    monkeypatch.setattr(step, "kw_write", lambda *a: writes.append(a) or True)
    monkeypatch.setattr(step, "warn", lambda *_a: None)
    step._install_corner_defaults()
    assert [a[-1] for a in writes if "CornerRadius" in a] == ([written] if written else [])


def test_nix_builds_the_bundled_effect(offline):
    root = offline.parent.parent
    assert '(offline + "/kwin-effects/better-blur-dx")' in (root / "nix/packages.nix").read_text()
    assert "kwin/effects/plugins/better_blur_dx.so" in (root / "flake.nix").read_text()

@pytest.mark.parametrize("frosted", [True, False])
def test_menu_bar_carries_tahoes_dark_veil(offline, frosted):
    """Tahoe's dark veil behind the transparent menu bar (the desktop at 0.80
    under the bar on a macOS capture over its bare wallpaper): 20 % black at
    the top fading to nothing at the bar's bottom edge, a Panel Colorizer
    panel layer, in the layouts and in the style switch; frosted drops it."""
    import json
    import theme_switch as ts
    scrim = json.loads(ts.TOP_BAR_SCRIM)
    stops = scrim["backgroundColor"]["gradient"]["stops"]
    assert scrim["backgroundColor"]["sourceType"] == 5
    assert scrim["backgroundColor"]["gradient"]["orientation"] == 1
    assert (stops[0]["color"], stops[0]["position"]) == ("#33000000", 0)
    assert (stops[-1]["color"], stops[-1]["position"]) == ("#00000000", 1)
    script = ts._top_bar_script(frosted)
    assert (("settings.panel.normal = " + ts.TOP_BAR_SCRIM) in script) is (not frosted)
    assert ('settings.panel.normal = {"enabled": false}' in script) is frosted
    for relative in ("layouts/mac-tahoe.js",
                     "look-and-feel/MacTahoeLiquidKde-Light/contents/layouts/org.kde.plasma.desktop-layout.js",
                     "look-and-feel/MacTahoeLiquidKde-Dark/contents/layouts/org.kde.plasma.desktop-layout.js"):
        assert f'"panel": {{ "normal": {ts.TOP_BAR_SCRIM} }}' in (offline / relative).read_text(), relative
