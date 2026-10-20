#!/usr/bin/env python3
"""Light/dark theme switcher: `mac-tahoe-theme-switch {light|dark|auto}
[install]`. Covers what Plasma's lookandfeelautoswitcher does NOT switch
(Kvantum, GTK 2/3/4, icon caches). Color schemes go through KDE's own
plasma-apply-colorscheme (correct [Colors:*] groups + ColorSchemeHash so
live Qt apps reload the palette); the manual [Colors:*] rewrite remains
only as a fallback for systems without the tool."""

import colorsys
import datetime as _dt
import fcntl
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path


LAF_LIGHT = "org.kde.mac-tahoe-liquid-kde.light"
LAF_DARK = "org.kde.mac-tahoe-liquid-kde.dark"
KVANTUM_THEME_LIGHT = "mac-tahoe-liquid-kde"
KVANTUM_THEME_DARK = "mac-tahoe-liquid-kdeDark"
KVANTUM_STYLE = "kvantum"
_PROC_ROOT = Path("/proc")
REDUCED_SUFFIX = "-ReducedTransparency"
DEFAULT_WALLPAPER = "MacTahoe"


def default_wallpaper() -> str:
    """Source/Nix editions use adjacent defaults; installed scripts bake them in."""
    if Path(__file__).name != "theme_switch.py":
        return DEFAULT_WALLPAPER
    try:
        value = json.loads(Path(__file__).with_name("defaults.json").read_text())
        wallpaper = value.get("wallpaper") if isinstance(value, dict) else None
        if wallpaper in ("MacTahoe", "MacGoldenGate"):
            return wallpaper
    except (OSError, ValueError):
        pass
    return DEFAULT_WALLPAPER


def _appearance_path() -> Path:
    return _xdg_config() / "mac-tahoe-liquid-kde/appearance.json"


def reduced_transparency() -> bool:
    try:
        state = json.loads(_appearance_path().read_text())
        return isinstance(state, dict) and state.get("transparency") == "reduced"
    except (OSError, ValueError):
        return False


def _surface_theme(name: str) -> str:
    return name + REDUCED_SUFFIX if reduced_transparency() else name


def set_transparency(value: str) -> int:
    """Persist the accessibility preference independently of scheduled mode."""
    if value not in ("standard", "reduced"):
        print("Transparency must be standard or reduced", file=sys.stderr)
        return 1
    with _theme_transition_lock():
        if value == "reduced":
            data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
            required = []
            for mode in ("Light", "Dark"):
                name = f"MacTahoeLiquidKde-{mode}{REDUCED_SUFFIX}"
                required += [data / "plasma/desktoptheme" / name,
                             Path.home() / ".themes" / name]
            for name in (KVANTUM_THEME_LIGHT, KVANTUM_THEME_DARK):
                required.append(_xdg_config() / "Kvantum" / (name + REDUCED_SUFFIX))
            if any(not path.is_dir() for path in required):
                print("Reinstall the Plasma, GTK and Kvantum themes first to add "
                      "reduced-transparency assets.", file=sys.stderr)
                return 1
        path = _appearance_path()
        try:
            if path.is_symlink():
                print("Appearance is managed declaratively; change its source configuration.", file=sys.stderr)
                return 1
            state = json.loads(path.read_text()) if path.exists() else {}
            if not isinstance(state, dict):
                raise ValueError("appearance settings must be an object")
            state["transparency"] = value
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_text(json.dumps(state) + "\n")
            temporary.replace(path)
        except (OSError, ValueError) as exc:
            print(f"Could not save appearance: {exc}", file=sys.stderr)
            return 1
        mode = detect_mode_by_system() or detect_mode_by_time()
        applied = _apply_unlocked(mode)
        refresh_acrylic_glass()
        return 0 if applied else 1

# ── Dock tint ────────────────────────────────────────────────────────
# The Dock's veil is the Plasma theme's (panel-background south-center):
#   macos           no veil: the Acrylic Glass material gives the colours;
#   neutral         no veil, and the glass loses its colour: the blur behind
#                   the Dock, menus and windows is grey (Saturation 0), so
#                   the Dock is neutral and context menus plain black;
#   accent          KDE's accent colour, 22 % on the Dock, and the context
#                   menus (Kvantum) and menu bar popovers tinted with it.
# The menu bar popovers' glass (GlassSurface.qml) follows it through
# glass.ini: the context menus' own colour for macos and neutral (Kvantum's
# menu fill at its opacity), the accent for accent.
# Theme Settings picks it (`mac-tahoe-theme-switch dock-tint <tint>`); it
# is kept in appearance.json and rewritten into the installed themes on
# every apply, as a theme reinstall brings the shipped veil back.
DOCK_TINTS = ("macos", "neutral", "accent")
DEFAULT_DOCK_TINT = "macos"
DEFAULT_GLASS_LEVEL = 50
_DOCK_VEIL_ALPHA = 0.22
_DOCK_VEIL_NEUTRAL = "#aaaaa1"
# The frosted style (the Dock before Tahoe): a denser veil, dark grey in the
# dark theme and white in the light one, over the heavier blur. Estimated:
# no capture of a pre-Tahoe Dock measured yet. A chosen tint keeps its
# colour at this density.
_DOCK_VEIL_FROSTED_ALPHA = 0.45
_DOCK_VEIL_FROSTED = {"Dark": "#1e1e20", "Light": "#f5f5f7"}
# The accent's share of the Kvantum context menus' fill (dark #333333,
# light white), so menu text stays legible.
_MENU_ACCENT_MIX = {"Dark": 0.35, "Light": 0.20}
_MENU_FILL = {"Dark": "#333333", "Light": "#ffffff"}
_MENU_ELEMENTS = ("menu-normal", "menu-normal-left", "menu-normal-topleft")
_DOCK_VEIL_RE = re.compile(r'(<rect\b[^>]*?)style="[^"]*"([^>]*\bid="south-center")')


def dock_tint() -> str:
    try:
        state = json.loads(_appearance_path().read_text())
    except (OSError, ValueError):
        return DEFAULT_DOCK_TINT
    tint = state.get("dock_tint") if isinstance(state, dict) else None
    return tint if tint in DOCK_TINTS else DEFAULT_DOCK_TINT


def glass_level() -> int:
    """Golden Gate's Liquid Glass intensity, from clear (0) to tinted (100)."""
    try:
        state = json.loads(_appearance_path().read_text())
    except (OSError, ValueError):
        return DEFAULT_GLASS_LEVEL
    value = state.get("glass_level") if isinstance(state, dict) else None
    if isinstance(value, bool) or not isinstance(value, int):
        return DEFAULT_GLASS_LEVEL
    return max(0, min(100, value))


def dock_veil_colour(tint: str | None = None) -> str:
    tint = tint or dock_tint()
    if tint == "accent":
        return accent_color_hex() or scheme_accent_hex(
            _kread("kdeglobals", "General", "ColorScheme")) or _DOCK_VEIL_NEUTRAL
    return _DOCK_VEIL_NEUTRAL


def dock_veil(theme: str, tint: str | None = None, glass: str | None = None) -> tuple[str, float]:
    """(colour, opacity) of the Dock veil in the Plasma theme `theme`."""
    tint = tint or dock_tint()
    uncoloured = tint in ("macos", "neutral")
    if (glass or glass_style()) == "frosted":
        colour = (_DOCK_VEIL_FROSTED["Light" if "Light" in theme else "Dark"]
                  if uncoloured else dock_veil_colour(tint))
        return colour, _DOCK_VEIL_FROSTED_ALPHA
    if uncoloured:
        return _DOCK_VEIL_NEUTRAL, 0
    return dock_veil_colour(tint), _DOCK_VEIL_ALPHA


def write_glass_tint(tint: str | None = None) -> bool:
    """glass.ini, read by the popovers' GlassSurface.qml (QSettings): the
    tint name, the Golden Gate glass level and, for the accent tint, the
    accent as rrggbb."""
    tint = tint or dock_tint()
    accent = ""
    if tint == "accent":
        accent = (accent_color_hex() or scheme_accent_hex(
            _kread("kdeglobals", "General", "ColorScheme")) or "").lstrip("#")
    path = _appearance_path().with_name("glass.ini")
    text = f"Tint={tint}\nAccent={accent}\nGlassLevel={glass_level()}\n"
    try:
        if path.exists() and path.read_text() == text:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".{os.getpid()}.tmp")
        temporary.write_text(text)
        temporary.replace(path)
        return True
    except OSError as exc:
        print(f"theme apply: glass tint not written ({path}: {exc})", file=sys.stderr)
        return False


def set_glass_level(value: str) -> int:
    """Persist Golden Gate's clear-to-tinted control for menu-bar glass."""
    try:
        level = int(value)
    except (TypeError, ValueError):
        level = -1
    if not 0 <= level <= 100:
        print("Glass level must be an integer from 0 to 100", file=sys.stderr)
        return 1
    with _theme_transition_lock():
        path = _appearance_path()
        try:
            if path.is_symlink():
                print("Appearance is managed declaratively; change its source configuration.",
                      file=sys.stderr)
                return 1
            state = json.loads(path.read_text()) if path.exists() else {}
            if not isinstance(state, dict):
                raise ValueError("appearance settings must be an object")
            state["glass_level"] = level
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_text(json.dumps(state) + "\n")
            temporary.replace(path)
        except (OSError, ValueError) as exc:
            print(f"Could not save appearance: {exc}", file=sys.stderr)
            return 1
        write_glass_tint()
        return 0


def apply_dock_tint(tint: str | None = None, glass: str | None = None) -> bool:
    """Write the Dock veil of `tint` (default: the saved one) and of the
    glass style into every installed AquaDesktop Plasma theme, and the tint
    of the popovers' glass. True when a Plasma theme file changed."""
    write_glass_tint(tint)
    changed = False
    for theme in sorted((_xdg_data() / "plasma/desktoptheme").glob("MacTahoeLiquidKde-*")):
        # Reduced transparency keeps its own opaque Dock.
        if theme.name.endswith(REDUCED_SUFFIX):
            continue
        colour, alpha = dock_veil(theme.name, tint, glass)
        style = f'style="opacity:{alpha};fill:{colour}"'
        path = theme / "widgets/panel-background.svgz"
        try:
            text = gzip.decompress(path.read_bytes()).decode("utf-8")
        except (OSError, EOFError, gzip.BadGzipFile, UnicodeError):
            continue
        new = _DOCK_VEIL_RE.sub(lambda m: m.group(1) + style + m.group(2), text, count=1)
        if new == text:
            continue
        try:
            temporary = path.with_name(path.name + ".tmp")
            temporary.write_bytes(gzip.compress(new.encode("utf-8"), mtime=0))
            temporary.replace(path)
            changed = True
        except OSError as exc:
            print(f"theme apply: Dock tint not written ({path}: {exc})", file=sys.stderr)
    return changed


def set_dock_tint(value: str) -> int:
    """Save the Dock tint and apply it now (a theme apply reloads the
    Plasma theme's SVGs)."""
    if value not in DOCK_TINTS:
        print("Dock tint must be " + ", ".join(DOCK_TINTS), file=sys.stderr)
        return 1
    with _theme_transition_lock():
        path = _appearance_path()
        try:
            if path.is_symlink():
                print("Appearance is managed declaratively; change its source configuration.",
                      file=sys.stderr)
                return 1
            state = json.loads(path.read_text()) if path.exists() else {}
            if not isinstance(state, dict):
                raise ValueError("appearance settings must be an object")
            state["dock_tint"] = value
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_text(json.dumps(state) + "\n")
            temporary.replace(path)
        except (OSError, ValueError) as exc:
            print(f"Could not save appearance: {exc}", file=sys.stderr)
            return 1
        apply_dock_tint(value)
        # The neutral tint also changes the blur's saturation.
        apply_glass_preset(current_mode())
        # The accent tint colours the context menus (Kvantum).
        if apply_kvantum_accent():
            cycle_widget_style_live(KVANTUM_STYLE)
        return 0 if reload_plasma_theme() else 1


def reload_plasma_theme() -> bool:
    """Make Plasma reread the theme's SVGs (a rewritten Dock veil): its
    theme watcher only reloads on a name change, so pass through the
    theme's reduced-transparency twin (or back) for half a second."""
    name = _kread("plasmarc", "Theme", "name")
    if not name.startswith("MacTahoeLiquidKde-"):
        return False
    twin = name[:-len(REDUCED_SUFFIX)] if name.endswith(REDUCED_SUFFIX) else name + REDUCED_SUFFIX
    if not (_xdg_data() / "plasma/desktoptheme" / twin).is_dir():
        return False
    cache = Path.home() / ".cache"
    for pattern in ("ksvg-elements*", "plasma_theme_*"):
        for f in cache.glob(pattern):
            try:
                f.unlink()
            except OSError:
                pass
    ok = _kwrite("--file", "plasmarc", "--group", "Theme", "--key", "name", twin)
    time.sleep(0.5)
    return _kwrite("--file", "plasmarc", "--group", "Theme", "--key", "name", name) and ok

