from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from theme_variants import SUFFIX

from distro import is_debian_family, qt6_plugins_dir, user_service_manager_command
from steps._helpers import (
    DATA_HOME, HOME, build_dir, cmake_build, fail, have, info, kw_write, offline, ok,
    reinstall, install_reduced_variant, sudo_install_file, sudo_remove, warn,
)
from utils import kw_read, run_user

DEST_DIR = HOME / ".config/Kvantum/mac-tahoe-liquid-kde"
DEST_DIR_DARK = HOME / ".config/Kvantum/mac-tahoe-liquid-kdeDark"

_THEMES = ("mac-tahoe-liquid-kde", "mac-tahoe-liquid-kdeDark")
# The untouched themes: the theme switch rewrites the copies above from
# them in the user's accent colour (theme_switch.apply_kvantum_accent).
ORIGINALS_DIR = DATA_HOME / "mac-tahoe-liquid-kde/kvantum"
MENU_ICONS_KEY = "ShowIconsInMenuItems"

ENGINE_VERSION = "1.1.8"
ENGINE_COMMIT = "058534fc15d1798c3887590166f05c598e8e946c"
ENGINE_SHA256 = "7aa9099345e48048ebdad768f583944ac042f87b216fa0b26a169c7e05425047"
ENGINE_ARCHIVE = offline("kvantum-engine", f"Kvantum-{ENGINE_VERSION}.tar.xz")
ENGINE_WORK = build_dir("kvantum-engine")
ENGINE_SOURCE = ENGINE_WORK / f"Kvantum-{ENGINE_VERSION}"
ENGINE_BUILD = ENGINE_WORK / "build"
ENGINE_MARKER = Path("/usr/share/mac-tahoe-liquid-kde/kvantum-engine.json")
# AquaDesktop's patches (src/offline/kvantum-engine/patches): KDE's accent
# colour recolours the theme as it loads, live; macOS menu shortcuts.
ENGINE_PATCHES = offline("kvantum-engine", "patches")
# The patched engine for every distribution, in the user's data directory:
# Qt prefers QT_PLUGIN_PATH (set by the Plasma environment script below)
# over its own plugin directory, so the distro's file is never replaced.
USER_PLUGIN_ROOT = DATA_HOME / "mac-tahoe-liquid-kde/qt6/plugins"
USER_ENGINE = USER_PLUGIN_ROOT / "styles/libkvantum.so"
ENV_TEMPLATE = offline("plasma-env/mac-tahoe-kvantum.sh.in")
ENV_MARKER = "# Managed by mac-tahoe-liquid-kde: Tahoe Kvantum engine\n"
ENGINE_LICENSE = Path(
    "/usr/share/licenses/mac-tahoe-liquid-kde/Kvantum.txt"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _engine_destination() -> Path:
    return qt6_plugins_dir() / "styles/libkvantum.so"


def _marker_plugin_hashes(marker: object) -> set[str]:
    """Return plugin digests that a valid marker currently owns.

    A reinstall publishes a pending marker before replacing the plugin.  That
    marker accepts both the old and new digest, so an interruption on either
    side of the atomic plugin rename cannot strand an unowned system file.
    Final markers retain the original single-digest schema for compatibility.
    """
    if not isinstance(marker, dict):
        return set()

    def valid_digest(value: object) -> bool:
        return (
            isinstance(value, str)
            and len(value) == 64
            and all(char in "0123456789abcdef" for char in value)
        )

    hashes: set[str] = set()
    current = marker.get("plugin_sha256")
    if valid_digest(current):
        hashes.add(current)
    if marker.get("state") == "pending":
        previous = marker.get("previous_plugin_sha256")
        if valid_digest(previous):
            hashes.add(previous)
    return hashes


def _read_engine_marker() -> dict | None:
    try:
        marker = json.loads(ENGINE_MARKER.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return marker if isinstance(marker, dict) else None


def _engine_matches_ownership_marker() -> bool:
    destination = _engine_destination()
    if (
        not ENGINE_MARKER.is_file()
        or not destination.is_file()
        or destination.is_symlink()
    ):
        return False
    try:
        return _sha256(destination) in _marker_plugin_hashes(
            _read_engine_marker()
        )
    except OSError:
        return False


def _bundled_engine_required() -> bool:
    """Whether this host needs our offline Qt 6 engine.

    Debian-family releases can lag on Qt 5-only Kvantum packages. Never
    overwrite an unmarked distro-owned Qt 6 plugin; keep rebuilding only a
    plugin whose ownership marker and digest prove that we installed it.
    """
    if not is_debian_family():
        return False
    destination = _engine_destination()
    if not destination.is_file():
        return True
    return _engine_matches_ownership_marker()


def deps():
    # The patched engine is built everywhere (see USER_ENGINE).
    if is_debian_family():
        # Theme selection has a kwriteconfig6 fallback and does not require
        # Kvantum Manager.
        return [
            "qmake6:qt6-base",
            "qt6-svg-cmake:qt6-svg",
            "cmake",
            "make",
            "g++:gcc",
            "patch",
            "kf6-windowsystem-cmake:kwindowsystem",
            "x11-cmake:libx11",
            "xext-cmake:libxext",
        ]
    return [
        "qmake6:qt6-base",
        "qt6-svg-cmake:qt6-svg",
        "cmake",
        "make",
        "g++:gcc",
        "patch",
        "kf6-windowsystem-cmake:kwindowsystem",
        "x11-cmake:libx11",
        "xext-cmake:libxext",
        "kvantummanager:kvantum",
    ]


def _extract_bundled_engine() -> bool:
    if not ENGINE_ARCHIVE.is_file():
        fail(f"Kvantum Qt 6 source archive missing: {ENGINE_ARCHIVE}")
        return False
    actual = _sha256(ENGINE_ARCHIVE)
    if actual != ENGINE_SHA256:
        fail(
            "Kvantum Qt 6 source checksum mismatch "
            f"(expected {ENGINE_SHA256}, got {actual})"
        )
        return False

    staging = ENGINE_WORK / ".extracting"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(ENGINE_ARCHIVE, "r:xz") as archive:
            members = archive.getmembers()
            if not members:
                raise ValueError("archive is empty")
            for member in members:
                relative = PurePosixPath(member.name)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or not relative.parts
                    or relative.parts[0] != ENGINE_SOURCE.name
                ):
                    raise ValueError(f"unsafe archive path: {member.name}")
                if not (member.isfile() or member.isdir()):
                    raise ValueError(f"unsafe archive member: {member.name}")
            archive.extractall(staging, members=members)
        extracted = staging / ENGINE_SOURCE.name
        if not (extracted / "Kvantum/CMakeLists.txt").is_file():
            raise ValueError("Kvantum/CMakeLists.txt missing from archive")
        _apply_patches(extracted)
        shutil.rmtree(ENGINE_SOURCE, ignore_errors=True)
        extracted.replace(ENGINE_SOURCE)
        return True
    except (OSError, tarfile.TarError, ValueError, subprocess.SubprocessError) as exc:
        fail(f"Kvantum Qt 6 source archive rejected ({exc})")
        return False
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _apply_patches(source: Path) -> None:
    """AquaDesktop's patches, in order; any that does not apply cleanly
    rejects the source (raises)."""
    for patch in sorted(ENGINE_PATCHES.glob("*.patch")):
        result = subprocess.run(
            ["patch", "-p1", "--forward", "--batch", "--silent", "-d", str(source),
             "-i", str(patch)],
            check=False, capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            raise ValueError(f"{patch.name} does not apply: "
                             f"{(result.stdout + result.stderr).strip()[:200]}")


def build_artifacts() -> list[Path]:
    return [ENGINE_BUILD / "style/libkvantum.so"]


def build() -> None:
    if not _extract_bundled_engine():
        return
    cmake_build(
        ENGINE_SOURCE / "Kvantum",
        ENGINE_BUILD,
        f"Kvantum Qt 6 engine v{ENGINE_VERSION}",
        targets=("kvantum",),
    )


def _install_bundled_engine() -> bool:
    if not _bundled_engine_required():
        return True
    artifact = ENGINE_BUILD / "style/libkvantum.so"
    license_source = ENGINE_SOURCE / "Kvantum/COPYING"
    if not artifact.is_file() or not license_source.is_file():
        fail("Kvantum Qt 6 build artefacts missing")
        return False

    destination = _engine_destination()
    previous_hash: str | None = None
    if destination.is_file() and not destination.is_symlink():
        if not _engine_matches_ownership_marker():
            warn(
                "A distro/user-owned Kvantum Qt 6 engine appeared during the "
                "build — leaving it unchanged"
            )
            return True
        try:
            previous_hash = _sha256(destination)
        except OSError as exc:
            fail(f"Kvantum Qt 6 engine could not be read ({exc})")
            return False
    elif destination.exists() or destination.is_symlink():
        fail("Kvantum Qt 6 engine destination is not a regular owned file")
        return False

    # Prepare both marker states before any system mutation. The pending marker
    # is published first and recognizes the plugin on either side of its atomic
    # replacement. A crash or later copy failure therefore leaves enough proof
    # for the next install/uninstall to recover safely.
    plugin_hash = _sha256(artifact)
    marker_data = {
        "version": ENGINE_VERSION,
        "commit": ENGINE_COMMIT,
        "source_sha256": ENGINE_SHA256,
        "plugin_sha256": plugin_hash,
    }
    pending_data = {**marker_data, "state": "pending"}
    if previous_hash and previous_hash != plugin_hash:
        pending_data["previous_plugin_sha256"] = previous_hash
    pending_marker_source = ENGINE_WORK / "kvantum-engine.pending.json"
    final_marker_source = ENGINE_WORK / "kvantum-engine.json"
    try:
        final_marker_source.parent.mkdir(parents=True, exist_ok=True)
        pending_marker_source.write_text(
            json.dumps(pending_data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        final_marker_source.write_text(
            json.dumps(marker_data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        fail(f"Kvantum ownership marker could not be prepared ({exc})")
        return False

    if not sudo_install_file(
        pending_marker_source,
        ENGINE_MARKER,
        "Kvantum ownership transaction prepared",
    ):
        return False
    if not sudo_install_file(
        artifact, destination, f"Kvantum Qt 6 engine v{ENGINE_VERSION} installed"
    ):
        return False
    if not sudo_install_file(
        license_source, ENGINE_LICENSE, "Kvantum GPL-3.0 license installed"
    ):
        # Keep the pending marker and installed engine together. Removing the
        # new plugin here would also lose the previous version it atomically
        # replaced; the next run can safely finish or uninstall this state.
        return False

    if not sudo_install_file(
        final_marker_source, ENGINE_MARKER,
        "Kvantum bundled-source marker installed",
    ):
        # The pending marker already recognizes the installed digest. Retain it
        # as recovery state instead of creating an unmarked system plugin.
        return False
    return True


def kvantum_env_path() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
    return config_home / "plasma-workspace/env/mac-tahoe-kvantum.sh"


def _env_script_owned(path: Path) -> bool:
    try:
        return not path.is_symlink() and path.read_text(encoding="utf-8").startswith(ENV_MARKER)
    except (OSError, UnicodeError):
        return False


def _install_user_engine() -> None:
    """The patched engine in the user's data directory, and the Plasma
    environment script that puts it first in QT_PLUGIN_PATH (from the next
    login on)."""
    artifact = ENGINE_BUILD / "style/libkvantum.so"
    if not artifact.is_file():
        warn("Tahoe Kvantum engine not built — the distribution's engine stays in use")
        return
    try:
        USER_ENGINE.parent.mkdir(parents=True, exist_ok=True)
        staging = USER_ENGINE.with_name(USER_ENGINE.name + ".new")
        shutil.copy2(artifact, staging)
        # A running app keeps the old file mapped: replace, never rewrite.
        staging.replace(USER_ENGINE)
        env_path = kvantum_env_path()
        if env_path.exists() and not _env_script_owned(env_path):
            warn(f"{env_path} is not ours — leaving it; the Tahoe Kvantum engine "
                 "stays unused")
            return
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(
            ENV_TEMPLATE.read_text(encoding="utf-8")
            .replace("@PLUGIN_DIR@", shlex.quote(str(USER_PLUGIN_ROOT)))
            .replace("@PLUGIN@", shlex.quote(str(USER_ENGINE))),
            encoding="utf-8")
    except OSError as exc:
        warn(f"Tahoe Kvantum engine not installed ({exc})")
        return
    _export_to_running_session()
    ok("Tahoe Kvantum engine (accent colour, macOS shortcuts) — apps started "
       "from now on use it; log out once for the rest")


def _export_to_running_session(remove: bool = False) -> None:
    """The environment script only runs at login: give the running session's
    service manager and D-Bus activation the same QT_PLUGIN_PATH, so apps it
    starts from now on load the engine (or, on removal, no longer do)."""
    current = os.environ.get("QT_PLUGIN_PATH", "")
    parts = [p for p in current.split(":") if p and p != str(USER_PLUGIN_ROOT)]
    value = ":".join(parts if remove else [str(USER_PLUGIN_ROOT), *parts])
    commands = []
    manager = (user_service_manager_command("set-environment", f"QT_PLUGIN_PATH={value}") if value
               else user_service_manager_command("unset-environment", "QT_PLUGIN_PATH"))
    if manager:
        commands.append(manager)
    if have("dbus-update-activation-environment"):
        commands.append(["dbus-update-activation-environment", f"QT_PLUGIN_PATH={value}"])
    for command in commands:
        try:
            run_user(command, check=False, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass


def _remove_user_engine() -> None:
    env_path = kvantum_env_path()
    if _env_script_owned(env_path):
        env_path.unlink(missing_ok=True)
    _export_to_running_session(remove=True)
    # USER_PLUGIN_ROOT is <data>/mac-tahoe-liquid-kde/qt6/plugins.
    shutil.rmtree(USER_PLUGIN_ROOT.parent, ignore_errors=True)


def _install_one(name: str) -> None:
    src = offline("kvantum/mac-tahoe-liquid-kde")
    dst = (DEST_DIR_DARK if "Dark" in name else DEST_DIR)
    dst.mkdir(parents=True, exist_ok=True)
    ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
    for ext in (".kvconfig", ".svg"):
        f = src / f"{name}{ext}"
        if f.is_file():
            shutil.copy2(f, dst / f.name)
            shutil.copy2(f, ORIGINALS_DIR / f.name)
        else:
            warn(f"Kvantum file {f.name} not found")


def install() -> None:
    src = offline("kvantum/mac-tahoe-liquid-kde")
    if not src.is_dir():
        fail(f"Kvantum theme source not found at {src}")
        return

    if not _install_bundled_engine():
        return
    _install_user_engine()

    existed = any(
        (d.is_dir() and any(d.glob("*.kvconfig")))
         for d in (DEST_DIR, DEST_DIR_DARK)
    )

    for name in _THEMES:
        _install_one(name)
        destination = DEST_DIR_DARK if "Dark" in name else DEST_DIR
        install_reduced_variant(src, destination.with_name(name + SUFFIX), "kvantum", name)

    if any((DEST_DIR / f"{_THEMES[0]}{e}").is_file() for e in (".kvconfig", ".svg")):
        ok("mac-tahoe-liquid-kde theme (installed)")
    else:
        fail("mac-tahoe-liquid-kde theme (copy failed)")
        return

    if any((DEST_DIR_DARK / f"{_THEMES[1]}{e}").is_file() for e in (".kvconfig", ".svg")):
        if existed:
            reinstall("mac-tahoe-liquid-kdeDark theme")
        else:
            ok("mac-tahoe-liquid-kdeDark theme (installed)")
    else:
        fail("mac-tahoe-liquid-kdeDark theme (copy failed)")
        return

    if kw_write("--file", "kdeglobals", "--group", "KDE",
                "--key", "widgetStyle", "kvantum"):
        ok("Widget style installed")
    else:
        warn("Widget style not applied — kwriteconfig6 unavailable "
             "(install plasma-workspace or your distro's equivalent)")
    # Qt Quick / Kirigami apps draw their own controls; give them the same
    # macOS rows and switches (System Settings, Discover...).
    # macOS menus show no icons, only the label and the right-aligned
    # shortcut. KDE's platform theme hides QWidget menu icons from this key,
    # and kded's gtkconfig mirrors it into GTK's gtk-menu-images.
    if kw_write("--file", "kdeglobals", "--group", "KDE",
                "--key", MENU_ICONS_KEY, "false"):
        ok("Menus without icons")
    from steps import _qqc2_style
    _qqc2_style.install()
    info("Kvantum Qt styling installed")


def _remove_bundled_engine() -> None:
    if not ENGINE_MARKER.is_file():
        return
    destination = _engine_destination()
    try:
        marker = json.loads(ENGINE_MARKER.read_text(encoding="utf-8"))
    except OSError as exc:
        fail(
            "Kvantum ownership marker could not be read — retaining the "
            f"engine, marker, and license for recovery ({exc})"
        )
        return
    except (ValueError, TypeError) as exc:
        fail(
            "Kvantum ownership marker is invalid — retaining the engine, "
            f"marker, and license for recovery ({exc})"
        )
        return
    owned_hashes = _marker_plugin_hashes(marker)
    if not owned_hashes:
        fail(
            "Kvantum ownership marker has no valid plugin digest — retaining "
            "the engine, marker, and license for recovery"
        )
        return
    owned = False
    if destination.is_file() and not destination.is_symlink() and owned_hashes:
        try:
            owned = _sha256(destination) in owned_hashes
        except OSError as exc:
            fail(
                "Kvantum Qt 6 engine ownership could not be verified — "
                f"retaining its marker and license for recovery ({exc})"
            )
            return

    if owned:
        removed = sudo_remove(destination, "bundled Kvantum Qt 6 engine")
        if not removed and destination.exists():
            fail(
                "Kvantum Qt 6 engine could not be removed — retaining its "
                "ownership marker and license for recovery"
            )
            return
    elif destination.exists() or destination.is_symlink():
        warn(
            "Kvantum Qt 6 engine changed since installation — leaving the "
            "distro/user-owned plugin in place"
        )
    sudo_remove(ENGINE_MARKER, "Kvantum bundled-source marker")
    sudo_remove(ENGINE_LICENSE, "Kvantum bundled-source license")


def uninstall() -> None:
    for directory in (DEST_DIR, DEST_DIR_DARK):
        shutil.rmtree(directory.with_name(directory.name + SUFFIX), ignore_errors=True)
    any_was_installed = False
    for d in (DEST_DIR, DEST_DIR_DARK):
        if d.is_dir():
            any_was_installed = True
    if any_was_installed:
        if kw_write("--file", "kdeglobals", "--group", "KDE",
                    "--key", "widgetStyle", "Breeze"):
            ok("Widget style reset to Breeze")
        if have("kvantummanager"):
            env = os.environ.copy()
            env["QT_QPA_PLATFORM"] = "offscreen"
            run_user(
                ["kvantummanager", "--set", "Default"],
                check=False, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        for d in (DEST_DIR, DEST_DIR_DARK):
            try:
                shutil.rmtree(d)
            except OSError:
                pass
    shutil.rmtree(ORIGINALS_DIR, ignore_errors=True)
    if any(d.is_dir() for d in (DEST_DIR, DEST_DIR_DARK)):
        fail("MacTahoeLiquidKde themes (some leftovers)")
    elif any_was_installed:
        ok("MacTahoeLiquidKde themes removed")
    else:
        ok("MacTahoeLiquidKde themes (not installed)")
    # Back to KDE's default (icons shown) only if the value is still ours.
    if kw_read("kdeglobals", "KDE", MENU_ICONS_KEY) == "false":
        kw_write("--file", "kdeglobals", "--group", "KDE",
                 "--key", MENU_ICONS_KEY, "--delete")
    from steps import _qqc2_style
    _qqc2_style.uninstall()
    _remove_bundled_engine()
    _remove_user_engine()
    shutil.rmtree(ENGINE_WORK, ignore_errors=True)
    info("Kvantum Qt styling removed")
