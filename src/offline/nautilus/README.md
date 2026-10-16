# Nautilus overrides

This directory holds optional Nautilus-specific overrides picked up by
`src/scripts/steps/nautilus.py` on install.

Accepted files:

| File         | Destination                         | Purpose                               |
|--------------|-------------------------------------|---------------------------------------|
| `gtk.css`    | `~/.config/nautilus/gtk.css`        | Nautilus-only CSS overrides (opt-in)  |
| `finder-gtk4.css` | appended to every `gtk/*/gtk-4.0/*.css` sheet | The macOS Tahoe Finder look (see below) |

Nautilus sidebar bookmarks are generated **dynamically** from
`~/.config/user-dirs.dirs` at install time. The labels match the
actual folder names on disk, which follow the system language
(Desktop, Documentos, Downloads, …). This replaces the old static
`bookmarks` template approach.

The bulk of the macOS-style theming (sidebar, path bar, header buttons,
window chrome) is delivered by the **GTK theme** at `src/offline/gtk/`,
which already contains 1.5k+ Nautilus-specific selectors. This directory
is only for per-machine or per-version tweaks that don't belong in the
shared theme.

Leave the directory otherwise empty — the step handles installation,
default-filemanager wiring, a few macOS-like gsettings defaults, and the
GTK/GNOME headerbar button layout (`close,minimize,maximize:`).

## Finder look

`finder-gtk4.css` turns Nautilus 51 (libadwaita) into a macOS Tahoe Finder
window: a sidebar card floating 8 px inside the window with only the traffic
lights on top, a bold folder title instead of the path bar, 36 px toolbar
capsules and a round search button. Nautilus reads the GTK4 user stylesheet,
which `theme_switch` links to `gtk-<Mode>.css`, so the block is appended
between markers to every `gtk-4.0` sheet of both variants. Edit
`finder-gtk4.css`, then re-append it (`tests/test_nautilus_finder.py` fails
while the sheets are out of date).

The generic macOS Tahoe controls (capsule buttons, linked capsules, glass
header bar buttons, segmented controls, Finder-style sidebar selection) live
in `src/offline/gtk/tahoe-controls-gtk4.css` and are inserted the same way,
just before the Finder block (`tests/test_gtk_tahoe_controls.py`).
