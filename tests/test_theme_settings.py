"""Theme Settings (src/offline/theme-settings): the GTK 4 window for the
appearance, the accent colour, the Glass style and the Icon Manager, and
how the theme_switch step installs it."""

import configparser
import importlib.util

import pytest

FILES = ("theme_settings.py", "theme-settings.css",
         "org.kde.mac-tahoe-liquid-kde.themesettings.desktop")


def test_sources_and_launcher(offline):
    folder = offline / "theme-settings"
    for name in FILES:
        assert (folder / name).is_file(), name
    parser = configparser.RawConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    parser.read(folder / FILES[2], encoding="utf-8")
    entry = parser["Desktop Entry"]
    assert entry["Exec"] == "mac-tahoe-theme-settings"
    assert entry["Name[fr]"] == "Réglages du thème"
    assert parser["Desktop Action Icons"]["Exec"] == "mac-tahoe-theme-settings --page icons"
    # The desktop file id is the application id (portal registration).
    app = (folder / FILES[0]).read_text()
    assert f'APP_ID = "{FILES[2].removesuffix(".desktop")}"' in app


def test_drives_only_the_installed_tools(offline):
    app = (offline / "theme-settings/theme_settings.py").read_text()
    assert '".local/bin/mac-tahoe-theme-switch"' in app
    assert 'HERE.parent / "icon-manager/icon_manager.py"' in app
    assert '["accent", colour or "multicolour"]' in app
    # macOS layout: the traffic lights live in the sidebar, no title bar.
    assert 'decoration_layout="close,minimize,maximize:"' in app
    assert "self.set_titlebar(Gtk.Box(visible=False))" in app


@pytest.fixture
def ts(offline, monkeypatch):
    gi = pytest.importorskip("gi")
    try:
        gi.require_version("Gtk", "4.0")
    except ValueError:
        pytest.skip("GTK 4 introspection data is not installed")
    spec = importlib.util.spec_from_file_location(
        "theme_settings", offline / "theme-settings/theme_settings.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reads_mode_accent_and_style(ts, monkeypatch, tmp_path):
    values = {
        ("KDE", "LookAndFeelPackage"): "org.kde.mac-tahoe-liquid-kde.light",
        ("General", "AccentColor"): "255,141,40",
        ("Colors:Selection", "BackgroundNormal"): "255,141,40",
    }
    monkeypatch.setattr(ts, "kread", lambda _f, g, k: values.get((g, k), ""))
    assert ts.current_mode() == "light"
    assert ts.custom_accent() == "#ff8d28"
    assert ts.effective_accent() == "#ff8d28"
    values[("KDE", "LookAndFeelPackage")] = "org.kde.mac-tahoe-liquid-kde.dark"
    values[("General", "AccentColor")] = ""
    assert ts.current_mode() == "dark" and ts.custom_accent() == ""

    style = tmp_path / "glass-style"
    monkeypatch.setattr(ts, "GLASS_STYLE_FILE", style)
    assert ts.glass_style() == "tahoe"
    style.write_text("frosted\n")
    assert ts.glass_style() == "frosted"
    style.write_text("bogus\n")
    assert ts.glass_style() == "tahoe"


def test_auto_needs_the_installed_schedule(ts, monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.setattr(ts, "CONFIG", tmp_path)
    crontab = {"out": ""}
    monkeypatch.setattr(ts.subprocess, "run",
                        lambda *_a, **_k: SimpleNamespace(stdout=crontab["out"]))
    assert not ts.auto_available()
    crontab["out"] = "0 6 * * * /home/u/.local/bin/mac-tahoe-theme-switch auto # theme\n"
    assert ts.auto_available()   # OpenRC
    crontab["out"] = ""
    (tmp_path / "systemd/user").mkdir(parents=True)
    (tmp_path / "systemd/user" / ts.THEME_TIMER).write_text("[Timer]\n")
    assert ts.auto_available()   # systemd


def test_french_strings(ts):
    assert ts._FR["Appearance"] == "Apparence"
    assert ts._FR["Frosted"] == "Givré"


def test_step_installs_and_removes_the_app(monkeypatch, tmp_path, offline):
    from steps import theme_switch as step

    paths = {
        "src": offline / "theme-settings",
        "app": tmp_path / "apps/theme-settings",
        "bin": tmp_path / "bin/mac-tahoe-theme-settings",
        "desktop": tmp_path / "applications" / step.THEME_SETTINGS_DESKTOP,
    }
    monkeypatch.setattr(step, "_theme_settings_paths", lambda: paths)
    for name in ("ok", "warn"):
        monkeypatch.setattr(step, name, lambda *_a: None)
    step._install_theme_settings()
    assert (paths["app"] / "theme_settings.py").is_file()
    assert (paths["app"] / "theme-settings.css").is_file()
    assert paths["bin"].stat().st_mode & 0o111
    assert str(paths["app"] / "theme_settings.py") in paths["bin"].read_text()
    assert paths["desktop"].is_file()
    step._uninstall_theme_settings()
    assert not paths["app"].exists() and not paths["bin"].exists()
    assert not paths["desktop"].exists()
