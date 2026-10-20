"""The Acrylic Glass KWin effect, installed by the ``acrylic_glass``
feature: the per-style materials, and the migration away from Better Blur
DX."""

import re

import pytest

GLASS = "kwin-effects/acrylic-glass"


def test_acrylic_glass_replaces_better_blur_dx(offline):
    """Upstream's Acrylic Glass is the glass: Better Blur DX, which earlier
    AquaDesktop releases bundled, is gone, and its install is migrated."""
    assert (offline / GLASS / "src/presets.json").is_file()
    assert not (offline / "kwin-effects/better-blur-dx").exists()
    from steps import acrylic_glass as step
    assert step._RETIRED_EFFECT == "better_blur_dx"
    assert step._RETIRED_GROUP == "Effect-better-blur-dx"


def test_presets_tahoe_and_frosted():
    import json
    import theme_switch as ts
    from steps import acrylic_glass as step
    assert ts.GLASS_EFFECT == "liquidglass" and ts.GLASS_GROUP == "Effect-liquidglass"
    presets = ts.GLASS_PRESETS
    assert set(presets) == {"dark-tahoe", "light-tahoe", "dark-frosted", "light-frosted"}
    assert ts.GLASS_STYLES == ("tahoe", "frosted")
    # Every preset sets the same keys: switching styles leaves nothing behind.
    assert len({tuple(sorted(p)) for p in presets.values()}) == 1
    # Tahoe is upstream's tahoe material, the same in both appearances
    # (the switch carries a copy: it is installed without the checkout).
    upstream = json.loads((step.SRC / "src/presets.json").read_text())[1]
    assert upstream["id"] == "tahoe"
    for mode in ("dark", "light"):
        tahoe = presets[f"{mode}-tahoe"]
        for key, value in upstream["values"].items():
            expected = str(value).lower() if isinstance(value, bool) else str(value)
            if expected[0].isdigit():
                assert float(tahoe[key]) == float(expected), key
            else:
                assert tahoe[key] == expected, key
        assert tahoe["MaterialPreset"] == "1"
    # Frosted: a heavier blur, no refraction or colour drift, dimmed to
    # 85 % in dark mode (measured on a macOS dark Dock), lifted in light.
    dark, light = presets["dark-frosted"], presets["light-frosted"]
    assert float(dark["BlurStrength"]) > float(presets["dark-tahoe"]["BlurStrength"])
    for frosted in (dark, light):
        assert frosted["MagnifyGlassStrength"] == "0.0" and frosted["RgbDriftStrength"] == "0.0"
        assert frosted["RefractionWidth"] == "0.0"
    assert (dark["Brightness"], light["Brightness"]) == ("0.85", "1.12")
    assert dark == {**light, "Brightness": "0.85"}
    # The neutral tint takes the colour out of the glass.
    assert ts.glass_preset("dark", "tahoe", "neutral")["Saturation"] == "0"


@pytest.mark.parametrize("enabled", [True, False])
def test_theme_switch_writes_the_mode_preset_only_while_enabled(
        monkeypatch, tmp_path, enabled):
    import theme_switch as ts
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    kwinrc = tmp_path / "kwinrc"
    kwinrc.write_text(f"[Plugins]\nliquidglassEnabled={'true' if enabled else 'false'}\n")
    monkeypatch.setattr(ts, "_kwinrc_path", lambda: kwinrc)
    writes, calls = [], []
    monkeypatch.setattr(ts, "_kwrite", lambda *a: writes.append(a) or True)
    monkeypatch.setattr(ts, "_qdbus", lambda *a: calls.append(a) or True)

    assert ts.apply_glass_preset("light") is enabled
    if enabled:
        written = {a[a.index("--key") + 1]: a[-1] for a in writes}
        assert all(a[3] == "Effect-liquidglass" for a in writes)
        # Tahoe is the default style, macOS the default tint.
        assert written == ts.GLASS_PRESETS["light-tahoe"]
        assert calls == [("org.kde.KWin", "/Effects",
                          "org.kde.kwin.Effects.reconfigureEffect", "liquidglass")]
    else:
        assert writes == [] and calls == []


