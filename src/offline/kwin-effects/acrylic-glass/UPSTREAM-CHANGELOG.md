# Changelog

Changes in this fork compared to [4v3ngR/kwin-effects-glass](https://github.com/4v3ngR/kwin-effects-glass).
Tested on KWin 6.8.0, Plasma Wayland, CachyOS.

## [Unreleased] - 2026-10-18

### Fixed

- **Glass artifacts on windows animated by other KWin effects** (for example Bouncing Popups).
  Context menus and popups lost the top of their glass while they bounced or slid, and a stray
  bright line was left on top of them afterwards.
  - Cause: KWin repaints an animated window only inside its normal frame area. While a window
    overshoots (scale above 1.0, or a translation past its resting position) the glass reaches
    beyond that area, so its top was cut off. Frames that happened to have a larger repaint area
    drew the glass in full, and the next frames never erased that strip, which left the line behind.
  - Fix: while a window is scaled or moved by another effect, the glass requests a repaint of the
    transformed area plus a margin (at least 16 px, or 12% of the window size), so the following
    frame is always covered and old glass pixels are erased.
- Glass shape on scaled windows is now mapped around the window origin, the same way KWin scales
  the window, with outward rounding so no part of the shape can collapse or leave gaps.
- Rim corner radius now shrinks together with the window while it is scaled by another effect.

### Added

- New setting **Improve glass on scaled/animated windows** (General tab, on by default). It
  switches all three fixes above. Turn it off to get the original behavior.

### Previously added in this fork

<!-- Adjust this list to match what the fork actually contains. -->

- Cursor rim light (brightness, thickness, radius)
- Squircle corners
- Smooth edge antialiasing (widget style)
- Widget border light
- Separate corner radius for notifications
