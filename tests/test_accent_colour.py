"""The accent colour beyond KDE's palette: Kvantum's own blues, the
`accent` command Theme Settings runs, and the white menu bar."""

import colorsys

import pytest

import theme_switch as ts


def _hls(colour):
    return colorsys.rgb_to_hls(*(int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)))


def test_recolor_moves_only_accent_blues():
    text = ('highlight.color=#0088FF\ninactive.highlight.color=#DCDCDC\n'
            '<path fill="#315bef"/><path fill="#b74aff"/><path fill="#ffffff"/>')
    out = ts.recolor_accent(text, "#ff8d28")
    assert "highlight.color=#ff8d28" in out          # the base accent itself
    assert "#DCDCDC" in out and "#b74aff" in out and "#ffffff" in out
    swapped = out.split('<path fill="')[1][:7]
    h, l, _s = _hls(swapped)
    assert abs(h * 360 - _hls("#ff8d28")[0] * 360) < 2
    # #315bef is lighter than the base blue: it stays lighter than orange.
    assert l > _hls("#ff8d28")[1]


def test_recolor_handles_graphite():
    out = ts.recolor_accent("x=#0088ff", "#8c8c8c")
    assert out == "x=#8c8c8c"


@pytest.fixture
def kvantum(monkeypatch, tmp_path):
    data, config = tmp_path / "data", tmp_path / "config"
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    originals = data / "mac-tahoe-liquid-kde/kvantum"
    originals.mkdir(parents=True)
    monkeypatch.setattr(ts, "kvantum_originals_dir", lambda: originals)
    for theme in (ts.KVANTUM_THEME_LIGHT, ts.KVANTUM_THEME_DARK):
        (originals / f"{theme}.kvconfig").write_text("[%General]\nhighlight.color=#0088FF\n")
        (originals / f"{theme}.svg").write_text(
            '<svg><rect fill="#195edc"/>' + "<g/>" * 300 + "</svg>")
        (config / "Kvantum" / theme).mkdir(parents=True)
    return config / "Kvantum"


def test_kvantum_copies_follow_the_accent_and_come_back(kvantum):
    light = kvantum / ts.KVANTUM_THEME_LIGHT / f"{ts.KVANTUM_THEME_LIGHT}.kvconfig"
    assert ts.apply_kvantum_accent("#34c759")
    assert light.read_text() == "[%General]\nhighlight.color=#34c759\n"
    assert not ts.apply_kvantum_accent("#34c759")   # unchanged: no reload
    assert ts.apply_kvantum_accent("")
    assert light.read_text() == "[%General]\nhighlight.color=#0088FF\n"


def test_broken_originals_never_reach_the_live_themes(kvantum, monkeypatch):
    """Originals that are not a Kvantum theme (a test's fakes, a truncated
    copy) are refused instead of replacing the working themes."""
    originals = ts.kvantum_originals_dir()
    light = kvantum / ts.KVANTUM_THEME_LIGHT / f"{ts.KVANTUM_THEME_LIGHT}.kvconfig"
    light.write_text("[%General]\nworking=1\n")
    (originals / f"{ts.KVANTUM_THEME_LIGHT}.kvconfig").write_text("[General]\n")
    (originals / f"{ts.KVANTUM_THEME_LIGHT}.svg").write_text("<svg/>")
    ts.apply_kvantum_accent("#ff383c")
    assert light.read_text() == "[%General]\nworking=1\n"


def test_kvantum_accent_without_originals_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(ts, "kvantum_originals_dir", lambda: tmp_path / "none")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    assert ts.apply_kvantum_accent("#ff2d55") is False


