"""Render real Kvantum menu states without accessing the desktop session."""
import os
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize("mode", ["", "Dark"])
def test_menu_selection_is_neutral_translucent_and_rounded(repo, tmp_path, mode):
    pytest.importorskip("PyQt6.QtWidgets")
    config = tmp_path / "Kvantum"
    config.mkdir()
    shutil.copytree(repo / "src/offline/kvantum/mac-tahoe-liquid-kde",
                    config / "mac-tahoe-liquid-kde")
    (config / "kvantum.kvconfig").write_text(
        f"[General]\ntheme=mac-tahoe-liquid-kde{mode}\n"
    )
    env = os.environ.copy()
    env.update(HOME=str(tmp_path), XDG_CONFIG_HOME=str(tmp_path),
               QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="generic")
    env.pop("DBUS_SESSION_BUS_ADDRESS", None)
    result = subprocess.run([sys.executable, "-c", '''
import sys
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication, QMenu, QStyle, QStyleFactory, QStyleOptionMenuItem
app = QApplication([])
style = QStyleFactory.create("kvantum")
if style is None:
    sys.exit(77)
app.setStyle(style)
menu = QMenu()
for flag in (QStyle.StateFlag.State_MouseOver, QStyle.StateFlag.State_Selected,
             QStyle.StateFlag.State_Sunken):
    option = QStyleOptionMenuItem()
    option.initFrom(menu)
    option.rect = QRect(0, 0, 220, 32)
    option.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Active | flag
    image = QImage(220, 32, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    style.drawControl(QStyle.ControlElement.CE_MenuItem, option, painter, menu)
    painter.end()
    center = image.pixelColor(110, 16)
    assert center.red() == center.green() == center.blue(), center.getRgb()
    assert 15 < center.alpha() < 65, center.getRgb()
    # The original 3px menu frame has an antialiased corner pixel.
    assert image.pixelColor(0, 0).alpha() < center.alpha() / 4
    # Every slice must meet without a transparent seam.
    for x in range(220):
        assert image.pixelColor(x, 16).alpha() == center.alpha(), x
'''], env=env, capture_output=True, text=True, timeout=30)
    if result.returncode == 77:
        pytest.skip("Kvantum Qt6 style plugin required")
    assert result.returncode == 0, result.stdout + result.stderr
