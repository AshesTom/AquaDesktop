"""Battery flyout geometry and truthful charge states against the 2x reference."""
import os
import shutil
import subprocess

import pytest

UI = "plasmoids/org.kde.mac-tahoe-liquid-kde.battery/contents/ui"


def test_reference_geometry_and_system_font(offline):
    view = (offline / UI / "BatteryView.qml").read_text()
    main = (offline / UI / "main.qml").read_text()
    energy = (offline / UI / "EnergyMode.qml").read_text()
    assert "implicitWidth: 280" in view
    assert "width: view.implicitWidth + 28" in main
    assert "radius: 18" in main
    assert "font.pixelSize" not in view + energy
    assert "font: Kirigami.Theme.defaultFont" in view + energy
    assert "width: 26" in energy and "x: 34" in energy
    assert "control.profiles.indexOf(modelData) >= 0" in energy
    assert "energy.expanded = !energy.expanded" in energy
    assert "view.refresh();" in main
    # Item.visible inherits the Loader visibility: binding back to it hides
    # the entire section through a visibility cycle. Use backend availability.
    assert "visible: item !== null && item.available" in view
    assert "energyLoader.item.available" in view


def test_no_invented_app_energy_or_charge_limit(offline):
    view = (offline / UI / "BatteryView.qml").read_text()
    main = (offline / UI / "main.qml").read_text()
    assert "property var energyApplications: null" in view
    # Hidden, never a placeholder, while no app uses significant energy.
    assert "view.energyApplications.length > 0" in view
    assert '"Information Unavailable"' not in view
    assert '"No Apps Using Significant Energy"' not in view
    assert "energyApplications: root.energyApplications" in main
    assert "InhibitionControl" not in view
    assert "profileHolds" not in view
    assert "charge_control_end_threshold" in main
    assert "value > 0 && value <= 100" in main
    assert "chargeLimit: root.chargeLimit" in main


def test_significant_energy_script(offline, tmp_path):
    script = offline / "plasmoids/org.kde.mac-tahoe-liquid-kde.battery/contents/code/significant-energy.sh"
    main = (offline / UI / "main.qml").read_text()
    assert "../code/significant-energy.sh" in main
    text = script.read_text()
    assert "app.slice" in text and "@autostart.service" in text
    result = subprocess.run(["sh", str(script), "1000"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0 and result.stdout == ""


def test_charge_states_in_qml(offline, tmp_path):
    qml = shutil.which("qml6") or shutil.which("qml")
    if not qml:
        pytest.skip("no QML runtime")
    probe = tmp_path / "probe.qml"
    probe.write_text(f'''import QtQuick
import "file://{offline / UI}"
Item {{
    BatteryView {{ id: view; width: implicitWidth; height: implicitHeight }}
    Timer {{
        interval: 100; running: true
        onTriggered: {{
            function record() {{ console.log("STATUS[" + view.chargeStatus + "]"); }}
            view.pluggedIn = true; view.charging = true; view.chargeLimit = 80; record();
            view.chargeLimit = 0; record();
            view.charging = false; view.percent = 100; record();
            view.percent = 80; view.chargeLimit = 80; record();
            view.percent = 46; record();
            view.pluggedIn = false; view.remainingMs = 0; record();
            view.remainingMs = 5400000; record();
            console.log("GEOMETRY[" + view.implicitWidth + "," + (view.implicitHeight > 0) + "]");
            Qt.quit();
        }}
    }}
}}''')
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_FORCE_STDERR_LOGGING": "1",
           "LANGUAGE": "en", "XDG_CONFIG_HOME": str(tmp_path / "config"),
           "XDG_CONFIG_DIRS": str(tmp_path / "defaults"),
           "XDG_DATA_HOME": str(tmp_path / "data"), "XDG_CACHE_HOME": str(tmp_path / "cache"),
           "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent"}
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    result = subprocess.run([qml, str(probe)], env=env, capture_output=True, text=True, timeout=15)
    if "is not installed" in result.stderr:
        pytest.skip("required QML modules missing")
    statuses = [line.split("STATUS[", 1)[1].rsplit("]", 1)[0]
                for line in result.stderr.splitlines() if "STATUS[" in line]
    assert statuses == ["Charging to 80% Limit", "Charging to Full", "Fully Charged",
                        "Charged to 80% Limit", "Not Charging", "", "1 h 30 min remaining"], result.stderr
    assert "GEOMETRY[280,true]" in result.stderr
    assert "TypeError" not in result.stderr and "ReferenceError" not in result.stderr
    assert "Property has already" not in result.stderr