# The window and Dock glass: upstream's Acrylic Glass KWin effect (bundled
# in src/offline/kwin-effects/acrylic-glass): KWin effect id and its kwinrc
# group. The names keep "glass" for the style and the presets.
GLASS_EFFECT = "liquidglass"
GLASS_GROUP = "Effect-liquidglass"
# The material of each style, chosen with
# `mac-tahoe-theme-switch style {tahoe|frosted}`:
#   tahoe   (default) upstream's Tahoe material (presets.json "tahoe": soft,
#           fully blurred glass with a narrow refracted edge), the same in
#           both appearances. The menu bar has no background.
#   frosted the macOS frosted material, the look before Tahoe, measured on
#           a macOS dark Dock: the wallpaper heavily blurred and dimmed to
#           about 85 %, no refraction or colour drift. The menu bar gets its
#           translucent, blurred background back, full width.
# Every preset sets the same keys, so switching styles leaves nothing of the
# other behind. Every light/dark switch rewrites them, so tuning them in the
# effect's settings only lasts until the next change. MaterialPreset marks
# the material as chosen, so a reinstall keeps it.
# Upstream's tahoe material (acrylic-glass/src/presets.json), copied: the
# switch is installed alone in ~/.local/bin, without the checkout.
_TAHOE_MATERIAL = {
    "BlurStrength": "7.0", "MaterialOpacity": "1.0", "NoiseStrength": "1",
    "RgbDriftStrength": "6.0", "MagnifyGlassStrength": "0.02",
    "RefractionWidth": "18.0", "HighlightWidth": "1.5",
    "HighlightStrength": "0.11", "Brightness": "1.0", "Contrast": "1.0",
    "Saturation": "1.05", "DarkGradientOverlay": "false",
    "GradientTopColor": "#000000", "GradientBottomColor": "#000000",
    "GradientTopOpacity": "0.38", "GradientBottomOpacity": "0.02",
    "MaterialPreset": "1",
}
_FROSTED_MATERIAL = dict(
    _TAHOE_MATERIAL, BlurStrength="8.0", RgbDriftStrength="0.0",
    MagnifyGlassStrength="0.0", RefractionWidth="0.0", HighlightStrength="0.10",
    Saturation="1.0", GradientTopOpacity="0.0", GradientBottomOpacity="0.0")

GLASS_PRESETS = {
    "dark-tahoe": dict(_TAHOE_MATERIAL),
    "light-tahoe": dict(_TAHOE_MATERIAL),
    "dark-frosted": dict(_FROSTED_MATERIAL, Brightness="0.85"),
    # No light frosted capture measured yet: the dark calibration mirrored.
    "light-frosted": dict(_FROSTED_MATERIAL, Brightness="1.12"),
}


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _drop_privs_in_child() -> None:
    """Duplicate of utils.drop_privs_in_child (the canonical copy) — this
    file ships standalone to ~/.local/bin and cannot import utils.
    No-op without SUDO_UID/SUDO_GID, i.e. in plain user runs."""
    sudo_uid = os.environ.get("SUDO_UID")
    sudo_gid = os.environ.get("SUDO_GID")
    if not sudo_uid or not sudo_gid:
        return
    # GID first: changing UID can drop the right to call setresgid.
    os.setresgid(int(sudo_gid), int(sudo_gid), int(sudo_gid))
    os.setresuid(int(sudo_uid), int(sudo_uid), int(sudo_uid))


def _run_user(cmd: list[str], *, timeout: int,
              env: dict[str, str] | None = None,
              capture: bool = False) -> subprocess.CompletedProcess:
    """Every child spawn goes through here. steps/apply.py imports these
    helpers into the sudo'd installer (ruid=0, euid=user), where a bare
    child trips Qt6's setuid abort and the call silently fails."""
    kwargs: dict = {"check": False, "timeout": timeout, "env": env,
                    "preexec_fn": _drop_privs_in_child}
    if capture:
        kwargs.update(capture_output=True, text=True)
    else:
        kwargs.update(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return subprocess.run(cmd, **kwargs)


def _xdg_config() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or
                str(Path.home() / ".config"))


def _kdeglobals_path() -> Path:
    return _xdg_config() / "kdeglobals"


def _qdbus(*args: str) -> bool:
    # Fedora ships the Qt6 client as qdbus-qt6, not qdbus6 (see utils.qdbus_cmd).
    for q in ("qdbus6", "qdbus-qt6", "qdbus"):
        if _have(q):
            try:
                return _run_user([q, *args], timeout=10).returncode == 0
            except subprocess.TimeoutExpired:
                return False
    return False


_HAS_DBUS: bool | None = None


def _has_session_dbus() -> bool:
    global _HAS_DBUS
    if _HAS_DBUS is not None:
        return _HAS_DBUS
    if not os.environ.get("DBUS_SESSION_BUS_ADDRESS") or not _have("dbus-send"):
        _HAS_DBUS = False
        return _HAS_DBUS
    try:
        _HAS_DBUS = _run_user(
            ["dbus-send", "--session", "--print-reply",
             "--dest=org.freedesktop.DBus", "/org/freedesktop/DBus",
             "org.freedesktop.DBus.ListNames"],
            timeout=5,
        ).returncode == 0
    except subprocess.TimeoutExpired:
        _HAS_DBUS = False
    return _HAS_DBUS


def _sync_session_env_runtime_dir() -> None:
    """Recover the session bus/Wayland socket from the user runtime dir.

    Scheduled jobs can have a deliberately small environment on any init.
    The per-user runtime directory exposes stable socket names, so use it
    rather than guessing a display owned by another user.
    """
    uid = int(os.environ.get("SUDO_UID") or os.getuid())
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{uid}")
    if not runtime.is_dir():
        return
    os.environ.setdefault("XDG_RUNTIME_DIR", str(runtime))
    if "WAYLAND_DISPLAY" not in os.environ:
        for socket in sorted(runtime.glob("wayland-*")):
            if socket.is_socket() and not socket.name.endswith(".lock"):
                os.environ["WAYLAND_DISPLAY"] = socket.name
                break
    if "DBUS_SESSION_BUS_ADDRESS" not in os.environ:
        bus = runtime / "bus"
        if bus.is_socket():
            os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus}"


def _sync_session_env_from_plasmashell() -> None:
    """Fill X11 and remaining session values from a same-user shell.

    The switcher is installed as a standalone script, so it cannot import the
    installer's distro layer. ``/proc`` is init-agnostic and works for a
    systemd user service, OpenRC cron, and manually launched sessions alike.
    """
    try:
        uid = int(os.environ.get("SUDO_UID") or os.getuid())
    except ValueError:
        uid = os.getuid()
    wanted = {
        "DBUS_SESSION_BUS_ADDRESS", "DISPLAY", "WAYLAND_DISPLAY",
        "XAUTHORITY", "XDG_CACHE_HOME", "XDG_CONFIG_HOME",
        "XDG_CURRENT_DESKTOP", "XDG_DATA_HOME", "XDG_RUNTIME_DIR",
        "XDG_SESSION_TYPE", "XDG_STATE_HOME",
    }
    try:
        processes = list(_PROC_ROOT.iterdir())
    except OSError:
        return
    for process in processes:
        if not process.name.isdigit():
            continue
        try:
            if process.stat().st_uid != uid:
                continue
            if (process / "comm").read_text().strip() != "plasmashell":
                continue
            raw = (process / "environ").read_bytes()
        except OSError:
            continue
        for entry in raw.split(b"\0"):
            key_raw, sep, value_raw = entry.partition(b"=")
            key = key_raw.decode(errors="ignore")
            if not sep or key not in wanted or key in os.environ:
                continue
            value = value_raw.decode(errors="ignore")
            if value:
                os.environ[key] = value
        break


def _sync_session_env() -> None:
    global _HAS_DBUS
    old_bus = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
    _sync_session_env_runtime_dir()
    _sync_session_env_from_plasmashell()
    if os.environ.get("DBUS_SESSION_BUS_ADDRESS") != old_bus:
        # A pre-sync probe may have cached a sparse cron env as bus-less.
        _HAS_DBUS = None


def _theme_transition_lock_path() -> Path:
    """One lock shared by timer and manual theme transitions."""
    try:
        uid = int(os.environ.get("SUDO_UID") or os.getuid())
    except ValueError:
        uid = os.getuid()
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{uid}")
    if runtime.is_dir():
        return runtime / "mac-tahoe-liquid-kde-theme-apply.lock"
    state = Path(os.environ.get("XDG_STATE_HOME") or
                 str(Path.home() / ".local/state"))
    return state / "mac-tahoe-liquid-kde" / "theme-apply.lock"


@contextmanager
def _theme_transition_lock():
    """Prevent two live theme pipelines from interleaving.

    A login service, timer and manual command can overlap. Without a
    cross-process lock they can rewrite Plasma settings and caches at the same
    time, leaving different panel containments rendered from different
    variants. Lock setup is best-effort so an unusual read-only state/runtime
    directory never makes an otherwise usable switcher fail.
    """
    lock = None
    locked = False
    try:
        path = _theme_transition_lock_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = path.open("w", encoding="utf-8")
        fcntl.flock(lock, fcntl.LOCK_EX)
        locked = True
        lock.write(f"{os.getpid()}\n")
        lock.flush()
    except OSError:
        if lock is not None:
            lock.close()
            lock = None
    try:
        yield
    finally:
        if lock is not None:
            if locked:
                try:
                    fcntl.flock(lock, fcntl.LOCK_UN)
                except OSError:
                    pass
            lock.close()


def _kwrite(*args: str) -> bool:
    if not _have("kwriteconfig6"):
        return False
    cmd = ["kwriteconfig6"]
    if _has_session_dbus():
        cmd.append("--notify")
    cmd.extend(args)
    try:
        return _run_user(cmd, timeout=5).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def _kread(file: str, group: str, key: str) -> str:
    if not _have("kreadconfig6"):
        return ""
    try:
        return _run_user(
            ["kreadconfig6", "--file", file, "--group", group, "--key", key],
            timeout=5, capture=True,
        ).stdout.strip()
    except subprocess.TimeoutExpired:
        return ""


def _build_group_args(section: str) -> list[str]:
    args: list[str] = []
    rest = section
    while True:
        idx = rest.find("][")
        if idx < 0:
            break
        args.extend(["--group", rest[:idx]])
        rest = rest[idx + 2:]
    args.extend(["--group", rest])
    return args


