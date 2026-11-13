#!/usr/bin/env python3
"""MacTahoe Liquid KDE — Theme Settings.

A GTK 4 window laid out like macOS System Settings for what this theme adds
to Plasma:

- Appearance: Light / Dark (/ Auto when the 06:00 / 18:00 schedule is
  installed) and the accent colour;
- Liquid Glass: the window blur style, Liquid Glass (macOS Tahoe) or Frosted
  (the pre-Tahoe look, with the translucent menu bar back), and Golden Gate's
  clear-to-tinted control for menu-bar popovers;
- Desktop & Dock: the Dock's size, magnification and auto-hide, the
  minimize effect and the hot corners;
- Icons: the Icon Manager (macOS .icns icons per app, Light and Dark, and
  the Tinted icon style), when it is installed next to this app.

Every change goes through the tools the installer puts in place, run in the
background: mac-tahoe-theme-switch (mode, style, accent colour, Dock) and
the Icon Manager's command line (icon_manager.py, next to this app).

SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

APP_ID = "org.kde.mac-tahoe-liquid-kde.themesettings"
HERE = Path(__file__).resolve().parent
HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")
THEME_SWITCH = Path(os.environ.get("MAC_TAHOE_THEME_SWITCH")
                    or HOME / ".local/bin/mac-tahoe-theme-switch")
# Installed next to this app (apps/icon-manager); src/offline/icon-manager
# in the repository.
ICON_MANAGER = Path(os.environ.get("MAC_TAHOE_ICON_MANAGER")
                    or HERE.parent / "icon-manager/icon_manager.py")
GLASS_STYLE_FILE = CONFIG / "mac-tahoe-liquid-kde/glass-style"
THEME_TIMER = "mac-tahoe-liquid-kde-theme.timer"
WALLPAPER = DATA / "wallpapers/MacTahoe/contents"
BASE_ICON_THEMES = {"light": "MacTahoeLiquidKde-Icons", "dark": "MacTahoeLiquidKde-Icons-dark"}

# macOS Tahoe's accent colours; None is Multicolour (the colour scheme's own),
# "wallpaper" lets Plasma take it from the wallpaper.
ACCENTS = (
    ("multicolour", None),
    ("blue", "#0088ff"),
    ("purple", "#cb30e0"),
    ("pink", "#ff2d55"),
    ("red", "#ff383c"),
    ("orange", "#ff8d28"),
    ("yellow", "#ffcc00"),
    ("green", "#34c759"),
    ("graphite", "#8c8c8c"),
    ("wallpaper", "wallpaper"),
)

# ── Translations ──────────────────────────────────────────────────────

_FR = {
    "Theme Settings": "Réglages du thème",
    "Dock tint": "Teinte du Dock",
    "The Dock's glass in macOS colours, without any tint (a neutral Dock and black context "
    "menus), like the Control Center's bubbles, or with the accent colour.":
        "Le verre du Dock aux couleurs de macOS, sans teinte (Dock neutre et menus contextuels "
        "noirs), comme les bulles du Centre de contrôle, ou à la couleur d'accentuation.",
    "Neutral": "Neutre",
    "Control Center": "Centre de contrôle",
    "Accent Color": "Couleur d'accentuation",
    "MacTahoe Liquid KDE account": "Compte MacTahoe Liquid KDE",
    "Users": "Utilisateurs",
    "Search": "Rechercher",
    "Appearance": "Apparence",
    "Liquid Glass": "Liquid Glass",
    "Icons": "Icônes",
    "About": "À propos",
    "Choose how your Mac-like desktop looks: light, dark, or switching by "
    "itself, and the colour of buttons, selections and highlights.":
        "Choisissez l'apparence du bureau : claire, sombre ou automatique, et la "
        "couleur des boutons, sélections et surbrillances.",
    "Auto": "Auto",
    "Light": "Clair",
    "Dark": "Sombre",
    "Accent color": "Couleur d'accentuation",
    "Multicolour": "Multicolore",
    "Wallpaper": "Fond d'écran",
    "Blue": "Bleu", "Purple": "Violet", "Pink": "Rose", "Red": "Rouge",
    "Orange": "Orange", "Yellow": "Jaune", "Green": "Vert", "Graphite": "Graphite",
    "Auto switches to Light at 06:00 and to Dark at 18:00.":
        "Auto passe en Clair à 6 h et en Sombre à 18 h.",
    "Light and Dark last until the next switch; reinstall with --light or "
    "--dark to keep one.":
        "Clair et Sombre durent jusqu'au prochain changement ; réinstallez avec "
        "--light ou --dark pour en garder un.",
    "The material of windows, menus, the Dock and the menu bar.":
        "Le matériau des fenêtres, des menus, du Dock et de la barre des menus.",
    "Menu bar glass intensity": "Intensité du verre des menus",
    "Adjust the popovers from ultra-clear to fully tinted, like macOS Golden Gate.":
        "Réglez les popovers d'un verre très clair à une teinte soutenue, comme dans macOS Golden Gate.",
    "Frosted": "Givré",
    "Clear, lightly blurred glass, as in macOS Tahoe.":
        "Un verre clair et légèrement flouté, comme dans macOS Tahoe.",
    "Deeply blurred frosted glass and a translucent menu bar, as before Tahoe.":
        "Un verre dépoli très flouté et une barre des menus translucide, comme avant Tahoe.",
    "Window blur is off. Turn on the Acrylic Glass effect in System Settings → "
    "Window Management → Desktop Effects to see it.":
        "Le flou des fenêtres est désactivé. Activez l'effet Acrylic Glass dans "
        "Configuration du système → Gestion des fenêtres → Effets de bureau.",
    "Give your apps macOS icons from .icns files, with a Light and a Dark "
    "version, or tint them all with the accent colour.":
        "Donnez à vos apps des icônes macOS à partir de fichiers .icns, en version "
        "claire et sombre, ou teintez-les toutes avec la couleur d'accentuation.",
    "Icon style": "Style des icônes",
    "Default": "Par défaut",
    "Tinted": "Teinté",
    "Clear": "Clair",
    "Import a folder of .icns files": "Importer un dossier de fichiers .icns",
    "Files are matched to apps by name; “Dark” in a name sets the Dark icon.":
        "Les fichiers sont associés aux apps par leur nom ; « Dark » dans le nom "
        "définit l'icône sombre.",
    "Import…": "Importer…",
    "Reset all icons": "Réinitialiser toutes les icônes",
    "Back to the theme's icons and the Default style.":
        "Revenir aux icônes du thème et au style par défaut.",
    "Reset": "Réinitialiser",
    "Applications": "Applications",
    "Search apps": "Rechercher une app",
    "Drop an .icns file on an app, or click it.":
        "Déposez un fichier .icns sur une app, ou cliquez dessus.",
    "Choose…": "Choisir…",
    "Extract from a disk image": "Extraire d'une image disque",
    "Takes the icon of an app in a macOS .dmg, with its Dark, Tinted and "
    "Clear versions when the app has them.":
        "Prend l'icône d'une app d'un .dmg macOS, avec ses versions Sombre, "
        "Teintée et Transparente quand l'app les fournit.",
    "Disk images (.dmg)": "Images disque (.dmg)",
    "No app icon found in {name}.": "Aucune icône d'app trouvée dans {name}.",
    "App in the image": "App de l'image",
    "Apply to": "Appliquer à",
    "Cancel": "Annuler",
    "Apply": "Appliquer",
    "Customized": "Personnalisée",
    "The Icon Manager is not installed.": "Le gestionnaire d'icônes n'est pas installé.",
    "A macOS Tahoe look for KDE Plasma.": "L'apparence de macOS Tahoe pour KDE Plasma.",
    "Window blur": "Flou des fenêtres",
    "Font rendering": "Rendu des polices",
    "Applying…": "Application…",
    "Could not apply the change.": "Impossible d'appliquer la modification.",
    "Icon images (.icns, .png, .svg)": "Images d'icônes (.icns, .png, .svg)",
    "Theme switch not found: reinstall the theme.":
        "Commutateur de thème introuvable : réinstallez le thème.",
    "Back": "Précédent",
    "Forward": "Suivant",
    "Glass tint": "Teinte du verre",
    "macOS": "macOS",
    "The colour of the glass: Apple's, none (a neutral Dock and black context menus), or "
    "the accent colour on the Dock, the context menus and the menu bar popovers.":
        "La couleur du verre : celle d'Apple, aucune (Dock neutre et menus contextuels "
        "noirs), ou la couleur d'accentuation sur le Dock, les menus contextuels et les "
        "menus de la barre.",
    "Opaque menus, Dock and windows, as in macOS' accessibility settings.":
        "Menus, Dock et fenêtres opaques, comme dans les réglages d'accessibilité de macOS.",
    "Desktop & Dock": "Bureau et Dock",
    "The Dock's size and magnification, how windows minimize and what the screen's "
    "corners do.":
        "La taille et l'agrandissement du Dock, la réduction des fenêtres et l'action des "
        "coins de l'écran.",
    "Dock": "Dock",
    "Size": "Taille",
    "Small": "Petite",
    "Large": "Grande",
    "Magnification": "Agrandissement",
    "Off": "Désactivé",
    "Max": "Max.",
    "Automatically hide and show the Dock": "Masquer/afficher automatiquement le Dock",
    "Minimize windows using": "Réduire les fenêtres avec l'effet",
    "Genie Effect": "Effet Génie",
    "Scale Effect": "Effet Échelle",
    "Hot Corners": "Coins actifs",
    "Move the pointer into a corner of the screen to start an action.":
        "Placez le pointeur dans un coin de l'écran pour lancer une action.",
    "—": "—",
    "Mission Control": "Mission Control",
    "Application Windows": "Fenêtres de l'application",
    "All Windows": "Toutes les fenêtres",
    "Desktop": "Bureau",
    "Launchpad": "Launchpad",
    "Lock Screen": "Verrouiller l'écran",
    "The Dock is not running: its settings come back with Plasma.":
        "Le Dock n'est pas lancé : ses réglages reviennent avec Plasma.",
    "Version": "Version",
}


def _language() -> str:
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if value:
            return value.split(":")[0].split(".")[0].split("_")[0]
    return "en"


_STRINGS = _FR if _language() == "fr" else {}


def _(text: str) -> str:
    return _STRINGS.get(text, text)


# ── System state ──────────────────────────────────────────────────────


def user_full_name() -> str:
    """The real name (GECOS) of the user, else the login name."""
    import pwd
    try:
        entry = pwd.getpwuid(os.getuid())
    except KeyError:
        return os.environ.get("USER", "")
    full = entry.pw_gecos.split(",")[0].strip()
    return full or entry.pw_name


def avatar_path() -> Path | None:
    """The picture KDE's Users settings set: AccountsService's icon, else
    ~/.face(.icon)."""
    user = os.environ.get("USER") or ""
    for path in (Path("/var/lib/AccountsService/icons") / user, HOME / ".face.icon", HOME / ".face"):
        try:
            if path.is_file() and path.stat().st_size > 0:
                return path
        except OSError:
            continue
    return None


def avatar_widget(size: int) -> Gtk.Widget:
    """A round avatar: the user's picture, else their initials on a grey
    gradient, like macOS' default account picture."""
    frame = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
    frame.add_css_class("avatar")
    frame.set_size_request(size, size)
    frame.set_overflow(Gtk.Overflow.HIDDEN)
    path = avatar_path()
    texture = None
    if path is not None:
        try:
            texture = Gdk.Texture.new_from_filename(str(path))
        except GLib.Error:
            texture = None
    if texture is not None:
        picture = Gtk.Picture(paintable=texture, content_fit=Gtk.ContentFit.COVER, can_shrink=True)
        picture.set_size_request(size, size)
        picture.set_hexpand(True)
        frame.append(picture)
    else:
        words = [w for w in user_full_name().replace(".", " ").split() if w]
        initials = "".join(w[0] for w in words[:2]).upper() or "?"
        text = label(initials, "avatar-initials", xalign=0.5)
        text.set_hexpand(True)
        frame.add_css_class("avatar-empty")
        frame.append(text)
    return frame


