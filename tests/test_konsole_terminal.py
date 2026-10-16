"""Konsole as macOS Terminal (AquaDesktop).

Terminal's default window is its "Basic" profile: 80 x 24, black on white
in light mode, white on #1D1E1D in dark mode, Terminal's ANSI palette
(iTerm2-Color-Schemes "Terminal Basic" / "Terminal Basic Dark", the light
one also Wikipedia's Terminal.app column), a steady grey block cursor.
"""

import configparser
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
KONSOLE = REPO / "src/offline/konsole"
sys.path.insert(0, str(REPO / "src/scripts"))

from steps import apps  # noqa: E402

LIGHT = {
    "Background": "255,255,255", "Foreground": "0,0,0",
    "Color0": "0,0,0", "Color1": "153,0,0", "Color2": "0,166,0", "Color3": "153,153,0",
    "Color4": "0,0,178", "Color5": "178,0,178", "Color6": "0,166,178", "Color7": "191,191,191",
    "Color0Intense": "102,102,102", "Color1Intense": "229,0,0", "Color2Intense": "0,217,0",
    "Color3Intense": "191,191,0", "Color4Intense": "0,0,255", "Color5Intense": "229,0,229",
    "Color6Intense": "0,216,216", "Color7Intense": "229,229,229",
}
DARK = {
    "Background": "29,30,29", "Foreground": "255,255,255",
    "Color1": "198,83,57", "Color2": "106,196,75", "Color4": "100,68,237",
    "Color7": "209,209,209", "Color0Intense": "144,144,144", "Color7Intense": "237,237,237",
}


def _ini(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, comment_prefixes=("#",))
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    return parser


@pytest.mark.parametrize("scheme, colours", [
    ("MacTahoeLiquidKdeLight", LIGHT), ("MacTahoeLiquidKdeDark", DARK),
])
def test_colour_schemes_are_terminal_basic(scheme, colours):
    ini = _ini(KONSOLE / f"{scheme}.colorscheme")
    for group, value in colours.items():
        assert ini[group]["Color"] == value, group
    # Every Konsole slot is there, opaque, bold in the text colour.
    for i in range(8):
        for suffix in ("", "Faint", "Intense"):
            assert f"Color{i}{suffix}" in ini, f"Color{i}{suffix}"
    assert ini["ForegroundIntense"]["Color"] == ini["Foreground"]["Color"]
    assert ini["General"]["Opacity"] == "1" and ini["General"]["Blur"] == "false"


@pytest.mark.parametrize("profile, name, scheme, cursor", [
    ("MacTahoeLiquidKde-Light", "AquaDesktop Light", "MacTahoeLiquidKdeLight", "127,127,127"),
    ("MacTahoeLiquidKde-Dark", "AquaDesktop Dark", "MacTahoeLiquidKdeDark", "157,157,157"),
])
def test_profiles_open_terminals_default_window(profile, name, scheme, cursor):
    ini = _ini(KONSOLE / f"{profile}.profile")
    assert ini["General"]["Name"] == name
    assert ini["Appearance"]["ColorScheme"] == scheme
    assert (KONSOLE / f"{scheme}.colorscheme").is_file()
    assert ini["General"]["TerminalColumns"] == "80" and ini["General"]["TerminalRows"] == "24"
    assert ini["General"]["LocalTabTitleFormat"] == "%u — %n"
    assert ini["Cursor Options"]["CursorShape"] == "0"
    assert ini["Cursor Options"]["CustomCursorColor"] == cursor
    assert ini["Terminal Features"]["BlinkingCursorEnabled"] == "false"
    # The system's fixed font, never a hard-coded one.
    assert "Font" not in ini["Appearance"]
    # konsolerc names the profiles by their Name.
    assert name in (apps.LIGHT_PROFILE, apps.DARK_PROFILE)


class _Config(dict):
    def write(self, *args):
        file, group, key, value = args[1], args[3], args[5], args[6]
        if value == "--delete":
            self.pop((file, group, key), None)
        else:
            self[(file, group, key)] = value
        return True

    def read(self, file, group, key):
        return self.get((file, group, key), "")


