# Live desktop proof

Each green entry represents an installed graphical QEMU guest, native package
installation and compilation, light/dark rendering, Firefox interaction,
Nautilus appearance, a real reboot, and successful uninstall. The same installer
engine serves Tahoe and Golden Gate; their edition previews are captured separately
for each release. These results describe the recorded VM configuration.

[Run the checks yourself](README.md). Screenshots below are original 3840×2160
captures at 2× scale. Open an image to inspect it at full resolution.

<details>
<summary><b>Debian testing (Forky) — ✅ VM verified · v0.57.3</b></summary>

Plasma 6.7.4 · Qt 6.11.2 · Wayland · systemd · VirtIO/virgl.
Official Debian testing cloud image, with a normal KDE desktop. Debian 13's
stock Plasma 6.3 is below this project's minimum; this run does not qualify it.

| Check | Result |
| --- | --- |
| Full installation and host SDK builds | ✅ Passed |
| Light and dark desktop, loaded Acrylic Glass, Dock autohide | ✅ Passed |
| Firefox rendering, text input, button action and appearance | ✅ Passed |
| Nautilus light/dark pixels and live switching | ✅ Passed |
| Live switch preserves app, Plasma and KWin processes | ✅ Passed |
| Reboot and desktop/app checks | ✅ Passed |
| Full uninstall and removal checks | ✅ Passed |

**Light**

![Debian light](../../src/screenshots/vm/debian/light-fe7e071861fc.png)

**Dark**

![Debian dark](../../src/screenshots/vm/debian/dark-26cc7394098f.png)

**After reboot**

![Debian after reboot](../../src/screenshots/vm/debian/reboot-124d50c56945.png)

[Machine-readable results and image hashes](../../src/screenshots/vm/debian/report.json).

</details>

The remaining distributions are being qualified one at a time. Their existing
README status stays unchanged until their application checks and screenshots
have been reviewed.
