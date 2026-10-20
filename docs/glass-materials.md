# Glass materials

Open **System Settings → Desktop Effects → Acrylic Glass → Configure**.
Choose a preset, adjust its controls if desired, and press **Apply**.

| Preset | Appearance |
| --- | --- |
| Clear | Transparent glass with a light blur and a restrained edge reflection. |
| Tahoe | Soft, fully blurred glass with a narrow refracted edge. Default in Tahoe. |
| Golden Gate | Deeper blur, gentler refraction and a black gradient at the top. Default in Golden Gate. |

Each preset replaces the complete material: blur, opacity, refraction, color
separation, highlights, grain, brightness, contrast, saturation and gradient.
There is one smooth blur implementation. **Fine tuning** exposes the detailed
controls without requiring a choice of blur algorithm.

**Glass opacity** controls how much of the blurred material covers the original
background. Keep it at 1 for a fully blurred surface; lower it to reveal more
of the sharp background. Text and icons retain their own opacity. Gradient
colors and strengths are independent of this coverage, so a lighter bottom
does not lose its blur. Disable **Enable gradient** for an untinted material.

Selecting another preset replaces your material adjustments. **Restore this
preset** reapplies the selected preset, including its gradient colors.
**Cancel** discards pending changes. Saved adjustments survive reopening the
settings and reinstalling either edition. Corners and window rules are
independent and are never reset by selecting a material.

On upgrade, a complete stock configuration from the previous installer migrates
to the edition's new optics. Custom settings and the previously saved gradient
toggle are preserved. Select a preset explicitly to replace a custom legacy
configuration with the complete new material.

Plasma and Kvantum supply thin, transparent fills over the compositor's glass
in both light and dark mode. Launcher labels use the system complementary
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

The Golden Gate preset adds the requested black upper gradient while keeping
blur across the full Dock and menu surface. Its numerical settings are project
tuning, not values supplied by Apple. It compresses backdrop contrast before
the stronger upper tint, keeping the gradient visible over dark windows as well
as light ones in both appearance modes.
