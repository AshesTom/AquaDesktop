"""MacTahoe icon themes: extracts the pre-built
MacTahoeLiquidKde-Icons.tar.zst into ~/.local/share/icons. The tarball is
rebuilt offline via _assemble() (maintainer refresh workflow, see below)."""

import re
import shutil
import subprocess
import tarfile
from pathlib import Path

from steps._helpers import (
    DATA_HOME, HOME, fail, info, install_tree, offline, ok, temp_dir,
)
from utils import remove_path, run_user

OFFLINE_DIR = offline("icons")
DEST_DIR = DATA_HOME / "icons"
_THEME_NAMES = (
    "MacTahoeLiquidKde-Icons",
    "MacTahoeLiquidKde-Icons-dark",
)
# Icon Manager (src/offline/icon-manager): the engine of Theme Settings'
# Icons page, and the user's custom icons with the overlay themes built from
# them (MacTahoeLiquidKde-Icons[-dark]-custom), which a reinstall must keep.
ICON_MANAGER_SRC = offline("icon-manager")
ICON_MANAGER_FILES = ("icon_manager.py", "dmg.py", "car.py")
# macOS 26's Dark renders and tinted/clear masks of the pack's Apple icons.
ICON_MANAGER_DIRS = ("macos-styles",)
_OVERLAY_SUFFIX = "-custom"
# The standalone Qt app of earlier builds: its UI, launcher and command.
_LEGACY_ICON_MANAGER = ("IconManager.qml",)


def _icon_manager_paths() -> dict:
    return {
        "app": DATA_HOME / "mac-tahoe-liquid-kde/apps/icon-manager",
        "store": DATA_HOME / "mac-tahoe-liquid-kde/icon-manager",
        "desktop": DATA_HOME / "applications/org.kde.mac-tahoe-liquid-kde.iconmanager.desktop",
        "bin": HOME / ".local/bin/mac-tahoe-icon-manager",
        "state": HOME / ".config/mac-tahoe-liquid-kde/icon-manager.json",
    }

# Subdirs _assemble() cherry-picks from upstream into the default theme.
_DEFAULT_DIRS = (
    "actions", "animations", "apps", "categories", "devices", "emotes",
    "emblems", "mimes", "places", "preferences",
)
_DEFAULT_STATUS_SIZES = ("16", "22", "24", "32", "symbolic")
_AT2X_DIRS = (*_DEFAULT_DIRS, "status")

# macOS-style menu bar glyphs (Wi-Fi, Bluetooth, volume, brightness, battery,
# search) for the exact names the Plasma tray applets request, cut out of
# the Sosumi theme's sheets (see macos-status/import_sosumi.py). Overlaid at
# install time so the tray never falls back to Breeze for them.
STATUS_OVERLAY_DIR = OFFLINE_DIR / "macos-status"
_SCHEME_COLOR_RE = re.compile(r"(\.ColorScheme-Text \{ *color:)(#[0-9a-fA-F]{3,8})")


def deps():
    return ["zstd"]


