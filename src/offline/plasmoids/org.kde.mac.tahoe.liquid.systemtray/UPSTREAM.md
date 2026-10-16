# Plasma system tray — AquaDesktop fork

Plasma lays its system tray out in QML compiled into the stock applet's
plugin (a local QML override is ignored), so the only way to give the menu
bar a macOS tray is to build that applet under our own ID. Everything here
is upstream's code except the changes listed below.

- Project: `https://invent.kde.org/plasma/plasma-workspace`
- Path: `applets/systemtray`
- Tag: `v6.7.5` (matches the Plasma this theme targets)
- `systemtraytypedefs.h`: from `statusnotifierwatcher/` of the same tag.
- `dbus/org.freedesktop.DBus.Properties.xml`: from `libkmpris/dbus/` of the
  same tag.
- libdbusmenuqt: the Global Menu's copy (upstream's, unchanged).
- License: GPL-2.0-or-later / LGPL-2.0-or-later, as stated in each file.

## Changes

- Applet ID `org.kde.mac.tahoe.liquid.systemtray` (metadata trimmed to one
  language; `X-Plasma-Provides` offers `org.kde.plasma.systemtray`). Not
  enabled by default: the layouts add it when it is installed, else
  Plasma's tray.
- Translations: Plasma's own `plasma_applet_org.kde.plasma.systemtray`
  domain (`TRANSLATION_DOMAIN`), so the fork stays translated.
- `CMakeLists.txt`: standalone build; `config-X11.h` generated with
  `HAVE_X11 0`; the private QML plugin (`org.kde.plasma.private.systemtray`)
  is not built, Plasma's stays in use.
- `qml/main.qml`: no expander arrow in the bar (macOS has none); the
  Control Center's "Other Status Items" bubble opens the menu through the
  applet's `activated()`.
- `qml/ExpandedRepresentation.qml`: the other items as a 280 px macOS menu
  (no "Status and Notifications" title, no pin, a "Status Items Settings…"
  row); an open applet keeps the heading with Back and its actions.
- `qml/HiddenItemsView.qml`, `qml/AbstractItem.qml`: one column of 28 px
  rows, 18 px icons, 13 px one-line labels, the accent highlight with 6 px
  corners, nothing highlighted on open.
- `qml/StatusNotifierItem.qml`, `qml/PlasmoidItem.qml`,
  `qml/BackgroundAppItem.qml`: no tooltip over a menu row.
- `qml/ExpanderArrow.qml`: white glyphs, no tooltip (kept for vertical
  panels' sake; hidden in the menu bar).

When Plasma moves on, diff the new tag's `applets/systemtray` against
`v6.7.5` and carry the changes over.
