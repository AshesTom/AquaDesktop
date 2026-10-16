"""Application settings: Konsole as macOS Terminal.

Terminal's default window is its "Basic" profile: 80 x 24, black on white
in light mode and white on near black in dark mode, Terminal's own ANSI
palette, a steady grey block cursor. Konsole gets the same as two profiles
(src/offline/konsole) and, from Konsole 26.08, switches between them with
the system's appearance (konsolerc [LightDarkTheme]). Like Terminal, new
windows open at the profile's size rather than the last one's.
"""
import re
import shutil

from steps._helpers import DATA_HOME, info, offline, ok, warn
from utils import kw_read, kw_write

KONSOLE_DIR = DATA_HOME / "konsole"
LIGHT_PROFILE = "AquaDesktop Light"
DARK_PROFILE = "AquaDesktop Dark"
_LEGACY_PROFILES = {
    LIGHT_PROFILE: "Tahoe Gate Light",
    DARK_PROFILE: "Tahoe Gate Dark",
}
# konsolerc keys, each written only when absent (or already ours) and
# removed on uninstall only while it still holds our value.
KONSOLE_SETTINGS = (
    ("LightDarkTheme", "SyncProfileWithSystemTheme", "true"),
    ("LightDarkTheme", "LightThemeProfile", LIGHT_PROFILE),
    ("LightDarkTheme", "DarkThemeProfile", DARK_PROFILE),
    ("KonsoleWindow", "RememberWindowSize", "false"),
)


def _konsole_files() -> list:
    src = offline("konsole")
    return sorted(p for p in src.iterdir() if p.suffix in (".profile", ".colorscheme")) \
        if src.is_dir() else []


def install() -> None:
    files = _konsole_files()
    if not files:
        warn("Konsole profiles not found — Terminal look skipped")
        return
    KONSOLE_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    for src in files:
        dest = KONSOLE_DIR / src.name
        # A profile the user changed in Konsole stays theirs.
        if src.suffix == ".profile" and dest.is_file():
            # Rename our old display name without replacing custom settings.
            try:
                original = dest.read_text(encoding="utf-8")
                updated = original
                for current, legacy in _LEGACY_PROFILES.items():
                    updated = re.sub(rf"(?m)^Name={re.escape(legacy)}$",
                                     "Name=" + current, updated)
                if updated != original:
                    dest.write_text(updated, encoding="utf-8")
            except OSError as exc:
                warn(f"{src.name} name not updated ({exc})")
            continue
        try:
            shutil.copy2(src, dest)
        except OSError as exc:
            warn(f"{src.name} not installed ({exc})")
            continue
        ok(src.name)
        n += 1
    # A default profile the user picked wins: the light/dark sync would
    # replace it in every new window.
    if kw_read("konsolerc", "Desktop Entry", "DefaultProfile"):
        ok("Konsole keeps your default profile (AquaDesktop Light / Dark available)")
    else:
        written = True
        for group, key, value in KONSOLE_SETTINGS:
            if kw_read("konsolerc", group, key) in ("", value, _LEGACY_PROFILES.get(value, value)):
                written = kw_write("--file", "konsolerc", "--group", group,
                                   "--key", key, value) and written
        if written:
            ok("Konsole opens like macOS Terminal (light and dark)")
        else:
            warn("Konsole profiles installed but konsolerc not written — "
                 "kwriteconfig6 unavailable (pick AquaDesktop in Konsole's settings)")
    info(f"{n} Konsole file(s) installed")


def uninstall() -> None:
    for group, key, value in KONSOLE_SETTINGS:
        if kw_read("konsolerc", group, key) in (value, _LEGACY_PROFILES.get(value, value)):
            kw_write("--file", "konsolerc", "--group", group, "--key", key, "--delete")
    n = 0
    for src in _konsole_files():
        dest = KONSOLE_DIR / src.name
        if dest.is_file():
            dest.unlink()
            ok(f"{src.name} removed")
            n += 1
    info(f"{n} Konsole file(s) removed")
