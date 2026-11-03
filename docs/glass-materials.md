# Glass materials

Acrylic Glass is [kwin-effects-glass](https://github.com/AndyKaslana/kwin-effects-glass)
(AndyKaslana's fork of 4v3ngR's Glass, itself derived from KWin's blur),
bundled and built at install time. Open **System Settings → Desktop Effects →
Acrylic Glass → Configure** to tune it, and press **Apply**.

| Preset | Appearance |
| --- | --- |
| Tahoe | Blurred glass with a narrow refracted edge, a thin specular rim, a soft light that follows the pointer and squircle corners. Default in Tahoe. |
| Golden Gate | Tahoe's optical values under a 15% black tint. Default in Golden Gate. |

Both presets use blur strength 5 on the 1–15 scale (windows, Dock and
decorations), grain 1 and saturation 1.33. The liquid glass edge uses
physically based (Snell's law) refraction: strength 6 is an index of
refraction of 1.3 over a 20-pixel edge, with RGB fringing 2 under a light
border. Body refraction carries the lens 40 pixels inward at strength 40.
Refraction applies to menus, popups and the Dock, not to application windows.
Brightness and contrast remain 1.

Installing or reinstalling Acrylic Glass writes the complete preset of the
repository being run: **Tahoe** from Tahoe, **Golden Gate** from Golden Gate.
Corner radii, window rules and settings outside the preset are preserved.
**Defaults** in the settings page restores the Tahoe material. Settings saved by
the previous Acrylic Glass engine are cleared on install; its window and popup
corner radii carry over to the new radius settings.

Theme Settings' **Frosted** style is the same material more deeply blurred
(strength 11), without refraction, colour fringing or rim lights, dimmed in Dark
and lifted in Light.

Corners follow KDE Rounded Corners when it is installed: the glass uses each
window's live corner radius. Otherwise windows use 22 px, menus 12 px and the
Dock 20 px.

Tahoe Plasma applet popups, tooltips, Qt menus and the detached search capsule
use a 55% white fill in light mode and a slightly clearer 48% black fill in dark
mode. Golden Gate installs a nearly clear 1% white fill in both modes, letting
the tint supply the darkness. Golden Gate light native Qt menus use a 60% white
translucent surface so their dark system text remains readable. Text follows
the system window foreground throughout. The Dock uses identical assets in both
modes and retains its thin transparent fill. Contours use a 0.75 logical-pixel
dark outer line and a 0.75 logical-pixel light inner line, following each
surface's native rounded mask.

Frameless applet popups and tooltips are glassed only where they ask for blur,
so the transparent room around them (the Downloads fan) stays clear. GTK
client-side popups keep their own readable fills; KWin cannot blur those
surfaces in the same way as Plasma popups and Qt menus.

Acrylic Glass builds separate Wayland and X11 modules against each backend's
KWin SDK. The installer requests the SDK for the current desktop session and
also builds the other backend when its SDK is already installed.

## Visual references

These are independently tuned KDE materials, inspired by Apple's published
screenshots and design guidance; they do not reproduce Apple's renderer.

- [macOS Tahoe 26 introduction](https://www.apple.com/newsroom/2025/06/macos-tahoe-26-makes-the-mac-more-capable-productive-and-intelligent-than-ever/): translucent Dock and controls that reflect the surrounding desktop.
- [Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/): blur and tint preserve legibility, with clearer and more substantial materials for different surfaces.
