# Window controls

The native installer offers **Flat** and **Glassy** close, minimize and maximize
buttons. Tahoe starts with Flat; Golden Gate starts with Glassy. An explicit
choice overrides the edition for this installation. A new wizard launch starts
with its source edition's defaults again.

`src/scripts/window_controls.py` constructs the glassy controls offline from
circles, paths and gradients. It does not import the fork's SVG drawings.
The flat controls retain the bundled Tahoe artwork and its notices. Both styles
share the existing frame geometry and configurable window shadows.

The visual treatment uses solid red, yellow and green for Flat, and saturated
color gradients, a broad white upper reflection and a bright lower caustic for
Glassy. Dark glassy controls retain those reflections. Inactive controls become neutral;
hover reveals the action glyph and pressing adds a darker response. Disabled
states are fainter. These are static SVG approximations, not dynamic optical
refraction or a claim of exact macOS rendering. KDE's additional window buttons
retain their existing artwork.

Both Aurorae families are installed. The choice selects the matching family
in the installer, global-theme defaults, configuration verifier and standalone
theme switcher. The switcher embeds the transaction's choice so scheduled,
login and manual light/dark transitions retain it without the source checkout.
GTK 3/4 uses matching SVGs for Glassy and the original assets for Flat; each
reinstallation starts from fresh bundled GTK sources. GTK below 4.20 requires
explicit light/dark selection for literal SVG URLs in its adaptive stylesheet.
Nix staging retains the edition default without running the graphical installer.

Standalone GTK SVGs use a 128×128 intrinsic canvas with a 16×16 view box;
the stylesheet keeps the buttons at their existing 16 logical pixels. This
prevents GTK from enlarging a low-resolution raster on high-DPI displays.
Aurorae state-sheet dimensions and frame geometry remain unchanged.

The installer previews are lossless crops of a focused Nautilus window in a
disposable VM at 3840×2160 with 4× display scale. Each crop includes the rounded
corner, all three controls, surrounding title bar and the start of the sidebar.
The separate Window shadows page compares None, Soft, Medium and Hard with
eight additional Nautilus crops: four levels in each appearance mode. Those
crops show the lower window corner against an identical neutral background,
with room for the shadow to fade. Medium remains the default.
`src/installer/assets/sources.json` records the original capture hash, crop,
VM image identity and content-addressed output filename. These are separate
from the complete fixed-profile release screenshot bundle.

Component checks cover both styles in both editions, Aurorae install/reinstall
and removal, GTK asset selection, standalone switching and wizard navigation.
Native previews establish the rendered title-bar appearance; release captures
separately verify the complete desktop and each installer page.
