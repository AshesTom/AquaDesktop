"""Desktop & Dock (theme_switch dock / minimize / hot-corners and the
Theme Settings page): what macOS' Desktop & Dock settings offer, on the
Plasma Dock and KWin. Plasma and KWin are faked: nothing reaches a live
session."""

import json

import pytest

import theme_switch as ts


@pytest.fixture
def kwin(tmp_path, monkeypatch):
    """A kwinrc file the fakes of kwriteconfig6 write into."""
    path = tmp_path / "kwinrc"
    path.write_text("[Effect-overview]\nBorderActivate=9\n")
    monkeypatch.setattr(ts, "_kwinrc_path", lambda: path)
    calls = []

    def kwrite(*args):
        group, key, value = args[3], args[5], args[6]
        sections = ts._parse_ini(path)
        sections.setdefault(group, {})[key] = value
        path.write_text("".join(f"[{g}]\n" + "".join(f"{k}={v}\n" for k, v in keys.items())
                                for g, keys in sections.items()))
        return True
    monkeypatch.setattr(ts, "_kwrite", kwrite)
    monkeypatch.setattr(ts, "_qdbus", lambda *a: calls.append(a) or True)
    return path, calls


def test_hot_corners_take_a_corner_from_any_action(kwin):
    path, calls = kwin
    # The theme leaves the top-left corner to the Apple menu (9: none).
    assert ts.hot_corners() == dict.fromkeys(ts.HOT_CORNERS, "none")
    assert ts.set_hot_corner("bottom-right", "desktop")
    assert ts.set_hot_corner("top-right", "mission-control")
    assert ts.hot_corners() == {"top-left": "none", "top-right": "mission-control",
                                "bottom-left": "none", "bottom-right": "desktop"}
    kwinrc = ts._parse_ini(path)
    assert kwinrc["ElectricBorders"]["BottomRight"] == "ShowDesktop"
    assert kwinrc["Effect-overview"]["BorderActivate"] == "1"
    # Moving Mission Control's corner to the desktop action frees it.
    assert ts.set_hot_corner("top-right", "lock-screen")
    kwinrc = ts._parse_ini(path)
    assert kwinrc["Effect-overview"]["BorderActivate"] == "9"
    assert kwinrc["ElectricBorders"]["TopRight"] == "LockScreen"
    assert ts.set_hot_corner("top-right", "none")
    assert ts.hot_corners()["top-right"] == "none"
    assert ("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure") in calls
    assert not ts.set_hot_corner("middle", "desktop")
    assert not ts.set_hot_corner("top-left", "notification-center")


def test_kwin_default_overview_corner_is_read(kwin):
    path, _calls = kwin
    path.write_text("")
    assert ts.hot_corners()["top-left"] == "mission-control"


def test_minimize_genie_or_scale(kwin):
    path, calls = kwin
    assert ts.minimize_effect() == "scale"
    assert ts.set_minimize_effect("genie")
    assert ts.minimize_effect() == "genie"
    plugins = ts._parse_ini(path)["Plugins"]
    assert (plugins["magiclampEnabled"], plugins["squashEnabled"]) == ("true", "false")
    assert ("org.kde.KWin", "/Effects", "org.kde.kwin.Effects.loadEffect", "magiclamp") in calls
    assert ("org.kde.KWin", "/Effects", "org.kde.kwin.Effects.unloadEffect", "squash") in calls
    assert not ts.set_minimize_effect("suck")


def test_dock_settings_through_plasma(monkeypatch):
    scripts = []

    def evaluate(script):
        scripts.append(script)
        return '{"autohide": true, "size": 64, "magnification": 160}\n'
    monkeypatch.setattr(ts, "_evaluate_plasma_script", evaluate)
    assert ts.dock_settings() == {"autohide": True, "size": 64, "magnification": 160}
    # The Dock: the bottom panel holding a task manager.
    assert 'panel.location !== "bottom"' in scripts[0]
    assert "mac\\.tahoe\\.liquid\\.(icon)?task" in scripts[0]
    assert ts.set_dock("autohide", "off") and 'panel.hiding = "none";' in scripts[-1]
    assert ts.set_dock("size", "200") and "panel.height = 96;" in scripts[-1]
    assert ts.set_dock("magnification", "130")
    assert 'w.writeConfig("dockMagnification", 130)' in scripts[-1]
    count = len(scripts)
    assert not ts.set_dock("size", "big") and not ts.set_dock("position", "left")
    assert len(scripts) == count
    monkeypatch.setattr(ts, "_evaluate_plasma_script", lambda script: "\n")
    assert ts.dock_settings() is None and not ts.set_dock("autohide", "on")


def test_command_line(monkeypatch, capsys):
    monkeypatch.setattr(ts, "_sync_session_env", lambda: None)
    monkeypatch.setattr(ts, "dock_settings", lambda: {"autohide": False, "size": 64,
                                                      "magnification": 160})
    seen = []
    monkeypatch.setattr(ts, "set_dock", lambda k, v: seen.append((k, v)) or True)
    monkeypatch.setattr(ts, "hot_corners", lambda: {"top-left": "none"})
    monkeypatch.setattr(ts, "set_hot_corner", lambda c, a: seen.append((c, a)) or True)
    monkeypatch.setattr(ts, "minimize_effect", lambda: "genie")
    assert ts.main(["dock"]) == 0
    assert json.loads(capsys.readouterr().out)["size"] == 64
    assert ts.main(["dock", "size", "70"]) == 0 and seen[-1] == ("size", "70")
    assert ts.main(["hot-corners"]) == 0 and "top-left" in capsys.readouterr().out
    assert ts.main(["hot-corners", "top-left", "desktop"]) == 0
    assert ts.main(["minimize"]) == 0 and capsys.readouterr().out.strip() == "genie"
    assert ts.main(["dock", "size"]) == 1


def test_theme_settings_page(offline):
    app = (offline / "theme-settings/theme_settings.py").read_text()
    assert '("dock", "Desktop & Dock", "dock", "graphite", DockPage)' in app
    for command in ('["dock", key, value]', '["minimize", key]', '["hot-corners", c, key]'):
        assert command in app
    # The glyphs are drawn by the app: icon themes rarely have -symbolic names.
    pages = app[app.index("PAGES = ("):app.index(")\n\n", app.index("PAGES = ("))]
    assert "-symbolic" not in pages
    css = (offline / "theme-settings/theme-settings.css").read_text()
    for control in ("switch.mac-switch", ".mac-slider scale", "dropdown.mac-popup"):
        assert control in css
