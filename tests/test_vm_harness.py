"""Regression coverage for the graphical VM harness."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
VM = (REPO / "vm").read_text()
PLYMOUTH_RENDER = (REPO / "tests/vm/render.sh").read_text()
NEON_CLOUD_PATH = REPO / ".vm/cloud-init/neon.yaml"
SYSTEMD_CLOUD_PATHS = tuple(
    path
    for path in sorted((REPO / ".vm/cloud-init").glob("*.yaml"))
)


def _provision_script(path: Path) -> str:
    """Return cloud-init's YAML block scalar exactly as bash receives it."""
    content = path.read_text().split("    content: |\n", 1)[1]
    content = content.split("\nruncmd:\n", 1)[0]
    return "\n".join(
        line[6:] if line.startswith("      ") else line
        for line in content.splitlines()
    ) + "\n"


def test_vm_excludes_retired_gentoo_targets():
    result = subprocess.run(
        [str(REPO / "vm"), "list"], check=True, capture_output=True, text=True,
    )
    assert not any("gentoo" in name for name in result.stdout.splitlines())


def test_vm_lists_neon():
    result = subprocess.run(
        [str(REPO / "vm"), "list"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "neon" in result.stdout.splitlines()


def test_neon_vm_uses_signed_official_sources_and_qt6_build_deps():
    cloud = NEON_CLOUD_PATH.read_text()

    assert "cloud-images.ubuntu.com/noble/current" in VM
    assert "http://archive.neon.kde.org/user" in cloud
    assert "444DABCF3667D0283F894EDDE6D4736255751E5D" in cloud
    assert "Signed-By: /etc/apt/keyrings/mttkde-neon-archive-keyring.asc" in cloud
    assert "base-files" in cloud
    assert "neon-desktop" in cloud and "plasmalogin" in cloud
    assert "python3-pyqt6.qtqml" in cloud
    assert "qt6-svg-dev" in cloud and "libxext-dev" in cloud
    assert "/home/tester/macos-tahoe-liquid-kde" in cloud
    assert "--exclude=.vm" in cloud and "--exclude=build" in cloud
    assert "trusted=yes" not in cloud
    assert "add-apt-repository" not in cloud


def test_neon_provision_script_is_valid_bash():
    result = subprocess.run(
        ["bash", "-n"],
        input=_provision_script(NEON_CLOUD_PATH),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_systemd_cloud_images_dispatch_their_provisioner():
    """The provision script is a YAML block scalar.  ``runcmd`` must be a
    root key after that block, or cloud-init writes the dispatcher into the
    script instead of ever executing it and the guest stops at a bare login.
    """
    failures = []
    for path in SYSTEMD_CLOUD_PATHS:
        text = path.read_text()
        root_marker = "\nruncmd:\n"
        if root_marker not in text:
            failures.append(f"{path.name}: missing root runcmd")
            continue
        commands = text.rsplit(root_marker, 1)[1]
        if not re.search(
            r"(?m)^  - /usr/local/bin/mttkde-provision\.sh$",
            commands,
        ):
            failures.append(f"{path.name}: provisioner is not dispatched")

    assert not failures, "\n".join(failures)


def test_plymouth_render_harness_does_not_depend_on_active_window_focus():
    assert 'scrot --overwrite --window "$window_id"' in PLYMOUTH_RENDER
    assert "spectacle --background --nonotify --activewindow" not in PLYMOUTH_RENDER
    assert "xdotool windowactivate" not in PLYMOUTH_RENDER


def test_plymouth_render_harness_forces_visible_progress():
    assert "on_boot_progress(0, 0.65)" in PLYMOUTH_RENDER
    assert "Plymouth.SetBootProgressFunction(mttkde_harness_progress)" in PLYMOUTH_RENDER
    assert "on_boot_progress(duration, 0.65)" in PLYMOUTH_RENDER
    assert "apply_layout" not in PLYMOUTH_RENDER


def test_plymouth_render_harness_validates_pixels_and_propagates_failure():
    for invariant in (
        "captured the desktop, not Plymouth",
        "logo is missing or off-centre",
        "boot progress fill is missing",
        "shutdown unexpectedly shows a progress bar",
        "Plymouth log contains a script error",
    ):
        assert invariant in PLYMOUTH_RENDER
    assert "exit 1" in PLYMOUTH_RENDER
