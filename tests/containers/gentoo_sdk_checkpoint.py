"""Persist completed SDK stages and recover failed stages from GHCR images."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
CONTAINERS = ROOT / "tests/containers"
PHASES = ("configured", "toolchain", "qtbase", "qttools", "frameworks", "plasma", "verify")
LABEL = "org.mttkde.sdk"


def run(*args, check=True, capture=False):
    return subprocess.run(args, check=check, text=True, capture_output=capture)


def pull(image):
    result = run("docker", "pull", image, check=False, capture=True)
    if result.returncode == 0:
        return True
    message = result.stdout + result.stderr
    if any(marker in message.lower() for marker in ("manifest unknown", "manifest not found", "name unknown")):
        return False
    raise RuntimeError(f"Cannot read checkpoint {image}: {message}")


def checkpoint_keys(epoch):
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,31}", epoch):
        raise ValueError("Checkpoint epoch must be a short lowercase tag component")
    dockerfile = (CONTAINERS / "Dockerfile.gentoo-base").read_bytes().split(b"FROM configured AS sdk")[0]
    digest = hashlib.sha256(dockerfile + (CONTAINERS / "gentoo_sdk_stage.py").read_bytes())
    keys = {"configured": f"{epoch}-{digest.hexdigest()[:16]}"}
    packages = json.loads((CONTAINERS / "gentoo-sdk-packages.json").read_text())
    for phase in PHASES[1:]:
        digest.update(json.dumps([phase, packages[phase]], sort_keys=True).encode())
        keys[phase] = f"{epoch}-{digest.hexdigest()[:16]}"
    return keys


def state(image, key, phase):
    labels = json.loads(run("docker", "inspect", "--format", "{{json .Config.Labels}}", image, capture=True).stdout)
    if not labels or labels.get(f"{LABEL}.key") != key or labels.get(f"{LABEL}.phase") != phase:
        raise RuntimeError(f"Checkpoint metadata does not match {phase}: {image}")
    status = labels.get(f"{LABEL}.status")
    if status not in {"complete", "partial"}:
        raise RuntimeError(f"Invalid checkpoint status: {image}")
    return status


def publish(image, registry, epoch, phase):
    run("docker", "push", image)
    # This alias preserves completed package work even after a recipe fix
    # changes the content-addressed stage key. It is never a CI base image.
    recovery = f"{registry}:recovery-{epoch}-{phase}"
    run("docker", "tag", image, recovery)
    run("docker", "push", recovery)


def build(registry, epoch, phase):
    if not re.fullmatch(r"[a-z0-9][a-z0-9./_-]+", registry):
        raise ValueError("Invalid image repository")
    keys = checkpoint_keys(epoch)
    image = f"{registry}:checkpoint-{keys[phase]}-{phase}"
    exists = pull(image)
    status = state(image, keys[phase], phase) if exists else None
    if status == "complete":
        print(f"Reuse completed {phase}: {image}", flush=True)
    elif phase == "configured":
        seed = None
        # A USE/profile fix must not discard hours of completed source builds.
        # Reapply the new configuration over the furthest recovery image.
        for earlier in reversed(PHASES[1:]):
            candidate = f"{registry}:recovery-{epoch}-{earlier}"
            if pull(candidate):
                seed = candidate
                break
        if seed is None:
            seed = f"{registry}:latest"
            if not pull(seed):
                seed = "gentoo/stage3:systemd"
        run("docker", "build", "--target", "configured", "--build-arg", f"GENTOO_BASE={seed}",
            "--label", f"{LABEL}.key={keys[phase]}", "--label", f"{LABEL}.phase={phase}",
            "--label", f"{LABEL}.configuration={keys['configured']}",
            "--label", f"{LABEL}.status=complete", "-f", str(CONTAINERS / "Dockerfile.gentoo-base"),
            "-t", image, str(ROOT))
        publish(image, registry, epoch, phase)
    else:
        if status == "partial":
            base = image
            print(f"Resume installed packages from {image}", flush=True)
        else:
            previous = PHASES[PHASES.index(phase) - 1]
            base = f"{registry}:checkpoint-{keys[previous]}-{previous}"
            if not pull(base) or state(base, keys[previous], previous) != "complete":
                raise RuntimeError(f"Complete the {previous} stage before {phase}")
            recovery = f"{registry}:recovery-{epoch}-{phase}"
            if pull(recovery):
                labels = json.loads(run("docker", "inspect", "--format", "{{json .Config.Labels}}", recovery, capture=True).stdout)
                if ((labels or {}).get(f"{LABEL}.configuration") == keys["configured"]
                        and labels.get(f"{LABEL}.parent") == keys[previous]):
                    if labels.get(f"{LABEL}.phase") != phase or labels.get(f"{LABEL}.status") not in {"complete", "partial"}:
                        raise RuntimeError("Invalid recovery image metadata")
                    base = recovery
        container = "mttkde-sdk-" + uuid.uuid4().hex[:12]
        run("docker", "create", "--name", container, "--env", "MTTKDE_GENTOO_SDK_BUILD=1", base,
            "timeout", "--signal=TERM", "--kill-after=120", "18000",
            "python3", "/usr/local/libexec/gentoo_sdk_stage.py", phase)
        try:
            # A later-stage recipe change must not invalidate earlier images.
            run("docker", "cp", str(CONTAINERS / "gentoo-sdk-packages.json"),
                f"{container}:/usr/local/share/gentoo-sdk-packages.json")
            run("docker", "start", "--attach", container, check=False)
            finished = json.loads(run("docker", "inspect", "--format", "{{json .State}}", container, capture=True).stdout)
            if finished["Running"]:
                raise RuntimeError("Refusing to checkpoint a running package manager")
            code = finished["ExitCode"]
            outcome = "complete" if code == 0 else "partial"
            run("docker", "commit", "--change", f"LABEL {LABEL}.key={keys[phase]}",
                "--change", f"LABEL {LABEL}.phase={phase}",
                "--change", f"LABEL {LABEL}.configuration={keys['configured']}",
                "--change", f"LABEL {LABEL}.parent={keys[PHASES[PHASES.index(phase) - 1]]}",
                "--change", f"LABEL {LABEL}.status={outcome}", container, image)
            publish(image, registry, epoch, phase)
            print(f"Saved {outcome} checkpoint: {image}", flush=True)
            if code:
                raise SystemExit(code)
        finally:
            logs = ROOT / "build/gentoo-sdk-logs" / phase
            logs.mkdir(parents=True, exist_ok=True)
            run("docker", "cp", f"{container}:/var/log/mttkde-sdk/.", str(logs), check=False)
            run("docker", "rm", "-f", container, check=False)

    if phase == "verify":
        run("docker", "tag", image, f"{registry}:latest")
        run("docker", "push", f"{registry}:latest")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--epoch", required=True)
    parser.add_argument("--phase", choices=PHASES, required=True)
    args = parser.parse_args()
    build(args.registry, args.epoch, args.phase)
