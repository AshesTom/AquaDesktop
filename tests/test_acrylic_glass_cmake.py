"""Static guards for the Acrylic Glass CMake fallback paths."""

import re
import shutil
import subprocess

import pytest
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "src/offline/kwin-effects/acrylic-glass"


def test_acrylic_glass_fails_cleanly_without_kwin_dev_support():
    top = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "if(NOT GLASS_WAYLAND AND NOT GLASS_X11)" in top
    assert "Acrylic Glass requires KWin development files for Wayland or X11." in top


def test_acrylic_glass_only_configures_kcm_when_a_kwin_backend_is_available():
    src = (ROOT / "src/CMakeLists.txt").read_text(encoding="utf-8")
    assert "if(GLASS_WAYLAND OR GLASS_X11)" in src
    assert "add_subdirectory(kcm)" in src


def test_acrylic_glass_version_floor_matches_preflight():
    """The effect's CMake floor, the preflight runtime floor, and the
    README must all agree on 6.6 — they drifted once (CMake said 6.4
    while preflight blocked <6.6), which is exactly the inconsistency
    this test exists to prevent."""
    sys.path.insert(0, str(REPO / "src/scripts"))
    import preflight

    assert preflight._MIN_PLASMA == (6, 6)

    top = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "VERSION_LESS 6.6" in top
    assert "requires KDE Plasma 6.6+" in top
    # The retired 6.4 floor must not creep back.
    assert "VERSION_LESS 6.4" not in top


def test_acrylic_glass_preset_fits_kcm_ranges():
    """Installer tuning must remain representable in the effect KCM."""
    from steps import acrylic_glass

    preset = dict(acrylic_glass._PRESET)
    # Contributor/MR tuning is not part of the project preset.
    assert "AcrylicGlassType" not in preset
    assert "RgbDriftStrength" not in preset
    assert preset["BlurStrength"] == "3.5"
    assert preset["HighlightStrength"] == "0.30"
    assert preset["HighlightWidth"] == "24"
    assert preset["MagnifyGlassStrength"] == "0.03"
    assert preset["RefractionWidth"] == "96"
    assert preset["Saturation"] == "1.0"

    root = ET.parse(ROOT / "src/kcm/config.ui").getroot()
    for key in ("RgbDriftStrength", "MagnifyGlassStrength"):
        if key not in preset:
            continue
        widget = root.find(f".//widget[@name='kcfg_{key}']")
        assert widget is not None
        maximum = widget.find("./property[@name='maximum']/double")
        assert maximum is not None and maximum.text is not None
        assert float(preset[key]) <= float(maximum.text)


def test_acrylic_glass_installs_the_effect_default_blur(monkeypatch, tmp_path):
    """The real install path must not replace the KCM default with strength 5."""
    from steps import acrylic_glass
    from subprocess import CompletedProcess

    build = tmp_path / "build"
    for name in ("src/liquidglass.so", "src/kcm/kwin_liquidglass_config.so"):
        artifact = build / name
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.touch()
    monkeypatch.setattr(acrylic_glass, "BUILD", build)
    monkeypatch.setattr(acrylic_glass, "_plugin_dir", lambda: tmp_path / "plugins")
    monkeypatch.setattr(acrylic_glass, "LEGACY_USER_PLUGIN_DIR", tmp_path / "legacy")
    monkeypatch.setattr(acrylic_glass, "sudo_install_file", lambda *args: True)
    monkeypatch.setattr(acrylic_glass, "qdbus_call", lambda *args: True)
    monkeypatch.setattr(acrylic_glass, "qdbus_cmd", lambda: None)
    monkeypatch.setattr(acrylic_glass, "have", lambda command: True)
    monkeypatch.setattr(acrylic_glass, "run_user",
                        lambda command, **kwargs: CompletedProcess(command, 0, "28\n"))
    monkeypatch.setattr(acrylic_glass.time, "sleep", lambda seconds: None)
    writes = []
    monkeypatch.setattr(acrylic_glass, "kw_write",
                        lambda *args: writes.append(args) or True)

    acrylic_glass.install()

    config = ET.parse(ROOT / "src/glass.kcfg").getroot()
    entry = config.find(".//{*}entry[@name='BlurStrength']/{*}default")
    assert entry is not None
    default = entry.text
    assert default == "3.5"
    blur_writes = [args for args in writes if "BlurStrength" in args]
    assert blur_writes == [("--file", "kwinrc", "--group", "Effect-liquidglass",
                           "--key", "BlurStrength", default)]
    # The complete install must preserve the #89 workaround, including
    # avoiding the obsolete Menu/Dialog/Tooltip/Bottom radius keys.
    assert not any(args[-2].endswith("CornerRadius") for args in writes)


