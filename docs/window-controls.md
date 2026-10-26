# Golden Gate window controls

The Golden Gate edition uses its own Aurorae packages and matching GTK 3/4
titlebutton artwork. Tahoe keeps its existing buttons. Both editions share the
existing frame geometry, title-bar height, and installer shadow choices.

## Reference comparison, 26 October 2026

Apple's [Golden Gate overview](https://www.apple.com/os/macos/) describes the
refined Liquid Glass design. Its Mail close-up illustrates toolbar materials,
but does not show traffic-light controls, so it is not a button specification.

The direct visual references are Stephen Hackett's first-hand
[Golden Gate beta 6 screenshots](https://512pixels.net/2026/08/golden-gate-beta-6-stoplights-liquid-glass/):
[light](https://media.512pixels.net/wp-content/uploads/2026/08/goldengate-window-controls.jpg)
and [dark](https://media.512pixels.net/wp-content/uploads/2026/08/goldengate-window-controls-dark-mode.jpg).
These show colored gradients on active controls, restrained side edges, bright
top/bottom reflections in dark mode, neutral reflective inactive controls,
and glyphs on hover. The displayed circles are approximately 14 logical pixels
across, with roughly 23 logical pixels between centers at the apparent 2× scale.
Light-mode centerline samples informed the three-stop color gradients. JPEG
compression and backdrop-dependent rendering prevent treating these values as
an Apple specification. The references establish the beta 6 appearance, not
pixel-perfect fidelity to every later release.

The compared contributor revision is
[jadetheda 5513f48b7770c97088fefd95219a6f5be57898ec](https://github.com/jadetheda/macos-golden-gate-liquid-kde/commit/5513f48b7770c97088fefd95219a6f5be57898ec).
Its frame SVGs closely match the existing Tahoe geometry, with changed shadow
and outline opacity. Its buttons introduce color gradients and stronger edge
reflections. It supplies no verifiable external source for that artwork;
the metadata's “1:1” claim is not evidence of exact matching.

| Property | Existing Tahoe | Contributor fork | This update |
| --- | --- | --- | --- |
| Active buttons | Flat color | Gradients and reflective rims | Original SVG gradients informed by the screenshots |
| Inactive buttons | Flat gray | Translucent gray and highlights | Neutral gradients and top/bottom reflections |
| States | Existing Aurorae states | Five state groups | Eight Aurorae states, including inactive hover/press and disabled |
| GTK title bars | Existing PNG assets | Unchanged | Same scalable SVG construction as Aurorae, including restore |
| Window frames | Existing geometry and configurable shadows | Opacity and title-bar changes | Existing geometry and shadow controls preserved |
| Installation | Tahoe theme names | Bootstrap source-text replacement | Shared package assembly, edition-aware selection and cleanup |

`src/scripts/window_controls.py` constructs new artwork from basic SVG shapes;
it does not embed or redistribute the reference screenshots or copy the fork's
SVG files. Source images are research references only. Existing frame and
metadata notices remain intact. There is no new downloaded dependency.

## Integration and limits

Both Aurorae families are assembled offline from the same frame templates.
Golden Gate uses 7-pixel button spacing, while retaining the existing title-bar
height and centered-title margins. The switcher derives the decoration name
from the same edition default already baked into its standalone executable;
login, scheduled and manual switches therefore agree. Global-theme activation
stages the same edition. The verifier checks the
selected edition. Uninstall removes both managed families.

GTK staging substitutes only the bundled titlebutton image references with
resolution-independent SVG files. Existing selectors, hit targets,
layout and the rest of the theme remain unchanged. Nix uses the same assembly
functions. Reinstalling Tahoe restores its original GTK sources.

These are static SVG approximations. They do not reproduce Apple's dynamic
refraction or the physical motion of its hovered glass controls. Aurorae owns
its hover behavior, which need not match AppKit's group-hover behavior. KDE's
extra keep-above, keep-below and all-desktops buttons use the same material but
are project extensions, not macOS controls.

Regression coverage is in `tests/test_window_controls.py`, the shadow,
theme-switch, verifier and Nix tests. Rendered contact sheets are asset checks,
not substitutes for native desktop or release screenshots.

Older GTK 4 versions use a palette-adaptive stylesheet without CSS media queries.
The switcher selects the matching literal SVG URLs when regenerating that sheet.
Applications that cache user stylesheets may need to be reopened after an
edition update or a change to those URLs; the installer never kills them.