def install() -> None:
    """Extract the pre-built MacTahoeLiquidKde-Icons tarball into
    ~/.local/share/icons, then rebuild GTK icon caches."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    tarball = OFFLINE_DIR / "MacTahoeLiquidKde-Icons.tar.zst"
    if not tarball.is_file():
        fail(f"offline tarball missing: {tarball}")
        return

    n = 0
    with temp_dir("mttkde-icons") as staging:
        # Extract away from the live icon path. Removing an active theme before
        # this completes makes every running KDE process report
        # "Icon theme ... not found" and briefly fall back to Breeze.
        # tar --zstd is used over Python tarfile because the zstandard module
        # isn't in every distro's default Python.
        res = subprocess.run(
            ["tar", "--zstd", "-xf", str(tarball), "-C", str(staging)],
            check=False, capture_output=True, text=True,
        )
        if res.returncode != 0:
            fail(f"tar --zstd failed ({res.returncode}): {res.stderr.strip()}")
            return

        for name in _THEME_NAMES:
            source = staging / name
            if not (source / "index.theme").is_file():
                fail(f"{name} (index.theme missing from offline archive)")
                continue
            _overlay_status_icons(source)
            if install_tree(source, DEST_DIR / name, name):
                n += 1

    # Clean only our own obsolete variants, and only after both current themes
    # are safely live. A failed extraction must leave the installed theme intact.
    if n == len(_THEME_NAMES):
        for old in DEST_DIR.glob("MacTahoeLiquidKde-Icons*"):
            # The Icon Manager's overlays hold the user's own icons.
            if old.is_dir() and old.name not in _THEME_NAMES \
                    and not old.name.endswith(_OVERLAY_SUFFIX):
                shutil.rmtree(old, ignore_errors=True)

    if shutil.which("gtk-update-icon-cache"):
        for theme in DEST_DIR.glob("MacTahoeLiquidKde-Icons*"):
            if theme.is_dir():
                run_user(
                    ["gtk-update-icon-cache", "-f", "-t", str(theme)],
                    check=False,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )

    label = "icon theme" if n == 1 else "icon themes"
    info(f"{n} {label} installed/reinstalled")
    _install_icon_manager()


def _install_icon_manager() -> None:
    paths = _icon_manager_paths()
    if not all((ICON_MANAGER_SRC / name).is_file() for name in ICON_MANAGER_FILES):
        fail("Icon Manager (missing sources)")
        return
    paths["app"].mkdir(parents=True, exist_ok=True)
    for name in ICON_MANAGER_FILES:
        shutil.copy2(ICON_MANAGER_SRC / name, paths["app"] / name)
    for name in ICON_MANAGER_DIRS:
        shutil.rmtree(paths["app"] / name, ignore_errors=True)
        if (ICON_MANAGER_SRC / name).is_dir():
            shutil.copytree(ICON_MANAGER_SRC / name, paths["app"] / name)
    # Theme Settings (theme_switch step) is its window now.
    for name in _LEGACY_ICON_MANAGER:
        (paths["app"] / name).unlink(missing_ok=True)
    for key in ("bin", "desktop"):
        paths[key].unlink(missing_ok=True)
    ok("Icon Manager")


def _restore_custom_launchers(state_path: Path) -> None:
    """Undo the Icon Manager's launcher edits (the ones naming an icon file):
    drop the per-user copies it created, put the original Icon= back in the
    user's own launchers."""
    import json
    try:
        launchers = json.loads(state_path.read_text(encoding="utf-8")).get("launchers", {})
    except (OSError, ValueError):
        return
    for app_id, record in launchers.items():
        target = DATA_HOME / "applications" / f"{app_id}.desktop"
        if record.get("created"):
            target.unlink(missing_ok=True)
        elif target.is_file():
            text = target.read_text(encoding="utf-8")
            target.write_text(re.sub(r"(?m)^Icon=.*$", f"Icon={record.get('icon', '')}", text),
                              encoding="utf-8")


def _uninstall_icon_manager() -> None:
    paths = _icon_manager_paths()
    _restore_custom_launchers(paths["state"])
    for key in ("app", "store"):
        shutil.rmtree(paths[key], ignore_errors=True)
    for key in ("desktop", "bin", "state"):
        paths[key].unlink(missing_ok=True)
    ok("Icon Manager removed")


def _theme_text_color(theme: Path) -> str | None:
    sample = theme / "status/22/audio-volume-high-symbolic.svg"
    try:
        match = _SCHEME_COLOR_RE.search(sample.read_text(encoding="utf-8"))
    except OSError:
        return None
    return match.group(2) if match else None


