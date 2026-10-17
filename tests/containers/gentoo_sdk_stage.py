"""Run one resumable SDK stage inside the dedicated Gentoo build container."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    marker = Path("/etc/mttkde-sdk-build")
    if (os.environ.get("MTTKDE_GENTOO_SDK_BUILD") != "1"
            or not marker.is_file() or marker.read_text().strip() != "gentoo-sdk"):
        raise SystemExit("This helper only runs inside the SDK build container")
    packages = json.loads(Path("/usr/local/share/gentoo-sdk-packages.json").read_text())
    phase = sys.argv[1]
    if phase not in packages:
        raise SystemExit(f"Unknown SDK phase: {phase}")
    if phase == "verify":
        for atoms in packages.values():
            for atom in atoms:
                subprocess.run(["portageq", "has_version", "/", atom], check=True)
        subprocess.run(["qmake6", "-query", "QT_VERSION"], check=True)
        if not Path("/var/db/repos/gentoo/profiles/repo_name").is_file():
            raise SystemExit("Gentoo repository metadata is missing")
        return 0

    # Reconsider USE/dependency changes while keeping already-correct packages.
    # buildpkg preserves completed source builds even if a later package fails.
    env = os.environ.copy()
    env["FEATURES"] = env.get("FEATURES", "") + " buildpkg binpkg-multi-instance"
    env["MAKEOPTS"] = f"-j{max(1, min(4, os.cpu_count() or 1))}"
    command = [
        "emerge", "--update", "--newuse", "--deep", "--with-bdeps=y",
        "--autounmask", "--autounmask-write", "--autounmask-continue=y",
        "--getbinpkg", "--usepkg", "--backtrack=100",
        "--autounmask-backtrack=y", "--binpkg-respect-use=y",
        "--binpkg-changed-deps=y", "--keep-going=y", *packages[phase],
    ]
    result = subprocess.run(command, env=env)
    # Keep package build logs, but do not push gigabytes of failed work dirs.
    logs = Path("/var/log/mttkde-sdk")
    logs.mkdir(parents=True, exist_ok=True)
    work = Path("/var/tmp/portage")
    if work.is_dir():
        for log in work.glob("*/*/temp/build.log"):
            shutil.copyfile(log, logs / ("-".join(log.relative_to(work).parts[:2]) + ".log"))
        shutil.rmtree(work)
        work.mkdir()
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
