"""Window and Dock glass: upstream's Acrylic Glass KWin effect (liquidglass).

AquaDesktop: Acrylic Glass replaces Better Blur DX, which earlier AquaDesktop
releases installed; its plugin and settings are migrated away on install.
The glass styles (tahoe, frosted) write the material from theme_switch.py.
"""

import hashlib
import json
import re
import subprocess
import time
import uuid
from pathlib import Path

from distro import qt6_plugins_dir
from steps._helpers import (
    build_dir, cmake_build, fail, info, kw_write, ok, offline, qdbus_call,
    sudo_install_file, sudo_remove, warn, _as_root,
)
from utils import have, qdbus_cmd, run_user
from theme_switch import default_wallpaper

SRC = offline("kwin-effects/acrylic-glass")
BUILD = build_dir("kwin-effects/acrylic-glass")
HOME = Path.home()
LEGACY_USER_PLUGIN_DIR = HOME / ".local/lib/qt6/plugins"


def deps():
    return [
        "qmake6:qt6-base",
        "qt6-gui-cmake:qt6-base",
        "qt6-uitools-cmake:qt6-tools",
        "cmake",
        "ecm:extra-cmake-modules",
        "make",
        "g++:gcc",
        "pkg-config:pkgconf",
        # KF6 components required by the acrylic-glass CMakeLists.
        "kf6-config-cmake:kconfig",
        "kf6-configwidgets-cmake:kconfigwidgets",
        "kf6-coreaddons-cmake:kcoreaddons",
        "kf6-crash-cmake:kcrash",
        "kf6-globalaccel-cmake:kglobalaccel",
        "kf6-i18n-cmake:ki18n",
        "kf6-kio-cmake:kio",
        "kf6-service-cmake:kservice",
        "kf6-notifications-cmake:knotifications",
        "kf6-widgetsaddons-cmake:kwidgetsaddons",
        "kf6-windowsystem-cmake:kwindowsystem",
        "kf6-guiaddons-cmake:kguiaddons",
        "kf6-kcmutils-cmake:kcmutils",
        # KWin (Wayland) is mandatory: the effect refuses to configure
        # if neither GLASS_WAYLAND nor GLASS_X11 ends up enabled.
        "kwin-cmake:kwin",
        "kdecoration-cmake:kdecoration",
        # XCB is REQUIRED even with the X11 path off — the Wayland code uses it.
        "epoxy-cmake:libepoxy",
        "x11-cmake:libx11",
        "xcb-cmake:libxcb",
        # Extension headers included transitively by KWin's public SDK.
        "xcb-composite-cmake:libxcb",
        "xcb-randr-cmake:libxcb",
        "xcb-res-cmake:libxcb",
        "xcb-shm-cmake:libxcb",
        "xcb-sync-cmake:libxcb",
        # KWin 6.7+ exports find_dependency(Vulkan), so find_package(KWin)
        # fails at configure time without these — even on non-Vulkan machines.
        "vulkan-loader-cmake:vulkan-icd-loader",
        "vulkan-headers-cmake:vulkan-headers",
    ]


def build_artifacts() -> list[Path]:
    return [
        BUILD / "src/liquidglass.so",
        BUILD / "src/kcm/kwin_liquidglass_config.so",
    ]


def _plugin_dir() -> Path:
    """Kept by name for preflight's _enumerate_destinations(); delegates to
    the shared qt6_plugins_dir() discovery (same raise-on-missing contract)."""
    return qt6_plugins_dir()


def build() -> None:
    if not (SRC / "CMakeLists.txt").is_file():
        return
    # AquaDesktop: builds must not touch the live desktop, another
    # component can still fail and abort the install. The install phase
    # disables the conflicting blur effects.
    cmake_build(SRC, BUILD, "Acrylic Glass")


_CORNER_DEFAULTS = (
    ("WindowCornerRadius", "22"),
    ("DockCornerRadius", "20"),
    ("PopupCornerRadius", "6"),
)

