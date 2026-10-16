# Plasma notifications applet — AquaDesktop fork

Plasma lays its notification popups out in QML compiled into the stock
applet's plugin, so the only way to get macOS Tahoe banners is to build that
applet under our own ID. Everything here is upstream's code except the
changes listed below.

- Project: `https://invent.kde.org/plasma/plasma-workspace`
- Path: `applets/notifications`
- Tag: `v6.7.5` (matches the Plasma this theme targets)
- `protocols/plasma-shell.xml`: `https://invent.kde.org/libraries/plasma-wayland-protocols`,
  tag `v1.23.0`, shipped so the build does not need plasma-wayland-protocols.
- License: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
  (applet), LGPL-2.1-or-later (protocol), as stated in each file.

## Changes

- Applet ID `org.kde.mac.tahoe.liquid.notifications`, QML module URI
  `plasma.applet.org.kde.mac.tahoe.liquid.notifications`; `X-Plasma-Provides`
  still offers `org.kde.plasma.notifications`. Not enabled by default: the
  layout swaps it in for the stock applet in the system tray.
- Translations: every `i18n*()` names Plasma's own
  `plasma_applet_org.kde.plasma.notifications` domain (C++ through
  `TRANSLATION_DOMAIN`), so the fork stays fully translated.
- `CMakeLists.txt`: standalone build (upstream's builds inside
  plasma-workspace).
- `global/Globals.qml`: banners 344 px wide, 10 px from the screen edge,
  15 px under the menu bar, 6 px apart.
- `NotificationPopup.qml`: one fixed banner width; no space pulled up for a
  header row.
- `delegates/DelegatePopup.qml`: rewritten as a macOS banner — 32 px app
  icon on the left, bold title over the body (13 px), no header and no
  timeout bar, a round close button in the top-left corner on hover.

When Plasma moves on, diff the new tag's `applets/notifications` against
`v6.7.5` and carry the changes over; the C++ files are upstream's apart from
the module URI.
