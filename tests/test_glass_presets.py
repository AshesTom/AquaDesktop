"""Exercise the real material controls and installer preservation contract."""
import os
import select
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from steps import acrylic_glass as glass

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def kcm_probe(tmp_path_factory):
    if not shutil.which("cmake"):
        pytest.skip("CMake required for the native KCM")
    build = tmp_path_factory.mktemp("glass-kcm-build")
    result = subprocess.run(["cmake", "-S", str(REPO / "tests/glass"), "-B", str(build),
                             f"-DGLASS_SOURCE={glass.SRC}"], capture_output=True, text=True, timeout=60)
    if "GLASS_KCM_SDK_MISSING" in result.stdout:
        pytest.skip("KWin D-Bus development interface required")
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(["cmake", "--build", str(build), "-j2"],
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return build


def test_native_material_preset_controls(kcm_probe, tmp_path):
    if not shutil.which("dbus-run-session"):
        pytest.skip("private D-Bus session required")
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG")}
    env.update(HOME=str(tmp_path), XDG_CONFIG_HOME=str(tmp_path / "config"),
               XDG_CONFIG_DIRS=str(tmp_path / "system"), QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(["dbus-run-session", "--", str(kcm_probe / "glass-kcm-probe"),
                             str(kcm_probe / "kcm/kwin_liquidglass_config.so"),
                             str(glass.SRC / "src/presets.json")],
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "save/reopen, cancel and restore verified" in result.stderr
    # The KCM ends with Tahoe selected, omitting keys equal to schema defaults.
    # A subsequent Golden Gate install must not fill them with Golden values.
    config = tmp_path / "config/kwinrc"
    saved = config.read_bytes()
    env["PYTHONPATH"] = str(REPO / "src/scripts")
    result = subprocess.run([sys.executable, "-c",
                             "from steps import acrylic_glass as g; "
                             "g.default_wallpaper = lambda: 'MacGoldenGate'; "
                             "g._install_material_defaults()"],
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert config.read_bytes() == saved


@pytest.mark.parametrize("edition", ["MacTahoe", "MacGoldenGate"])
@pytest.mark.parametrize("existing", ["fresh", "legacy", "custom", "saved-preset", "empty"])
def test_material_installation_preserves_customizations_and_migrates_stock(monkeypatch, edition, existing):
    monkeypatch.setattr(glass, "default_wallpaper", lambda: edition)
    golden = edition == "MacGoldenGate"
    saved = {}
    if existing != "fresh":
        saved = dict(BlurStrength="4.0" if golden else "3.5", Brightness="1.0", Contrast="1.0",
                     Saturation="1.0", HighlightStrength="0.30", HighlightWidth="24",
                     MagnifyGlassStrength="0.015" if golden else "0.03", NoiseStrength="2",
                     RefractionWidth="72" if golden else "96", DarkGradientOverlay="false")
    if existing == "custom":
        saved["BlurStrength"] = "8.25"
        saved["GradientTopColor"] = "#263a51"
    elif existing == "saved-preset":
        saved["MaterialPreset"] = "0"
        saved["MaterialOpacity"] = "0.4"
    elif existing == "empty":
        saved["MagnifyGlassStrength"] = ""
    saved |= {"WindowCornerRadius": "13.5", "WindowClasses": "custom-app"}
    original = saved.copy()
    monkeypatch.setattr(glass, "have", lambda command: True)
    monkeypatch.setattr(glass, "run_user", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0, saved.get(command[6], command[-1]) + "\n"))
    writes = []
    def write(*args):
        writes.append(args[-2])
        saved[args[-2]] = args[-1]
        return True
    monkeypatch.setattr(glass, "kw_write", write)
    glass._install_material_defaults()
    if existing in ("fresh", "legacy"):
        assert saved["BlurStrength"] == ("6.5" if golden else "5.0")
        assert saved["MagnifyGlassStrength"] == ("0.008" if golden else "0.02")
    else:
        assert all(saved[key] == value for key, value in original.items())
    if existing != "fresh":
        assert saved["DarkGradientOverlay"] == "false"
    assert saved["WindowCornerRadius"] == "13.5"
    assert saved["WindowClasses"] == "custom-app"
    writes.clear()
    glass._install_material_defaults()
    assert not writes


@pytest.mark.parametrize("failure", ["missing-tool", "exit", "timeout", "write"])
def test_material_default_errors_do_not_mark_a_successful_migration(monkeypatch, failure):
    monkeypatch.setattr(glass, "have", lambda command: failure != "missing-tool")
    def read(command, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 5)
        return subprocess.CompletedProcess(command, 1 if failure == "exit" else 0, command[-1] + "\n")
    monkeypatch.setattr(glass, "run_user", read)
    writes = []
    monkeypatch.setattr(glass, "kw_write", lambda *args: writes.append(args[-2]) or False)
    glass._install_material_defaults()
    assert "MaterialPreset" not in writes
    assert len(writes) == (1 if failure == "write" else 0)


def test_native_glass_shader_pixels(kcm_probe, tmp_path):
    if not shutil.which("Xvfb"):
        pytest.skip("Xvfb required for isolated software OpenGL")
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG")}
    env.update(HOME=str(tmp_path), XDG_CONFIG_HOME=str(tmp_path / "config"),
               XDG_CONFIG_DIRS=str(tmp_path / "system"), QT_QPA_PLATFORM="xcb",
               LIBGL_ALWAYS_SOFTWARE="1")
    with (tmp_path / "xvfb.log").open("w") as log:
        server = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "640x480x24", "-nolisten", "tcp"],
                                  stdout=subprocess.PIPE, stderr=log, text=True, env=env)
        try:
            assert select.select([server.stdout], [], [], 15)[0], "Xvfb did not start"
            display = server.stdout.readline().strip()
            assert display.isdigit(), (tmp_path / "xvfb.log").read_text()
            env["DISPLAY"] = ":" + display
            result = subprocess.run([str(kcm_probe / "glass-shader-probe"), str(glass.SRC / "src/shaders")],
                                    env=env, capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stdout + result.stderr
            assert "both profiles verified" in result.stderr
        finally:
            server.terminate()
            server.wait(timeout=5)