def kread(file: str, group: str, key: str) -> str:
    try:
        return subprocess.run(["kreadconfig6", "--file", file, "--group", group, "--key", key],
                              check=False, capture_output=True, text=True,
                              timeout=5).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _rgb_to_hex(value: str) -> str:
    parts = value.split(",")
    try:
        r, g, b = (int(p) for p in parts[:3])
    except ValueError:
        return ""
    return f"#{r:02x}{g:02x}{b:02x}"


def current_mode() -> str:
    """As mac-tahoe-theme-switch sees it: the Global Theme it applied."""
    laf = kread("kdeglobals", "KDE", "LookAndFeelPackage")
    return "light" if laf == "org.kde.mac-tahoe-liquid-kde.light" else "dark"


def custom_accent() -> str:
    """The accent chosen by the user, empty for Multicolour."""
    return _rgb_to_hex(kread("kdeglobals", "General", "AccentColor"))


def effective_accent() -> str:
    """The accent in use (the selection colour the scheme was applied with)."""
    return (_rgb_to_hex(kread("kdeglobals", "Colors:Selection", "BackgroundNormal"))
            or custom_accent() or "#0088ff")


def dock_tint() -> str:
    """The Dock's veil, as mac-tahoe-theme-switch keeps it."""
    try:
        state = json.loads((CONFIG / "mac-tahoe-liquid-kde/appearance.json").read_text())
    except (OSError, ValueError):
        return "macos"
    tint = state.get("dock_tint") if isinstance(state, dict) else None
    return tint if tint in ("macos", "neutral", "accent") else "macos"


def glass_level() -> int:
    """The menu bar popovers' Golden Gate clear-to-tinted setting."""
    try:
        state = json.loads((CONFIG / "mac-tahoe-liquid-kde/appearance.json").read_text())
    except (OSError, ValueError):
        return 50
    value = state.get("glass_level") if isinstance(state, dict) else None
    return max(0, min(100, value)) if isinstance(value, int) and not isinstance(value, bool) else 50


def glass_style() -> str:
    try:
        style = GLASS_STYLE_FILE.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return "tahoe"
    return style if style in ("tahoe", "frosted") else "tahoe"


def glass_enabled() -> bool:
    """The window glass effect (Acrylic Glass, theme_switch.GLASS_EFFECT)."""
    return kread("kwinrc", "Plugins", "liquidglassEnabled") == "true"


def auto_available() -> bool:
    """The installer's 06:00 / 18:00 schedule (./install --auto) is in place:
    a user timer, or a crontab entry on OpenRC."""
    if (CONFIG / "systemd/user" / THEME_TIMER).is_file():
        return True
    try:
        crontab = subprocess.run(["crontab", "-l"], check=False, capture_output=True,
                                 text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "mac-tahoe-theme-switch" in crontab


# ── Background jobs ───────────────────────────────────────────────────


class Jobs:
    """Runs commands one after the other, off the UI thread, reporting
    "progress N" / "report …" lines and the end of the queue."""

    def __init__(self, changed: Callable[[bool, int, str], None]) -> None:
        self._queue: list[tuple[list[str], Callable[[bool, str], None] | None]] = []
        self._running = False
        self._changed = changed
        self.progress = -1

    @property
    def busy(self) -> bool:
        return self._running

    def run(self, argv: list[str], done: Callable[[bool, str], None] | None = None) -> None:
        self._queue.append((argv, done))
        if not self._running:
            self._next()

    def _next(self) -> None:
        if not self._queue:
            self._running = False
            self.progress = -1
            self._changed(False, -1, "")
            return
        argv, done = self._queue.pop(0)
        self._running = True
        self.progress = -1
        self._changed(True, -1, "")
        try:
            proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE
                                      | Gio.SubprocessFlags.STDERR_PIPE)
        except GLib.Error as exc:
            if done:
                done(False, exc.message)
            self._next()
            return
        stream = Gio.DataInputStream.new(proc.get_stdout_pipe())
        report: list[str] = []

        def finished(p, result):
            try:
                ok = p.wait_check_finish(result)
            except GLib.Error:
                ok = False
            error = ""
            if not ok:
                try:
                    error = p.get_stderr_pipe().read_bytes(4096, None).get_data().decode(
                        errors="replace").strip()
                except GLib.Error:
                    pass
            if done:
                done(ok, "\n".join(report) if ok else error)
            self._next()

        def line(s, result):
            try:
                text, _len = s.read_line_finish_utf8(result)
            except GLib.Error:
                text = None
            if text is None:
                proc.wait_check_async(None, finished)
                return
            if text.startswith("progress "):
                try:
                    self.progress = int(text.split()[1])
                except (IndexError, ValueError):
                    pass
                self._changed(True, self.progress, "")
            elif text.startswith("report "):
                report.append(text[len("report "):])
            s.read_line_async(GLib.PRIORITY_DEFAULT, None, line)

        stream.read_line_async(GLib.PRIORITY_DEFAULT, None, line)


