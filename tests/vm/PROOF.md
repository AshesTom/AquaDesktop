# Live desktop proof

Each green entry represents an installed graphical QEMU guest, native package
installation and compilation, light/dark rendering, Firefox interaction,
Nautilus appearance, a real reboot, and successful uninstall. The same installer
engine serves Tahoe and Golden Gate; their edition previews are captured separately
for each release. These results describe the recorded VM configuration.

[Run the checks yourself](README.md). Screenshots below are original 3840×2160
captures at 2× scale. Open an image to inspect it at full resolution.

<a id="debian"></a>
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

<a id="cachyos"></a>
<details>
<summary><b>CachyOS — ✅ VM verified · v0.57.4</b></summary>

Plasma 6.8.0 · Qt 6.12.0 · Wayland · systemd · VirtIO/virgl.
Installed from the official CachyOS ISO and upgraded with its native repositories.

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

![CachyOS light](../../src/screenshots/vm/cachyos/light-34d9c45c3a52.png)

**Dark**

![CachyOS dark](../../src/screenshots/vm/cachyos/dark-6dcf101c30cf.png)

**After reboot**

![CachyOS after reboot](../../src/screenshots/vm/cachyos/reboot-bc01b2bc88bb.png)

[Machine-readable results and image hashes](../../src/screenshots/vm/cachyos/report.json).

</details>

<a id="arch"></a>
<details>
<summary><b>Arch Linux — ✅ VM verified · v0.57.5</b></summary>

Plasma 6.8.0 · Qt 6.12.0 · Wayland · systemd · VirtIO/virgl.
Official Arch cloud image with KDE Plasma installed from its native repositories.

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

![Arch Linux light](../../src/screenshots/vm/arch/light-dcd9652b57c9.png)

**Dark**

![Arch Linux dark](../../src/screenshots/vm/arch/dark-237f5d92f8d7.png)

**After reboot**

![Arch Linux after reboot](../../src/screenshots/vm/arch/reboot-289081492443.png)

[Machine-readable results and image hashes](../../src/screenshots/vm/arch/report.json).

</details>

<a id="endeavouros"></a>
<details>
<summary><b>EndeavourOS — evidence pending</b></summary>

The current application checks and reviewed 4K screenshots have not been published yet.

</details>

<a id="fedora"></a>
<details>
<summary><b>Fedora — evidence pending</b></summary>

The current application checks and reviewed 4K screenshots have not been published yet.

</details>

<a id="manjaro"></a>
<details>
<summary><b>Manjaro — evidence pending</b></summary>

The current application checks and reviewed 4K screenshots have not been published yet.

</details>

<a id="artix"></a>
<details>
<summary><b>Artix Linux (OpenRC) — evidence pending</b></summary>

The current application checks and reviewed 4K screenshots have not been published yet.

</details>

<a id="garuda"></a>
<details>
<summary><b>Garuda Linux — evidence pending</b></summary>

The current application checks and reviewed 4K screenshots have not been published yet.

</details>

<a id="nobara"></a>
<details>
<summary><b>Nobara — evidence pending</b></summary>

The current application checks and reviewed 4K screenshots have not been published yet.

</details>

<a id="opensuse"></a>
<details>
<summary><b>openSUSE Tumbleweed — evidence pending</b></summary>

The current application checks and reviewed 4K screenshots have not been published yet.

</details>

<a id="neon"></a>
<details>
<summary><b>KDE neon — evidence pending</b></summary>

The current application checks and reviewed 4K screenshots have not been published yet.

</details>

The remaining distributions are being qualified one at a time. Their existing
README status stays unchanged until their application checks and screenshots
have been reviewed.
