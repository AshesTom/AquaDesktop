# Glass materials

Open **System Settings → Desktop Effects → Acrylic Glass → Configure**.
Choose a preset, adjust its controls if desired, and press **Apply**.

| Preset | Appearance |
| --- | --- |
| Tahoe | Smooth, rounded convex lensing over translucent glass with a light frosted blur. Default in Tahoe. |
| Golden Gate | Tahoe's optical values with an 85% black tint that fades out at 55% of menu height. The lower 45% and Dock stay untinted. Default in Golden Gate. |

Each preset replaces the complete material: blur, opacity, refraction, color
separation, highlights, grain, brightness, contrast, saturation and gradient.
There is one smooth blur implementation. **Fine tuning** exposes the detailed
controls without requiring a choice of blur algorithm.
Both presets use a blur strength of 5 on the 0–20 scale, grain 1,
RGB separation 12, magnification 0.1, and saturation 1.33. The refracted
edge is 18 wide, with highlight width 3.5 and strength 0.1. Brightness,
contrast and material opacity remain 1. The gradient stays specific to
each preset.
Menu brightness is 0.75 so blurred dark context menus keep their contrast over
bright wallpaper. Applet popups and the launcher use normal material brightness,
so this menu setting does not make the launcher darker.

**Glass opacity** controls how much of the blurred material covers the original
background. Keep it at 1 for full material coverage; lower it to reveal more
of the sharp background. The Dock uses a clearer centre while preserving the
refracted rim; applet popups retain full blur coverage. Text and icons retain
their own opacity. Gradient
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

Tahoe Plasma applet popups, tooltips, Qt menus and the detached search capsule
use a 55% white fill in light mode. In dark mode, general applet popups retain
an 82% black fill. The application launcher and task-manager preview tooltips
use 45%, while the detached search capsule uses 48%, so their blurred backdrops
remain visible. The launcher tile reflections are softened to prevent seams.
Tahoe's material gradient stays disabled by default; when enabled, it eases from
36% black at the top to 14% at the bottom.
Golden Gate installs a nearly clear 1% white fill in dark mode, letting its
stronger upper gradient supply the tint.
Golden Gate light native Qt menus use a 60% white translucent surface so their
dark system text remains readable above that gradient. This exception affects
only the light Golden Gate Kvantum menu assets; dark menus, Tahoe, dialogs,
tooltips and Plasma surfaces keep their existing fills.
Text follows the system window foreground throughout. The Dock
uses identical assets in both modes and retains its thin transparent fill.
Contours use a 0.75 logical-pixel dark outer line and a 0.75 logical-pixel
light inner line, following each surface's native rounded mask. The Dock uses
24% opacity on the outer line and 30% on the inner line for a visible thin edge. The gradient
only tints the blurred backdrop; it does not change text, blur coverage,
contours or the Dock. Both editions share surface geometry with edition-specific
fills; there is no separate reduced-transparency mode.
GTK client-side popups keep their own readable fills; KWin cannot blur those
surfaces in the same way as Plasma popups and Qt menus.

## Visual references

These are independently tuned KDE materials, inspired by Apple's published
screenshots and design guidance; they do not reproduce Apple's renderer.

The X11 lens models the pane as a GPU height field. A rounded-rectangle signed
distance field defines the bezel, and a smooth convex profile supplies the
surface normal. GLSL `refract` bends backdrop samples through an approximate
slab; Fresnel transmission reduces displacement at grazing angles. A broad
convex dome extends the magnification across the pane. The edge blend avoids a
crease where the nearest edge changes, while a displacement limit and
aperture-scaled strength keep the mapping fold-free on small popups. This is an
approximation based on general lens optics, not a pixel-matched copy of a
proprietary renderer.

