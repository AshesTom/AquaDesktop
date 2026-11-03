"""Exercise material controls and installation of each edition's preset."""
import configparser
import json
import os
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


def test_native_kcm_keeps_tahoe_defaults_and_user_tuning(kcm_probe, tmp_path):
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
    # The KCM's Defaults leaves a sparse configuration (KConfig omits schema
    # defaults, radii and window rules included).
    # Installing either edition must write its complete material over it.
    config = tmp_path / "config/kwinrc"
    env["PYTHONPATH"] = str(REPO / "src/scripts")
    for edition, index in (("MacGoldenGate", 2), ("MacTahoe", 1)):
        result = subprocess.run([sys.executable, "-c",
                                 "from steps import acrylic_glass as g; "
                                 f"g.default_wallpaper = lambda: {edition!r}; "
                                 "assert g._install_material_preset()"],
                                env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        saved = configparser.ConfigParser()
        saved.optionxform = str
        saved.read(config)
        material = saved["Effect-liquidglass"]
        assert material.items() >= _preset_values(index).items()


def _preset_values(preset_value):
    presets = json.loads((glass.SRC / "src/presets.json").read_text())
    preset = next(preset for preset in presets if preset["value"] == preset_value)
    return {key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in preset["values"].items()}


@pytest.mark.parametrize("edition", ["MacTahoe", "MacGoldenGate"])
@pytest.mark.parametrize("existing", ["fresh", "legacy", "custom", "tahoe", "golden-gate", "empty"])
def test_installation_reapplies_complete_edition_material(monkeypatch, edition, existing):
    monkeypatch.setattr(glass, "default_wallpaper", lambda: edition)
    saved = {}
    if existing != "fresh":
        saved = dict(BlurStrength="3", Brightness="1.2", Contrast="1.0",
                     Saturation="1.0", RefractionStrength="12", NoiseStrength="2",
                     TintColor="#40ffffff", RimSpecular="false")
    if existing == "custom":
        saved["BlurStrength"] = "9"
        saved["PhysicallyBasedRefraction"] = "true"
    elif existing in ("tahoe", "golden-gate"):
        saved = _preset_values(1 if existing == "tahoe" else 2)
    elif existing == "empty":
        saved["RimWidth"] = ""
    independent = {"TopCornerRadius": "13.5", "DockCornerRadius": "0",
                   "MenuCornerRadius": "", "WindowClasses": "custom-app",
                   "BlurMatching": "true", "BlurNonMatching": "false"}
    saved |= independent
    def write(*args):
        saved[args[-2]] = args[-1]
        return True
    monkeypatch.setattr(glass, "kw_write", write)
    assert glass._install_material_preset()
    expected = _preset_values(2 if edition == "MacGoldenGate" else 1) | independent
    if existing == "custom":
        # Optics outside the preset stay the user's.
        expected["PhysicallyBasedRefraction"] = "true"
    assert saved == expected
    assert glass._install_material_preset()
    assert saved == expected


@pytest.mark.parametrize("failed_key", ["BlurStrength", "TintColor", "EdgeAA"])
def test_material_write_failure_does_not_report_success(monkeypatch, capsys, failed_key):
    writes = []
    def write(*args):
        writes.append(args[-2])
        return args[-2] != failed_key
    monkeypatch.setattr(glass, "kw_write", write)
    assert not glass._install_material_preset()
    assert writes[-1] == failed_key
    assert f"{failed_key} preset not applied" in capsys.readouterr().out