def test_set_accent_applies_palette_kvantum_and_reloads(kvantum, monkeypatch):
    calls, writes, cycles = [], [], []
    monkeypatch.setattr(ts, "_have", lambda cmd: cmd == "plasma-apply-colorscheme")
    monkeypatch.setattr(ts, "_run_user",
                        lambda cmd, **kw: calls.append(cmd) or type("R", (), {"returncode": 0})())
    monkeypatch.setattr(ts, "_kwrite", lambda *a: writes.append(a) or True)
    accent = {"value": ""}
    monkeypatch.setattr(ts, "_kread", lambda f, g, k: accent["value"] if k == "AccentColor"
                        else "MacTahoeLiquidKdeDark")
    monkeypatch.setattr(ts, "cycle_widget_style_live", lambda style: cycles.append(style))

    assert ts.set_accent("#cb30e0")
    assert calls[-1] == ["plasma-apply-colorscheme", "--accent-color", "#cb30e0"]
    assert cycles == ["kvantum"]
    # A chosen colour stops following the wallpaper.
    assert writes == [("--file", "kdeglobals", "--group", "General",
                       "--key", "accentColorFromWallpaper", "false")]

    # Multicolour: the accent forgotten, then the scheme itself re-applied
    # (through the other one, or KDE skips it), without --accent-color.
    calls.clear()
    assert ts.set_accent("multicolour")
    assert writes[-1][-1] == "--delete" and "AccentColor" in writes[-1]
    assert calls == [["plasma-apply-colorscheme", "MacTahoeLiquidKdeLight"],
                     ["plasma-apply-colorscheme", "MacTahoeLiquidKdeDark"]]
    assert not ts.set_accent("blue")
    # From the wallpaper: Plasma derives it, nothing else is applied.
    calls.clear()
    assert ts.set_accent("wallpaper")
    assert writes[-1][-1] == "true" and "accentColorFromWallpaper" in writes[-1]
    assert calls == []



def test_accent_command_line(monkeypatch, capsys):
    seen = []
    monkeypatch.setattr(ts, "_sync_session_env", lambda: None)
    monkeypatch.setattr(ts, "set_accent", lambda value: seen.append(value) or True)
    monkeypatch.setattr(ts, "accent_color_hex", lambda: "")
    monkeypatch.setattr(ts, "accent_from_wallpaper", lambda: False)
    assert ts.main(["accent"]) == 0 and capsys.readouterr().out.strip() == "multicolour"
    assert ts.main(["accent", "#FF8D28"]) == 0 and seen == ["#FF8D28"]
    assert ts.main(["accent", "orange"]) == 1
    assert ts.main(["accent", "wallpaper"]) == 0 and seen[-1] == "wallpaper"


@pytest.mark.parametrize("frosted", [True, False])
def test_menu_bar_text_is_white_in_both_styles(frosted):
    script = ts._top_bar_script(frosted)
    assert '["widgets", "trayWidgets"]' in script
    assert "normal.backgroundColor.enabled = false;" in script
    assert "normal.foregroundColor.sourceType = 0;" in script
    assert f'normal.foregroundColor.custom = "{ts.TOP_BAR_FOREGROUND}";' in script
    assert ts.TOP_BAR_FOREGROUND == "#ffffff"


def test_engine_recolours_so_the_files_stay_untouched(kvantum, monkeypatch):
    """With the Tahoe Kvantum engine the themes keep their own blue: the
    engine recolours them as it loads them, for any accent."""
    monkeypatch.setattr(ts, "kvantum_engine_follows_accent", lambda: True)
    light = kvantum / ts.KVANTUM_THEME_LIGHT / f"{ts.KVANTUM_THEME_LIGHT}.kvconfig"
    ts.apply_kvantum_accent("#34c759")
    assert "#0088FF" in light.read_text()


def test_engine_counts_only_once_the_session_loads_it(monkeypatch, tmp_path):
    """Installed but not loaded yet (no new login): the theme files are
    still rewritten, so menus follow the accent meanwhile."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    engine = tmp_path / "mac-tahoe-liquid-kde/qt6/plugins/styles/libkvantum.so"
    engine.parent.mkdir(parents=True)
    engine.write_bytes(b"so")
    monkeypatch.setenv("QT_PLUGIN_PATH", "/usr/lib/qt6/plugins")
    assert ts.kvantum_engine_follows_accent() is False
    monkeypatch.setenv("QT_PLUGIN_PATH", f"{tmp_path}/mac-tahoe-liquid-kde/qt6/plugins:/usr/lib/qt6/plugins")
    assert ts.kvantum_engine_follows_accent() is True