def test_install_retires_better_blur_dx(monkeypatch, tmp_path):
    from steps import acrylic_glass as step
    plugins = tmp_path / "plugins"
    effects = plugins / "kwin/effects/plugins"
    hashed = effects / ".better_blur_dx-76ebef8cb9848757"
    hashed.mkdir(parents=True)
    (hashed / "better_blur_dx.so").write_bytes(b"so")
    (effects / "better_blur_dx.so").symlink_to(".better_blur_dx-76ebef8cb9848757/better_blur_dx.so")
    config = plugins / "kwin/effects/configs/kwin_better_blur_dx_config.so"
    config.parent.mkdir(parents=True)
    config.write_bytes(b"so")
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    kwinrc = home / ".config/kwinrc"
    kwinrc.write_text("[Effect-better-blur-dx]\nBlurStrength=5\n\n[Plugins]\n"
                      "better_blur_dxEnabled=true\n")
    writes, calls, removed = [], [], []
    monkeypatch.setattr(step.Path, "home", lambda: home)
    monkeypatch.setattr(step, "_plugin_dir", lambda: plugins)
    monkeypatch.setattr(step, "kw_write", lambda *a: writes.append(a) or True)
    monkeypatch.setattr(step, "qdbus_call", lambda *a: calls.append(a) or True)
    monkeypatch.setattr(step, "sudo_remove", lambda path, label: removed.append(path) or True)

    step._remove_better_blur_dx()

    assert ("--file", "kwinrc", "--group", "Plugins", "--key",
            "better_blur_dxEnabled", "false") == writes[0]
    assert calls == [("org.kde.KWin", "/Effects",
                      "org.kde.kwin.Effects.unloadEffect", "better_blur_dx")]
    assert "[Effect-better-blur-dx]" not in kwinrc.read_text()
    assert "[Plugins]" in kwinrc.read_text()
    assert {effects / "better_blur_dx.so", config, hashed} <= set(removed)


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
    """The Dock draws no fill of its own: the glass is the effect's. The
    hint keeps any veil
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
    """The Dock rim, its blur mask and the glass' Dock corners share one
    radius."""
    import gzip
    from steps import acrylic_glass as step

    radius = int(float(dict(step._CORNER_DEFAULTS)["DockCornerRadius"]))
    svg = gzip.decompress((offline / f"plasma-theme/MacTahoeLiquidKde-{theme}"
                           "/widgets/panel-background.svgz").read_bytes()).decode()
    for prefix in ("south-", "mask-south-"):
        corner = re.search(r'id="%stopleft".*?</(?:svg:)?g>' % prefix, svg, re.S).group(0)
        assert f'width="{radius}" height="{radius}"' in corner, prefix


def test_nix_builds_the_bundled_effect(offline):
    root = offline.parent.parent
    assert '(offline + "/kwin-effects/acrylic-glass")' in (root / "nix/packages.nix").read_text()
    assert "kwin/effects/plugins/liquidglass.so" in (root / "flake.nix").read_text()

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


@pytest.mark.parametrize('build_succeeds', [False, True])
def test_build_never_mutates_the_live_desktop(monkeypatch, build_succeeds):
    from steps import acrylic_glass as step
    builds = []
    monkeypatch.setattr(step, 'cmake_build', lambda *args: builds.append(args) or build_succeeds)
    def unexpected(*args, **kwargs):
        pytest.fail('Build phase attempted a live config write or effect unload')
    monkeypatch.setattr(step, 'kw_write', unexpected)
    monkeypatch.setattr(step, 'qdbus_call', unexpected)
    step.build()
    assert len(builds) == 1


def test_popover_bubbles_are_recovered_from_the_blur_region(offline, tmp_path):
    """Every rounded bubble of a popover's region (built like
    org.kde.mac.tahoe.liquid.glass does) comes back as its own box, its
    corner radius within a pixel, so the glass draws each one on its own."""
    import shlex
    import shutil
    import subprocess
    if not shutil.which("c++") or not shutil.which("pkg-config"):
        pytest.skip("C++ compiler and pkg-config required")
    flags = subprocess.run(["pkg-config", "--cflags", "--libs", "Qt6Gui"],
                           capture_output=True, text=True, timeout=10)
    if flags.returncode:
        pytest.skip("Qt6Gui development files required")
    source = tmp_path / "shapes.cpp"
    source.write_text(r'''
#include "glass_shapes.hpp"
#include <QPainterPath>
#include <QPolygon>
#include <QRegion>
#include <cassert>
#include <cmath>
int main() {
    struct B { QRectF r; qreal radius; };
    const B bubbles[] = {{{10, 10, 140, 64}, 20}, {{160, 10, 64, 64}, 20},
                         {{10, 84, 288, 40}, 20}, {{10, 134, 288, 120}, 24}};
    QRegion region;
    for (const B &b : bubbles) {
        QPainterPath path;
        path.addRoundedRect(b.r, b.radius, b.radius);
        region |= QRegion(path.toFillPolygon().toPolygon());
    }
    QList<QRectF> rects;
    for (const QRect &r : region) rects.append(QRectF(r));
    const auto shapes = AquaGlass::glassShapes(rects, 24);
    assert(shapes.size() == 4);
    for (size_t i = 0; i < 4; ++i) {
        assert(std::abs(shapes[i].box.x() - bubbles[i].r.x()) <= 1);
        assert(std::abs(shapes[i].box.width() - bubbles[i].r.width()) <= 1);
        assert(std::abs(shapes[i].box.height() - bubbles[i].r.height()) <= 1);
        assert(std::abs(shapes[i].radius - bubbles[i].radius) <= 1);
    }
    // More bubbles than the glass takes: the window box instead.
    assert(AquaGlass::glassShapes(rects, 3).empty());
}
''')
    binary = tmp_path / "shapes"
    subprocess.run(["c++", "-std=c++20", "-fPIC", f"-I{offline / GLASS / 'src'}", str(source),
                    "-o", str(binary), *shlex.split(flags.stdout)],
                   check=True, capture_output=True, timeout=120)
    subprocess.run([str(binary)], check=True, timeout=10)


def test_glass_is_drawn_bubble_by_bubble(offline):
    """A client region that does not fill its undecorated window is drawn
    per bubble: each one's box, radius and lens centre, in the glass and
    the grain passes; decorated and Rounded Corners windows keep the box."""
    effect = (offline / GLASS / "src/effect.cpp").read_text()
    assert '#include "glass_shapes.hpp"' in effect
    assert 'if (!blurInfo.frame && w->property("_mttkde_corner_shape_v1").toList().size() != 2) {' in effect
    assert effect.count("vbo->draw(GL_TRIANGLES, 6 + bubbleRanges[i].first * 6, bubbleRanges[i].second * 6);") == 2
    assert "m_roundedOnscreenPass.lensCenterLocation, QVector2D(0.5f, 0.5f)" in effect
    for shader in ("glass.glsl", "glass_core.glsl"):
        text = (offline / GLASS / "src/shaders" / shader).read_text()
        assert "lgLensUV(uv, lensCenter, magnifyGlassStrength, edgeQ)" in text, shader
    assert 'parameter == QLatin1String("windows")' in effect
