"""Window and Dock glass: the Better Blur DX KWin effect (xarblu).

The feature keeps its historical ``acrylic_glass`` id (``--acrylic-glass``,
features.json) so existing installs and scripts keep working; the Glass and
Acrylic Glass effects earlier releases installed are migrated away on
install. Source: src/offline/kwin-effects/better-blur-dx (UPSTREAM.md there
lists the AquaDesktop changes: the Dock's own blur and its edge lens).
"""

import subprocess
import time
import uuid
from pathlib import Path

from distro import qt6_plugins_dir
from steps._helpers import (
    build_dir, cmake_build, info, kw_write, ok, offline, qdbus_call,
    sudo_install_file, sudo_remove, theme_mode, warn,
)
from theme_switch import GLASS_EFFECT, GLASS_GROUP, glass_preset
from utils import have, qdbus_cmd, run_user

SRC = offline("kwin-effects/better-blur-dx")
BUILD = build_dir("kwin-effects/better-blur-dx")
HOME = Path.home()
LEGACY_USER_PLUGIN_DIR = HOME / ".local/lib/qt6/plugins"

_EFFECT_SO = "kwin/effects/plugins/better_blur_dx.so"
_CONFIG_SO = "kwin/effects/configs/kwin_better_blur_dx_config.so"
# The effects earlier releases installed: (KWin id, kwinrc group, files).
_REPLACED_EFFECTS = (
    ("glass", "Effect-blurplus", (
        "kwin/effects/plugins/glass.so",
        "kwin/effects/configs/kwin_glass_config.so",
    )),
    ("liquidglass", "Effect-liquidglass", (
        "kwin/effects/plugins/liquidglass.so",
        "kwin/effects/configs/kwin_liquidglass_config.so",
    )),
)


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
        # KF6 components required by the effect's CMakeLists (and KWin's SDK).
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
        "kf6-colorscheme-cmake:kcolorscheme",
        # KWin (Wayland) is mandatory: the effect is built against its SDK.
        "kwin-cmake:kwin",
        "kdecoration-cmake:kdecoration",
        # XCB is REQUIRED by KWin's public SDK even on Wayland.
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
        BUILD / "src/better_blur_dx.so",
        BUILD / "src/kcm/kwin_better_blur_dx_config.so",
    ]


def _plugin_dir() -> Path:
    """Kept by name for preflight's _enumerate_destinations(); delegates to
    the shared qt6_plugins_dir() discovery (same raise-on-missing contract)."""
    return qt6_plugins_dir()


def build() -> None:
    if not (SRC / "CMakeLists.txt").is_file():
        return
    # Unload the effects that would keep a .so mapped while it is replaced,
    # and the stock blur, which would blur a second time.
    kw_write("--file", "kwinrc", "--group", "Plugins",
             "--key", "blurEnabled", "false")
    for effect in (GLASS_EFFECT, "blur"):
        qdbus_call("org.kde.KWin", "/Effects",
                   "org.kde.kwin.Effects.unloadEffect", effect)

    cmake_build(SRC, BUILD, "Better Blur DX")


# Every mode: blur behind every window (the translucent Kvantum / GTK
# surfaces need it) and decorations. Menus and docks are never force-blurred
# (they ask for their own region), and plasmashell is on the deny-list:
# Plasma surfaces keep exactly the region they request, so frameless popups
# (the Dock's Downloads fan, the Control Center's room around its bubbles)
# stay clear. The rest of the list are windows that render a stray glass
# shape when force-blurred, and VirtualBox VMs whatever the case of their
# class (issue #90: glass filled their fullscreen / seamless cutouts).
_SHARED = (
    ("BlurDecorations", "true"),
    ("BlurMatching", "false"),
    ("BlurNonMatching", "true"),
    ("BlurDocks", "false"),
    ("BlurMenus", "false"),
    ("WindowClasses", "plasmashell\ncairo-dock\nkwin_wayland\nlinux-wallpaperengine\n"
                      "xembedsniproxy\n/(?i)^VirtualBoxVM$/"),
)

# The windows' radius (Plasma surfaces, the Dock included, bring their own
# rounded blur region, which the effect respects).
_CORNER_DEFAULTS = (
    ("CornerRadius", "22"),
)
# Defaults earlier releases seeded: still holding one means the user never
# tuned it, so the current default replaces it.
_PREVIOUS_CORNER_DEFAULTS: dict[str, tuple[str, ...]] = {}