def _edition_preset() -> dict[str, str]:
    # The KCM embeds this same file. Editions choose only the starting point.
    presets = json.loads((SRC / "src/presets.json").read_text())
    index = 2 if default_wallpaper() == "MacGoldenGate" else 1
    values = presets[index]["values"]
    return {key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in values.items()} | {"MaterialPreset": str(index)}


def _install_material_defaults() -> None:
    defaults = _edition_preset()
    if not have("kreadconfig6"):
        warn("Acrylic Glass material preserved — kreadconfig6 is unavailable")
        return
    sentinel = f"__mttkde_absent_{uuid.uuid4().hex}__"
    saved = {}
    # A failed read cannot authorize replacement of a customized material.
    try:
        for key in defaults:
            result = run_user(
                ["kreadconfig6", "--file", "kwinrc", "--group", "Effect-liquidglass",
                 "--key", key, "--default", sentinel],
                check=False, capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                raise OSError(f"kreadconfig6 failed for {key}")
            value = (result.stdout or "").removesuffix("\n").removesuffix("\r")
            saved[key] = None if value == sentinel else value
    except (OSError, subprocess.TimeoutExpired) as exc:
        warn(f"Acrylic Glass material preserved — could not read settings ({exc})")
        return

    # A saved KCM material can deliberately omit keys equal to its schema
    # defaults. Filling those from the edition would overwrite that selection.
    if saved["MaterialPreset"] is not None:
        return

    # Upgrade the complete previous installer material once. Any custom optical
    # value (including an explicit empty value) prevents this migration. Radius,
    # window rules and the previously independent gradient toggle stay untouched.
    golden = default_wallpaper() == "MacGoldenGate"
    legacy = dict(BlurStrength=4.0 if golden else 3.5, Brightness=1.0, Contrast=1.0,
                  Saturation=1.0, HighlightStrength=0.30, HighlightWidth=24.0,
                  MagnifyGlassStrength=0.015 if golden else 0.03, NoiseStrength=2,
                  RefractionWidth=72.0 if golden else 96.0)
    try:
        migrate = (saved["MaterialPreset"] is None and saved["MaterialOpacity"] is None
                   and all(saved[key] is not None and float(saved[key]) == value
                           for key, value in legacy.items())
                   and (saved["RgbDriftStrength"] is None
                        or float(saved["RgbDriftStrength"]) == (16.0 if golden else 45.0)))
    except ValueError:
        migrate = False
    for key, value in defaults.items():
        if saved[key] is None or (migrate and key in {*legacy, "RgbDriftStrength"}):
            if not kw_write("--file", "kwinrc", "--group", "Effect-liquidglass",
                            "--key", key, value):
                warn(f"Acrylic Glass {key} default not applied — kwriteconfig6 failed")
                return


def _install_corner_defaults() -> None:
    """Seed missing radii without undoing the user's corner tuning (#89).

    The current effect has only three radius controls: popups also cover
    menus/tooltips, and normal windows cover dialogs and bottom corners.
    Preserve even explicitly empty values; failed reads never authorize a
    write. KConfig's cascade handles both user and system configuration.
    """
    _install_missing_defaults(_CORNER_DEFAULTS)


def _install_missing_defaults(defaults) -> None:
    if not have("kreadconfig6"):
        warn("Acrylic Glass settings preserved — kreadconfig6 is unavailable")
        return
    sentinel = f"__mttkde_absent_{uuid.uuid4().hex}__"
    for key, default in defaults:
        try:
            result = run_user(
                ["kreadconfig6", "--file", "kwinrc", "--group",
                 "Effect-liquidglass", "--key", key, "--default", sentinel],
                check=False, capture_output=True, text=True, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            warn(f"Acrylic Glass {key} preserved — could not read it ({exc})")
            continue
        if result.returncode != 0:
            warn(f"Acrylic Glass {key} preserved — kreadconfig6 failed")
            continue
        if (result.stdout or "").removesuffix("\n").removesuffix("\r") == sentinel:
            if not kw_write("--file", "kwinrc", "--group", "Effect-liquidglass",
                            "--key", key, default):
                warn(f"Acrylic Glass {key} default not applied — kwriteconfig6 failed")


def _plugin_mapping_matches(maps: str, plugin: Path) -> bool | None:
    installed = plugin.stat()
    matches = []
    for line in maps.splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) != 6 or fields[5].removesuffix(" (deleted)") != str(plugin):
            continue
        # Btrfs subvolume stat devices can differ from /proc/maps devices.
        # The exact path plus inode identifies the installed file.
        matches.append(int(fields[4]) == installed.st_ino
                       and not fields[5].endswith(" (deleted)"))
    return all(matches) if matches else None


def _versioned_effect_path(source: Path, directory: Path) -> Path:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    return directory / ".mttkde-liquidglass" / digest / "liquidglass.so"


def _owned_effect_paths(directory: Path) -> list[Path]:
    return [directory / "liquidglass.so", *sorted(
        path for path in (directory / ".mttkde-liquidglass").glob("*/liquidglass.so")
        if re.fullmatch(r"[0-9a-f]{64}", path.parent.name)
    )]


def _install_effect_binary(source: Path, destination: Path) -> bool:
    # Immutable filenames bypass Qt's resident-library cache. Reusing an
    # identical build must preserve its inode, not replace a mapped file.
    if destination.is_file() and not destination.is_symlink():
        if source.read_bytes() == destination.read_bytes():
            ok("Acrylic Glass already installed")
            return True
        fail("Acrylic Glass versioned file has unexpected contents")
        return False
    return sudo_install_file(source, destination, "Acrylic Glass installed")


def _activate_effect_binary(destination: Path, link: Path) -> bool:
    # Qt canonicalizes this path before caching the library; the basename
    # remains liquidglass, which KDE uses as the plugin/configuration ID.
    temporary = link.with_name(f".liquidglass-link-{uuid.uuid4().hex}")
    try:
        with _as_root():
            temporary.symlink_to(destination.relative_to(link.parent))
            temporary.replace(link)
        return True
    except OSError as exc:
        fail(f"Could not activate Acrylic Glass: {exc}")
        return False
    finally:
        with _as_root():
            temporary.unlink(missing_ok=True)


def _running_build_matches() -> bool | None:
    q = qdbus_cmd()
    try:
        header = (BUILD / "src/build_identity.h").read_text()
        identity = re.search(r'MTTKDE_GLASS_BUILD_ID "([0-9a-f]{64})"', header)
        if not q or not identity:
            return None
        result = run_user([q, "org.kde.KWin", "/Effects",
                           "org.kde.kwin.Effects.debug", "liquidglass", ""],
                          check=False, capture_output=True, text=True, timeout=5)
        return result.stdout.strip() == identity[1] if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _running_plugin_matches(plugin: Path) -> bool | None:
    q = qdbus_cmd()
    if not q:
        return None
    try:
        result = run_user(
            [q, "org.freedesktop.DBus", "/org/freedesktop/DBus",
             "org.freedesktop.DBus.GetConnectionUnixProcessID", "org.kde.KWin"],
            check=False, capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        pid = int(result.stdout.strip())
        if pid <= 0:
            return None
        # KWin's capabilities can deny same-user access to its mappings.
        with _as_root():
            maps = Path(f"/proc/{pid}/maps").read_text()
        return _plugin_mapping_matches(maps, plugin)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


# AquaDesktop: the Better Blur DX effect earlier releases installed, its
# settings module, and the hashed copy a live update placed next to it.
_RETIRED_EFFECT = "better_blur_dx"
_RETIRED_GROUP = "Effect-better-blur-dx"
_RETIRED_FILES = ("kwin/effects/plugins/better_blur_dx.so",
                  "kwin/effects/configs/kwin_better_blur_dx_config.so")


def _strip_kwinrc_group(group: str) -> None:
    kwinrc = Path.home() / ".config/kwinrc"
    try:
        text = kwinrc.read_text()
    except OSError:
        return
    header = f"[{group}]"
    if header not in text:
        return
    out: list[str] = []
    skip = False
    for line in text.splitlines():
        if line.startswith("["):
            skip = line.startswith(header)
        if not skip:
            out.append(line)
    kwinrc.write_text("\n".join(out) + "\n")


def _remove_better_blur_dx() -> None:
    """Disable it before unloading (a reconfigure could otherwise load it
    again), then drop its plugin, its hashed copies and its settings."""
    kw_write("--file", "kwinrc", "--group", "Plugins",
             "--key", f"{_RETIRED_EFFECT}Enabled", "false")
    qdbus_call("org.kde.KWin", "/Effects",
               "org.kde.kwin.Effects.unloadEffect", _RETIRED_EFFECT)
    _strip_kwinrc_group(_RETIRED_GROUP)
    system_dir = _plugin_dir()
    targets = [system_dir / relpath for relpath in _RETIRED_FILES]
    effect_dir = system_dir / "kwin/effects/plugins"
    if effect_dir.is_dir():
        targets += sorted(effect_dir.glob(".better_blur_dx-*"))
    for target in targets:
        if target.exists() or target.is_symlink():
            sudo_remove(target, f"{target.name} (replaced by Acrylic Glass)")


def install() -> None:
    system_dir = _plugin_dir()
    effect_so = BUILD / "src/liquidglass.so"
    config_so = BUILD / "src/kcm/kwin_liquidglass_config.so"
    effect_dir = system_dir / "kwin/effects/plugins"
    dest_config = system_dir / "kwin/effects/configs/kwin_liquidglass_config.so"

    if not effect_so.is_file():
        return
    dest_effect = _versioned_effect_path(effect_so, effect_dir)
    _remove_better_blur_dx()
    # Disable the conflicting blur effects only after every build succeeded.
    for effect in ("glass", "blur"):
        kw_write("--file", "kwinrc", "--group", "Plugins",
                 "--key", f"{effect}Enabled", "false")
        qdbus_call("org.kde.KWin", "/Effects",
                   "org.kde.kwin.Effects.unloadEffect", effect)

    # Disable discovery while switching versions. Qt can retain the old
    # library even after the effect instance has been unloaded.
    kw_write("--file", "kwinrc", "--group", "Plugins",
             "--key", "liquidglassEnabled", "false")
    qdbus_call("org.kde.KWin", "/Effects",
               "org.kde.kwin.Effects.unloadEffect", "liquidglass")
    qdbus_call("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")
    time.sleep(2)
    ok("Acrylic Glass unloaded for safe upgrade")

    # Drop user-path leftovers from old sudoless installs.
    for so in (LEGACY_USER_PLUGIN_DIR / "kwin/effects/plugins/liquidglass.so",
               LEGACY_USER_PLUGIN_DIR / "kwin/effects/configs/kwin_liquidglass_config.so"):
        if so.is_file():
            try:
                so.unlink()
                ok(f"{so.name} (removed user-path leftover)")
            except OSError:
                pass

    if not _install_effect_binary(effect_so, dest_effect):
        return
    if not sudo_install_file(config_so, dest_config, "Acrylic Glass KCM installed"):
        warn("Acrylic Glass KCM install failed")

    if not _activate_effect_binary(dest_effect, effect_dir / "liquidglass.so"):
        return
    # Retire only our versioned files. The discovery link stays in place.
    for previous in _owned_effect_paths(effect_dir):
        if previous.parent != effect_dir and previous != dest_effect:
            if not sudo_remove(previous, "Previous Acrylic Glass binary removed"):
                fail("Could not retire the previous Acrylic Glass plugin")
                return
            with _as_root():
                try:
                    previous.parent.rmdir()
                except OSError:
                    pass

    _install_material_defaults()
    _install_corner_defaults()
    _install_missing_defaults((("BlurDecorations", "true"),
                               ("BlurMatching", "false"), ("BlurNonMatching", "true")))
    ok("Acrylic Glass material settings ready")
    kw_write("--file", "kwinrc", "--group", "Plugins",
             "--key", "liquidglassEnabled", "true")

    # Reload the effect instance. Qt may still retain its old shared library;
    # activeEffects alone cannot prove the newly installed code is running.
    qdbus_call("org.kde.KWin", "/Effects",
               "org.kde.kwin.Effects.unloadEffect", "liquidglass")
    qdbus_call("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")
    qdbus_call("org.kde.KWin", "/Effects",
               "org.kde.kwin.Effects.loadEffect", "liquidglass")

    q = qdbus_cmd()
    active = ""
    if q:
        try:
            res = run_user([q, "org.kde.KWin", "/Effects",
                            "org.kde.kwin.Effects.activeEffects"],
                           check=False, capture_output=True, text=True,
                           timeout=10)
            if res.returncode == 0:
                active = res.stdout or ""
        except (OSError, subprocess.TimeoutExpired):
            pass
    if "liquidglass" in active.splitlines():
        identity_matches = _running_build_matches()
        if identity_matches is None:
            identity_matches = _running_plugin_matches(dest_effect)
        if identity_matches is False:
            warn("Acrylic Glass installed, but KWin still has the previous "
                 "plugin loaded. Log out and back in to use this update; "
                 "reloading the effect or restarting Plasma is not enough.")
        elif identity_matches is True:
            ok("Acrylic Glass loaded")
        else:
            warn("Acrylic Glass is active, but its running build could not be verified.")
    else:
        warn("Acrylic Glass installed but activation was not confirmed. "
             "Log out and back in after a KWin upgrade; if it remains inactive, "
             "check the KWin log for liquidglass shader or plugin errors.")


def uninstall() -> None:
    # Persist the disabled state before asking KWin to unload the effect.
    # Unloading first can race a config notification/reconfigure and let KWin
    # immediately load the still-enabled plugin again, leaving every window
    # translucent until the user logs out even though the .so was removed.
    disabled = kw_write(
        "--file", "kwinrc", "--group", "Plugins",
        "--key", "liquidglassEnabled", "false",
    )
    unloaded = qdbus_call(
        "org.kde.KWin", "/Effects",
        "org.kde.kwin.Effects.unloadEffect", "liquidglass",
    )
    reconfigured = qdbus_call(
        "org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure",
    )
    if not disabled:
        warn("Acrylic Glass could not be disabled in kwinrc")
    if not unloaded and not reconfigured:
        # A reconfigure with liquidglassEnabled=false is an equivalent live
        # unload.  Only warn when neither live path reached KWin.
        warn("Acrylic Glass live unload was not confirmed — log out once if "
             "window transparency remains")

    # Strip the whole [Effect-liquidglass] group — leaving it behind would
    # let a reinstall keep stale tuned values.
    kwinrc = Path.home() / ".config/kwinrc"
    if kwinrc.is_file():
        text = kwinrc.read_text()
        if "[Effect-liquidglass]" in text:
            out: list[str] = []
            skip = False
            for line in text.splitlines():
                if line.startswith("[Effect-liquidglass]"):
                    skip = True
                    continue
                if skip and line.startswith("["):
                    skip = False
                if not skip:
                    out.append(line)
            kwinrc.write_text("\n".join(out) + "\n")

    system_dir = _plugin_dir()
    for so in (*_owned_effect_paths(system_dir / "kwin/effects/plugins"),
               system_dir / "kwin/effects/configs/kwin_liquidglass_config.so"):
        sudo_remove(so, so.name)
    # Drop user-path leftovers from old sudoless installs.
    for so in (LEGACY_USER_PLUGIN_DIR / "kwin/effects/plugins/liquidglass.so",
               LEGACY_USER_PLUGIN_DIR / "kwin/effects/configs/kwin_liquidglass_config.so"):
        if so.is_file():
            try:
                so.unlink()
                ok(f"{so.name} (legacy user-path)")
            except OSError as exc:
                fail(f"{so.name} ({exc})")

    # AquaDesktop: an install that never upgraded keeps Better Blur DX.
    _remove_better_blur_dx()

    # Refresh KWin's effect catalogue after the plugin files disappear.  This
    # also repaints windows immediately on sessions where unloadEffect is
    # asynchronous, instead of leaving the old effect mapped until logout.
    qdbus_call("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")
    info("Acrylic Glass removed")
