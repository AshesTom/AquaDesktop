# Installer testing

Native installer screens for Tahoe 0.61.4, captured in a disposable KDE Plasma VM.
Dark appearance was selected for this installation test.
The gallery is captured from the release source and reviewed before publication.
Release checks cover both editions, theme switching, installation, reboot and removal.

For test commands and the capture workflow, see [CONTRIBUTING.md](CONTRIBUTING.md).

## v0.61.4 focused validation

Installer changes were checked from Tahoe commits `217277a`, `78a5907` and
`3fdcba1` on the maintainer's Linux development environment, using offscreen
Qt for wizard navigation. The final shadow renderer passed all nine component
regressions, including rendered active/inactive SVG pixels, both appearance
modes, reinstall regeneration and uninstall cleanup.

```sh
QT_QPA_PLATFORM=offscreen python -m pytest -q \
  tests/test_window_shadows.py tests/test_installer_wizard.py tests/test_cli.py \
  tests/test_installer_ui.py tests/test_step_guards.py tests/test_release_screenshots.py
QT_QPA_PLATFORM=offscreen python -m pytest -q \
  tests/test_gtk_upgrade.py tests/test_gtk_window_geometry.py \
  tests/test_theme_switch.py tests/test_apply_safety.py
```

The first group passed 187 checks before the two rendered-shadow regressions
were added; the final shadow component then passed nine checks. The second
group passed 125 checks. Golden Gate's prepared source passed the affected
wizard/GTK checks (38), followed by all nine final shadow regressions. Its
wrapper suite passed 40 checks.

A disposable KDE neon VM (Plasma 6.8.1, Qt 6.11.1, Wayland) verified that a full
reinstall preserves customized panel IDs, widgets, Dock height and hiding
behavior, while an explicit reset restores the default layout. Skipping
Nautilus preserved the existing Dolphin MIME associations. Light/dark/light
configuration transitions passed. Shadow visual checks use the same pinned
VM image as the release capture profile; the release gallery has its own
complete capture and review gate.

These checks do not reproduce the reporter's Firefox freezes or establish the
cause of their mixed application colors. The full distro matrix and exact
release commit checks remain the responsibility of the required push CI on
both `main` and `dev`.

## Installation steps

Scroll horizontally through the installation steps.

<table>
<tr>
  <td align="center"><img src="src/screenshots/installer-welcome_dark_v4-32223c17c4ea.png" alt="Welcome" width="500"><br>Welcome</td>
  <td align="center"><img src="src/screenshots/installer-appearance_dark_v4-a6f5633f614d.png" alt="Appearance" width="500"><br>Appearance</td>
  <td align="center"><img src="src/screenshots/installer-icons_dark_v4-fb1bad1909be.png" alt="Icons and color" width="500"><br>Icons and color</td>
  <td align="center"><img src="src/screenshots/installer-wallpaper_dark_v4-7ee3602eddd1.png" alt="Wallpaper" width="500"><br>Wallpaper</td>
  <td align="center"><img src="src/screenshots/installer-launcher_dark_v4-28b8fff306a0.png" alt="Launcher" width="500"><br>Launcher</td>
  <td align="center"><img src="src/screenshots/installer-layout_dark_v4-d821969d38ed.png" alt="Top bar and Dock" width="500"><br>Top bar and Dock</td>
  <td align="center"><img src="src/screenshots/installer-effects_dark_v4-2d52a7df710d.png" alt="Effects" width="500"><br>Effects</td>
  <td align="center"><img src="src/screenshots/installer-fonts_dark_v4-49334d088f34.png" alt="Fonts" width="500"><br>Fonts</td>
  <td align="center"><img src="src/screenshots/installer-firefox_dark_v4-56f96e001034.png" alt="Firefox" width="500"><br>Firefox</td>
  <td align="center"><img src="src/screenshots/installer-files_dark_v4-350e0f628f26.png" alt="File manager" width="500"><br>File manager</td>
  <td align="center"><img src="src/screenshots/installer-boot_dark_v4-e3d53438aa3c.png" alt="Boot animation" width="500"><br>Boot animation</td>
  <td align="center"><img src="src/screenshots/installer-oled_dark_v4-7114243e7a32.png" alt="OLED protection" width="500"><br>OLED protection</td>
  <td align="center"><img src="src/screenshots/installer-summary_dark_v4-f841f26bacc1.png" alt="Summary" width="500"><br>Summary</td>
</tr>
</table>