# ── Widgets ───────────────────────────────────────────────────────────


def label(text: str, *classes: str, xalign: float = 0, wrap: bool = False) -> Gtk.Label:
    widget = Gtk.Label(label=text, xalign=xalign)
    if wrap:
        widget.set_wrap(True)
        widget.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    for css in classes:
        widget.add_css_class(css)
    return widget


# The sidebar and header glyphs, drawn here like SF Symbols: icon themes
# rarely carry the -symbolic names, and GTK then shows a missing image.
_GLYPHS = {
    "appearance": '<circle cx="12" cy="12" r="7.5" fill="none" stroke="#fff" stroke-width="2"/>'
                  '<path d="M12 4.5a7.5 7.5 0 0 1 0 15z" fill="#fff"/>',
    "glass": '<path d="M12 3.2c3.6 4.4 6.2 7.7 6.2 10.9a6.2 6.2 0 0 1-12.4 0'
             'c0-3.2 2.6-6.5 6.2-10.9z" fill="#fff"/>'
             '<path d="M9.3 13.6a3 3 0 0 0 2.2 3.4" fill="none" stroke="#000" '
             'stroke-opacity=".28" stroke-width="1.5" stroke-linecap="round"/>',
    "dock": '<rect x="3" y="4.5" width="18" height="13" rx="2.5" fill="none" stroke="#fff" '
            'stroke-width="1.8"/><rect x="6.5" y="13.2" width="11" height="2.4" rx="1.2" '
            'fill="#fff"/><path d="M9 20.5h6" stroke="#fff" stroke-width="1.8" '
            'stroke-linecap="round"/>',
    "icons": '<rect x="4" y="4" width="7" height="7" rx="2" fill="#fff"/>'
             '<rect x="13" y="4" width="7" height="7" rx="2" fill="#fff"/>'
             '<rect x="4" y="13" width="7" height="7" rx="2" fill="#fff"/>'
             '<rect x="13" y="13" width="7" height="7" rx="2" fill="#fff"/>',
    "about": '<circle cx="12" cy="12" r="8" fill="none" stroke="#fff" stroke-width="2"/>'
             '<circle cx="12" cy="8.2" r="1.3" fill="#fff"/>'
             '<rect x="10.9" y="10.6" width="2.2" height="6" rx="1.1" fill="#fff"/>',
    "warning": '<path d="M12 3.5 21 19.5H3z" fill="#fff" stroke="#fff" stroke-width="1.5" '
               'stroke-linejoin="round"/><rect x="11" y="9" width="2" height="5.5" rx="1" '
               'fill="#ff8a00"/><circle cx="12" cy="16.9" r="1.1" fill="#ff8a00"/>',
    "corners": '<rect x="4" y="5" width="16" height="12" rx="2" fill="none" stroke="#fff" '
               'stroke-width="1.8"/><path d="M4 9V7a2 2 0 0 1 2-2h2M20 9V7a2 2 0 0 0-2-2h-2" '
               'stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>'
               '<path d="M9 20.5h6" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/>',
}
_GLYPH_TEXTURES: dict[tuple[str, int], Gdk.Texture | None] = {}


def glyph_texture(name: str, pixels: int) -> Gdk.Texture | None:
    key = (name, pixels)
    if key not in _GLYPH_TEXTURES:
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{pixels}" height="{pixels}" '
               f'viewBox="0 0 24 24">{_GLYPHS[name]}</svg>')
        try:
            _GLYPH_TEXTURES[key] = Gdk.Texture.new_from_bytes(GLib.Bytes.new(svg.encode()))
        except GLib.Error:
            _GLYPH_TEXTURES[key] = None
    return _GLYPH_TEXTURES[key]


def glyph_image(icon: str, size: int) -> Gtk.Image:
    """One of _GLYPHS (rendered at twice the size, for HiDPI), else a
    themed icon name."""
    texture = glyph_texture(icon, size * 2) if icon in _GLYPHS else None
    if texture is not None:
        image = Gtk.Image.new_from_paintable(texture)
    else:
        image = Gtk.Image.new_from_icon_name(icon)
    image.set_pixel_size(size)
    return image


def tile(icon: str, colour: str, size: int = 22) -> Gtk.Widget:
    """A sidebar / row icon: a white glyph on a coloured rounded square."""
    box = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
    box.add_css_class("tile")
    box.add_css_class(f"tile-{colour}")
    box.set_size_request(size, size)
    image = glyph_image(icon, int(size * 0.72))
    image.set_size_request(size, size)
    box.append(image)
    return box


def group(*rows: Gtk.Widget) -> Gtk.Box:
    """macOS settings group: rounded box, rows split by inset separators."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.add_css_class("group")
    for index, row in enumerate(rows):
        if index:
            sep = Gtk.Separator()
            sep.add_css_class("row-separator")
            box.append(sep)
        box.append(row)
    return box


def row(title: str, subtitle: str = "", end: Gtk.Widget | None = None,
        icon: Gtk.Widget | None = None) -> Gtk.Box:
    box = Gtk.Box(spacing=10)
    box.add_css_class("row")
    if icon is not None:
        box.append(icon)
    text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
    text.append(label(title, "row-title"))
    if subtitle:
        text.append(label(subtitle, "row-subtitle", wrap=True))
    box.append(text)
    if end is not None:
        end.set_valign(Gtk.Align.CENTER)
        box.append(end)
    return box


def header_card(icon: Gtk.Widget, title: str, description: str) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    box.add_css_class("header-card")
    icon.set_halign(Gtk.Align.CENTER)
    icon.set_margin_bottom(8)
    box.append(icon)
    box.append(label(title, "header-title", xalign=0.5))
    desc = label(description, "header-description", xalign=0.5, wrap=True)
    desc.set_justify(Gtk.Justification.CENTER)
    desc.set_max_width_chars(60)
    box.append(desc)
    return box


def big_tile(icon: str, colour: str) -> Gtk.Widget:
    widget = tile(icon, colour, 64)
    widget.add_css_class("big")
    return widget


def section(title: str) -> Gtk.Label:
    widget = label(title, "section-title")
    widget.set_margin_top(6)
    return widget


def switch(active: bool, changed: Callable[[bool], None]) -> Gtk.Switch:
    """A macOS switch; `changed` only runs for the user's own clicks."""
    widget = Gtk.Switch(active=active, valign=Gtk.Align.CENTER)
    widget.add_css_class("mac-switch")
    widget.updating = False

    def toggled(w: Gtk.Switch, _param) -> None:
        if not w.updating:
            changed(w.get_active())
    widget.connect("notify::active", toggled)
    return widget


def set_switch(widget: Gtk.Switch, active: bool) -> None:
    widget.updating = True
    widget.set_active(active)
    widget.updating = False


class Slider(Gtk.Box):
    """macOS slider: a thin track with tick marks between two captions.
    `changed` runs once the value rests (350 ms), not on every step."""

    def __init__(self, low: float, high: float, step: float, left: str, right: str,
                 changed: Callable[[float], None], marks: int = 0):
        super().__init__(spacing=10, valign=Gtk.Align.CENTER)
        self.add_css_class("mac-slider")
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, low, high, step)
        self.scale.set_draw_value(False)
        self.scale.set_size_request(220, -1)
        self.scale.set_hexpand(True)
        for index in range(marks):
            self.scale.add_mark(low + (high - low) * index / max(1, marks - 1),
                                Gtk.PositionType.BOTTOM, None)
        self.append(label(left, "slider-caption"))
        self.append(self.scale)
        self.append(label(right, "slider-caption"))
        self._changed = changed
        self._updating = False
        self._timer = 0
        self.scale.connect("value-changed", self._moved)

    def set_value(self, value: float) -> None:
        self._updating = True
        self.scale.set_value(value)
        self._updating = False

    def _moved(self, _scale) -> None:
        if self._updating:
            return
        if self._timer:
            GLib.source_remove(self._timer)
        self._timer = GLib.timeout_add(350, self._rest)

    def _rest(self) -> bool:
        self._timer = 0
        self._changed(self.scale.get_value())
        return False