def _parse_ini(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    section: str | None = None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return sections
    for raw in text.splitlines():
        line = raw.rstrip("\r").strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            sections.setdefault(section, {})
            continue
        if "=" in line and section is not None:
            key, value = line.split("=", 1)
            sections[section][key.strip()] = value
    return sections


def _is_color_group(name: str) -> bool:
    return name.startswith(("Colors:", "ColorEffects:")) or name == "WM"


def _scrub_malformed_color_groups() -> None:
    path = _kdeglobals_path()
    if not path.is_file():
        return
    bad = re.compile(r"^\[(Colors:|ColorEffects:).*(\\x5d\\x5b).*\]$")
    text = path.read_text(encoding="utf-8", errors="replace")
    out: list[str] = []
    skip = False
    for line in text.splitlines():
        if bad.match(line):
            skip = True
            continue
        if skip and line.startswith("["):
            skip = False
        if not skip:
            out.append(line)
    path.write_text("\n".join(out) + ("\n" if text.endswith("\n") else ""),
                    encoding="utf-8")


def _delete_color_groups_direct() -> bool:
    if not _have("kwriteconfig6"):
        return False
    path = _kdeglobals_path()
    if not path.is_file():
        return True
    _scrub_malformed_color_groups()
    sections = _parse_ini(path)
    keys: set[tuple[str, str]] = set()
    for section, items in sections.items():
        if _is_color_group(section):
            for key in items:
                keys.add((section, key))
    for section, key in sorted(keys):
        if not _kwrite("--file", "kdeglobals",
                       *_build_group_args(section),
                       "--key", key, "--delete"):
            return False
    return True


def reset_kde_color_scheme_config(scheme: str) -> bool:
    return apply_color_scheme(scheme)


def apply_color_scheme(scheme: str) -> bool:
    """Apply a color scheme to kdeglobals.

    Prefer KDE's own ``plasma-apply-colorscheme`` (same package as
    kwriteconfig6): it rewrites the [Colors:*] groups and
    ColorSchemeHash exactly the way the Colors KCM does, so live Qt
    apps reload the palette instead of keeping the previous scheme.
    Fall back to the manual rewrite only when the binary is missing
    (minimal/CI systems)."""
    if _have("plasma-apply-colorscheme"):
        # Without --accent-color the scheme's own colours come back, and the
        # accent chosen in Theme Settings (or System Settings) is lost.
        accent = accent_color_hex()
        extra = ["--accent-color", accent] if accent else []
        try:
            return _run_user(
                ["plasma-apply-colorscheme", scheme, *extra], timeout=15,
            ).returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False
    return apply_color_groups_direct(scheme)


def accent_color_hex() -> str:
    """kdeglobals' custom accent colour ([General] AccentColor, "r,g,b") as
    #rrggbb; empty when the colour scheme's own accent is used."""
    return _rgb_text_to_hex(_kread("kdeglobals", "General", "AccentColor"))


# ── Accent colour in Kvantum ─────────────────────────────────────────
# Kvantum draws selections, checked boxes, sliders and default buttons from
# its own SVG and kvconfig blues, not from the KDE palette. The kvantum
# step keeps the untouched themes in DATA/mac-tahoe-liquid-kde/kvantum;
# the user's copies in ~/.config/Kvantum are rewritten from them with every
# accent-family blue moved to the accent (same lightness offsets).
_KVANTUM_BASE_ACCENT = "#0088ff"
_HEX_COLOUR = re.compile(r"#([0-9a-fA-F]{6})(?![0-9a-fA-F])")


def kvantum_originals_dir() -> Path:
    return _xdg_data() / "mac-tahoe-liquid-kde/kvantum"


def _hex_to_rgb(colour: str) -> tuple[float, float, float]:
    colour = colour.lstrip("#")
    return tuple(int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))


def recolor_accent(text: str, accent: str) -> str:
    """Every accent-family blue of `text` (hue 195-232°, saturated, mid
    lightness) in the hue of `accent`, keeping its offset from the theme's
    own accent in lightness and its relative saturation."""
    ah, al, as_ = colorsys.rgb_to_hls(*_hex_to_rgb(accent))
    _bh, bl, bs = colorsys.rgb_to_hls(*_hex_to_rgb(_KVANTUM_BASE_ACCENT))

    def swap(match: re.Match) -> str:
        h, l, sat = colorsys.rgb_to_hls(*_hex_to_rgb(match.group(1)))
        if not (195 / 360 <= h <= 232 / 360 and sat >= 0.5 and 0.3 <= l <= 0.75):
            return match.group(0)
        new_l = min(0.95, max(0.05, al + (l - bl)))
        new_s = min(1.0, as_ * sat / bs)
        r, g, b = colorsys.hls_to_rgb(ah, new_l, new_s)
        return "#{:02x}{:02x}{:02x}".format(*(round(c * 255) for c in (r, g, b)))

    return _HEX_COLOUR.sub(swap, text)


def kvantum_engine_follows_accent() -> bool:
    """The Tahoe Kvantum engine (steps/kvantum.py, USER_ENGINE) recolours the
    themes itself, live, for any accent (the wallpaper's too) — once the
    session loads it: QT_PLUGIN_PATH names its directory. Until then (just
    installed, not logged in again) the themes are rewritten instead."""
    root = _xdg_data() / "mac-tahoe-liquid-kde/qt6/plugins"
    if not (root / "styles/libkvantum.so").is_file():
        return False
    return str(root) in os.environ.get("QT_PLUGIN_PATH", "").split(":")


def menu_tint_colour(theme: str, tint: str | None = None) -> str:
    """The Kvantum context menus' fill in `theme`: its own, or mixed with
    the accent for the accent tint."""
    variant = "Dark" if theme.endswith("Dark") else "Light"
    base = _MENU_FILL[variant]
    if (tint or dock_tint()) != "accent":
        return base
    accent = accent_color_hex() or scheme_accent_hex(
        _kread("kdeglobals", "General", "ColorScheme"))
    if not accent:
        return base
    share = _MENU_ACCENT_MIX[variant]
    mixed = (round(b * (1 - share) + a * share)
             for b, a in zip(_hex_to_rgb255(base), _hex_to_rgb255(accent)))
    return "#" + "".join(f"{c:02x}" for c in mixed)