def test_corner_defaults_only_seed_missing_keys(monkeypatch):
    from subprocess import CompletedProcess
    from steps import acrylic_glass

    values = {"WindowCornerRadius": "28", "DockCornerRadius": ""}
    writes = []
    monkeypatch.setattr(acrylic_glass, "have", lambda command: True)

    def read(command, **kwargs):
        assert command[:5] == ["kreadconfig6", "--file", "kwinrc", "--group",
                               "Effect-liquidglass"]
        key = command[command.index("--key") + 1]
        return CompletedProcess(command, 0, values.get(key, command[-1]) + "\n")

    monkeypatch.setattr(acrylic_glass, "run_user", read)
    monkeypatch.setattr(acrylic_glass, "kw_write", lambda *args: writes.append(args) or True)
    acrylic_glass._install_corner_defaults()
    assert [args[-2:] for args in writes] == [("PopupCornerRadius", "6")]


def test_corner_defaults_do_not_replace_custom_values(monkeypatch):
    from subprocess import CompletedProcess
    from steps import acrylic_glass

    monkeypatch.setattr(acrylic_glass, "have", lambda command: True)
    monkeypatch.setattr(acrylic_glass, "run_user",
                        lambda command, **kwargs: CompletedProcess(command, 0, "28\n"))
    writes = []
    monkeypatch.setattr(acrylic_glass, "kw_write", lambda *args: writes.append(args) or True)
    acrylic_glass._install_corner_defaults()
    acrylic_glass._install_corner_defaults()
    assert writes == []


def test_corner_defaults_fail_closed_on_missing_reader(monkeypatch, capsys):
    from steps import acrylic_glass

    monkeypatch.setattr(acrylic_glass, "have", lambda command: False)
    writes = []
    monkeypatch.setattr(acrylic_glass, "kw_write", lambda *args: writes.append(args) or True)
    acrylic_glass._install_corner_defaults()
    assert writes == []
    assert "kreadconfig6" in capsys.readouterr().out


def test_corner_defaults_fail_closed_on_read_errors(monkeypatch, capsys):
    import subprocess
    from steps import acrylic_glass

    def read(command, **kwargs):
        key = command[command.index("--key") + 1]
        if key == "WindowCornerRadius":
            raise OSError("reader unavailable")
        if key == "DockCornerRadius":
            raise subprocess.TimeoutExpired(command, 5)
        return subprocess.CompletedProcess(command, 1, command[-1] + "\n")

    monkeypatch.setattr(acrylic_glass, "have", lambda command: True)
    monkeypatch.setattr(acrylic_glass, "run_user", read)
    writes = []
    monkeypatch.setattr(acrylic_glass, "kw_write", lambda *args: writes.append(args) or True)
    acrylic_glass._install_corner_defaults()
    assert writes == []
    output = capsys.readouterr().out
    assert all(key in output for key, _ in acrylic_glass._CORNER_DEFAULTS)


def test_corner_defaults_warn_on_failed_write(monkeypatch, capsys):
    from subprocess import CompletedProcess
    from steps import acrylic_glass

    monkeypatch.setattr(acrylic_glass, "have", lambda command: True)
    monkeypatch.setattr(acrylic_glass, "run_user",
                        lambda command, **kwargs: CompletedProcess(command, 0, command[-1] + "\n"))
    monkeypatch.setattr(acrylic_glass, "kw_write", lambda *args: False)
    acrylic_glass._install_corner_defaults()
    assert "kwriteconfig6" in capsys.readouterr().out


