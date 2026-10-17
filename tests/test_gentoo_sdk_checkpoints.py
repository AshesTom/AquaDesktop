"""Checkpoint recovery, stage invalidation and publication safety."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import uuid

import pytest


@pytest.fixture
def sdk(repo, monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("gentoo_sdk_checkpoint", repo / "tests/containers/gentoo_sdk_checkpoint.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module


class Docker:
    def __init__(self, sdk, code=0, running=False):
        self.sdk, self.code, self.running = sdk, code, running
        self.images = {}
        self.calls = []

    def image(self, phase, status="complete"):
        key = self.sdk.checkpoint_keys("test")[phase]
        name = f"example/sdk:checkpoint-{key}-{phase}"
        self.images[name] = {f"{self.sdk.LABEL}.key": key, f"{self.sdk.LABEL}.phase": phase,
                             f"{self.sdk.LABEL}.configuration": self.sdk.checkpoint_keys("test")["configured"],
                             f"{self.sdk.LABEL}.status": status}
        if phase != "configured":
            previous = self.sdk.PHASES[self.sdk.PHASES.index(phase) - 1]
            self.images[name][f"{self.sdk.LABEL}.parent"] = self.sdk.checkpoint_keys("test")[previous]
        return name

    def run(self, *args, **kwargs):
        self.calls.append(args)
        output = ""
        if args[1] == "inspect":
            output = json.dumps({"Running": self.running, "ExitCode": self.code}) if ".State" in args[3] else json.dumps(self.images[args[-1]])
        elif args[1] == "commit":
            self.images[args[-1]] = dict(arg[6:].split("=", 1) for arg in args if arg.startswith("LABEL "))
        elif args[1] == "tag":
            self.images[args[-1]] = self.images[args[-2]].copy()
        elif args[1] == "build":
            name = args[args.index("-t") + 1]
            self.images[name] = dict(args[i + 1].split("=", 1) for i, arg in enumerate(args) if arg == "--label")
        return subprocess.CompletedProcess(args, 0, output, "")


def install_fake(sdk, monkeypatch, **kwargs):
    docker = Docker(sdk, **kwargs)
    monkeypatch.setattr(sdk, "run", docker.run)
    monkeypatch.setattr(sdk, "pull", lambda image: image in docker.images)
    return docker


def test_failed_stage_persists_before_reporting_failure_and_resumes(sdk, monkeypatch):
    docker = install_fake(sdk, monkeypatch, code=23)
    previous = docker.image("toolchain")
    with pytest.raises(SystemExit) as failure:
        sdk.build("example/sdk", "test", "qtbase")
    assert failure.value.code == 23
    current = next(image for image in docker.images if image.endswith("-qtbase"))
    assert docker.images[current][f"{sdk.LABEL}.status"] == "partial"
    assert ("docker", "push", current) in docker.calls
    assert previous in next(call for call in docker.calls if call[1] == "create")
    assert not any(call[-1].endswith(":latest") for call in docker.calls)
    docker.calls.clear()
    docker.code = 0
    sdk.build("example/sdk", "test", "qtbase")
    assert current in next(call for call in docker.calls if call[1] == "create")
    assert docker.images[current][f"{sdk.LABEL}.status"] == "complete"


def test_complete_stage_does_not_run_packages_again(sdk, monkeypatch):
    docker = install_fake(sdk, monkeypatch)
    docker.image("qtbase")
    sdk.build("example/sdk", "test", "qtbase")
    assert all(call[1] == "inspect" for call in docker.calls)


def test_missing_predecessor_does_not_restart_from_stage3(sdk, monkeypatch):
    docker = install_fake(sdk, monkeypatch)
    with pytest.raises(RuntimeError, match="Complete the qtbase"):
        sdk.build("example/sdk", "test", "qttools")
    assert not docker.calls


def test_running_package_manager_is_never_committed(sdk, monkeypatch):
    docker = install_fake(sdk, monkeypatch, running=True)
    docker.image("toolchain")
    with pytest.raises(RuntimeError, match="running package manager"):
        sdk.build("example/sdk", "test", "qtbase")
    assert not any(call[1] in {"commit", "push", "tag"} for call in docker.calls)


@pytest.mark.parametrize("code", [0, 23])
def test_only_successful_sdk_verification_promotes_latest(sdk, monkeypatch, code):
    docker = install_fake(sdk, monkeypatch, code=code)
    docker.image("plasma")
    if code:
        with pytest.raises(SystemExit):
            sdk.build("example/sdk", "test", "verify")
    else:
        sdk.build("example/sdk", "test", "verify")
    promotions = [call for call in docker.calls if call[1] == "tag" and call[-1].endswith(":latest")]
    assert bool(promotions) == (code == 0)
    if promotions:
        assert promotions[0][-1] == "example/sdk:latest"


def test_later_recipe_change_preserves_earlier_stage_keys(sdk, monkeypatch, tmp_path):
    import shutil
    source = tmp_path / "recipes"
    shutil.copytree(sdk.CONTAINERS, source)
    monkeypatch.setattr(sdk, "CONTAINERS", source)
    before = sdk.checkpoint_keys("test")
    path = source / "gentoo-sdk-packages.json"
    data = json.loads(path.read_text())
    data["plasma"].append("example/new-sdk-dependency")
    path.write_text(json.dumps(data))
    after = sdk.checkpoint_keys("test")
    assert all(before[p] == after[p] for p in sdk.PHASES[:5])
    assert all(before[p] != after[p] for p in ("plasma", "verify"))


def test_registry_network_error_does_not_discard_checkpoint(sdk, monkeypatch):
    monkeypatch.setattr(sdk, "run", lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "network timeout"))
    with pytest.raises(RuntimeError, match="network timeout"):
        sdk.pull("example/sdk:checkpoint")


def test_changed_stage_recipe_recovers_completed_packages(sdk, monkeypatch):
    docker = install_fake(sdk, monkeypatch)
    docker.image("toolchain")
    prior = docker.image("qtbase", "partial")
    recovery = "example/sdk:recovery-test-qtbase"
    docker.images[recovery] = docker.images.pop(prior)
    docker.images[recovery][f"{sdk.LABEL}.key"] = "previous-recipe-key"
    sdk.build("example/sdk", "test", "qtbase")
    assert recovery in next(call for call in docker.calls if call[1] == "create")


@pytest.mark.parametrize("changed", ["configuration", "parent"])
def test_changed_configuration_does_not_resume_incompatible_stage(sdk, monkeypatch, changed):
    docker = install_fake(sdk, monkeypatch)
    previous = docker.image("toolchain")
    prior = docker.image("qtbase", "partial")
    recovery = "example/sdk:recovery-test-qtbase"
    docker.images[recovery] = docker.images.pop(prior)
    docker.images[recovery][f"{sdk.LABEL}.{changed}"] = "different-predecessor"
    sdk.build("example/sdk", "test", "qtbase")
    assert previous in next(call for call in docker.calls if call[1] == "create")


def test_configuration_fix_reuses_furthest_recovery_image(sdk, monkeypatch):
    docker = install_fake(sdk, monkeypatch)
    earlier = docker.image("qttools", "partial")
    recovery = "example/sdk:recovery-test-qttools"
    docker.images[recovery] = docker.images.pop(earlier)
    docker.images[recovery][f"{sdk.LABEL}.configuration"] = "old-configuration"
    sdk.build("example/sdk", "test", "configured")
    command = next(call for call in docker.calls if call[1] == "build")
    assert f"GENTOO_BASE={recovery}" in command


def test_package_stage_refuses_execution_outside_builder(repo):
    import sys
    env = os.environ.copy()
    env.pop("MTTKDE_GENTOO_SDK_BUILD", None)
    result = subprocess.run([sys.executable, str(repo / "tests/containers/gentoo_sdk_stage.py"), "qtbase"],
                            env=env, text=True, capture_output=True)
    assert result.returncode != 0
    assert "only runs inside" in result.stderr


def test_real_docker_checkpoint_keeps_completed_work(sdk, monkeypatch, tmp_path):
    """Opt-in native persistence test; only registry transfer is replaced locally."""
    base = os.environ.get("MTTKDE_DOCKER_TEST_IMAGE")
    if not base:
        pytest.skip("Set MTTKDE_DOCKER_TEST_IMAGE to an existing Python-capable Docker image")
    registry = "mttkde-checkpoint-test-" + uuid.uuid4().hex[:12]
    keys = sdk.checkpoint_keys("native")
    predecessor = f"{registry}:checkpoint-{keys['toolchain']}-toolchain"
    target = f"{registry}:checkpoint-{keys['qtbase']}-qtbase"
    (tmp_path / "stage.py").write_text("""from pathlib import Path
