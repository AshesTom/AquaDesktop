# Glass materials

Open **System Settings → Desktop Effects → Acrylic Glass → Configure**.
Choose a preset, adjust its controls if desired, and press **Apply**.

| Preset | Appearance |
| --- | --- |
| Clear | Transparent glass with a light blur and a restrained edge reflection. |
| Tahoe | Soft, fully blurred glass with a narrow refracted edge. Default in Tahoe. |
| Golden Gate | Tahoe's optical values with a 95% black tint that fades out over the upper half of menus. The lower half and Dock stay untinted. Default in Golden Gate. |

Each preset replaces the complete material: blur, opacity, refraction, color
separation, highlights, grain, brightness, contrast, saturation and gradient.
There is one smooth blur implementation. **Fine tuning** exposes the detailed
controls without requiring a choice of blur algorithm.

**Glass opacity** controls how much of the blurred material covers the original
background. Keep it at 1 for full material coverage; lower it to reveal more
of the sharp background. Applet popups and the Dock use clearer centres while
preserving the refracted rim. Text and icons retain their own opacity. Gradient
colors and strengths are independent of this coverage, so a lighter bottom
does not lose its blur. Disable **Enable gradient** for an untinted material.

Selecting another preset replaces your material adjustments. **Restore this
preset** reapplies the selected preset, including its gradient colors.
**Cancel** discards pending changes. Saved adjustments survive reopening the
settings. Installing or reinstalling Acrylic Glass reapplies the complete
preset of the repository being run: **Tahoe** from Tahoe, **Golden Gate** from
Golden Gate. This replaces previous material selections and optical adjustments,
including the gradient toggle and colors. Corners and window rules remain
independent and are preserved.

Plasma applet popups and the Dock supply thin, transparent fills with a subtle
contour over the compositor's glass. Context menus use an 80% light or dark
fill in Plasma and Kvantum. Launcher labels use the system complementary
foreground with a soft shadow, preserving the glass behind them. Both editions
ship the same surfaces; there is no separate reduced-transparency mode.
GTK client-side popups keep their own readable fills; KWin cannot blur those
surfaces in the same way as Plasma popups and Qt menus.

## Visual references

These are independently tuned KDE materials, inspired by Apple's published
screenshots and design guidance; they do not reproduce Apple's renderer.

- [macOS Tahoe 26 introduction](https://www.apple.com/newsroom/2025/06/macos-tahoe-26-makes-the-mac-more-capable-productive-and-intelligent-than-ever/): translucent Dock and controls that reflect the surrounding desktop.
- [macOS Golden Gate](https://www.apple.com/os/macos/): more uniform refraction and improved contrast.
- [Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/): blur and tint preserve legibility, with clearer and more substantial materials for different surfaces.

The Golden Gate preset adds a black upper gradient to menus in both appearance
modes. It starts at 95% opacity and reaches zero at 50% of the surface height.
The lower half retains untinted blurred glass. The Dock and panels use a clearer
surface without the gradient: a shallow blur, less grain and a transparent
centre, with stronger refraction across a wider bevel. The bevel bends the
background perpendicular to each edge instead of stretching it toward the
centre of a long Dock. These adjustments follow the selected material and its
controls without changing saved settings; contextual menus keep their full blur.
Applet popups retain the selected blur with lower centre coverage. Golden Gate
and Tahoe share every optical value; only the gradient differs. These numerical
settings are project tuning, not values supplied by Apple. The black gradient
darkens lighter backdrops and leaves a fully black backdrop black.
