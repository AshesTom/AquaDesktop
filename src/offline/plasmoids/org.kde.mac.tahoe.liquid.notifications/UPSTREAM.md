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
- The notification history is macOS Tahoe's Notification Center, laid out
  after NextKde's history (`shell/desktop/modules/bar/NotificationHistory*.qml`,
  GPL-3.0; design only, no code copied):
  - `main.qml`: the history is a window of its own, a frameless
    `PlasmaCore.Dialog` 12 px from the screen's right edge under the menu
    bar, like the clock panel (`preferredRepresentation: compactRepresentation`,
    an empty `fullRepresentation`). Plasma's applet popup and the tray's
    (an `AppletPopup`, which has no `NoBackground` hint) draw a frame and a
    shadow around the whole popup. Every way of opening the history (icon
    or tray menu row, global shortcut) still goes through `expanded`, which
    is reset at once; "show notifications" requests open it too. Upstream's
    collapse-on-close and `lastRead` reset run when the window hides.
    `groupLimit: 1` and `expandUnread: false`: a group is a collapsed stack
    until clicked.
  - `FullRepresentation.qml`: no panel behind the history. The Do Not
    Disturb row (Clear All and Configure next to it) is a glass card, every
    notification its own glass card (24 px corners, no drawn border), 8 px
    apart, 356 px wide; no separator lines, no scroll bar (it would sit off
    the glass, where the window takes no clicks). A collapsed group shows
    only its newest card, with up to two cards peeking 6 px under it (never
    painted above its bottom edge); a click expands it, and its close
    button closes the whole group. An expanded group has a row of glass
    pills: the app, "Show Fewer", Configure and Close Group. Cards show
    close (top-left), restore and configure (top-right) on hover. The empty
    state is one pill. Every card and pill declares `glassRadius`, and
    `glassChanged()` tells the window's GlassBlur when one moves.
  - `delegates/DelegateHistory.qml`: the banner's layout (32 px app icon,
    bold title, 13 px body up to four lines) with the age beside the title
    and the footer (actions, thumbnails, jobs, reply) under the body;
    `delegates/DelegateHistoryGrouped.qml` is the same card.
  - `components/HeadingButtons.qml`: `showButtons`, so a card shows only
    the age.
  - New: `components/GlassCard.qml` (a glass bubble with `glassRadius`),
    `components/GlassSurface.qml` and `components/shaders/glasssurface.frag{,.qsb}`
    (the menu bar popovers' Liquid Glass face, identical copies),
    `components/WindowBlur.qml` and `components/BlurSettler.qml` (GlassBlur
    from `org.kde.mac.tahoe.liquid.glass`, in a Loader: without that module
    only the blur is lost). `CMakeLists.txt` lists them and ships the
    shader as a module resource.

When Plasma moves on, diff the new tag's `applets/notifications` against
`v6.7.5` and carry the changes over; the C++ files are upstream's apart from
the module URI.