def _overlay_status_icons(theme: Path) -> int:
    """Write the macOS tray glyphs into an extracted theme. Fixed-size
    directories win over scalable ones in icon lookup, and the first matching
    context in ``Directories`` wins among equal sizes, so each glyph replaces
    the theme's copy in every directory that has one (``system-search`` also
    lives in ``actions/``), and always lands in the 22 px (tray) and symbolic
    status directories. Existing entries are unlinked first: many are
    symlinks to other icons."""
    icons = sorted(STATUS_OVERLAY_DIR.glob("*-symbolic.svg"))
    if not icons:
        return 0
    color = _theme_text_color(theme)
    dirs = sorted(d for d in theme.glob("*/*") if d.is_dir() and not d.is_symlink())
    written = 0
    for icon in icons:
        body = icon.read_text(encoding="utf-8")
        if color:
            body = _SCHEME_COLOR_RE.sub(lambda m: m.group(1) + color, body, count=1)
        for directory in dirs:
            target = directory / icon.name
            always = directory.parent.name.startswith("status") and directory.name in ("22", "symbolic")
            if not always and not (target.exists() or target.is_symlink()):
                continue
            remove_path(target)
            target.write_text(body, encoding="utf-8")
            written += 1
    return written


def uninstall() -> None:
    _uninstall_icon_manager()
    n = 0
    for theme in DEST_DIR.glob("MacTahoeLiquidKde-Icons*"):
        if theme.is_dir():
            try:
                shutil.rmtree(theme)
                ok(theme.name); n += 1
            except OSError:
                fail(theme.name)
    info(f"{n} icon themes removed")


# ─────────────────────────────────────────────────────────────────────
# REFRESH WORKFLOW — maintainer-only: rebuilds the bundled tarball after
# an upstream theme update. Not called at install time.
# ─────────────────────────────────────────────────────────────────────


def _overlay_links(src: Path, dest: Path) -> None:
    for entry in src.iterdir():
        target = dest / entry.name
        if entry.is_symlink():
            remove_path(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(entry.readlink())
            continue
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            _overlay_links(entry, target)
            continue
        remove_path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry, target)