def _sandboxed(monkeypatch, tmp_path, config):
    monkeypatch.setattr(apps, "KONSOLE_DIR", tmp_path / "konsole")
    monkeypatch.setattr(apps, "kw_write", config.write)
    monkeypatch.setattr(apps, "kw_read", config.read)
    messages = []
    for name in ("ok", "warn", "info"):
        monkeypatch.setattr(apps, name, messages.append)
    return messages


def test_install_follows_the_appearance_and_keeps_user_edits(monkeypatch, tmp_path):
    config = _Config({("konsolerc", "KonsoleWindow", "RememberWindowSize"): "true"})
    _sandboxed(monkeypatch, tmp_path, config)
    edited = tmp_path / "konsole/MacTahoeLiquidKde-Dark.profile"
    edited.parent.mkdir()
    edited.write_text("[General]\nName=AquaDesktop Dark\n# the user's font\n")

    apps.install()

    for name in ("MacTahoeLiquidKde-Light.profile", "MacTahoeLiquidKdeLight.colorscheme",
                 "MacTahoeLiquidKdeDark.colorscheme"):
        assert (tmp_path / "konsole" / name).read_bytes() == (KONSOLE / name).read_bytes()
    assert "the user's font" in edited.read_text()
    assert config[("konsolerc", "LightDarkTheme", "SyncProfileWithSystemTheme")] == "true"
    assert config[("konsolerc", "LightDarkTheme", "LightThemeProfile")] == "AquaDesktop Light"
    assert config[("konsolerc", "LightDarkTheme", "DarkThemeProfile")] == "AquaDesktop Dark"
    # The user's own choice stays.
    assert config[("konsolerc", "KonsoleWindow", "RememberWindowSize")] == "true"

    apps.uninstall()

    assert config == {("konsolerc", "KonsoleWindow", "RememberWindowSize"): "true"}
    assert not list((tmp_path / "konsole").glob("MacTahoeLiquidKde*"))


def test_a_default_profile_the_user_picked_wins(monkeypatch, tmp_path):
    config = _Config({("konsolerc", "Desktop Entry", "DefaultProfile"): "Mine.profile"})
    _sandboxed(monkeypatch, tmp_path, config)

    apps.install()

    assert config == {("konsolerc", "Desktop Entry", "DefaultProfile"): "Mine.profile"}
    assert (tmp_path / "konsole/MacTahoeLiquidKde-Light.profile").is_file()


def test_konsole_reads_the_profiles(tmp_path):
    if not shutil.which("konsole"):
        pytest.skip("Konsole not installed")
    data = tmp_path / "data"
    shutil.copytree(KONSOLE, data / "konsole")
    env = {key: value for key, value in os.environ.items()
           if key not in ("DBUS_SESSION_BUS_ADDRESS", "WAYLAND_DISPLAY", "DISPLAY")}
    env.update({"QT_QPA_PLATFORM": "offscreen", "XDG_DATA_HOME": str(data),
                "XDG_CONFIG_HOME": str(tmp_path / "config"),
                "XDG_CACHE_HOME": str(tmp_path / "cache")})
    result = subprocess.run(["konsole", "--list-profiles"], env=env,
                            capture_output=True, text=True, timeout=30)
    listed = result.stdout.split()
    assert "MacTahoeLiquidKde-Light" in listed and "MacTahoeLiquidKde-Dark" in listed, result


def test_rebranding_keeps_existing_profile_settings(monkeypatch, tmp_path):
    config = _Config({
        ("konsolerc", "LightDarkTheme", "LightThemeProfile"): "Tahoe Gate Light",
        ("konsolerc", "LightDarkTheme", "DarkThemeProfile"): "Tahoe Gate Dark",
    })
    _sandboxed(monkeypatch, tmp_path, config)
    profile = tmp_path / "konsole/MacTahoeLiquidKde-Dark.profile"
    profile.parent.mkdir()
    profile.write_text("[General]\nName=Tahoe Gate Dark\n[Appearance]\nFont=My custom font\n")

    apps.install()

    assert profile.read_text() == (
        "[General]\nName=AquaDesktop Dark\n[Appearance]\nFont=My custom font\n")
    assert config[("konsolerc", "LightDarkTheme", "DarkThemeProfile")] == "AquaDesktop Dark"
    apps.uninstall()
    assert config == {}
