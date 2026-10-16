import shutil

from steps._helpers import (
    DATA_HOME, fail, info, kw_write, offline, ok, qdbus_call, reinstall, theme_mode,
    warn,
)
from utils import kw_read

DEST_DIR = DATA_HOME / "aurorae/themes"
VARIANTS = ("Dark", "Light")

# KWin script: the green traffic light enters full screen, like macOS.
FULLSCREEN_SCRIPT = "mac-tahoe-green-fullscreen"
SCRIPTS_DIR = DATA_HOME / "kwin/scripts"
# The macOS application switcher (Alt+Tab), a KWin window switcher layout.
SWITCHER = "mac-tahoe-switcher"
TABBOX_DIR = DATA_HOME / "kwin/tabbox"
# kwinrc [TabBox]: the layout, one entry per application (Cmd+Tab), and no
# highlighting of the other windows (macOS keeps them as they are).
SWITCHER_SETTINGS = (
    ("LayoutName", SWITCHER),
    ("ApplicationsMode", "1"),
    ("HighlightWindows", "false"),
)
# macOS keeps the top-left corner for the Apple menu; KWin's Overview takes
# it as a hot corner by default, so reaching for the Apple menu opened the
# Overview. KWin's ElectricNone (9) leaves the corner alone.
OVERVIEW_GROUP = "Effect-overview"
NO_HOT_CORNER = "9"


def _install_fullscreen_script() -> None:
    src = offline("kwin-scripts", FULLSCREEN_SCRIPT)
    if not (src / "metadata.json").is_file():
        warn(f"KWin script {FULLSCREEN_SCRIPT} not found at {src} — "
             "the green button keeps maximizing windows")
        return
    dest = SCRIPTS_DIR / FULLSCREEN_SCRIPT
    if dest.is_dir():
        shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    if kw_write("--file", "kwinrc", "--group", "Plugins",
                "--key", f"{FULLSCREEN_SCRIPT}Enabled", "--type", "bool", "true"):
        ok("Green button enters full screen (Ctrl+Meta+F toggles it)")
    else:
        warn(f"KWin script {FULLSCREEN_SCRIPT} installed but not enabled — "
             "kwriteconfig6 unavailable. Enable it in System Settings → "
             "Window Management → KWin Scripts.")


def _uninstall_fullscreen_script() -> None:
    qdbus_call("org.kde.KWin", "/Scripting",
               "org.kde.kwin.Scripting.unloadScript", FULLSCREEN_SCRIPT)
    kw_write("--file", "kwinrc", "--group", "Plugins",
             "--key", f"{FULLSCREEN_SCRIPT}Enabled", "--delete")
    dest = SCRIPTS_DIR / FULLSCREEN_SCRIPT
    if dest.is_dir():
        shutil.rmtree(dest, ignore_errors=True)
        ok(f"KWin script {FULLSCREEN_SCRIPT} removed")


def _install_switcher() -> None:
    src = offline("kwin-tabbox", SWITCHER)
    if not (src / "metadata.json").is_file():
        warn(f"App switcher {SWITCHER} not found at {src} — Alt+Tab keeps KWin's")
        return
    dest = TABBOX_DIR / SWITCHER
    if dest.is_dir():
        shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    failures = sum(not kw_write("--file", "kwinrc", "--group", "TabBox", "--key", key, value)
                   for key, value in SWITCHER_SETTINGS)
    if failures:
        warn(f"App switcher installed but {failures} kwinrc key(s) could not be written — "
             "pick it in System Settings → Window Management → Task Switcher.")
    else:
        ok("Alt+Tab is the macOS app switcher")


def _uninstall_switcher() -> None:
    # Back to KWin's own switcher only when ours is the one in use.
    if kw_read("kwinrc", "TabBox", "LayoutName") == SWITCHER:
        for key, _value in SWITCHER_SETTINGS:
            kw_write("--file", "kwinrc", "--group", "TabBox", "--key", key, "--delete")
    dest = TABBOX_DIR / SWITCHER
    if dest.is_dir():
        shutil.rmtree(dest, ignore_errors=True)
        ok(f"App switcher {SWITCHER} removed")