def _assemble(repo: Path, name: str) -> None:
    """Build ``CACHE/<name>`` + ``CACHE/<name>-dark`` from an upstream
    vinceliuice/MacTahoe-icon-theme clone; override CACHE, then tar --zstd
    the result into src/offline/icons/. Never runs at install time."""
    light = CACHE / name
    light.mkdir(parents=True, exist_ok=True)

    index = repo / "src/index.theme"
    if index.is_file():
        text = index.read_text().replace("MacTahoe", name)
        (light / "index.theme").write_text(text)

    src_root = repo / "src"
    for sub in _DEFAULT_DIRS:
        if (src_root / sub).is_dir():
            shutil.copytree(src_root / sub, light / sub, dirs_exist_ok=True)
    (light / "status").mkdir(exist_ok=True)
    for sz in _DEFAULT_STATUS_SIZES:
        d = src_root / "status" / sz
        if d.is_dir():
            shutil.copytree(d, light / "status" / sz, dirs_exist_ok=True)

    links_root = repo / "links"
    for sub in (*_DEFAULT_DIRS, "status"):
        if (links_root / sub).is_dir():
            _overlay_links(links_root / sub, light / sub)

    for fn in ("user-trash-dark.svg", "user-trash-full-dark.svg"):
        try: (light / "places/scalable" / fn).unlink()
        except FileNotFoundError: pass
        except OSError: pass

    for sub in _AT2X_DIRS:
        target = light / sub
        if target.is_dir():
            link = light / f"{sub}@2x"
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(sub)

    # Dark variant
    dark = CACHE / f"{name}-dark"
    dark.mkdir(parents=True, exist_ok=True)
    if index.is_file():
        text = index.read_text().replace("MacTahoe", f"{name}-dark")
        text = re.sub(r"^Inherits=.*",
                      f"Inherits={name},hicolor,breeze",
                      text, flags=re.MULTILINE)
        (dark / "index.theme").write_text(text)

    for sub in ("actions", "apps", "categories", "emblems", "devices",
                "mimes", "places", "status"):
        (dark / sub).mkdir(parents=True, exist_ok=True)

    shutil.copytree(src_root / "actions", dark / "actions", dirs_exist_ok=True)
    for size in ("16", "22", "32", "symbolic"):
        if (src_root / "apps" / size).is_dir():
            shutil.copytree(src_root / "apps" / size,
                            dark / "apps" / size, dirs_exist_ok=True)
    for size in ("22", "symbolic"):
        if (src_root / "categories" / size).is_dir():
            shutil.copytree(src_root / "categories" / size,
                            dark / "categories" / size, dirs_exist_ok=True)
    if (src_root / "emblems/symbolic").is_dir():
        shutil.copytree(src_root / "emblems/symbolic",
                        dark / "emblems/symbolic", dirs_exist_ok=True)
    if (src_root / "mimes/symbolic").is_dir():
        shutil.copytree(src_root / "mimes/symbolic",
                        dark / "mimes/symbolic", dirs_exist_ok=True)
    for size in ("16", "22", "24", "32", "symbolic"):
        if (src_root / "devices" / size).is_dir():
            shutil.copytree(src_root / "devices" / size,
                            dark / "devices" / size, dirs_exist_ok=True)
    for size in ("16", "22", "24", "scalable", "symbolic"):
        if (src_root / "places" / size).is_dir():
            shutil.copytree(src_root / "places" / size,
                            dark / "places" / size, dirs_exist_ok=True)
    if (src_root / "status/symbolic").is_dir():
        shutil.copytree(src_root / "status/symbolic",
                        dark / "status/symbolic", dirs_exist_ok=True)

    for svg in dark.rglob("*.svg"):
        try:
            text = svg.read_text(encoding="utf-8")
            if "#363636" in text:
                svg.write_text(text.replace("#363636", "#dedede"))
        except (OSError, UnicodeDecodeError):
            pass

    for old, new in (("user-trash-dark.svg", "user-trash.svg"),
                     ("user-trash-full-dark.svg", "user-trash-full.svg")):
        src_p = dark / "places/scalable" / old
        if src_p.is_file():
            shutil.move(str(src_p), str(dark / "places/scalable" / new))

    for sub in ("actions/16", "actions/22", "actions/24", "actions/32", "actions/symbolic",
                "devices/16", "devices/22", "devices/24", "devices/32", "devices/symbolic",
                "places/16", "places/22", "places/24", "places/scalable", "places/symbolic",
                "apps/16", "apps/22", "apps/32", "apps/symbolic",
                "categories/22", "categories/symbolic",
                "mimes/symbolic", "status/symbolic"):
        link_src = links_root / sub
        if link_src.is_dir():
            _overlay_links(link_src, dark / sub)

    for sub, target in (
        ("animations", f"../{name}/animations"),
        ("emotes", f"../{name}/emotes"),
        ("preferences", f"../{name}/preferences"),
        ("categories/32", f"../../{name}/categories/32"),
        ("apps/scalable", f"../../{name}/apps/scalable"),
        ("devices/scalable", f"../../{name}/devices/scalable"),
    ):
        link = dark / sub
        if link.is_symlink() or link.exists():
            try: link.unlink()
            except OSError:
                shutil.rmtree(link, ignore_errors=True)
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)

    for sz in ("16", "22", "24", "32"):
        link = dark / f"status/{sz}"
        if link.is_symlink() or link.exists():
            try: link.unlink()
            except OSError: shutil.rmtree(link, ignore_errors=True)
        link.symlink_to(f"../../{name}/status/{sz}")
    for sz in ("16", "22", "24"):
        link = dark / f"emblems/{sz}"
        if link.is_symlink() or link.exists():
            try: link.unlink()
            except OSError: shutil.rmtree(link, ignore_errors=True)
        link.symlink_to(f"../../{name}/emblems/{sz}")
    for sz in ("16", "22", "scalable"):
        link = dark / f"mimes/{sz}"
        if link.is_symlink() or link.exists():
            try: link.unlink()
            except OSError: shutil.rmtree(link, ignore_errors=True)
        link.symlink_to(f"../../{name}/mimes/{sz}")

    for sub in _AT2X_DIRS:
        target = dark / sub
        if target.is_dir():
            link = dark / f"{sub}@2x"
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(sub)


# Only _assemble() uses this; the maintainer refresh script overrides it.
CACHE = Path("/tmp/mttkde-icons-build")
