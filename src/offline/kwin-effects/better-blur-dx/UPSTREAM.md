# Better Blur DX — AquaDesktop copy

The window and Dock glass this theme installs (feature id `acrylic_glass`,
kept for existing installs). Everything here is upstream's code except the
changes listed below.

- Project: `https://github.com/xarblu/kwin-effects-better-blur-dx`
- Commit: `811bce88af12b15be01d1b388dc5174451450362` ("Version 2.6.0")
- Files: `CMakeLists.txt`, `LICENSE`, `README.md`, `src/` (the docs, CI
  workflows, Nix files, `build.sh` and `tools/` are left out).
- License: GPL-3.0 (`LICENSE`); the effect is a fork of KWin's blur effect.
- KWin effect id `better_blur_dx`, settings in kwinrc `[Effect-better-blur-dx]`.

## Changes

- `src/blur.kcfg`, `src/blur.h`, `src/blur.cpp`: `DockBlurStrength`
  (0: the general `BlurStrength`). Docks take their own blur: Apple's Dock
  keeps the desktop's texture (a blur of about 1 px, measured on a macOS
  Tahoe capture over its bare wallpaper) while the menu bar's popovers are
  heavily blurred.
- `src/blur.kcfg`, `src/blur.h`, `src/blur.cpp`: `DockBrightness`,
  `DockContrast` and `DockSaturation` (0: the general ones). Apple's Dock
  material lowers the contrast of the desktop under it and raises its
  saturation (fitted on two macOS Tahoe captures over their bare
  wallpapers: contrast 0.68, saturation 1.35, brightness 1.04), which no
  veil drawn over the blur can do; KWin 6.7 no longer passes a window's own
  contrast parameters.
- `src/blur.kcfg`, `src/blur.h`, `src/blur.cpp`: `RefractionDocksOnly`
  keeps the refraction to docks: macOS windows do not refract, and a
  popover's blur region is one rectangle around all its bubbles.

The Dock's refraction itself is upstream's lens mode (`RefractionMode` 1).

To update: copy the new commit's same paths over this directory, then carry
the changes above over (the `AquaDesktop` comments mark them).