class PopUp(Gtk.DropDown):
    """A macOS pop-up button over (key, title) choices."""

    def __init__(self, choices: tuple[tuple[str, str], ...], changed: Callable[[str], None]):
        super().__init__(model=Gtk.StringList.new([title for _key, title in choices]),
                         valign=Gtk.Align.CENTER)
        self.add_css_class("mac-popup")
        self.keys = [key for key, _title in choices]
        self._changed = changed
        self._updating = False
        self.connect("notify::selected", self._selected)

    def set_key(self, key: str) -> None:
        if key in self.keys:
            self._updating = True
            self.set_selected(self.keys.index(key))
            self._updating = False

    def _selected(self, *_args) -> None:
        index = self.get_selected()
        if not self._updating and 0 <= index < len(self.keys):
            self._changed(self.keys[index])


def query_json(argv: list[str], done: Callable[[object], None]) -> None:
    """Run a tool off the UI thread and hand its JSON output (None when it
    fails) to `done`."""
    try:
        proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE
                                  | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error:
        done(None)
        return

    def finished(p, result):
        try:
            _ok, out, _err = p.communicate_utf8_finish(result)
            value = json.loads(out) if out and out.strip() else None
        except (GLib.Error, ValueError):
            value = None
        done(value)
    proc.communicate_utf8_async(None, None, finished)


_WALLPAPERS: dict[tuple[str, int, int], Gdk.Texture | None] = {}


def wallpaper_picture(mode: str, width: int, height: int) -> Gtk.Widget:
    """The macOS Tahoe wallpaper of `mode`, cropped to width x height (the
    texture has that size, so the picture's natural size is the preview's)."""
    key = (mode, width, height)
    if key not in _WALLPAPERS:
        _WALLPAPERS[key] = _wallpaper_texture(mode, width, height)
    picture = Gtk.Picture(can_shrink=False, content_fit=Gtk.ContentFit.COVER)
    picture.set_size_request(width, height)
    if _WALLPAPERS[key] is not None:
        picture.set_paintable(_WALLPAPERS[key])
    return picture


def _wallpaper_texture(mode: str, width: int, height: int) -> Gdk.Texture | None:
    folder = WALLPAPER / ("images_dark" if mode == "dark" else "images")
    files = (sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))
             if folder.is_dir() else [])
    if not files:
        return None
    try:
        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf
        source = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(files[0]), width * 3, -1, True)
        scale = max(width / source.get_width(), height / source.get_height())
        w, h = max(width, round(source.get_width() * scale)), max(height, round(source.get_height() * scale))
        scaled = source.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)
        cropped = scaled.new_subpixbuf((w - width) // 2, (h - height) // 2, width, height)
        ok, data = cropped.save_to_bufferv("png", [], [])
        return Gdk.Texture.new_from_bytes(GLib.Bytes.new(bytes(data))) if ok else None
    except (GLib.Error, ImportError, ValueError):
        return None


class Choice(Gtk.Button):
    """A macOS picture choice (Appearance, window material): a thumbnail
    with a ring when selected, its name under it."""

    def __init__(self, title: str, thumbnail: Gtk.Widget, clicked: Callable[[], None]):
        super().__init__()
        self.add_css_class("choice")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame = Gtk.Box()
        frame.add_css_class("choice-frame")
        frame.append(thumbnail)
        box.append(frame)
        box.append(label(title, "choice-title", xalign=0.5))
        self.set_child(box)
        self.connect("clicked", lambda _b: clicked())

    def set_selected(self, selected: bool) -> None:
        if selected:
            self.add_css_class("selected")
        else:
            self.remove_css_class("selected")


def appearance_thumbnail(kind: str) -> Gtk.Widget:
    """A small desktop: the wallpaper and a window in the appearance; Auto
    shows both halves."""
    overlay = Gtk.Overlay(overflow=Gtk.Overflow.HIDDEN)
    overlay.add_css_class("thumb")
    overlay.set_child(wallpaper_picture("dark" if kind == "dark" else "light", 92, 60))
    window = Gtk.Box(halign=Gtk.Align.START, valign=Gtk.Align.START,
                     margin_start=12, margin_top=10)
    window.set_size_request(62, 40)
    for part in (("light", "dark") if kind == "auto" else (kind,)):
        half = Gtk.Box(hexpand=True, orientation=Gtk.Orientation.VERTICAL)
        half.add_css_class(f"mini-window-{part}")
        bar = Gtk.Box(spacing=2, margin_start=4, margin_top=4)
        if part == ("light" if kind == "auto" else kind):
            for colour in ("red", "yellow", "green"):
                dot = Gtk.Box()
                dot.add_css_class("dot")
                dot.add_css_class(f"dot-{colour}")
                bar.append(dot)
        half.append(bar)
        accent = Gtk.Box(margin_start=6, margin_top=8, margin_end=6)
        accent.add_css_class("mini-accent")
        half.append(accent)
        window.append(half)
    window.add_css_class("mini-window")
    overlay.add_overlay(window)
    return overlay


def glass_thumbnail(style: str, mode: str) -> Gtk.Widget:
    """The wallpaper behind a panel of the material, with a menu bar."""
    overlay = Gtk.Overlay(overflow=Gtk.Overflow.HIDDEN)
    overlay.add_css_class("thumb")
    overlay.set_child(wallpaper_picture(mode, 184, 108))
    menubar = Gtk.Box(valign=Gtk.Align.START)
    menubar.set_size_request(-1, 9)
    menubar.add_css_class(f"mini-menubar-{style}")
    overlay.add_overlay(menubar)
    panel = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, margin_top=8)
    panel.set_size_request(112, 62)
    panel.add_css_class(f"mini-glass-{style}")
    overlay.add_overlay(panel)
    dock = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.END, margin_bottom=5)
    dock.set_size_request(86, 14)
    dock.add_css_class(f"mini-glass-{style}")
    dock.add_css_class("mini-dock")
    overlay.add_overlay(dock)
    return overlay


def tint_thumbnail(tint: str, mode: str) -> Gtk.Widget:
    """The wallpaper behind a small Dock in the glass tint."""
    overlay = Gtk.Overlay(overflow=Gtk.Overflow.HIDDEN)
    overlay.add_css_class("thumb")
    overlay.set_child(wallpaper_picture(mode, 92, 60))
    dock = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.END, margin_bottom=7, spacing=3)
    dock.set_size_request(64, 15)
    dock.add_css_class("mini-glass-tahoe")
    dock.add_css_class(f"mini-tint-{tint}")
    for _index in range(4):
        app = Gtk.Box(valign=Gtk.Align.CENTER)
        app.set_size_request(9, 9)
        app.add_css_class("mini-app")
        dock.append(app)
    dock.get_first_child().set_margin_start(6)
    overlay.add_overlay(dock)
    return overlay


def corners_thumbnail(mode: str) -> Gtk.Widget:
    overlay = Gtk.Overlay(overflow=Gtk.Overflow.HIDDEN)
    overlay.add_css_class("thumb")
    overlay.add_css_class("screen")
    overlay.set_child(wallpaper_picture(mode, 200, 125))
    menubar = Gtk.Box(valign=Gtk.Align.START)
    menubar.set_size_request(-1, 7)
    menubar.add_css_class("mini-menubar-tahoe-bar")
    overlay.add_overlay(menubar)
    dock = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.END, margin_bottom=5)
    dock.set_size_request(90, 13)
    dock.add_css_class("mini-glass-tahoe")
    dock.add_css_class("mini-dock")
    overlay.add_overlay(dock)
    return overlay


# ── Pages ─────────────────────────────────────────────────────────────


