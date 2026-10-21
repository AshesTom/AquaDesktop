"""Static guards for container-image package-manager invariants."""


def test_arch_family_images_do_not_perform_partial_upgrades(repo):
    """Refreshing pacman metadata without upgrading the base image can mix
    Python and Expat ABIs, making pyexpat fail before the suite reaches project
    code. Every Arch-family dependency install must be a full sync upgrade.
    """
    containers = repo / "tests/containers"
    for distro in ("arch", "cachyos", "endeavouros", "garuda", "manjaro"):
        text = (containers / f"Dockerfile.{distro}").read_text()
        assert "pacman -Syu --noconfirm --needed" in text, distro
        assert "pacman -Sy --noconfirm --needed" not in text, distro


def test_retired_gentoo_has_no_ci_or_vm_targets(repo):
    for path in (repo / ".github/workflows").glob("*.yml"):
        assert "gentoo" not in path.read_text().lower(), path
    assert not list((repo / "tests/containers").glob("*gentoo*"))
    assert not list((repo / ".vm/cloud-init").glob("*gentoo*"))
    assert "continue-on-error:" not in (repo / ".github/workflows/test.yml").read_text()


def test_debian_container_uses_supported_sdk_and_both_runners(repo):
    text = (repo / "tests/containers/Dockerfile.debian").read_text()
    assert "ARG DEBIAN_SUITE=testing-slim" in text
    assert "FROM debian:${DEBIAN_SUITE}" in text
    assert 'CMD ["python3", "tests/containers/run_in_container.py"]' in text
    assert "          - debian\n" in (repo / ".github/workflows/test.yml").read_text()
    assert "    debian\n" in (repo / "tests/containers/run_matrix.sh").read_text()
    # Neon uses different names for these SDKs; Debian must use its own.
    for package in ("libplasmaactivities-dev", "libplasmaactivitiesstats-dev",
                    "qt6-wayland-dev", "libxcb-composite0-dev", "libxcb-randr0-dev",
                    "libxcb-res0-dev", "libxcb-shm0-dev", "libxcb-sync-dev"):
        assert package in text