marker = Path('/completed-package')
if not marker.exists():
    marker.write_text('built once')
    raise SystemExit(23)
assert marker.read_text() == 'built once'
Path('/resumed-successfully').write_text('yes')
""")
    (tmp_path / "Dockerfile").write_text(f"FROM {base}\nCOPY stage.py /usr/local/libexec/gentoo_sdk_stage.py\n")
    original = sdk.run

    def local_run(*args, **kwargs):
        if args[:2] == ("docker", "push"):
            return subprocess.CompletedProcess(args, 0, "", "")
        return original(*args, **kwargs)

    monkeypatch.setattr(sdk, "run", local_run)
    monkeypatch.setattr(sdk, "pull", lambda name: original("docker", "image", "inspect", name, check=False, capture=True).returncode == 0)
    try:
        original("docker", "build", "--network=none", "--label", f"{sdk.LABEL}.key={keys['toolchain']}",
                 "--label", f"{sdk.LABEL}.phase=toolchain", "--label", f"{sdk.LABEL}.status=complete",
                 "-t", predecessor, str(tmp_path))
        with pytest.raises(SystemExit) as failure:
            sdk.build(registry, "native", "qtbase")
        assert failure.value.code == 23
        assert sdk.state(target, keys["qtbase"], "qtbase") == "partial"
        sdk.build(registry, "native", "qtbase")
        assert sdk.state(target, keys["qtbase"], "qtbase") == "complete"
        original("docker", "run", "--rm", "--network=none", target, "test", "-f", "/resumed-successfully")
    finally:
        original("docker", "image", "rm", "-f", target, predecessor,
                 f"{registry}:recovery-native-qtbase", check=False)