class AppearancePage(Gtk.Box):
    def __init__(self, window: "SettingsWindow"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.window = window
        self.append(header_card(big_tile("appearance", "graphite"),
                                _("Appearance"),
                                _("Choose how your Mac-like desktop looks: light, dark, or switching "
                                  "by itself, and the colour of buttons, selections and highlights.")))
        choices = Gtk.Box(spacing=18, halign=Gtk.Align.START)
        self.modes: dict[str, Choice] = {}
        kinds = (("auto", _("Auto")),) if auto_available() else ()
        for kind, title in kinds + (("light", _("Light")), ("dark", _("Dark"))):
            choice = Choice(title, appearance_thumbnail(kind),
                            lambda k=kind: self.set_mode(k))
            self.modes[kind] = choice
            choices.append(choice)
        mode_row = row(_("Appearance"),
                       _("Auto switches to Light at 06:00 and to Dark at 18:00.") + " "
                       + _("Light and Dark last until the next switch; reinstall with --light "
                           "or --dark to keep one.") if auto_available() else "", choices)
        self.auto = auto_available()

        swatches = Gtk.Box(spacing=8)
        self.swatches: dict[str, Gtk.ToggleButton] = {}
        first = None
        for name, colour in ACCENTS:
            button = Gtk.ToggleButton()
            button.add_css_class("swatch")
            button.add_css_class(f"swatch-{name}")
            button.set_tooltip_text(_(name.capitalize()))
            if first is None:
                first = button
            else:
                button.set_group(first)
            button.connect("toggled", self._accent_toggled, colour)
            self.swatches[name] = button
            swatches.append(button)
        self.accent_name = label("", "row-subtitle")
        accent_end = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        accent_end.append(swatches)
        accent_end.append(self.accent_name)
        self.accent_name.set_xalign(0.5)
        self.append(group(mode_row, row(_("Accent color"), "", accent_end)))
        self._updating = False
        self.refresh()

    def refresh(self) -> None:
        self._updating = True
        # The schedule stays in charge: Light / Dark last until its next flip.
        mode = "auto" if self.auto else current_mode()
        for kind, choice in self.modes.items():
            choice.set_selected(kind == mode)
        accent = custom_accent()
        selected = "multicolour"
        for name, colour in ACCENTS:
            if colour and accent and colour.lower() == accent.lower():
                selected = name
        if accent and selected == "multicolour":
            selected = ""  # a colour picked elsewhere (System Settings)
        if kread("kdeglobals", "General", "accentColorFromWallpaper").lower() == "true":
            selected = "wallpaper"
        for name, button in self.swatches.items():
            button.set_active(name == selected)
        self.accent_name.set_label(_(selected.capitalize()) if selected else accent)
        self._updating = False

    def set_mode(self, kind: str) -> None:
        self.window.run_theme_switch([kind], self.window.refresh_all)

    def _accent_toggled(self, button: Gtk.ToggleButton, colour: str | None) -> None:
        if self._updating or not button.get_active():
            return
        self.window.set_accent(colour)


class GlassPage(Gtk.Box):
    def __init__(self, window: "SettingsWindow"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.window = window
        self.append(header_card(big_tile("glass", "cyan"),
                                _("Liquid Glass"),
                                _("The material of windows, menus, the Dock and the menu bar.")))
        mode = current_mode()
        cards = Gtk.Box(spacing=18, halign=Gtk.Align.CENTER)
        self.choices: dict[str, Choice] = {}
        for style, title in (("tahoe", _("Liquid Glass")), ("frosted", _("Frosted"))):
            choice = Choice(title, glass_thumbnail(style, mode),
                            lambda s=style: self.set_style(s))
            self.choices[style] = choice
            cards.append(choice)
        cards.set_margin_top(14)
        cards.set_margin_bottom(6)
        self.description = label("", "row-subtitle", xalign=0.5, wrap=True)
        self.description.set_justify(Gtk.Justification.CENTER)
        self.description.set_margin_bottom(12)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class("group")
        box.append(cards)
        box.append(self.description)
        self.append(box)

        self.glass_level = Slider(0, 100, 1, _("Clear"), _("Tinted"),
                                  self._glass_level_changed)
        level_box = group(row(
            _("Menu bar glass intensity"),
            _("Adjust the popovers from ultra-clear to fully tinted, like macOS Golden Gate.")),
            self.glass_level)
        self.append(level_box)

        # The glass's tint: Apple's colours, none (grey Dock, black menus) or
        # the accent, menus included (mac-tahoe-theme-switch dock-tint).
        tints = Gtk.Box(spacing=14, halign=Gtk.Align.CENTER)
        tints.set_margin_top(12)
        tints.set_margin_bottom(4)
        self.tint_choices: dict[str, Choice] = {}
        for tint, title in (("macos", _("macOS")), ("neutral", _("Neutral")),
                            ("accent", _("Accent Color"))):
            choice = Choice(title, tint_thumbnail(tint, mode),
                            lambda t=tint: self.set_tint(t))
            self.tint_choices[tint] = choice
            tints.append(choice)
        tint_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        tint_box.add_css_class("group")
        tint_box.append(row(_("Glass tint"),
                            _("The colour of the glass: Apple's, none (a neutral Dock and black "
                              "context menus), or the accent colour on the Dock, the context "
                              "menus and the menu bar popovers.")))
        tint_box.append(tints)
        tint_box.get_last_child().set_margin_bottom(14)
        self.append(tint_box)

        self.warning = row(_("Window blur"),
                           _("Window blur is off. Turn on the Acrylic Glass effect in System Settings → "
                             "Window Management → Desktop Effects to see it."),
                           icon=tile("warning", "orange"))
        self.warning_group = group(self.warning)
        self.append(self.warning_group)
        self.refresh()

    def refresh(self) -> None:
        style = glass_style()
        for name, choice in self.choices.items():
            choice.set_selected(name == style)
        self.description.set_label(
            _("Clear, lightly blurred glass, as in macOS Tahoe.") if style == "tahoe"
            else _("Deeply blurred frosted glass and a translucent menu bar, as before Tahoe."))
        self.warning_group.set_visible(not glass_enabled())
        tint = dock_tint()
        for name, choice in self.tint_choices.items():
            choice.set_selected(name == tint)
        self.glass_level.set_value(glass_level())

    def set_style(self, style: str) -> None:
        self.window.run_theme_switch(["style", style], self.window.refresh_all)

    def set_tint(self, tint: str) -> None:
        if tint != dock_tint():
            self.window.run_theme_switch(["dock-tint", tint], self.window.refresh_all)

    def _glass_level_changed(self, level: float) -> None:
        self.window.run_theme_switch(["glass-level", str(round(level))], self.window.refresh_all)



class DockPage(Gtk.Box):
    """macOS' Desktop & Dock: the Dock (Plasma), the minimize effect and the
    hot corners (KWin), through mac-tahoe-theme-switch dock / minimize /
    hot-corners."""

    CORNERS = (("top-left", 0, 0), ("top-right", 2, 0), ("bottom-left", 0, 1),
               ("bottom-right", 2, 1))
    ACTIONS = (("none", "—"), ("mission-control", "Mission Control"),
               ("app-windows", "Application Windows"), ("all-windows", "All Windows"),
               ("desktop", "Desktop"), ("launchpad", "Launchpad"),
               ("lock-screen", "Lock Screen"))

    def __init__(self, window: "SettingsWindow"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.window = window
        self.append(header_card(big_tile("dock", "graphite"), _("Desktop & Dock"),
                                _("The Dock's size and magnification, how windows minimize and "
                                  "what the screen's corners do.")))

        self.append(section(_("Dock")))
        self.size = Slider(40, 96, 2, _("Small"), _("Large"),
                           lambda v: self._dock("size", str(round(v))), marks=8)
        self.magnify = switch(True, self._magnify_toggled)
        self.magnification = Slider(110, 200, 5, _("Small"), _("Large"),
                                    lambda v: self._dock("magnification", str(round(v))),
                                    marks=7)
        magnify_end = Gtk.Box(spacing=12, valign=Gtk.Align.CENTER)
        magnify_end.append(self.magnification)
        magnify_end.append(self.magnify)
        self.autohide = switch(True, lambda on: self._dock("autohide", "on" if on else "off"))
        self.minimize = PopUp((("genie", _("Genie Effect")), ("scale", _("Scale Effect"))),
                              lambda key: self.window.run_theme_switch(
                                  ["minimize", key], self.refresh))
        self.dock_rows = (row(_("Size"), "", self.size),
                          row(_("Magnification"), "", magnify_end),
                          row(_("Automatically hide and show the Dock"), "", self.autohide))
        self.dock_missing = group(row(_("The Dock is not running: its settings come back with "
                                        "Plasma."), icon=tile("warning", "orange")))
        self.dock_missing.set_visible(False)
        self.append(self.dock_missing)
        self.append(group(*self.dock_rows, row(_("Minimize windows using"), "", self.minimize)))

        grid = Gtk.Grid(column_spacing=14, row_spacing=60, halign=Gtk.Align.CENTER)
        grid.set_margin_top(16)
        grid.set_margin_bottom(16)
        self.corner_popups: dict[str, PopUp] = {}
        actions = tuple((key, _(title)) for key, title in self.ACTIONS)
        for corner, column, line in self.CORNERS:
            popup = PopUp(actions, lambda key, c=corner: self.window.run_theme_switch(
                ["hot-corners", c, key], self.refresh))
            popup.set_valign(Gtk.Align.START if line == 0 else Gtk.Align.END)
            self.corner_popups[corner] = popup
            grid.attach(popup, column, line, 1, 1)
        screen = corners_thumbnail(current_mode())
        screen.set_valign(Gtk.Align.CENTER)
        grid.attach(screen, 1, 0, 1, 2)
        corners = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        corners.add_css_class("group")
        corners.append(row(_("Hot Corners"),
                           _("Move the pointer into a corner of the screen to start an action."),
                           icon=tile("corners", "blue")))
        corners.append(grid)
        self.append(corners)
        self.refresh()

    def refresh(self, *_args) -> None:
        tool = str(THEME_SWITCH)
        if not THEME_SWITCH.is_file():
            return
        query_json([tool, "dock"], self._dock_state)
        query_json([tool, "hot-corners"], self._corner_state)
        # KWin's Magic Lamp is macOS' Genie; Squash (KWin's default) its Scale.
        self.minimize.set_key("genie" if kread("kwinrc", "Plugins", "magiclampEnabled") == "true"
                              else "scale")

    def _dock_state(self, state: object) -> None:
        running = isinstance(state, dict)
        for widget in self.dock_rows:
            widget.set_sensitive(running)
        self.dock_missing.set_visible(not running)
        if not running:
            return
        self.size.set_value(float(state.get("size", 64)))
        magnification = int(state.get("magnification", 160))
        set_switch(self.magnify, magnification > 100)
        self.magnification.set_sensitive(magnification > 100)
        if magnification > 100:
            self.magnification.set_value(float(magnification))
        set_switch(self.autohide, bool(state.get("autohide")))

    def _corner_state(self, state: object) -> None:
        if isinstance(state, dict):
            for corner, popup in self.corner_popups.items():
                popup.set_key(str(state.get(corner, "none")))

    def _dock(self, key: str, value: str) -> None:
        self.window.run_theme_switch(["dock", key, value], self.refresh)

    def _magnify_toggled(self, on: bool) -> None:
        self.magnification.set_sensitive(on)
        value = round(self.magnification.scale.get_value()) if on else 100
        self._dock("magnification", str(max(110, value) if on else 100))


class IconsPage(Gtk.Box):
    def __init__(self, window: "SettingsWindow"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.window = window
        self.apps: list[dict] = []
        self.append(header_card(big_tile("view-app-grid-symbolic", "blue"), _("Icons"),
                                _("Give your apps macOS icons from .icns files, with a Light and a "
                                  "Dark version, or tint them all with the accent colour.")))
        if not ICON_MANAGER.is_file():
            self.append(group(row(_("The Icon Manager is not installed."))))
            return

        styles = Gtk.Box(spacing=0)
        styles.add_css_class("segmented")
        self.style_buttons: dict[str, Gtk.ToggleButton] = {}
        first = None
        for style, title in (("default", _("Default")), ("dark", _("Dark")),
                             ("clear", _("Clear")), ("tinted", _("Tinted"))):
            button = Gtk.ToggleButton(label=title)
            if first is None:
                first = button
            else:
                button.set_group(first)
            button.connect("toggled", self._style_toggled, style)
            self.style_buttons[style] = button
            styles.append(button)
        import_button = Gtk.Button(label=_("Import…"))
        import_button.connect("clicked", lambda _b: self._choose_folder())
        self.dmg_button = Gtk.Button(label=_("Choose…"))
        self.dmg_button.connect("clicked", lambda _b: self._choose_dmg())
        reset_button = Gtk.Button(label=_("Reset"))
        reset_button.add_css_class("destructive")
        reset_button.connect("clicked", lambda _b: self._run(["reset-all"]))
        self.append(group(
            row(_("Icon style"), "", styles),
            row(_("Import a folder of .icns files"),
                _("Files are matched to apps by name; “Dark” in a name sets the Dark icon."),
                import_button),
            row(_("Extract from a disk image"),
                _("Takes the icon of an app in a macOS .dmg, with its Dark, Tinted and "
                  "Clear versions when the app has them."),
                self.dmg_button),
            row(_("Reset all icons"), _("Back to the theme's icons and the Default style."),
                reset_button),
        ))

        heading = Gtk.Box(spacing=8)
        heading.append(label(_("Applications"), "section-title", wrap=False))
        heading.get_first_child().set_hexpand(True)
        self.search = Gtk.SearchEntry(placeholder_text=_("Search apps"))
        self.search.add_css_class("search")
        self.search.set_size_request(200, -1)
        self.search.connect("search-changed", lambda _e: self.flow.invalidate_filter())
        heading.append(self.search)
        heading.set_margin_top(6)
        self.append(heading)

        grid_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        grid_group.add_css_class("group")
        hint = label(_("Drop an .icns file on an app, or click it."), "row-subtitle", xalign=0.5)
        hint.set_margin_top(10)
        grid_group.append(hint)
        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
                                max_children_per_line=12, min_children_per_line=3,
                                row_spacing=6, column_spacing=6)
        self.flow.add_css_class("app-grid")
        self.flow.set_filter_func(self._filter)
        grid_group.append(self.flow)
        self.append(grid_group)
        self._updating = False
        self.refresh()

    # Data

    def refresh(self) -> None:
        if not ICON_MANAGER.is_file():
            return
        status = self._query("status") or {}
        self._updating = True
        style = status.get("style", "default")
        for name, button in self.style_buttons.items():
            button.set_active(name == style)
        self._updating = False
        self.apps = self._query("list") or []
        self.mode = current_mode()
        self.themes = {}
        child = self.flow.get_first_child()
        while child is not None:
            self.flow.remove(child)
            child = self.flow.get_first_child()
        for app in self.apps:
            self.flow.append(self._app_tile(app))

    def _query(self, command: str):
        try:
            out = subprocess.run([sys.executable, str(ICON_MANAGER), command], check=True,
                                 capture_output=True, text=True, timeout=30).stdout
            return json.loads(out)
        except (OSError, subprocess.SubprocessError, ValueError):
            return None

    def _theme(self, mode: str) -> Gtk.IconTheme:
        if mode not in self.themes:
            theme = Gtk.IconTheme()
            theme.set_theme_name(BASE_ICON_THEMES[mode])
            self.themes[mode] = theme
        return self.themes[mode]

    def icon_paintable(self, app: dict, mode: str, size: int) -> Gdk.Paintable | None:
        """What `mode` shows for `app`: its custom or tinted icon, else the
        theme's (the plain theme of that mode, not the session's)."""
        path = app.get(mode) or ""
        icon = app.get("icon", "")
        if not path and icon.startswith("/"):
            path = icon
        if path:
            try:
                return Gdk.Texture.new_from_filename(path)
            except GLib.Error:
                pass
        if not icon or icon.startswith("/"):
            icon = "application-x-executable"
        return self._theme(mode).lookup_icon(icon, None, size, self.get_scale_factor(),
                                             Gtk.TextDirection.NONE, Gtk.IconLookupFlags(0))

    # Grid

    def _filter(self, child: Gtk.FlowBoxChild) -> bool:
        text = self.search.get_text().strip().lower()
        return not text or text in child.app["name"].lower() or text in child.app["id"].lower()

    def _app_tile(self, app: dict) -> Gtk.FlowBoxChild:
        child = Gtk.FlowBoxChild()
        child.app = app
        button = Gtk.MenuButton()
        button.add_css_class("app-tile")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        image = Gtk.Image.new_from_paintable(self.icon_paintable(app, self.mode, 64))
        image.set_pixel_size(56)
        box.append(image)
        name = label(app["name"], "app-name", xalign=0.5)
        name.set_ellipsize(Pango.EllipsizeMode.END)
        name.set_max_width_chars(11)
        box.append(name)
        if app.get("light_custom") or app.get("dark_custom"):
            dot = Gtk.Box(halign=Gtk.Align.CENTER)
            dot.add_css_class("custom-dot")
            dot.set_tooltip_text(_("Customized"))
            box.append(dot)
        button.set_child(box)
        button.set_popover(self._app_popover(app))
        child.set_child(button)
        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect("drop", self._dropped_on_app, app, None)
        child.add_controller(drop)
        return child

    def _app_popover(self, app: dict) -> Gtk.Popover:
        popover = Gtk.Popover()
        popover.add_css_class("icon-popover")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.append(label(app["name"], "popover-title", xalign=0.5))
        wells = Gtk.Box(spacing=12, homogeneous=True)
        for mode, title in (("light", _("Light")), ("dark", _("Dark"))):
            well = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            frame = Gtk.Box(halign=Gtk.Align.CENTER)
            frame.add_css_class("well")
            frame.add_css_class(f"well-{mode}")
            image = Gtk.Image.new_from_paintable(self.icon_paintable(app, mode, 96))
            image.set_pixel_size(84)
            image.set_hexpand(True)
            frame.append(image)
            drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
            drop.connect("drop", self._dropped_on_app, app, mode)
            frame.add_controller(drop)
            well.append(frame)
            well.append(label(title, "row-subtitle", xalign=0.5))
            buttons = Gtk.Box(spacing=4, halign=Gtk.Align.CENTER)
            choose = Gtk.Button(label=_("Choose…"))
            choose.connect("clicked", lambda _b, m=mode: (popover.popdown(),
                                                          self._choose_file(app, m)))
            buttons.append(choose)
            if app.get(f"{mode}_custom"):
                reset = Gtk.Button.new_from_icon_name("edit-undo-symbolic")
                reset.set_tooltip_text(_("Reset"))
                reset.connect("clicked", lambda _b, m=mode: (popover.popdown(),
                                                             self._run(["reset", app["id"], m])))
                buttons.append(reset)
            well.append(buttons)
            wells.append(well)
        box.append(wells)
        popover.set_child(box)
        return popover

    # Actions

    def _style_toggled(self, button: Gtk.ToggleButton, style: str) -> None:
        if self._updating or not button.get_active():
            return
        self._run(["style", style])

    def _run(self, args: list[str]) -> None:
        def done(ok: bool, message: str) -> None:
            if message:
                self.window.toast(message if ok else _("Could not apply the change.") + "\n" + message)
            elif not ok:
                self.window.toast(_("Could not apply the change."))
            self.refresh()
        self.window.jobs.run([sys.executable, str(ICON_MANAGER), *args], done)

    def _dropped_on_app(self, _target, value, _x, _y, app: dict, mode: str | None) -> bool:
        files = value.get_files() if value else []
        for file in files[:2]:
            path = file.get_path()
            if not path:
                continue
            chosen = mode or ("dark" if "dark" in Path(path).name.lower() else "light")
            self._run(["set", app["id"], chosen, path])
        return bool(files)

    def _image_filter(self) -> Gio.ListStore:
        filters = Gio.ListStore.new(Gtk.FileFilter)
        images = Gtk.FileFilter()
        images.set_name(_("Icon images (.icns, .png, .svg)"))
        for suffix in ("icns", "png", "svg", "jpg", "webp", "dmg"):
            images.add_suffix(suffix)
        filters.append(images)
        return filters

    def _choose_dmg(self) -> None:
        dialog = Gtk.FileDialog(title=_("Extract from a disk image"))
        filters = Gio.ListStore.new(Gtk.FileFilter)
        images = Gtk.FileFilter()
        images.set_name(_("Disk images (.dmg)"))
        images.add_suffix("dmg")
        filters.append(images)
        dialog.set_filters(filters)
        downloads = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        if downloads:
            dialog.set_initial_folder(Gio.File.new_for_path(downloads))

        def chosen(d, result):
            try:
                file = d.open_finish(result)
            except GLib.Error:
                return
            if not file or not file.get_path():
                return
            path = file.get_path()
            self.dmg_button.set_sensitive(False)

            def listed(found):
                self.dmg_button.set_sensitive(True)
                if not found:
                    self.window.toast(_("No app icon found in {name}.").format(name=Path(path).name))
                    return
                self._dmg_popover(path, found).popup()
            query_json([sys.executable, str(ICON_MANAGER), "dmg", path], listed)
        dialog.open(self.window, None, chosen)

    def _dmg_popover(self, path: str, found: list[dict]) -> Gtk.Popover:
        """Which app of the image, onto which installed app, Light or Dark."""
        popover = Gtk.Popover()
        popover.add_css_class("icon-popover")
        popover.set_parent(self.dmg_button)
        popover.connect("closed", lambda p: GLib.idle_add(p.unparent))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for side in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{side}")(12)
        box.append(label(Path(path).name, "popover-title", xalign=0.5))
        apps = sorted(self.apps, key=lambda a: a["name"].lower())
        choice = {"bundle": found[0]["bundle"], "app": found[0]["match"], "mode": "light"}
        target = PopUp(tuple((a["id"], a["name"]) for a in apps),
                       lambda key: choice.update(app=key))

        def bundle_changed(key: str) -> None:
            choice["bundle"] = key
            match = next((f["match"] for f in found if f["bundle"] == key), "")
            if match:
                choice["app"] = match
                target.set_key(match)
        source = PopUp(tuple((f["bundle"], f["name"]) for f in found), bundle_changed)
        source.set_sensitive(len(found) > 1)
        if not choice["app"] and apps:
            choice["app"] = apps[0]["id"]
        target.set_key(choice["app"])
        appearance = PopUp((("light", _("Light")), ("dark", _("Dark"))),
                           lambda key: choice.update(mode=key))
        form = Gtk.Grid(row_spacing=8, column_spacing=10)
        for index, (title, widget) in enumerate(((_("App in the image"), source),
                                                 (_("Apply to"), target),
                                                 (_("Appearance"), appearance))):
            form.attach(label(title, "row-subtitle", xalign=1), 0, index, 1, 1)
            widget.set_hexpand(True)
            form.attach(widget, 1, index, 1, 1)
        box.append(form)
        buttons = Gtk.Box(spacing=6, halign=Gtk.Align.END)
        cancel = Gtk.Button(label=_("Cancel"))
        cancel.connect("clicked", lambda _b: popover.popdown())
        apply_button = Gtk.Button(label=_("Apply"))
        apply_button.add_css_class("suggested-action")

        def apply(_b):
            popover.popdown()
            if choice["app"]:
                self._run(["set-dmg", choice["app"], choice["mode"], path, choice["bundle"]])
        apply_button.connect("clicked", apply)
        buttons.append(cancel)
        buttons.append(apply_button)
        box.append(buttons)
        popover.set_child(box)
        return popover

    def _choose_file(self, app: dict, mode: str) -> None:
        dialog = Gtk.FileDialog(title=f"{app['name']} — {_(mode.capitalize())}")
        dialog.set_filters(self._image_filter())
        downloads = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        if downloads:
            dialog.set_initial_folder(Gio.File.new_for_path(downloads))

        def chosen(d, result):
            try:
                file = d.open_finish(result)
            except GLib.Error:
                return
            if file and file.get_path():
                self._run(["set", app["id"], mode, file.get_path()])
        dialog.open(self.window, None, chosen)

    def _choose_folder(self) -> None:
        dialog = Gtk.FileDialog(title=_("Import a folder of .icns files"))
        downloads = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        if downloads:
            dialog.set_initial_folder(Gio.File.new_for_path(downloads))

        def chosen(d, result):
            try:
                folder = d.select_folder_finish(result)
            except GLib.Error:
                return
            if folder and folder.get_path():
                self._run(["import", folder.get_path()])
        dialog.select_folder(self.window, None, chosen)


class AboutPage(Gtk.Box):
    def __init__(self, window: "SettingsWindow"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.append(header_card(big_tile("about", "grey"), "MacTahoe Liquid KDE",
                                _("A macOS Tahoe look for KDE Plasma.")))
        links = []
        for title, subtitle, url in (
            (_("Window blur"), "Acrylic Glass — MacTahoe Liquid KDE",
             "https://github.com/lestercorderomurillo/macos-tahoe-liquid-kde"),
            (_("Font rendering"), "lucidglyph — maximilionus", "https://github.com/maximilionus/lucidglyph"),
        ):
            button = Gtk.LinkButton(uri=url, label="↗")
            links.append(row(title, subtitle, button))
        self.append(group(*links))

    def refresh(self) -> None:
        pass


# ── Window ────────────────────────────────────────────────────────────

PAGES = (
    ("appearance", "Appearance", "appearance", "graphite", AppearancePage),
    ("glass", "Liquid Glass", "glass", "cyan", GlassPage),
    ("dock", "Desktop & Dock", "dock", "graphite", DockPage),
    ("icons", "Icons", "icons", "blue", IconsPage),
    ("about", "About", "about", "grey", AboutPage),
)
# The Icons page drives the Icon Manager; without it the page is left out.
if not ICON_MANAGER.is_file():
    PAGES = tuple(page for page in PAGES if page[0] != "icons")


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title=_("Theme Settings"))
        self.set_default_size(880, 680)
        self.set_size_request(720, 480)
        self.add_css_class("theme-settings")
        self.jobs = Jobs(self._jobs_changed)
        self.history: list[str] = []
        self.future: list[str] = []
        self._apply_appearance()

        # No title bar: the traffic lights sit in the sidebar, as on macOS.
        self.set_titlebar(Gtk.Box(visible=False))
        root = Gtk.Box()
        root.add_css_class("root")
        self.set_child(root)

        well = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        well.add_css_class("sidebar-well")
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.add_css_class("sidebar")
        sidebar.set_size_request(232, -1)
        sidebar.set_vexpand(True)
        well.append(sidebar)
        root.append(well)

        header = Gtk.HeaderBar(show_title_buttons=True, decoration_layout="close,minimize,maximize:")
        header.set_title_widget(Gtk.Box())
        header.add_css_class("sidebar-header")
        sidebar.append(header)

        self.search = Gtk.SearchEntry(placeholder_text=_("Search"))
        self.search.add_css_class("search")
        self.search.connect("search-changed", lambda _e: self.nav.invalidate_filter())
        sidebar.append(self.search)

        # macOS shows the account here: the user's picture and name; a
        # click opens KDE's Users settings, where both are changed.
        brand = Gtk.Button()
        brand.add_css_class("brand")
        brand.set_tooltip_text(_("Users"))
        brand.connect("clicked", lambda _b: subprocess.Popen(
            ["systemsettings", "kcm_users"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        line = Gtk.Box(spacing=10, halign=Gtk.Align.START)
        line.append(avatar_widget(40))
        names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        names.append(label(user_full_name(), "brand-title"))
        names.append(label(_("MacTahoe Liquid KDE account"), "brand-subtitle"))
        line.append(names)
        brand.set_child(line)
        sidebar.append(brand)

        self.nav = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.nav.add_css_class("nav")
        self.nav.set_filter_func(self._nav_filter)
        self.nav.connect("row-selected", self._nav_selected)
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        scroller.set_child(self.nav)
        sidebar.append(scroller)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        content.add_css_class("content")
        root.append(content)

        top = Gtk.WindowHandle()
        bar = Gtk.Box(spacing=8)
        bar.add_css_class("content-bar")
        nav_buttons = Gtk.Box()
        nav_buttons.add_css_class("nav-capsule")
        self.back = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        self.back.set_tooltip_text(_("Back"))
        self.back.connect("clicked", lambda _b: self._go_back())
        self.forward = Gtk.Button.new_from_icon_name("go-next-symbolic")
        self.forward.set_tooltip_text(_("Forward"))
        self.forward.connect("clicked", lambda _b: self._go_forward())
        nav_buttons.append(self.back)
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        nav_buttons.append(sep)
        nav_buttons.append(self.forward)
        bar.append(nav_buttons)
        self.title = label("", "content-title")
        self.title.set_hexpand(True)
        bar.append(self.title)
        self.status = label("", "status")
        bar.append(self.status)
        self.spinner = Gtk.Spinner()
        bar.append(self.spinner)
        top.set_child(bar)
        content.append(top)

        self.toast_label = label("", "toast", xalign=0.5, wrap=True)
        self.toast_revealer = Gtk.Revealer(child=self.toast_label,
                                           transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN)
        content.append(self.toast_revealer)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, vexpand=True)
        content.append(self.stack)
        self.pages: dict[str, Gtk.Widget] = {}
        self.rows: dict[str, Gtk.ListBoxRow] = {}
        for key, title, icon, colour, page_class in PAGES:
            page = page_class(self)
            page.set_margin_start(28)
            page.set_margin_end(28)
            page.set_margin_bottom(28)
            scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
            clamp = Gtk.Box(halign=Gtk.Align.FILL)
            clamp.append(page)
            page.set_hexpand(True)
            scroll.set_child(clamp)
            self.stack.add_named(scroll, key)
            self.pages[key] = page
            nav_row = Gtk.ListBoxRow()
            nav_row.key = key
            nav_row.title = _(title)
            line = Gtk.Box(spacing=9, halign=Gtk.Align.START)
            line.append(tile(icon, colour))
            line.append(label(_(title), "nav-label"))
            nav_row.set_child(line)
            self.nav.append(nav_row)
            self.rows[key] = nav_row

        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.connect("notify::gtk-theme-name", lambda *_a: self._apply_appearance())
            settings.connect("notify::gtk-application-prefer-dark-theme",
                             lambda *_a: self._apply_appearance())

    # Navigation

    def show_page(self, key: str, record: bool = True) -> None:
        if key not in self.rows:
            key = "appearance"
        current = self.stack.get_visible_child_name()
        if record and current and current != key:
            self.history.append(current)
            self.future.clear()
        self.stack.set_visible_child_name(key)
        self.title.set_label(self.rows[key].title)
        if self.nav.get_selected_row() is not self.rows[key]:
            self._navigating = True
            self.nav.select_row(self.rows[key])
            self._navigating = False
        self.back.set_sensitive(bool(self.history))
        self.forward.set_sensitive(bool(self.future))

    def _nav_selected(self, _box, nav_row) -> None:
        if nav_row is not None and not getattr(self, "_navigating", False):
            self.show_page(nav_row.key)

    def _go_back(self) -> None:
        if self.history:
            self.future.append(self.stack.get_visible_child_name())
            self.show_page(self.history.pop(), record=False)

    def _go_forward(self) -> None:
        if self.future:
            self.history.append(self.stack.get_visible_child_name())
            self.show_page(self.future.pop(), record=False)

    def _nav_filter(self, nav_row: Gtk.ListBoxRow) -> bool:
        text = self.search.get_text().strip().lower()
        return not text or text in nav_row.title.lower() or text in nav_row.key

    # Appearance of this window

    def _apply_appearance(self) -> None:
        dark = current_mode() == "dark"
        for css, on in (("dark", dark), ("light", not dark)):
            if on:
                self.add_css_class(css)
            else:
                self.remove_css_class(css)
        provider = getattr(self, "_accent_provider", None)
        display = Gdk.Display.get_default()
        if provider is None and display is not None:
            provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
            self._accent_provider = provider
        if provider is not None:
            provider.load_from_string(f"@define-color ts_accent {effective_accent()};")

    def refresh_all(self, *_args) -> None:
        self._apply_appearance()
        for page in self.pages.values():
            page.refresh()

    # Jobs

    def _jobs_changed(self, busy: bool, progress: int, _message: str) -> None:
        if busy:
            self.spinner.start()
            self.status.set_label(f"{progress} %" if progress >= 0 else _("Applying…"))
        else:
            self.spinner.stop()
            self.status.set_label("")

    def toast(self, message: str) -> None:
        self.toast_label.set_label(message)
        self.toast_revealer.set_reveal_child(True)
        GLib.timeout_add_seconds(6, lambda: self.toast_revealer.set_reveal_child(False) and False)

    def run_theme_switch(self, args: list[str], done: Callable[[], None]) -> None:
        if not THEME_SWITCH.is_file():
            self.toast(_("Theme switch not found: reinstall the theme."))
            return

        def finished(ok: bool, message: str) -> None:
            if not ok:
                self.toast(_("Could not apply the change.") + ("\n" + message if message else ""))
            done()
        self.jobs.run([str(THEME_SWITCH), *args], finished)

    def set_accent(self, colour: str | None) -> None:
        """A macOS accent colour, or Multicolour (None): the theme switch
        applies it to KDE's palette and to Kvantum, then tinted icons
        follow it."""
        self.run_theme_switch(["accent", colour or "multicolour"], lambda: None)
        if ICON_MANAGER.is_file():
            self.jobs.run([sys.executable, str(ICON_MANAGER), "refresh"],
                          lambda _ok, _m: self.refresh_all())
        else:
            self.jobs.run(["true"], lambda _ok, _m: self.refresh_all())


class ThemeSettings(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.add_main_option("page", 0, GLib.OptionFlags.NONE, GLib.OptionArg.STRING,
                             "Page to open: appearance, glass, dock, icons or about", "PAGE")

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_path(str(HERE / "theme-settings.css"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        options = command_line.get_options_dict().end().unpack()
        window = self.get_active_window()
        if window is None:
            window = SettingsWindow(self)
            window.show_page(options.get("page", "appearance"), record=False)
        elif "page" in options:
            window.show_page(options["page"])
        window.present()
        return 0


def main(argv: list[str]) -> int:
    return ThemeSettings().run(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
