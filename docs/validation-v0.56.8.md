# v0.56.8 validation

The release keeps the top menu bar and its controls backgroundless. Light popup surfaces use 55% white with dark text; dark surfaces use 55% black with light text. Both use faint black text shadows and paired dark/light contours. The Dock shares one surface between modes. The optional gradient changes tint independently and excludes the Dock.

## Visual matrix

All **192 native 3840 × 2160 captures** passed manual review in an owned, disposable KDE neon VM running Plasma 6.7.4 on Wayland, with virgl OpenGL and 200% desktop scaling. No host desktop settings or input were changed.

Each row covers eight captures: Launcher layouts 1 and 2, the real Dock, Menu, calendar, system tray, desktop context menu, and About This Computer. The detached search capsule is included with Launcher layout 2. White, black and bundled wallpaper backgrounds were tested with the gradient disabled and enabled.

| Mode | Material | Gradient | Background | Eight surfaces |
| --- | --- | --- | --- | --- |
| light | tahoe | off | white | Pass |
| light | tahoe | off | black | Pass |
| light | tahoe | off | wallpaper | Pass |
| light | tahoe | on | white | Pass |
| light | tahoe | on | black | Pass |
| light | tahoe | on | wallpaper | Pass |
| light | golden-gate | off | white | Pass |
| light | golden-gate | off | black | Pass |
| light | golden-gate | off | wallpaper | Pass |
| light | golden-gate | on | white | Pass |
| light | golden-gate | on | black | Pass |
| light | golden-gate | on | wallpaper | Pass |
| dark | tahoe | off | white | Pass |
| dark | tahoe | off | black | Pass |
| dark | tahoe | off | wallpaper | Pass |
| dark | tahoe | on | white | Pass |
| dark | tahoe | on | black | Pass |
| dark | tahoe | on | wallpaper | Pass |
| dark | golden-gate | off | white | Pass |
| dark | golden-gate | off | black | Pass |
| dark | golden-gate | off | wallpaper | Pass |
| dark | golden-gate | on | white | Pass |
| dark | golden-gate | on | black | Pass |
| dark | golden-gate | on | wallpaper | Pass |

The running Acrylic Glass source identity was verified as `a0bb571f6bfb1fc51b22bb853cf5a01eadaa05795a26d3e2d2e518c8a7c27ed8`. The actual Dock's empty surface strip had identical RGB pixels between light and dark on both black and white backgrounds. Palette-aware application icons are outside that material comparison. The capture fixture temporarily kept the Dock visible and restored autohide afterward.

Native Qt menus also passed on Wayland and Xwayland: eight material/mode/backend profiles, eleven cases each, with effect-off/on captures (176 supplementary frames). The synthetic Dock-role dialog in that probe tests role classification, not the real panel asset. GTK client-side popups retain their readable client fills; these checks do not claim compositor blur for GTK popovers.

The native Qt integer-ellipse regression failed against the pre-fix implementation. The final renderer recognizes that exact mask and places its antialiasing ramp inside the client region. Custom cutouts remain excluded; externally supplied Rounded Corners geometry retains precedence.

## Automated checks

- Full Tahoe suite: **1,489 passed**, including slow native QML and pinned Rounded Corners checks, with no skips.
- The same suite against Golden Gate's prepared shared source: **1,489 passed**, with no skips; wrapper suite: **15 passed**.
- Complete container matrix: CachyOS, Arch, Manjaro, EndeavourOS, Garuda, Fedora, Nobara, openSUSE Tumbleweed, KDE neon and Arch KDE unstable all passed package/path probes, C++ compilation and their available pytest checks. Container-only dependency skips are not counted as passes; native desktop tests were run separately.
- All three compiled components configured and built against Plasma 6.6 and 6.8 SDKs. The final About QML change was rebuilt across all ten containers and both SDKs; SDK checks are compile-only.
- Real VM uninstall → install cycles passed for both editions: Breeze `Next` after uninstall, `MacTahoe` or `MacGoldenGate` after install, and no accidental user-owned wallpaper screens. The timer regression also simulates an immediate persistent-timer callback after initial wallpaper ownership is recorded.
- GTK selected-row contrast: 33 relevant checks passed; fresh Nautilus processes were used for the light/dark documentation captures.
- Plymouth boot and shutdown render/pixel checks passed at native 4K inside the VM.

Container and SDK builds establish package/build compatibility, not live desktop qualification for every distro or Plasma version. Live desktop evidence above is specifically Plasma 6.7.4. Documentation's About preview uses canned hardware information; it does not describe the VM hardware.

## Evidence

[Download the reviewed captures and manifests](https://github.com/lestercorderomurillo/macos-tahoe-liquid-kde/releases/download/v0.56.8/visual-validation-v0.56.8.zip). The archive includes original matrix frames, SHA-256 review manifests, contact sheets, toolkit review sheets, and validation logs. README showcases are native 4K; component images are lossless crops without upscaling.