def test_acrylic_glass_gates_kwin_68_draw_window_api():
    """KWin 6.8 (6.7.90 beta onwards) made Effect::drawWindow() return
    bool and dropped snapToPixelGrid/snapToPixelGridF. The effect must
    switch its override signature on GLASS_KWIN_68 and keep its own pixel
    snapping helpers so it builds on 6.6, 6.7 and 6.8."""
    top = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "VERSION_GREATER_EQUAL 6.7.90" in top
    src = (ROOT / "src/CMakeLists.txt").read_text(encoding="utf-8")
    assert "target_compile_definitions(liquidglass PRIVATE GLASS_KWIN_68)" in src
    assert "target_compile_definitions(liquidglass_x11 PRIVATE GLASS_KWIN_68)" in src

    compat = (ROOT / "src/kwin_version_compat.h").read_text(encoding="utf-8")
    assert "#ifdef GLASS_KWIN_68" in compat
    assert "using AcrylicGlassDrawWindowResult = bool;" in compat
    assert "using AcrylicGlassDrawWindowResult = void;" in compat

    header = (ROOT / "src/effect.h").read_text(encoding="utf-8")
    assert "AcrylicGlassDrawWindowResult drawWindow(" in header

    effect = (ROOT / "src/effect.cpp").read_text(encoding="utf-8")
    assert "AcrylicGlassDrawWindowResult BlurEffect::drawWindow(" in effect
    # KWin's helpers are gone on 6.8; only the local copies may be called.
    assert re.search(r"(?<![A-Za-z_])snapToPixelGridF?\(", effect) is None
    assert "inline QRect agSnapToPixelGrid(" in effect
    assert "inline QRectF agSnapToPixelGridF(" in effect


def test_acrylic_glass_selects_abi_per_backend(tmp_path):
    if not shutil.which("cmake"):
        pytest.skip("cmake not available")
    source = (ROOT / "CMakeLists.txt").read_text()
    start = source.index("if(GLASS_WAYLAND)\n    find_package(KWin")
    end = source.index("find_package(KDecoration3 REQUIRED)", start)
    # Run the actual discovery/version logic with synthetic SDK versions.
    for wayland, x11, expected in [
        ("6.6.5", "", "OFF;OFF;OFF;OFF"),
        ("6.7.4", "", "ON;OFF;OFF;OFF"),
        ("6.7.90", "", "ON;OFF;ON;OFF"),
        ("6.8.0", "6.7.4", "ON;ON;ON;OFF"),
        ("", "6.8.0", "OFF;ON;OFF;ON"),
    ]:
        script = tmp_path / "versions.cmake"
        result = tmp_path / "result"
        script.write_text(
            # Match the project's policy baseline: older CMake otherwise
            # treats TRUE as a variable name rather than a boolean (CMP0012).
            "cmake_minimum_required(VERSION 3.16.0)\n"
            "macro(find_package)\nendmacro()\n"
            f"set(GLASS_WAYLAND {'ON' if wayland else 'OFF'})\n"
            f"set(GLASS_X11 {'ON' if x11 else 'OFF'})\n"
            "set(KWin_FOUND TRUE)\nset(KWinX11_FOUND TRUE)\n"
            f'set(KWin_VERSION "{wayland}")\n'
            f'set(KWinX11_VERSION "{x11}")\n'
            + source[start:end]
            + f'file(WRITE "{result}" "${{GLASS_KWIN_67_WAYLAND}};'
              '${GLASS_KWIN_67_X11};${GLASS_KWIN_68_WAYLAND};'
              '${GLASS_KWIN_68_X11}")\n')
        proc = subprocess.run(["cmake", "-P", str(script)],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert result.read_text() == expected