def _free_apple_menu_corner() -> None:
    # A corner the user set on purpose stays theirs.
    if kw_read("kwinrc", OVERVIEW_GROUP, "BorderActivate"):
        return
    if kw_write("--file", "kwinrc", "--group", OVERVIEW_GROUP,
                "--key", "BorderActivate", NO_HOT_CORNER):
        ok("Top-left corner left to the Apple menu (no Overview hot corner)")


def _restore_overview_corner() -> None:
    # KWin's default back, only if the value is still ours.
    if kw_read("kwinrc", OVERVIEW_GROUP, "BorderActivate") == NO_HOT_CORNER:
        kw_write("--file", "kwinrc", "--group", OVERVIEW_GROUP,
                 "--key", "BorderActivate", "--delete")


def install() -> None:
    src = offline("aurorae")
    if not src.is_dir():
        fail(f"Aurorae source not found at {src}")
        return

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    n_inst = n_re = 0
    for mode in VARIANTS:
        name = f"MacTahoeLiquidKde-{mode}"
        dest = DEST_DIR / name
        existed = dest.is_dir()
        dest.mkdir(parents=True, exist_ok=True)

        deco = src / name / "decoration.svg"
        if deco.is_file():
            shutil.copy2(deco, dest)
        rc = src / f"{name}rc"
        if rc.is_file():
            shutil.copy2(rc, dest / f"{name}rc")
        for icon in (src / f"icons-{mode}").glob("*.svg"):
            shutil.copy2(icon, dest)

        for fn in ("metadata.desktop", "metadata.json"):
            template = src / fn
            if template.is_file():
                (dest / fn).write_text(
                    template.read_text().replace("theme_name", name)
                )

        if existed:
            reinstall(name); n_re += 1
        else:
            ok(f"{name} (installed)"); n_inst += 1

    chosen = "MacTahoeLiquidKde-Light" if theme_mode() == "light" else "MacTahoeLiquidKde-Dark"
    write_failures = 0
    for key, value in (
        ("library", "org.kde.kwin.aurorae"),
        ("theme", f"__aurorae__svg__{chosen}"),
        ("ButtonsOnLeft", "XIA"),
        ("ButtonsOnRight", ""),
    ):
        if not kw_write("--file", "kwinrc",
                        "--group", "org.kde.kdecoration2",
                        "--key", key, value):
            write_failures += 1
    _install_fullscreen_script()
    _install_switcher()
    _free_apple_menu_corner()
    qdbus_call("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")
    if write_failures == 0:
        ok(f"Window decoration set to {chosen}")
    else:
        warn(f"Window decoration files installed but {write_failures} "
             "kwinrc key(s) could not be written — kwriteconfig6 "
             "unavailable. Install plasma-workspace or your distro's "
             "equivalent to apply the decoration on next login.")

    info(f"{n_inst + n_re} Aurorae themes — {n_inst} installed, {n_re} reinstalled")


def uninstall() -> None:
    n = 0
    for mode in VARIANTS:
        d = DEST_DIR / f"MacTahoeLiquidKde-{mode}"
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            ok(f"MacTahoeLiquidKde-{mode} removed")
            n += 1
    for key, value in (
        ("library", "org.kde.breeze"),
        ("theme", "Breeze"),
        ("ButtonsOnLeft", "M"),
        ("ButtonsOnRight", "IAX"),
    ):
        kw_write("--file", "kwinrc",
                 "--group", "org.kde.kdecoration2",
                 "--key", key, value)
    _uninstall_fullscreen_script()
    _uninstall_switcher()
    _restore_overview_corner()
    qdbus_call("org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")
    ok("Window decoration reset to Breeze")
    info(f"{n} Aurorae themes removed")