def _hex_to_rgb255(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def tint_kvantum_menus(svg: str, colour: str) -> str:
    """The fills of Kvantum's menu frame (centre, edges, corners) in `colour`."""
    for element in _MENU_ELEMENTS:
        index = svg.find(f'id="{element}"')
        if index < 0:
            continue
        start = svg.rfind("<", 0, index)
        end = (svg.index("</g>", index) if svg.startswith("<g", start)
               else svg.index(">", index))
        block = re.sub(r"fill:#[0-9a-fA-F]{6}", f"fill:{colour}", svg[start:end])
        svg = svg[:start] + block + svg[end:]
    return svg


def apply_kvantum_accent(accent: str | None = None) -> bool:
    """Rewrite the user's Kvantum themes for `accent` (default: kdeglobals'
    AccentColor; none restores the originals) and the glass tint's menu
    colour. True when a file changed.
    With the Tahoe Kvantum engine the themes stay untouched (it recolours
    them as it loads them)."""
    accent = accent_color_hex() if accent is None else accent
    if kvantum_engine_follows_accent():
        accent = ""
    originals = kvantum_originals_dir()
    changed = False
    for theme in (KVANTUM_THEME_LIGHT, KVANTUM_THEME_DARK):
        if not _kvantum_original_is_valid(originals, theme):
            continue
        for ext in (".kvconfig", ".svg"):
            source = originals / f"{theme}{ext}"
            target = _xdg_config() / "Kvantum" / theme / f"{theme}{ext}"
            if not target.parent.is_dir():
                continue
            try:
                text = source.read_text(encoding="utf-8")
                if accent:
                    text = recolor_accent(text, accent)
                if ext == ".svg":
                    # The accent tint (dock-tint accent) colours the menus.
                    text = tint_kvantum_menus(text, menu_tint_colour(theme))
                if target.is_file() and target.read_text(encoding="utf-8") == text:
                    continue
                target.write_text(text, encoding="utf-8")
                changed = True
            except (OSError, UnicodeError) as exc:
                print(f"theme apply: Kvantum accent not written ({target}: {exc})",
                      file=sys.stderr)
    return changed


def _kvantum_original_is_valid(originals: Path, theme: str) -> bool:
    """A real Kvantum theme: a kvconfig with its [%General] group and an
    SVG with drawing elements. Anything else would break every Qt app."""
    try:
        config = (originals / f"{theme}.kvconfig").read_text(encoding="utf-8")
        svg = (originals / f"{theme}.svg").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    if not config.startswith("[%General]") or "<svg" not in svg or len(svg) < 1024:
        print(f"theme apply: Kvantum originals of {theme} look broken; "
              "reinstall the Kvantum step", file=sys.stderr)
        return False
    return True


def scheme_accent_hex(scheme: str) -> str:
    """A colour scheme's own accent: its selection background."""
    path = _find_scheme_file(scheme)
    if path is None:
        return ""
    selection = _parse_ini(path).get("Colors:Selection", {})
    return _rgb_text_to_hex(selection.get("BackgroundNormal", ""))


def _rgb_text_to_hex(value: str) -> str:
    try:
        r, g, b = (int(p) for p in value.split(",")[:3])
    except ValueError:
        return ""
    if not all(0 <= c <= 255 for c in (r, g, b)):
        return ""
    return f"#{r:02x}{g:02x}{b:02x}"


ACCENT_FROM_WALLPAPER_KEY = "accentColorFromWallpaper"


def accent_from_wallpaper() -> bool:
    return _kread("kdeglobals", "General", ACCENT_FROM_WALLPAPER_KEY).lower() == "true"


def set_accent(accent: str) -> bool:
    """The accent colour everywhere: KDE's palette (plasma-apply-colorscheme)
    and Kvantum, reloaded live. "multicolour" brings the scheme's own
    accent back and forgets the custom one; "wallpaper" lets Plasma derive
    it from the wallpaper (and follow every wallpaper change; the Tahoe
    Kvantum engine follows it live)."""
    multicolour = accent == "multicolour"
    wallpaper = accent == "wallpaper"
    if not (multicolour or wallpaper) and not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        return False
    # Plasma's shell watches this key and writes AccentColor itself.
    _kwrite("--file", "kdeglobals", "--group", "General",
            "--key", ACCENT_FROM_WALLPAPER_KEY, "true" if wallpaper else "false")
    if wallpaper:
        return True
    if multicolour:
        # An accent applied as the scheme's own blue is not the scheme
        # (KDE derives darker selections from it): forget the accent, then
        # re-apply the scheme itself. KDE skips a scheme it thinks is
        # current, so pass through the other mode's scheme first.
        ok = _kwrite("--file", "kdeglobals", "--group", "General",
                     "--key", "AccentColor", "--delete")
        scheme = _kread("kdeglobals", "General", "ColorScheme")
        opposite = ("MacTahoeLiquidKdeLight" if scheme.endswith("Dark")
                    else "MacTahoeLiquidKdeDark")
        if scheme:
            apply_color_scheme(opposite)
            ok = apply_color_scheme(scheme) and ok
    else:
        ok = False
        if _have("plasma-apply-colorscheme"):
            try:
                ok = _run_user(["plasma-apply-colorscheme", "--accent-color", accent],
                               timeout=15).returncode == 0
            except (subprocess.TimeoutExpired, OSError):
                ok = False
    if apply_kvantum_accent("" if multicolour else accent):
        cycle_widget_style_live(KVANTUM_STYLE)
    # A Dock tinted with the accent follows it.
    if dock_tint() == "accent" and apply_dock_tint():
        reload_plasma_theme()
    return ok


def _find_scheme_file(scheme: str) -> Path | None:
    candidates = [
        Path.home() / ".local/share/color-schemes" / f"{scheme}.colors",
        Path("/usr/share/color-schemes") / f"{scheme}.colors",
    ]
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        candidates.insert(0, Path(xdg) / "color-schemes" / f"{scheme}.colors")
    for p in candidates:
        if p.is_file():
            return p
    return None


def apply_color_groups_direct(scheme: str) -> bool:
    if not _have("kwriteconfig6"):
        return False
    scheme_file = _find_scheme_file(scheme)
    if scheme_file is None:
        return False
    sections = _parse_ini(scheme_file)
    if not _delete_color_groups_direct():
        return False
    for section, items in sections.items():
        if not _is_color_group(section):
            continue
        group_args = _build_group_args(section)
        for key, value in items.items():
            if not _kwrite("--file", "kdeglobals", *group_args,
                           "--key", key, value):
                return False
    # Qt apps key cached palettes on ColorSchemeHash — without rewriting
    # it they keep serving the previous scheme's colors.
    digest = hashlib.sha1(scheme_file.read_bytes()).hexdigest()
    return _kwrite("--file", "kdeglobals", "--group", "General",
                   "--key", "ColorSchemeHash", digest)


# Accent-independent keys that tell a scheme's palette from another one
# (KDE rewrites the selection / focus / link colours with the accent).
_PALETTE_PROBES = (
    ("Colors:Window", "BackgroundNormal"),
    ("Colors:Window", "ForegroundNormal"),
    ("Colors:View", "BackgroundNormal"),
    ("Colors:Button", "BackgroundNormal"),
    ("Colors:Header", "BackgroundNormal"),
)


def palette_matches_scheme(scheme: str) -> bool | None:
    """Whether kdeglobals' [Colors:*] groups hold `scheme`'s palette (None
    when the scheme file is missing). The ColorScheme name alone proves
    nothing: Breeze Light's colours were found under our Dark name after a
    reinstall, and KDE skips re-applying a scheme it believes is current."""
    scheme_file = _find_scheme_file(scheme)
    if scheme_file is None:
        return None
    wanted = _parse_ini(scheme_file)
    current = _parse_ini(_kdeglobals_path())
    for group, key in _PALETTE_PROBES:
        value = wanted.get(group, {}).get(key)
        if value is not None and current.get(group, {}).get(key) != value:
            return False
    return True


def ensure_color_scheme(scheme: str) -> bool:
    """`scheme`'s palette in kdeglobals, verified: when it is not there,
    apply the opposite scheme then this one (KDE then sees a real change),
    and as a last resort write the groups straight from the scheme file."""
    if palette_matches_scheme(scheme) is not False:
        return True
    opposite = ("MacTahoeLiquidKdeLight" if scheme.endswith("Dark")
                else "MacTahoeLiquidKdeDark")
    apply_color_scheme(opposite)
    apply_color_scheme(scheme)
    if palette_matches_scheme(scheme) is not False:
        return True
    accent = accent_color_hex()
    ok = apply_color_groups_direct(scheme)
    if ok and accent and _have("plasma-apply-colorscheme"):
        try:
            _run_user(["plasma-apply-colorscheme", "--accent-color", accent], timeout=15)
        except (subprocess.TimeoutExpired, OSError):
            pass
    return ok and palette_matches_scheme(scheme) is not False


def repair_colors() -> bool:
    """The current mode's palette, verified (the installer runs this after
    its final Plasma restart)."""
    scheme = ("MacTahoeLiquidKdeLight" if current_mode() == "light"
              else "MacTahoeLiquidKdeDark")
    return ensure_color_scheme(scheme)


def detect_mode_by_time() -> str:
    h = _dt.datetime.now().hour
    return "light" if 6 <= h < 18 else "dark"


def detect_mode_by_system() -> str | None:
    """The light/dark mode the DESKTOP currently wants, read from the live
    system rather than the clock. Used only by the explicit ``follow-system``
    one-shot command; no background portal watcher is installed.

    Source of truth order:
    1. The xdg-desktop-portal appearance ``color-scheme`` (1=dark, 2=light) —
       what the native quick-settings toggle actually sets, and what libadwaita
       reads. This is the value that changed when the user toggled.
    2. Fall back to KDE's active ColorScheme name (…Dark / …Light).
    None when neither can be read (caller then leaves the mode unchanged)."""
    scheme = _read_portal_color_scheme()
    if scheme == 1:
        return "dark"
    if scheme == 2:
        return "light"
    name = _kread("kdeglobals", "General", "ColorScheme")
    if name:
        low = name.lower()
        if "dark" in low:
            return "dark"
        if "light" in low:
            return "light"
    return None


_PRC_PANEL_RE = re.compile(
    r"(\[PlasmaViews\]\[Panel \d+\]\n(?:[^\[]*\n)*)", re.MULTILINE,
)


def patch_dock_transparency() -> bool:
    """Re-assert panel glass settings after a Global Theme apply.

    Every panel is explicitly translucent so Plasma's Adaptive mode cannot
    turn the top bar opaque when a window touches it. Non-floating panels also
    keep applets-only floating. Global Theme applies can drop these view-state
    keys, so every theme switch restores them. Returns True if the file changed.
    """
    prc = _xdg_config() / "plasmashellrc"
    if not prc.is_file():
        return False
    try:
        text = prc.read_text()
    except OSError:
        return False

    def fix(m: "re.Match[str]") -> str:
        section = m.group(0)
        if "panelOpacity=" in section:
            section = re.sub(r"panelOpacity=\d+", "panelOpacity=2", section)
        else:
            section = section.rstrip() + "\npanelOpacity=2\n"
        if "floating=0" in section:
            if "floatingApplets=" in section:
                section = re.sub(r"floatingApplets=\d+", "floatingApplets=1",
                                 section)
            else:
                section = section.rstrip() + "\nfloatingApplets=1\n"
        return section

    new_text = _PRC_PANEL_RE.sub(fix, text)
    if new_text != text:
        try:
            prc.write_text(new_text)
        except OSError:
            return False
        return True
    return False


def _read_portal_color_scheme() -> int | None:
    """The freedesktop appearance ``color-scheme`` as an int (0 no-pref,
    1 prefer-dark, 2 prefer-light), or None if the portal can't be read."""
    if not _has_session_dbus():
        return None
    for tool in (
        ["gdbus", "call", "--session", "--dest",
         "org.freedesktop.portal.Desktop", "--object-path",
         "/org/freedesktop/portal/desktop", "--method",
         "org.freedesktop.portal.Settings.ReadOne",
         "org.freedesktop.appearance", "color-scheme"],
        ["gdbus", "call", "--session", "--dest",
         "org.freedesktop.portal.Desktop", "--object-path",
         "/org/freedesktop/portal/desktop", "--method",
         "org.freedesktop.portal.Settings.Read",
         "org.freedesktop.appearance", "color-scheme"],
    ):
        if not _have("gdbus"):
            return None
        try:
            res = _run_user(tool, timeout=5, capture=True)
        except subprocess.TimeoutExpired:
            return None
        if res.returncode != 0:
            continue
        m = re.search(r"uint32\s+(\d+)", res.stdout)
        if m:
            return int(m.group(1))
    return None


def _wallpaper_path(mode: str) -> Path | None:
    data_home = Path(os.environ.get("XDG_DATA_HOME") or
                     str(Path.home() / ".local/share"))
    base = data_home / "wallpapers"
    auto = base / default_wallpaper()
    if auto.is_dir():
        return auto
    legacy = base / ("MacTahoe-Dark" if mode == "dark" else "MacTahoe-Light")
    return legacy if legacy.is_dir() else None


_WALLPAPER_STATE_VERSION = 3


def _wallpaper_state_file() -> Path:
    state_home = Path(os.environ.get("XDG_STATE_HOME") or
                      str(Path.home() / ".local/state"))
    return state_home / "mac-tahoe-liquid-kde" / "wallpapers.json"


def _empty_wallpaper_state() -> dict:
    return {
        "version": _WALLPAPER_STATE_VERSION,
        "initialized": False,
        "enabled": True,
        "user_screens": [],
        "last_applied": [],
    }


def _normalize_wallpaper_snapshot(value: object) -> list[dict[str, object]]:
    """Validate and order a per-screen wallpaper snapshot.

    Plasma containment IDs can change when a panel layout is rebuilt, while
    screen numbers remain the stable identity users care about. Keep one
    non-empty image URL per screen and discard malformed state rather than
    ever feeding it back into evaluateScript.
    """
    if not isinstance(value, list):
        return []
    by_screen: dict[int, str] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        screen = item.get("screen")
        image = item.get("image")
        if isinstance(screen, bool) or not isinstance(screen, int) \
                or screen < 0 or not isinstance(image, str) or not image:
            continue
        by_screen[screen] = image
    return [
        {"screen": screen, "image": by_screen[screen]}
        for screen in sorted(by_screen)
    ]


def _normalize_wallpaper_screens(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    return sorted({screen for screen in value
                   if isinstance(screen, int) and not isinstance(screen, bool)
                   and screen >= 0})


def _load_wallpaper_state() -> dict:
    state = _empty_wallpaper_state()
    try:
        raw = json.loads(_wallpaper_state_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return state
    if not isinstance(raw, dict):
        return state
    state["initialized"] = raw.get("initialized") is True
    if isinstance(raw.get("enabled"), bool):
        state["enabled"] = raw["enabled"]
    state["last_applied"] = _normalize_wallpaper_snapshot(
        raw.get("last_applied"))
    if raw.get("version") == _WALLPAPER_STATE_VERSION:
        state["user_screens"] = _normalize_wallpaper_screens(
            raw.get("user_screens"))
        return state

    # Version 1 remembered a separate custom wallpaper for each color mode.
    # Preserve ownership only for the screens present in those custom slots.
    modes = raw.get("modes")
    if raw.get("version") == 1 and isinstance(modes, dict):
        state["user_screens"] = sorted({
            int(item["screen"])
            for mode in ("light", "dark")
            for item in _normalize_wallpaper_snapshot(modes.get(mode))
        })
    elif raw.get("version") == 2 and raw.get("user_override") is True:
        # v2 ownership was global. Treat every screen in its last snapshot as
        # user-owned so upgrading cannot overwrite a wallpaper it preserved.
        state["user_screens"] = [
            int(item["screen"]) for item in state["last_applied"]
        ]
    return state


def _save_wallpaper_state(state: dict) -> bool:
    path = _wallpaper_state_file()
    # A login apply and the scheduled switch may overlap briefly. Give each
    # writer its own temporary file so one process cannot rename away another
    # process's pending write.
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)
        return True
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        return False


def _evaluate_plasma_script(script: str) -> str | None:
    for q in ("qdbus6", "qdbus-qt6", "qdbus"):
        if not _have(q):
            continue
        try:
            res = _run_user(
                [q, "org.kde.plasmashell", "/PlasmaShell",
                 "org.kde.PlasmaShell.evaluateScript", script],
                timeout=15, capture=True,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return res.stdout if res.returncode == 0 else None
    return None


def _build_wallpaper_capture_script() -> str:
    return """
var out = [];
var all = desktops();
for (var i = 0; i < all.length; i++) {
    var d = all[i];
    d.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
    out.push({screen: d.screen, image: d.readConfig('Image', '')});
}
print(JSON.stringify(out));
"""


def _parse_wallpaper_reply(output: str | None) -> list[dict[str, object]]:
    for line in reversed((output or "").strip().splitlines()):
        line = line.strip()
        if not line.startswith("["):
            continue
        try:
            return _normalize_wallpaper_snapshot(json.loads(line))
        except json.JSONDecodeError:
            return []
    return []


_DESKTOP_SECTION_RE = re.compile(r"^Containments\]\[([^]]+)$")
_WALLPAPER_SECTION_RE = re.compile(
    r"^Containments\]\[([^]]+)\]\[Wallpaper\]"
    r"\[org\.kde\.image\]\[General$",
)


def _wallpapers_from_config() -> list[dict[str, object]]:
    path = _xdg_config() / "plasma-org.kde.plasma.desktop-appletsrc"
    sections = _parse_ini(path)
    screens: dict[str, int] = {}
    for section, values in sections.items():
        match = _DESKTOP_SECTION_RE.fullmatch(section)
        if not match or values.get("plugin") not in _DESKTOP_PLUGINS:
            continue
        try:
            screen = int(values.get("lastScreen", ""))
        except ValueError:
            continue
        if screen >= 0:
            screens[match.group(1)] = screen
    snapshot: list[dict[str, object]] = []
    for section, values in sections.items():
        match = _WALLPAPER_SECTION_RE.fullmatch(section)
        if not match or match.group(1) not in screens:
            continue
        image = values.get("Image", "")
        if image:
            snapshot.append({"screen": screens[match.group(1)],
                             "image": image})
    return _normalize_wallpaper_snapshot(snapshot)


# Desktop containments: Folder View and the plain Desktop.
_DESKTOP_PLUGINS = ("org.kde.plasma.folder", "org.kde.desktopcontainment")


def _build_wallpaper_plugin_script() -> str:
    return """
var out = [];
var all = desktops();
for (var i = 0; i < all.length; i++) {
    out.push({screen: all[i].screen, plugin: all[i].wallpaperPlugin});
}
print(JSON.stringify(out));
"""


def _foreign_wallpaper_screens() -> set[int]:
    """Screens whose wallpaper is not an image (Picture of the Day, a
    colour, a slideshow...): the user's choice, whatever org.kde.image's
    leftover Image key says. Live from plasmashell, else from its config."""
    reply = _evaluate_plasma_script(_build_wallpaper_plugin_script())
    for line in reversed((reply or "").strip().splitlines()):
        line = line.strip()
        if not line.startswith("["):
            continue
        try:
            items = json.loads(line)
        except json.JSONDecodeError:
            break
        return {item["screen"] for item in items
                if isinstance(item, dict) and isinstance(item.get("screen"), int)
                and not isinstance(item.get("screen"), bool) and item["screen"] >= 0
                and item.get("plugin") not in (None, "", "org.kde.image")}
    sections = _parse_ini(_xdg_config() / "plasma-org.kde.plasma.desktop-appletsrc")
    screens: set[int] = set()
    for section, values in sections.items():
        if not _DESKTOP_SECTION_RE.fullmatch(section) \
                or values.get("plugin") not in _DESKTOP_PLUGINS:
            continue
        try:
            screen = int(values.get("lastScreen", ""))
        except ValueError:
            continue
        if screen >= 0 and values.get("wallpaperplugin", "org.kde.image") != "org.kde.image":
            screens.add(screen)
    return screens


def _current_wallpapers() -> list[dict[str, object]]:
    live = _parse_wallpaper_reply(
        _evaluate_plasma_script(_build_wallpaper_capture_script()))
    return live or _wallpapers_from_config()


def _capture_wallpapers_with_retry(*, attempts: int = 4,
                                   wait_seconds: int = 5) -> list[dict[str, object]]:
    # Plasma may answer before its desktop containments finish restoring.
    for attempt in range(attempts):
        if attempt:
            time.sleep(wait_seconds)
        current = _current_wallpapers()
        if current:
            return current
    return []


def _build_wallpaper_apply_script(
        snapshot: list[dict[str, object]], skip: set[int] = frozenset()) -> str:
    by_screen = {
        str(item["screen"]): item["image"]
        for item in _normalize_wallpaper_snapshot(snapshot)
    }
    fallback = next(iter(by_screen.values()), "")
    return f"""
var wanted = {json.dumps(by_screen)};
var fallback = {json.dumps(fallback)};
var skip = {json.dumps(sorted(skip))};
var all = desktops();
var applied = 0;
for (var i = 0; i < all.length; i++) {{
    var d = all[i];
    if (skip.indexOf(d.screen) >= 0) continue;
    var image = wanted[String(d.screen)] || fallback;
    if (!image) continue;
    d.wallpaperPlugin = 'org.kde.image';
    d.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
    d.writeConfig('Image', image);
    applied++;
}}
print(applied > 0 ? 'applied' : 'no-desktops');
"""


def _write_wallpapers_to_config(
        snapshot: list[dict[str, object]], skip: set[int] = frozenset()) -> bool:
    wanted = {
        int(item["screen"]): str(item["image"])
        for item in _normalize_wallpaper_snapshot(snapshot)
    }
    if not wanted:
        return False
    fallback = next(iter(wanted.values()))
    sections = _parse_ini(
        _xdg_config() / "plasma-org.kde.plasma.desktop-appletsrc")
    writes: list[bool] = []
    for section, values in sections.items():
        match = _DESKTOP_SECTION_RE.fullmatch(section)
        if not match or values.get("plugin") not in _DESKTOP_PLUGINS:
            continue
        try:
            screen = int(values.get("lastScreen", ""))
        except ValueError:
            continue
        if screen in skip:
            continue
        image = wanted.get(screen, fallback)
        writes.append(_kwrite(
            "--file", "plasma-org.kde.plasma.desktop-appletsrc",
            "--group", "Containments", "--group", match.group(1),
            "--group", "Wallpaper", "--group", "org.kde.image",
            "--group", "General", "--key", "Image", image,
        ))
    return bool(writes) and all(writes)


def _apply_wallpaper_snapshot(
        snapshot: list[dict[str, object]], skip: set[int] = frozenset()) -> bool:
    snapshot = _normalize_wallpaper_snapshot(snapshot)
    if not snapshot:
        return False
    reply = _evaluate_plasma_script(_build_wallpaper_apply_script(snapshot, skip))
    if any(line.strip() == "applied"
           for line in (reply or "").splitlines()):
        return True
    return (_write_wallpapers_to_config(snapshot, skip) if skip
            else _write_wallpapers_to_config(snapshot))


def _theme_wallpaper_snapshot(
        current: list[dict[str, object]], wp: Path) \
        -> list[dict[str, object]]:
    screens = [int(item["screen"]) for item in current] or [0]
    image = f"file://{wp}"
    return [{"screen": screen, "image": image} for screen in sorted(screens)]


def _wallpaper_image_is_theme_managed(
        image: str) -> bool:
    base = Path(os.environ.get("XDG_DATA_HOME") or
                str(Path.home() / ".local/share")) / "wallpapers"
    managed = [str(base / name).rstrip("/") for name in (
        "MacTahoe", "MacGoldenGate", "MacTahoe-Light", "MacTahoe-Dark")]
    if image.startswith("file://"):
        image = image[7:]
    image = image.rstrip("/")
    return any(image == path or image.startswith(path + "/contents/")
               for path in managed)


def _env_bool(name: str) -> bool | None:
    value = os.environ.get(name)
    if value is None:
        return None
    return value.lower() == "true"


def _apply_theme_wallpaper(mode: str) -> tuple[bool, Path | None]:
    wp = _wallpaper_path(mode)
    if wp is None or not _have("plasma-apply-wallpaperimage"):
        return (False, wp)
    try:
        ok = _run_user(["plasma-apply-wallpaperimage", str(wp)],
                       timeout=20).returncode == 0
        return (ok, wp)
    except (OSError, subprocess.TimeoutExpired):
        return (False, wp)


def _apply_wallpaper(
        mode: str, context: str = "user",
        current_snapshot: list[dict[str, object]] | None = None) -> bool:
    """Apply bundled wallpapers only on screens this project still owns.

    Each screen is compared with the last snapshot this switcher applied. A
    changed screen becomes user-owned and stays untouched while other screens
    continue following the 06:00/18:00 transitions. The explicit one-shot
    wallpaper reset opts every screen back into management.
    """
    state = _load_wallpaper_state()
    was_initialized = bool(state["initialized"])
    was_enabled = bool(state["enabled"])
    feature = _env_bool("FEAT_WALLPAPERS")
    enabled = was_enabled if feature is None else feature
    reset = _env_bool("MTTKDE_RESET_WALLPAPERS") is True
    existing_env = _env_bool("MTTKDE_EXISTING_INSTALL")
    existing = (was_initialized or context != "install") \
        if existing_env is None else existing_env
    current = (_capture_wallpapers_with_retry()
               if current_snapshot is None
               else _normalize_wallpaper_snapshot(current_snapshot))
    last_applied = _normalize_wallpaper_snapshot(state.get("last_applied"))
    user_screens = set(_normalize_wallpaper_screens(
        state.get("user_screens")))
    current_by_screen = {
        int(item["screen"]): str(item["image"]) for item in current
    }
    last_by_screen = {
        int(item["screen"]): str(item["image"]) for item in last_applied
    }

    # An unreadable existing desktop is not evidence that we own its
    # wallpapers. Keep the persisted ownership intact until capture succeeds.
    # An explicit reset is permission to replace wallpapers even without it.
    appletsrc = _xdg_config() / "plasma-org.kde.plasma.desktop-appletsrc"
    if not current and not reset and (was_initialized or
                                     (existing and appletsrc.exists())):
        print("wallpaper: capture failed after retries — desktop state "
              "unknown, leaving wallpapers untouched", file=sys.stderr)
        return True

    state["initialized"] = True
    state["enabled"] = bool(enabled)

    if not enabled:
        state["last_applied"] = current
        _save_wallpaper_state(state)
        return True

    if reset:
        user_screens.clear()
        last_applied = []
        last_by_screen.clear()

    if current and not reset:
        for screen, image in current_by_screen.items():
            if screen in user_screens:
                continue
            if screen in last_by_screen and image != last_by_screen[screen]:
                user_screens.add(screen)
            elif ((not was_initialized and existing) or not was_enabled) \
                    and not _wallpaper_image_is_theme_managed(image):
                # Preserve deliberate pre-state and feature-disabled choices
                # per screen instead of disabling every monitor.
                user_screens.add(screen)

    # A screen showing another wallpaper type (Picture of the Day...) is the
    # user's even though org.kde.image's Image key still names ours.
    foreign = set() if reset else _foreign_wallpaper_screens()
    state["user_screens"] = sorted(user_screens)
    current_user_screens = user_screens.intersection(current_by_screen) | foreign
    if current and current_user_screens >= set(current_by_screen):
        state["last_applied"] = current
        _save_wallpaper_state(state)
        return True

    if current_user_screens:
        wp = _wallpaper_path(mode)
        applied = _theme_wallpaper_snapshot(current, wp) if wp else []
        for item in applied:
            screen = int(item["screen"])
            if screen in current_user_screens:
                item["image"] = current_by_screen[screen]
        # Reapply even when the package URL is unchanged: MacTahoe contains
        # both images/ and images_dark/, so rewriting the mixed snapshot makes
        # Plasma refresh the managed screens after the color-mode transition.
        applied = [item for item in applied if int(item["screen"]) not in foreign]
        success = bool(applied) and (_apply_wallpaper_snapshot(applied, skip=foreign)
                                     if foreign else _apply_wallpaper_snapshot(applied))
    else:
        success, wp = _apply_theme_wallpaper(mode)
        applied = _theme_wallpaper_snapshot(current, wp) if wp else []
        if not success and applied:
            # The official helper is preferred, but a headless install or a
            # temporarily unavailable session bus must still leave correct
            # on-disk per-screen config for the final Plasma restart.
            success = _apply_wallpaper_snapshot(applied)

    if success:
        state["last_applied"] = applied
    _save_wallpaper_state(state)
    return success


def flush_icon_caches() -> None:
    home = Path.home()
    for sub in (".cache/icon-cache.kcache", ".cache/kiconthemes"):
        shutil.rmtree(home / sub, ignore_errors=True)


def _kvantum_theme(mode: str) -> str:
    return _surface_theme(KVANTUM_THEME_DARK if mode == "dark" else KVANTUM_THEME_LIGHT)


def _set_kvantum_theme(mode: str) -> None:
    """Select the mode-specific profile with or without Kvantum Manager.

    KDE neon Noble has no Qt 6 Kvantum package. Its bundled engine does not
    need the manager GUI; the engine reads this same config key directly.
    """
    theme = _kvantum_theme(mode)
    if _have("kvantummanager"):
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        try:
            _run_user(
                ["kvantummanager", "--set", theme],
                timeout=15,
                env=env,
            )
        except subprocess.TimeoutExpired:
            pass
        return

    if not _have("kwriteconfig6"):
        return
    config = _xdg_config() / "Kvantum/kvantum.kvconfig"
    try:
        config.parent.mkdir(parents=True, exist_ok=True)
        _run_user(
            [
                "kwriteconfig6", "--file", str(config),
                "--group", "General", "--key", "theme", theme,
            ],
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


_GTK4_FINDER_START = ("/* >>> MacOS-Tahoe-KDE Finder block "
                      "(src/offline/nautilus/finder-gtk4.css) >>> */")
_GTK4_FINDER_END = "/* <<< MacOS-Tahoe-KDE Finder block <<< */"


def _gtk4_css_is_replaceable(path: Path, themes_root: Path) -> bool:
    """Whether gtk.css is generated/project-owned rather than user CSS.

    kde-gtk-config may write either a one-line colors import or the selected
    theme's complete stylesheet followed by that import. Releases 0.37.x-
    0.38.x recognized only the first form, so a generated LIGHT sheet was
    mistaken for user CSS and survived every dark apply.
    """
    if not path.exists() and not path.is_symlink():
        return True
    if path.is_symlink():
        try:
            return path.readlink().name in {"gtk-Dark.css", "gtk-Light.css"}
        except OSError:
            return False
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    import_line = "@import 'colors.css';"
    if text == import_line:
        return True
    if text.endswith(import_line):
        text = text[:-len(import_line)].rstrip()
    # A sheet carrying our Finder block is ours even when it no longer
    # matches the installed one: kde-gtk-config re-expands the previous
    # release's sheet, and that stale copy must not pin the old look.
    if _GTK4_FINDER_START in text and _GTK4_FINDER_END in text:
        return True
    for variant in ("MacTahoeLiquidKde-Light", "MacTahoeLiquidKde-Dark",
                    "MacTahoeLiquidKde-Light" + REDUCED_SUFFIX,
                    "MacTahoeLiquidKde-Dark" + REDUCED_SUFFIX):
        gtk4 = themes_root / variant / "gtk-4.0"
        for name in ("gtk.css", "gtk-Light.css", "gtk-Dark.css",
                     "gtk-dark.css"):
            candidate = gtk4 / name
            try:
                if candidate.is_file() and candidate.read_text(
                        encoding="utf-8").strip() == text:
                    return True
            except OSError:
                continue
    return False


def _apply_local_extras(mode: str) -> None:
    # widgetStyle remains the Qt plugin name "kvantum", but the profile
    # itself must match the mode. Both SVGs contain literal surface colors;
    # respect_DE=true cannot recolor those assets.
    _set_kvantum_theme(mode)

    home = Path.home()
    gtk_dest = home / ".themes"
    gtk_theme = _surface_theme("MacTahoeLiquidKde-Dark" if mode == "dark" else "MacTahoeLiquidKde-Light")

    if (gtk_dest / gtk_theme).is_dir():
        _qdbus("org.kde.GtkConfig", "/GtkConfig",
               "org.kde.GtkConfig.setGtkTheme", gtk_theme)
        if _have("gsettings"):
            for args in (
                ["set", "org.gnome.desktop.interface", "gtk-theme", gtk_theme],
                ["set", "org.gnome.desktop.wm.preferences",
                 "button-layout", "close,minimize,maximize:"],
                ["set", "org.gnome.desktop.interface", "color-scheme",
                 "prefer-dark" if mode == "dark" else "prefer-light"],
            ):
                try:
                    _run_user(["gsettings", *args], timeout=5)
                except subprocess.TimeoutExpired:
                    pass

        # Nautilus is a libadwaita application. It follows the system
        # light/dark preference, but it does not consume a third-party GTK
        # theme deeply enough to get our window chrome. GTK's user stylesheet
        # is therefore the compatibility layer and is refreshed by every
        # explicit or scheduled theme switch.
        gtk4_src = gtk_dest / gtk_theme / "gtk-4.0"
        gtk4_dest = home / ".config/gtk-4.0"
        if gtk4_src.is_dir():
            gtk4_dest.mkdir(parents=True, exist_ok=True)
            for sub in ("assets", "windows-assets"):
                src = gtk4_src / sub
                if not src.is_dir():
                    continue
                try:
                    shutil.copytree(src, gtk4_dest / sub, dirs_exist_ok=True)
                except OSError as exc:
                    print(f"theme apply: gtk4 {sub} copy skipped: {exc}",
                          file=sys.stderr)
            for fn in ("gtk-Dark.css", "gtk-Light.css"):
                src = gtk4_src / fn
                if src.is_file():
                    try:
                        shutil.copy2(src, gtk4_dest / fn)
                    except OSError as exc:
                        print(f"theme apply: gtk4 {fn} copy skipped: {exc}",
                              file=sys.stderr)

            gtk4_css = gtk4_dest / "gtk.css"
            try:
                if _gtk4_css_is_replaceable(gtk4_css, gtk_dest):
                    if gtk4_css.is_symlink() or gtk4_css.exists():
                        gtk4_css.unlink()
                    gtk4_css.symlink_to(f"gtk-{mode.capitalize()}.css")
                else:
                    print("theme apply: custom gtk4 gtk.css preserved; "
                          "Nautilus theme override skipped", file=sys.stderr)
            except OSError as exc:
                print(f"theme apply: gtk4 gtk.css link skipped: {exc}",
                      file=sys.stderr)

    flush_icon_caches()
    cache = home / ".cache"
    for f in cache.glob("ksvg-elements"):
        try: f.unlink()
        except OSError: pass
    for f in cache.glob("plasma_theme_*"):
        try: f.unlink()
        except OSError: pass


def _xdg_data() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share"))


def custom_icon_theme(base: str) -> str:
    """The Icon Manager's overlay of `base` when it has one (an icon theme
    holding only the user's custom app icons, inheriting `base`)."""
    overlay = f"{base}-custom"
    theme = _xdg_data() / "icons" / overlay
    # An overlay emptied while in use is removed once the session left it.
    if (theme / "index.theme").is_file() and any((theme / "apps/512").glob("*.png")):
        return overlay
    return base


def _notify_icon_theme_changed() -> bool:
    """Tell running KDE applications to reload their icon theme.

    KConfig's --notify flag only informs KConfig watchers. KIconLoader listens
    for KGlobalSettings.notifyChange(IconChanged), so writing kdeglobals alone
    leaves existing processes on the previous light/dark theme until restart.
    """
    if not _has_session_dbus() or not _have("dbus-send"):
        return False
    try:
        result = _run_user(
            ["dbus-send", "--session", "--type=signal", "/KGlobalSettings",
             "org.kde.KGlobalSettings.notifyChange", "int32:4", "int32:0"],
            timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


# macOS keeps its pointer in dark mode: the black arrow with a white outline
# and white hands with a black one. The inverted MacTahoeLiquidKde-Dark set
# stays installed for whoever picks it.
MACOS_CURSORS = "MacTahoeLiquidKde"


def write_kde_theme_config(
        mode: str, *, force_color_reload: bool = False) -> bool:
    if not _have("kwriteconfig6"):
        return False

    if mode == "dark":
        laf, icon, cursor = LAF_DARK, "MacTahoeLiquidKde-Icons-dark", MACOS_CURSORS
        scheme, plasma = "MacTahoeLiquidKdeDark", "MacTahoeLiquidKde-Dark"
        widget, aurorae = KVANTUM_STYLE, "__aurorae__svg__MacTahoeLiquidKde-Dark"
    else:
        laf, icon, cursor = LAF_LIGHT, "MacTahoeLiquidKde-Icons", MACOS_CURSORS
        scheme, plasma = "MacTahoeLiquidKdeLight", "MacTahoeLiquidKde-Light"
        widget, aurorae = KVANTUM_STYLE, "__aurorae__svg__MacTahoeLiquidKde-Light"

    plasma = _surface_theme(plasma)

    # Ask KDE to apply the palette while kdeglobals still names the outgoing
    # scheme.  If we stamp General/ColorScheme first, KDE can conclude the
    # target is already active and skip its live palette notification, leaving
    # plasmashell popups on the previous colors even though disk is correct.
    #
    # Reinstall is the self-healing path for an already-mixed session.  When
    # the requested name is already on disk, briefly apply the opposite scheme
    # first so KDE observes a real transition; the installer's final Plasma
    # restart then loads the converged target into every containment.
    if force_color_reload and _kread(
            "kdeglobals", "General", "ColorScheme") == scheme:
        opposite = ("MacTahoeLiquidKdeLight" if mode == "dark"
                    else "MacTahoeLiquidKdeDark")
        apply_color_scheme(opposite)
    color_ok = apply_color_scheme(scheme)
    icon = custom_icon_theme(icon)

    # AutomaticLookAndFeel=false: Plasma's sunrise/sunset scheduler must
    # not fight our 06:00 / 18:00 timer (idempotent).
    fixed = (
        ("kdeglobals", "KDE", "LookAndFeelPackage", laf),
        ("kdeglobals", "KDE", "AutomaticLookAndFeel", "false"),
        ("kdeglobals", "Icons", "Theme", icon),
        ("kdeglobals", "General", "ColorScheme", scheme),
        ("kdeglobals", "KDE", "widgetStyle", widget),
        ("kcminputrc", "Mouse", "cursorTheme", cursor),
        ("plasmarc", "Theme", "name", plasma),
    )
    for file, group, key, value in fixed:
        if not _kwrite("--file", file, "--group", group,
                       "--key", key, value):
            return False
    _notify_icon_theme_changed()
    for key, value in (
        ("library", "org.kde.kwin.aurorae"),
        ("theme", aurorae),
        ("BorderSize", "Tiny"),
        ("ButtonsOnLeft", "XIA"),
        ("ButtonsOnRight", ""),
    ):
        if not _kwrite("--file", "kwinrc", "--group", "org.kde.kdecoration2",
                       "--key", key, value):
            return False

    # The name is now stamped: make sure the palette under it is the scheme's.
    return ensure_color_scheme(scheme) and color_ok


def _live_tool_env() -> dict[str, str]:
    _sync_session_env()
    env = os.environ.copy()
    if env.get("WAYLAND_DISPLAY") and not env.get("QT_QPA_PLATFORM"):
        env["QT_QPA_PLATFORM"] = "wayland"
    return env


def _run_live_plasma_tool(cmd: list[str], *, timeout_seconds: int = 20) -> bool:
    if os.environ.get("MAC_TAHOE_SKIP_LIVE_APPLY", "").lower() == "true":
        return False
    try:
        return _run_user(cmd, timeout=timeout_seconds,
                         env=_live_tool_env()).returncode == 0
    except subprocess.TimeoutExpired:
        return False


_LAF_APPLY_ATTEMPTS = 3
_LAF_APPLY_FIRST_WAIT_SECONDS = 2
_LAF_APPLY_RETRY_SLEEP_SECONDS = 6

# Our own KWin effects: we manage these on purpose, so they're never treated
# as user effects to watch over. Everything else the user enabled in [Plugins]
# is a third-party effect we must not silently break.
_OWN_KWIN_EFFECT_KEYS = frozenset({
    # better_blur_dx / glass: the Better Blur DX and Glass effects of
    # earlier releases.
    "better_blur_dxEnabled", "liquidglassEnabled", "glassEnabled", "blurEnabled",
})


def _kwinrc_path() -> Path:
    return _xdg_config() / "kwinrc"


def _effect_id_for_key(key: str) -> str:
    """kwinrc [Plugins] key -> KWin effect id. Third-party binary effects use
    the ``kwin4_effect_<name>`` id (e.g. shapecornersEnabled -> the effect KWin
    reports as ``kwin4_effect_shapecorners`` or, on some builds, ``shapecorners``
    -- we match either)."""
    return key[:-len("Enabled")] if key.endswith("Enabled") else key


def _snapshot_foreign_effects() -> list[str]:
    """The effect ids the user has ENABLED in kwinrc [Plugins] that aren't ours.
    A theme switch fires org.kde.KWin.reconfigure, which makes KWin re-scan and
    re-load effects; a third-party COMPILED effect whose .so is ABI-incompatible
    with the running KWin (common after a KWin update) fails to load and drops
    out of the live effect list. The user's config key stays true, so this is a
    runtime-load failure, not a config loss -- we can't fix their binary, but we
    must not let it happen SILENTLY (#46)."""
    plugins = _parse_ini(_kwinrc_path()).get("Plugins", {})
    return [
        _effect_id_for_key(key)
        for key, value in plugins.items()
        if key.endswith("Enabled") and key not in _OWN_KWIN_EFFECT_KEYS
        and value.strip().lower() == "true"
    ]


def _kwin_loaded_effects() -> set[str] | None:
    """KWin's currently-LOADED effect ids (not activeEffects -- an enabled but
    idle effect is loaded yet not active). None when the query can't run (no
    session bus / no qdbus / timeout), so callers degrade to silence rather
    than a false 'effect broke' warning on headless or first-login installs."""
    if not _has_session_dbus():
        return None
    for q in ("qdbus6", "qdbus-qt6", "qdbus"):
        if not _have(q):
            continue
        try:
            res = _run_user(
                [q, "org.kde.KWin", "/Effects",
                 "org.kde.kwin.Effects.loadedEffects"],
                timeout=10, capture=True)
        except subprocess.TimeoutExpired:
            return None
        if res.returncode != 0:
            return None
        return {e.strip() for e in res.stdout.replace("\n", ",").split(",")
                if e.strip()}
    return None


def _effect_is_loaded(effect: str, loaded: set[str]) -> bool:
    return (
        effect in loaded
        or f"kwin4_effect_{effect}" in loaded
        or any(effect in candidate for candidate in loaded)
    )


def _restore_or_warn_foreign_effects(enabled_before: list[str]) -> list[str]:
    """Restore third-party effects after KWin's global reconfigure.

    A reconfigure can leave a compiled effect such as ``shapecorners``
    unloaded.  First ask KWin to load every missing effect again; warn only if
    it is still missing after bounded retries.  The user's Enabled key is
    never changed, so an ABI-incompatible effect remains recoverable after it
    is rebuilt instead of being silently disabled.
    """
    if not enabled_before:
        return []
    loaded = _kwin_loaded_effects()
    if loaded is None:
        return []

    missing = [
        effect for effect in enabled_before
        if not _effect_is_loaded(effect, loaded)
    ]
    for effect in missing:
        _qdbus("org.kde.KWin", "/Effects",
               "org.kde.kwin.Effects.loadEffect", effect)

    # Effect loading is asynchronous. Give explicitly restored effects a
    # bounded window to appear before reporting a real failure.
    for attempt in range(3):
        if not missing:
            break
        if attempt:
            time.sleep(1)
        refreshed = _kwin_loaded_effects()
        if refreshed is None:
            return []
        missing = [
            effect for effect in missing
            if not _effect_is_loaded(effect, refreshed)
        ]

    for effect in missing:
        print(
            f"theme apply: your KWin effect '{effect}' is enabled but KWin "
            "could not load it after the theme switch. The switcher retried "
            "it and left your setting enabled; rebuild/reinstall the effect "
            "for the current KWin if it remains absent.",
            file=sys.stderr,
        )
    return missing


def reconfigure_kwin_preserving_foreign_effects() -> list[str]:
    """Reconfigure KWin, then restore every enabled third-party effect."""
    foreign_effects = _snapshot_foreign_effects()
    _qdbus("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")
    missing = _restore_or_warn_foreign_effects(foreign_effects)
    _restore_own_compiled_effects()
    return missing


# Our own compiled effects are just as exposed to the reconfigure ABI-drop
# risk documented on _snapshot_foreign_effects as any third-party one --
# being "ours" doesn't make the .so any less likely to fall out of KWin's
# loaded-effect list. The installer reloads the Glass effect once at
# install time, but every routine light/dark switch reconfigures KWin too
# (see above), so this path needs the same protection or the effect can go
# dark until the next ./install.
_OWN_COMPILED_EFFECTS = (GLASS_EFFECT,)


def refresh_acrylic_glass() -> None:
    """Recreate enabled glass after Plasma has replaced its popup surfaces.

    Reconfigure alone can leave stale popup geometry after an appearance
    transition, observed on a 150% desktop. Reloading rebuilds the surface
    subscriptions and masks without changing the user's radius settings.
    """
    _restore_own_compiled_effects(refresh=True)


def _restore_own_compiled_effects(*, refresh: bool = False) -> None:
    plugins = _parse_ini(_kwinrc_path()).get("Plugins", {})
    enabled = [
        effect for effect in _OWN_COMPILED_EFFECTS
        if plugins.get(f"{effect}Enabled", "").strip().lower() == "true"
    ]
    if not enabled:
        return
    loaded = _kwin_loaded_effects()
    if loaded is None:
        return
    for effect in enabled:
        if _effect_is_loaded(effect, loaded):
            if not refresh:
                continue
            _qdbus("org.kde.KWin", "/Effects",
                   "org.kde.kwin.Effects.unloadEffect", effect)
        _qdbus("org.kde.KWin", "/Effects",
               "org.kde.kwin.Effects.loadEffect", effect)
        for attempt in range(3):
            time.sleep(1)
            refreshed = _kwin_loaded_effects()
            if refreshed is not None and _effect_is_loaded(effect, refreshed):
                break
        else:
            print(
                f"theme apply: your KWin effect '{effect}' is enabled but "
                "KWin could not load it after the theme switch. Rebuild/"
                "reinstall the effect for the current KWin if it remains "
                "absent.",
                file=sys.stderr,
            )


GLASS_STYLES = ("tahoe", "frosted")
DEFAULT_GLASS_STYLE = "tahoe"


def _glass_style_path() -> Path:
    return _xdg_config() / "mac-tahoe-liquid-kde/glass-style"


def glass_style() -> str:
    try:
        style = _glass_style_path().read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return DEFAULT_GLASS_STYLE
    return style if style in GLASS_STYLES else DEFAULT_GLASS_STYLE


def glass_preset_name(mode: str, style: str | None = None) -> str:
    style = style or glass_style()
    return f"{mode}-{style}"


def glass_preset(mode: str, style: str | None = None, tint: str | None = None) -> dict:
    """The Acrylic Glass keys of `mode` in the glass style, with the Dock
    tint's: the neutral tint takes the colour out of all the glass."""
    preset = dict(GLASS_PRESETS[glass_preset_name(mode, style)])
    if (tint or dock_tint()) == "neutral":
        preset.update(Saturation="0")
    return preset


def set_glass_style(style: str) -> bool:
    if style not in GLASS_STYLES:
        return False
    path = _glass_style_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(style + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


def current_mode() -> str:
    laf = _kread("kdeglobals", "KDE", "LookAndFeelPackage")
    return "light" if laf == LAF_LIGHT else "dark"


COLORIZER_ID = "luisbocanegra.panel.colorizer"


# The menu bar's text and icons: white in both appearances, as macOS draws
# them over the wallpaper. Panel Colorizer only recolours the widgets'
# foreground; their background stays off.
TOP_BAR_FOREGROUND = "#ffffff"
# Tahoe's dark veil behind the transparent menu bar, measured on a macOS
# Tahoe capture over its bare wallpaper (Golden Gate, shown at 1920 px):
# the desktop at 0.80 under the bar, back to 1.0 some 80 px down. A panel
# cannot draw past its 30 px, so the veil fades from 20 % black at the top
# edge to nothing at the bar's bottom edge (Panel Colorizer's panel layer,
# a vertical gradient).
TOP_BAR_SCRIM = '{"enabled": true, "backgroundColor": {"enabled": true, "sourceType": 5, "alpha": 1, "gradient": {"orientation": 1, "stops": [{"color": "#33000000", "position": 0}, {"color": "#2b000000", "position": 0.45}, {"color": "#12000000", "position": 0.8}, {"color": "#00000000", "position": 1}]}}}'


def _top_bar_script(frosted: bool) -> str:
    """Plasma script setting the menu bar's native background through its
    Panel Colorizer: hidden for Tahoe (as the layout installs it), back on
    for frosted; Tahoe's dark veil (TOP_BAR_SCRIM), off for frosted; and its
    white text and icons. Only those settings change;
    the rest of the user's Colorizer settings stay."""
    background = ('{"enabled": true, "opacity": 1, "shadow": false}' if frosted
                  else '{"enabled": false, "opacity": 0, "shadow": false}')
    # Tahoe's veil only: frosted has its own translucent background.
    scrim = '{"enabled": false}' if frosted else TOP_BAR_SCRIM
    return (
        "panels().forEach(function (panel) {\n"
        "    if (panel.location !== \"top\") return;\n"
        f"    panel.widgets(\"{COLORIZER_ID}\").forEach(function (widget) {{\n"
        "        widget.currentConfigGroup = [\"General\"];\n"
        "        var settings = {};\n"
        "        try { settings = JSON.parse(widget.readConfig(\"globalSettings\", \"{}\")) || {}; }\n"
        "        catch (e) { settings = {}; }\n"
        "        settings.nativePanel = settings.nativePanel || {};\n"
        f"        settings.nativePanel.background = {background};\n"
        f"        settings.panel = settings.panel || {{}};\n"
        f"        settings.panel.normal = {scrim};\n"
        "        [\"widgets\", \"trayWidgets\"].forEach(function (key) {\n"
        "            settings[key] = settings[key] || {};\n"
        "            var normal = settings[key].normal = settings[key].normal || {};\n"
        "            normal.enabled = true;\n"
        "            normal.backgroundColor = normal.backgroundColor || {};\n"
        "            normal.backgroundColor.enabled = false;\n"
        "            normal.foregroundColor = normal.foregroundColor || {};\n"
        "            normal.foregroundColor.enabled = true;\n"
        "            normal.foregroundColor.sourceType = 0;\n"
        "            normal.foregroundColor.alpha = 1;\n"
        f"            normal.foregroundColor.custom = \"{TOP_BAR_FOREGROUND}\";\n"
        "        });\n"
        "        widget.writeConfig(\"globalSettings\", JSON.stringify(settings));\n"
        "        print(\"ok\\n\");\n"
        "    });\n"
        "});\n"
    )


def apply_top_bar_style(style: str | None = None) -> bool:
    """The menu bar of the style: no background (Tahoe) or the translucent,
    blurred bar macOS had before Tahoe (frosted). Needs a running Plasma."""
    style = style or glass_style()
    out = _evaluate_plasma_script(_top_bar_script(style == "frosted"))
    return bool(out) and "ok" in out


def apply_glass_preset(mode: str) -> bool:
    """Write the mode's Glass blur, in the chosen style, and have KWin
    re-read it. Only while the effect is enabled: a user who turned it off
    keeps it off."""
    plugins = _parse_ini(_kwinrc_path()).get("Plugins", {})
    if plugins.get(f"{GLASS_EFFECT}Enabled", "").strip().lower() != "true":
        return False
    written = True
    for key, value in glass_preset(mode).items():
        written = _kwrite("--file", "kwinrc", "--group", GLASS_GROUP,
                          "--key", key, value) and written
    _qdbus("org.kde.KWin", "/Effects",
           "org.kde.kwin.Effects.reconfigureEffect", GLASS_EFFECT)
    return written


def _apply_lookandfeel_live(laf: str) -> bool:
    """Up to three attempts: 2s lead-in, then 6s between retries. On a
    fresh login plasma-apply-lookandfeel exits 0 against a not-yet-ready
    bus WITHOUT re-rendering — don't shorten the lead-in."""
    if not _have("plasma-apply-lookandfeel"):
        return False
    for attempt in range(_LAF_APPLY_ATTEMPTS):
        if attempt == 0:
            time.sleep(_LAF_APPLY_FIRST_WAIT_SECONDS)
        else:
            time.sleep(_LAF_APPLY_RETRY_SLEEP_SECONDS)
        if _run_live_plasma_tool(
            ["plasma-apply-lookandfeel", "-a", laf, "--keep-auto"],
        ):
            return True
    return False


def apply_cursortheme_live(theme: str) -> bool:
    if not _have("plasma-apply-cursortheme"):
        return False
    return _run_live_plasma_tool(["plasma-apply-cursortheme", theme])


def _broadcast_widget_style_change(style: str) -> bool:
    """True when at least one signal lands — the portal endpoints are
    optional and must not turn a delivered change into a failure."""
    if not _has_session_dbus():
        return False
    sent = False
    for cmd in (
        ["dbus-send", "--session", "--type=signal",
         "/KGlobalSettings", "org.kde.KGlobalSettings.notifyChange",
         "int32:2", "int32:0"],
        ["dbus-send", "--session", "--type=signal",
         "/org/freedesktop/portal/desktop",
         "org.freedesktop.impl.portal.Settings.SettingChanged",
         "string:org.kde.kdeglobals.KDE", "string:widgetStyle",
         f"variant:string:{style}"],
        ["dbus-send", "--session", "--type=signal",
         "/org/freedesktop/portal/desktop",
         "org.freedesktop.portal.Settings.SettingChanged",
         "string:org.kde.kdeglobals.KDE", "string:widgetStyle",
         f"variant:string:{style}"],
    ):
        try:
            sent = _run_user(cmd, timeout=5).returncode == 0 or sent
        except subprocess.TimeoutExpired:
            pass
    return sent


def cycle_widget_style_live(target: str) -> bool:
    """Kvantum can't hot-reload kvconfig; only QApplication::setStyle()
    re-instantiates the plugin — so write Breeze, broadcast, write the
    target back (https://github.com/tsujan/Kvantum/discussions/975).
    SIGTERM/SIGINT mid-cycle would strand widgetStyle=Breeze on disk;
    the finally + signal handler guarantee disk ends at the target.
    False when a widgetStyle write fails or a broadcast phase lands
    nothing — silent success here would mask a sudo'd-uninstall failure."""
    if not _have("kwriteconfig6") or not _has_session_dbus():
        return False
    if not target:
        return False

    phase_ok: list[bool] = []

    def _restore_target() -> None:
        phase_ok.append(_kwrite("--file", "kdeglobals", "--group", "KDE",
                                "--key", "widgetStyle", target))
        phase_ok.append(bool(_broadcast_widget_style_change(target)))

    interrupted: list[int] = []

    def _on_signal(signum, _frame):
        interrupted.append(signum)

    # signal.signal() only works on the main thread. The installer UI runs
    # steps off-thread, where registering a handler raises ValueError; guard it
    # so the cycle still runs (it just can't intercept a mid-cycle SIGTERM
    # there — the finally still restores the target on disk).
    handlers_installed = False
    old_term = old_int = None
    if threading.current_thread() is threading.main_thread():
        try:
            old_term = signal.signal(signal.SIGTERM, _on_signal)
            old_int = signal.signal(signal.SIGINT, _on_signal)
            handlers_installed = True
        except ValueError:
            handlers_installed = False
    try:
        phase_ok.append(_kwrite("--file", "kdeglobals", "--group", "KDE",
                                "--key", "widgetStyle", "Breeze"))
        phase_ok.append(bool(_broadcast_widget_style_change("Breeze")))
        time.sleep(0.4)
    finally:
        _restore_target()
        if handlers_installed:
            signal.signal(signal.SIGTERM, old_term)
            signal.signal(signal.SIGINT, old_int)
    if interrupted:
        raise SystemExit(128 + interrupted[0])
    return all(phase_ok)


def _apply_unlocked(mode: str, context: str = "user") -> bool:
    """Config writes + best-effort live niceties. Returns False when the
    core config writes fail (kwriteconfig6 missing or a write error).
    Live LAF is skipped during install — Plasma restarts anyway and
    running both races plasmashell's QML teardown."""
    cursor = MACOS_CURSORS
    widget = KVANTUM_STYLE
    laf = LAF_DARK if mode == "dark" else LAF_LIGHT

    # Record which third-party KWin effects the user has enabled before we
    # trigger the reconfigure that makes KWin re-scan effects. If one fails to
    # reload (an ABI-incompatible third-party .so), we warn by name instead of
    # letting it break silently (#46). We never touch its config key.
    foreign_effects = _snapshot_foreign_effects()

    # Capture before the live look-and-feel apply.  Even if a third-party LAF
    # carries wallpaper defaults, it must not erase the outgoing custom choice
    # before our per-mode state has seen it.
    wallpaper_before = _capture_wallpapers_with_retry()

    # Apply the live look-and-feel while Plasma still sees the outgoing
    # package in kdeglobals.  Writing the target package first can make the
    # live tool treat parts of the transition as already current, leaving
    # individual panel containments on the outgoing Plasma theme.
    if context != "install":
        if not _apply_lookandfeel_live(laf):
            print("theme apply: live look-and-feel apply skipped",
                  file=sys.stderr)

    try:
        # Before the Kvantum profile is (re)selected below, so it loads in
        # the accent colour.
        apply_kvantum_accent()
    except Exception as exc:
        print(f"theme apply: Kvantum accent failed, continuing: {exc!r}",
              file=sys.stderr)
    config_ok = write_kde_theme_config(
        mode, force_color_reload=context == "install",
    )
    if not config_ok:
        print("theme apply: core KDE config writes failed, theme not "
              "fully applied", file=sys.stderr)
    try:
        # Before the SVG caches are dropped (in the extras), so the Plasma
        # theme reload picks it up.
        apply_dock_tint()
        _apply_local_extras(mode)
    except Exception as exc:
        print(f"theme apply: extras step failed, continuing: {exc!r}",
              file=sys.stderr)
    try:
        apply_glass_preset(mode)
    except Exception as exc:
        print(f"theme apply: glass preset failed, continuing: {exc!r}",
              file=sys.stderr)
    try:
        _apply_wallpaper(mode, context=context,
                         current_snapshot=wallpaper_before)
    except Exception as exc:
        print(f"theme apply: wallpaper step failed, continuing: {exc!r}",
              file=sys.stderr)
    if not apply_cursortheme_live(cursor):
        print("theme apply: live cursor apply skipped", file=sys.stderr)
    if not cycle_widget_style_live(widget):
        print("theme apply: widget-style cycle skipped", file=sys.stderr)
    # Keep the dock translucent so the glass shows through (a theme apply can
    # drop panelOpacity, painting an opaque black panel over the effect).
    patch_dock_transparency()
    _qdbus("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")
    # After KWin re-scans effects, restore a user's third-party effects and
    # warn if one still cannot load (best-effort when KWin is unavailable).
    _restore_or_warn_foreign_effects(foreign_effects)
    _restore_own_compiled_effects()
    return config_ok


def apply(mode: str, context: str = "user") -> bool:
    """Run one complete, cross-process-serialized theme transition."""
    with _theme_transition_lock():
        return _apply_unlocked(mode, context=context)


def follow_system() -> int:
    """Apply whichever mode the desktop currently wants (System Settings /
    quick-settings choice), so a NATIVE light/dark toggle drives our full
    theme. No-op success when the current mode can't be read (don't guess and
    fight the user's real state).

    This is an explicit one-shot command, not a background watcher. Automatic
    switching remains controlled only by the 06:00/18:00 scheduler."""
    with _theme_transition_lock():
        mode = detect_mode_by_system()
        if mode is None:
            return 0
        return 0 if _apply_unlocked(mode, context="user") else 1


# ── Desktop & Dock ───────────────────────────────────────────────────
# What macOS' Desktop & Dock settings offer, on the Plasma Dock and KWin.
# Plasma keeps the Dock's own settings (its panel and its task manager's
# `dockMagnification`), KWin the rest: nothing is duplicated in a state
# file, so `dock` / `minimize` / `hot-corners` without a value print what
# is in use.
DOCK_SIZE_RANGE = (40, 96)
DOCK_MAGNIFICATION_RANGE = (100, 200)
_DOCK_TASKS_RE = r"/^org\.kde\.(mac\.tahoe\.liquid\.(icon)?task|plasma\.icontasks)/"
# Theme Settings shows `dock` output: {"autohide": bool, "size": int,
# "magnification": int}, one line of JSON, or nothing without a Dock.
_DOCK_SCRIPT = (
    "var out = null;\n"
    "panels().forEach(function (panel) {\n"
    "    if (out !== null || panel.location !== \"bottom\") return;\n"
    "    var tasks = panel.widgets().filter(function (w) {\n"
    f"        return {_DOCK_TASKS_RE}.test(w.type);\n"
    "    });\n"
    "    if (!tasks.length) return;\n"
    "    %s\n"
    "    tasks[0].currentConfigGroup = [\"General\"];\n"
    "    out = {autohide: panel.hiding === \"autohide\", size: panel.height,\n"
    "           magnification: parseInt(tasks[0].readConfig(\"dockMagnification\", 160)) || 160};\n"
    "});\n"
    "print(out === null ? \"\" : JSON.stringify(out));\n"
)


def _dock_script(change: str = "") -> str:
    return _DOCK_SCRIPT % change


def dock_settings() -> dict | None:
    out = _evaluate_plasma_script(_dock_script())
    try:
        settings = json.loads(out.strip()) if out and out.strip() else None
    except ValueError:
        return None
    return settings if isinstance(settings, dict) else None


def set_dock(key: str, value: str) -> bool:
    """autohide on|off, size N (px), magnification N (%, 100: off)."""
    if key == "autohide" and value in ("on", "off"):
        change = f"panel.hiding = \"{'autohide' if value == 'on' else 'none'}\";"
    elif key in ("size", "magnification") and value.isdigit():
        low, high = DOCK_SIZE_RANGE if key == "size" else DOCK_MAGNIFICATION_RANGE
        number = max(low, min(high, int(value)))
        if key == "size":
            change = f"panel.height = {number};"
        else:
            # Every task manager of the Dock: the minimized-windows one too.
            change = ("tasks.forEach(function (w) { w.currentConfigGroup = [\"General\"]; "
                      f"w.writeConfig(\"dockMagnification\", {number}); }});")
    else:
        return False
    out = _evaluate_plasma_script(_dock_script(change))
    return bool(out and out.strip())


# Minimize windows using: Genie (KWin's Magic Lamp) or Scale (Squash, KWin's
# default).
MINIMIZE_EFFECTS = {"genie": "magiclamp", "scale": "squash"}


def minimize_effect() -> str:
    plugins = _parse_ini(_kwinrc_path()).get("Plugins", {})
    return "genie" if plugins.get("magiclampEnabled", "").strip().lower() == "true" else "scale"


def set_minimize_effect(name: str) -> bool:
    if name not in MINIMIZE_EFFECTS:
        return False
    ok = True
    for other, effect in MINIMIZE_EFFECTS.items():
        on = other == name
        ok = _kwrite("--file", "kwinrc", "--group", "Plugins",
                     "--key", f"{effect}Enabled", "true" if on else "false") and ok
        _qdbus("org.kde.KWin", "/Effects",
               f"org.kde.kwin.Effects.{'loadEffect' if on else 'unloadEffect'}", effect)
    return ok


# Hot corners, macOS' actions on KWin's screen edges. KWin's border ids:
# 1 top right, 3 bottom right, 5 bottom left, 7 top left, 9 none.
HOT_CORNERS = {"top-left": ("7", "TopLeft"), "top-right": ("1", "TopRight"),
               "bottom-left": ("5", "BottomLeft"), "bottom-right": ("3", "BottomRight")}
# Effect actions: (kwinrc group, key, KWin's default corners). Overview is on
# the top-left corner by default; the theme leaves that corner to the Apple
# menu (BorderActivate=9, steps/window_decorations.py).
_HOT_CORNER_EFFECTS = {
    "mission-control": ("Effect-overview", "BorderActivate", "7"),
    "app-windows": ("Effect-windowview", "BorderActivateClass", ""),
    "all-windows": ("Effect-windowview", "BorderActivateAll", ""),
}
# KWin's own edge actions ([ElectricBorders]).
_HOT_CORNER_ACTIONS = {"desktop": "ShowDesktop", "lock-screen": "LockScreen",
                       "launchpad": "ApplicationLauncher"}
HOT_CORNER_CHOICES = ("none", *_HOT_CORNER_EFFECTS, *_HOT_CORNER_ACTIONS)


def _corner_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip() not in ("", "9")]


def hot_corners() -> dict[str, str]:
    kwinrc = _parse_ini(_kwinrc_path())
    corners = {name: "none" for name in HOT_CORNERS}
    for name, (border, key) in HOT_CORNERS.items():
        action = kwinrc.get("ElectricBorders", {}).get(key, "None")
        for choice, kwin in _HOT_CORNER_ACTIONS.items():
            if action == kwin:
                corners[name] = choice
    for choice, (group, key, default) in _HOT_CORNER_EFFECTS.items():
        for border in _corner_list(kwinrc.get(group, {}).get(key, default)):
            for name, (corner_border, _key) in HOT_CORNERS.items():
                if border == corner_border:
                    corners[name] = choice
    return corners


def set_hot_corner(corner: str, choice: str) -> bool:
    """Give `corner` the action `choice` (none clears it), taking it from
    whatever action had it."""
    if corner not in HOT_CORNERS or choice not in HOT_CORNER_CHOICES:
        return False
    border, key = HOT_CORNERS[corner]
    kwinrc = _parse_ini(_kwinrc_path())
    ok = _kwrite("--file", "kwinrc", "--group", "ElectricBorders", "--key", key,
                 _HOT_CORNER_ACTIONS.get(choice, "None"))
    for effect, (group, effect_key, default) in _HOT_CORNER_EFFECTS.items():
        borders = [b for b in _corner_list(kwinrc.get(group, {}).get(effect_key, default))
                   if b != border]
        if effect == choice:
            borders.append(border)
        ok = _kwrite("--file", "kwinrc", "--group", group, "--key", effect_key,
                     ",".join(borders) or "9") and ok
    _qdbus("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")
    return ok


USAGE = ("Usage: mac-tahoe-theme-switch "
         "{light|dark|auto|follow-system} [install]\n"
         "       mac-tahoe-theme-switch repair-colors\n"
         "       mac-tahoe-theme-switch style [tahoe|frosted]\n"
         "       mac-tahoe-theme-switch accent [#rrggbb|multicolour|wallpaper]\n"
         "       mac-tahoe-theme-switch transparency {standard|reduced}\n"
         "       mac-tahoe-theme-switch dock-tint [macos|neutral|accent]\n"
         "       mac-tahoe-theme-switch glass-level [0-100]\n"
         "       mac-tahoe-theme-switch dock [autohide on|off | size N | magnification N]\n"
         "       mac-tahoe-theme-switch minimize [genie|scale]\n"
         "       mac-tahoe-theme-switch hot-corners [CORNER ACTION]\n"
         "       mac-tahoe-theme-switch patch-dock")


def main(argv: list[str]) -> int:
    if not argv:
        print(USAGE, file=sys.stderr)
        return 1

    _sync_session_env()
    mode = argv[0]
    if mode == "transparency":
        return set_transparency(argv[1]) if len(argv) == 2 else 1
    if mode == "dock-tint":
        if len(argv) == 1:
            print(dock_tint())
            return 0
        return set_dock_tint(argv[1]) if len(argv) == 2 else 1
    if mode == "glass-level":
        if len(argv) == 1:
            print(glass_level())
            return 0
        return set_glass_level(argv[1]) if len(argv) == 2 else 1
    if mode == "dock":
        if len(argv) == 1:
            settings = dock_settings()
            print(json.dumps(settings) if settings else "")
            return 0 if settings else 1
        return 0 if len(argv) == 3 and set_dock(argv[1], argv[2]) else 1
    if mode == "minimize":
        if len(argv) == 1:
            print(minimize_effect())
            return 0
        return 0 if len(argv) == 2 and set_minimize_effect(argv[1]) else 1
    if mode == "hot-corners":
        if len(argv) == 1:
            print(json.dumps(hot_corners()))
            return 0
        return 0 if len(argv) == 3 and set_hot_corner(argv[1], argv[2]) else 1
    if mode == "patch-dock" and len(argv) == 1:
        patch_dock_transparency()
        return 0
    if mode == "style":
        # Without a value: print the current window blur style.
        if len(argv) == 1:
            print(glass_style())
            return 0
        if not set_glass_style(argv[1]):
            print(USAGE, file=sys.stderr)
            return 1
        apply_glass_preset(current_mode())
        apply_top_bar_style(argv[1])
        # The Dock's veil follows the style too.
        if apply_dock_tint(glass=argv[1]):
            reload_plasma_theme()
        return 0
    if mode == "accent":
        # Without a value: print the accent in use.
        if len(argv) == 1:
            print("wallpaper" if accent_from_wallpaper() else accent_color_hex() or "multicolour")
            return 0
        if not re.fullmatch(r"#[0-9a-fA-F]{6}|multicolour|wallpaper", argv[1]):
            print(USAGE, file=sys.stderr)
            return 1
        return 0 if set_accent(argv[1]) else 1
    if mode == "follow-system":
        return follow_system()
    if mode == "repair-colors":
        return 0 if repair_colors() else 1
    if mode == "auto":
        mode = detect_mode_by_time()
    if mode not in ("light", "dark"):
        print(USAGE, file=sys.stderr)
        return 1

    context = argv[1] if len(argv) > 1 else "user"
    return 0 if apply(mode, context=context) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