The Tahoe Dock layout also uses Panel Colorizer for its custom panel
background. Its QML C++ module is separate from the plasmoid package and must
be rebuilt after Plasma updates. If Plasma reports that
`org.kde.plasma.panelcolorizer` cannot be imported, Panel Colorizer falls back
without the custom blur background even though KWin's Acrylic Glass effect is
active. On Debian, install the module to the user prefix and expose its QML
directory through `QML_IMPORT_PATH` before restarting Plasma.

The shader tests check the mapping Jacobian at default and maximum strength on
the reference surface and five smaller popup sizes, down to 64×48 px. The
X11 smoke test separately checks that a private KWin X11 compositor loads the
built module and keeps the active desktop plugin untouched.

To render a deterministic optical comparison, run
`MTTKDE_GLASS_SHADER_CAPTURE_DIR=/tmp/liquidglass-optics pytest -q tests/test_glass_presets.py -k native_glass_shader_pixels`.
It writes a flat control, a black-background lens reflection and
0.08/0.12/0.22/0.25 refraction PNGs over colored
bands and diagonal lines, plus 0.12 blur comparisons at the 0.35/0.45/0.55/0.8
offsets and 0.22/0.25 captures at 0.45. The probe checks that each stronger blur lowers edge energy while
retaining the smooth lens mapping. It uses software OpenGL under Xvfb; it checks
shader behavior, not KWin's live GPU/compositor integration.

On an active X11 session with NVIDIA GLX, run the same offscreen shader probe
on the discrete GPU with
`MTTKDE_RUN_GPU_SHADER_PROBE=1 MTTKDE_GLASS_SHADER_CAPTURE_DIR=/tmp/liquidglass-nvidia pytest -q tests/test_glass_presets.py -k nvidia_gpu`.
It checks the OpenGL renderer string before running and records the selected
renderer. It does not take a desktop screenshot or prove KWin compositor
integration; use the separate X11 smoke test below to verify module loading.

To smoke-test the freshly built X11 module in a private KWin/Xvfb session, run
`MTTKDE_X11_PLUGIN=/path/to/liquidglass_x11.so pytest -q tests/test_acrylic_glass_x11_smoke.py`.
The test checks that KWin's OpenGL compositor is active, the exact module is
loaded and supported, and the running desktop plugin remains untouched. It
validates integration state, not the rendered image or GPU quality.

- [macOS Tahoe 26 introduction](https://www.apple.com/newsroom/2025/06/macos-tahoe-26-makes-the-mac-more-capable-productive-and-intelligent-than-ever/): translucent Dock and controls that reflect the surrounding desktop.
- [macOS Golden Gate](https://www.apple.com/os/macos/): more uniform refraction and improved contrast.
- [Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/): blur and tint preserve legibility, with clearer and more substantial materials for different surfaces.

The Golden Gate preset adds a black upper gradient to menus in both appearance
modes. It starts at 85% opacity and reaches zero at 55% of the surface height.
The lower 45% retains untinted blurred glass. Launcher text has a soft, low-opacity
halo: white behind dark text and black behind light text. The halo is centered
and diffused rather than drawn as a hard outline. In light mode, category pills
use a translucent white backing to separate dark labels from the upper gradient.
The Dock and panels use a clearer surface without the gradient: a smooth blur, less grain and 98% centre
coverage, with a mild angled refraction and a thin bright edge. Its compact
Dual Kawase pyramid uses up to three levels, followed by a dense Gaussian
finish. The finish samples adjacent texels instead of separating image copies.
The Dock uses more blur and less refraction and color separation
to soften the backdrop without stretching it into a wide band.
The Dock's blur taps and centre coverage soften backdrop detail without
making the glass opaque. The lens bends the backdrop inward at an angle near
the rim, with its strength independent of the Dock's length.
These adjustments follow the selected material and its
controls without changing saved settings; contextual menus keep their full blur.
Applet popups retain the selected blur with full centre coverage. Golden Gate
and Tahoe share every optical value; only the gradient differs. These numerical
settings are project tuning, not values supplied by Apple. The black gradient
darkens lighter backdrops and leaves a fully black backdrop black.