def _install_corner_defaults() -> None:
    """Seed missing radii without undoing the user's corner tuning (#89):
    explicitly empty values are kept too, and a failed read never
    authorizes a write."""
    if not have("kreadconfig6"):
        warn("Glass corner settings preserved — kreadconfig6 is unavailable")
        return
    sentinel = f"__mttkde_absent_{uuid.uuid4().hex}__"
    for key, default in _CORNER_DEFAULTS:
        try:
            result = run_user(
                ["kreadconfig6", "--file", "kwinrc", "--group",
                 GLASS_GROUP, "--key", key, "--default", sentinel],
                check=False, capture_output=True, text=True, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            warn(f"Glass {key} preserved — could not read it ({exc})")
            continue
        if result.returncode != 0:
            warn(f"Glass {key} preserved — kreadconfig6 failed")
            continue
        value = (result.stdout or "").removesuffix("\n").removesuffix("\r")
        if value == sentinel or value in _PREVIOUS_CORNER_DEFAULTS.get(key, ()):
            if not kw_write("--file", "kwinrc", "--group", GLASS_GROUP,
                            "--key", key, default):
                warn(f"Glass {key} default not applied — kwriteconfig6 failed")


def _strip_kwinrc_group(group: str) -> None:
    """Drop a whole kwinrc group, so a reinstall never keeps stale values."""
    kwinrc = HOME / ".config/kwinrc"
    if not kwinrc.is_file():
        return
    text = kwinrc.read_text()
    header = f"[{group}]"
    if header not in text:
        return
    out: list[str] = []
    skip = False
    for line in text.splitlines():
        if line.startswith(header):
            skip = True
            continue
        if skip and line.startswith("["):
            skip = False
        if not skip:
            out.append(line)
    kwinrc.write_text("\n".join(out) + "\n")


def _remove_replaced_effects() -> None:
    """Earlier releases installed Glass (``glass``) and Acrylic Glass
    (``liquidglass``): disable each before unloading (a reconfigure could
    otherwise load it again), then drop its plugin and settings."""
    system_dir = _plugin_dir()
    for effect, group, files in _REPLACED_EFFECTS:
        kw_write("--file", "kwinrc", "--group", "Plugins",
                 "--key", f"{effect}Enabled", "false")
        qdbus_call("org.kde.KWin", "/Effects",
                   "org.kde.kwin.Effects.unloadEffect", effect)
        _strip_kwinrc_group(group)
        for relpath in files:
            target = system_dir / relpath
            if target.exists():
                sudo_remove(target, f"{target.name} (replaced by Better Blur DX)")
            legacy = LEGACY_USER_PLUGIN_DIR / relpath
            if legacy.is_file():
                try:
                    legacy.unlink()
                    ok(f"{legacy.name} (removed user-path leftover)")
                except OSError:
                    pass


def _kwin_has_effect(effect: str) -> bool:
    q = qdbus_cmd()
    if not q:
        return False
    try:
        res = run_user([q, "org.kde.KWin", "/Effects",
                        "org.kde.kwin.Effects.activeEffects"],
                       check=False, capture_output=True, text=True,
                       timeout=10)
    except subprocess.TimeoutExpired:
        return False
    return effect in (res.stdout or "").split()


def install() -> None:
    system_dir = _plugin_dir()
    effect_so = BUILD / "src/better_blur_dx.so"
    config_so = BUILD / "src/kcm/kwin_better_blur_dx_config.so"
    if not effect_so.is_file():
        return

    _remove_replaced_effects()

    # Unload before replacing the .so so KWin doesn't hold the file.
    kw_write("--file", "kwinrc", "--group", "Plugins",
             "--key", f"{GLASS_EFFECT}Enabled", "false")
    qdbus_call("org.kde.KWin", "/Effects",
               "org.kde.kwin.Effects.unloadEffect", GLASS_EFFECT)
    qdbus_call("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")
    time.sleep(2)
    ok("Better Blur DX unloaded for safe upgrade")

    if not sudo_install_file(effect_so, system_dir / _EFFECT_SO, "Better Blur DX installed"):
        return
    if not sudo_install_file(config_so, system_dir / _CONFIG_SO, "Better Blur DX settings installed"):
        warn("Better Blur DX settings module install failed")

    for key, value in _SHARED:
        kw_write("--file", "kwinrc", "--group", GLASS_GROUP, "--key", key, value)
    # The theme switch rewrites the per-mode blur on every light/dark change;
    # seed it now for an explicit mode ("auto" is resolved by that switch).
    mode = theme_mode()
    if mode in ("dark", "light"):
        for key, value in glass_preset(mode).items():
            kw_write("--file", "kwinrc", "--group", GLASS_GROUP, "--key", key, value)
    _install_corner_defaults()
    ok("Glass preset installed")
    kw_write("--file", "kwinrc", "--group", "Plugins",
             "--key", f"{GLASS_EFFECT}Enabled", "true")

    # Order matters: unload stale handle → reconfigure → loadEffect. loadEffect
    # returns true even when nothing changed; only activeEffects proves it took.
    qdbus_call("org.kde.KWin", "/Effects",
               "org.kde.kwin.Effects.unloadEffect", GLASS_EFFECT)
    qdbus_call("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")
    qdbus_call("org.kde.KWin", "/Effects",
               "org.kde.kwin.Effects.loadEffect", GLASS_EFFECT)
    if _kwin_has_effect(GLASS_EFFECT):
        ok("Better Blur DX loaded")
    else:
        ok("Better Blur DX installed (log out and back in to activate)")


def uninstall() -> None:
    # Persist the disabled state before asking KWin to unload the effect:
    # unloading first can race a reconfigure and load the still-enabled
    # plugin again, leaving every window translucent until logout.
    disabled = kw_write(
        "--file", "kwinrc", "--group", "Plugins",
        "--key", f"{GLASS_EFFECT}Enabled", "false",
    )
    unloaded = qdbus_call(
        "org.kde.KWin", "/Effects",
        "org.kde.kwin.Effects.unloadEffect", GLASS_EFFECT,
    )
    reconfigured = qdbus_call(
        "org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure",
    )
    if not disabled:
        warn("Better Blur DX could not be disabled in kwinrc")
    if not unloaded and not reconfigured:
        warn("Better Blur DX live unload was not confirmed — log out once if "
             "window transparency remains")

    _strip_kwinrc_group(GLASS_GROUP)
    system_dir = _plugin_dir()
    for relpath in (_EFFECT_SO, _CONFIG_SO):
        so = system_dir / relpath
        sudo_remove(so, so.name)
    # Glass / Acrylic Glass leftovers from earlier releases.
    _remove_replaced_effects()

    # Refresh KWin's effect catalogue after the plugin files disappear.
    qdbus_call("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")
    info("Better Blur DX removed")
