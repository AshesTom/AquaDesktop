"""Capture synchronization and standalone About labels."""
import importlib.machinery
import importlib.util
import os
import shutil
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture
def capture_module(repo):
    loader = importlib.machinery.SourceFileLoader('screenshot_workflow', str(repo / 'src/scripts/screenshots'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_capture_rejects_overlapping_workflows(capture_module, tmp_path, monkeypatch):
    monkeypatch.setattr(capture_module.tempfile, 'gettempdir', lambda: str(tmp_path))
    with capture_module._capture_lock():
        with pytest.raises(RuntimeError, match='already running'):
            with capture_module._capture_lock():
                pytest.fail('A second capture acquired the lock')
    with capture_module._capture_lock():
        pass


def test_about_capture_never_runs_when_preview_is_not_ready(capture_module, monkeypatch):
    class Process:
        pass
    process = Process()
    events = []
    monkeypatch.setattr(capture_module.shutil, 'which', lambda name: name)
    monkeypatch.setattr(capture_module, '_spawn', lambda *a, **kw: process)
    def not_ready(proc):
        raise RuntimeError('not ready')
    monkeypatch.setattr(capture_module, '_wait_ready', not_ready)
    monkeypatch.setattr(capture_module, '_spectacle_activewindow', lambda path: events.append('capture'))
    monkeypatch.setattr(capture_module, '_kill_group', lambda proc: events.append('cleanup'))
    with pytest.raises(RuntimeError, match='not ready'):
        capture_module.shoot_about('light')
    assert events == ['cleanup']


@pytest.mark.parametrize("edition", ["MacTahoe", "MacGoldenGate"])
def test_about_labels_survive_empty_host_translation_context(repo, tmp_path, monkeypatch, edition):
    import glass_surfaces
    pytest.importorskip('PyQt6.QtQuick')
    from PyQt6.QtCore import QLibraryInfo
    imports = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.QmlImportsPath))
    if not (imports / 'org/kde/ki18n/qmldir').is_file():
        pytest.skip('KDE QML translations are not installed')
    probe = r'''
import sys
from PyQt6.QtCore import QObject, QUrl, pyqtSlot
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlProperty, QQmlExpression
from PyQt6.QtQuick import QQuickItem
class EmptyTranslations(QObject):
    @pyqtSlot(str, result=str)
    def i18n(self, message):
        return ''
app = QGuiApplication([])
engine = QQmlApplicationEngine()
# Initialize Plasma's SVG image set as the plasmashell host does.
host_component = QQmlComponent(engine)
host_component.setData(b'import org.kde.plasma.core as PlasmaCore; PlasmaCore.Dialog { visible: false }', QUrl())
host = host_component.create()
assert host is not None, host_component.errors()
errors = []
engine.warnings.connect(lambda warnings: errors.extend(w.toString() for w in warnings))
context = EmptyTranslations()
engine.rootContext().setContextObject(context)
engine.setInitialProperties({'visible': False, 'fetcherCommand': 'true'})
engine.load(QUrl.fromLocalFile(sys.argv[1]))
assert engine.rootObjects(), 'About window failed to load: ' + '\n'.join(errors)
texts = set()
def visit(item):
    text = item.property('text')
    if isinstance(text, str):
        texts.add(text)
    for child in item.childItems():
        visit(child)
visit(engine.rootObjects()[0].contentItem())
expected = {'Chip', 'Cores', 'Memory', 'Graphics', 'Startup disk', 'Network',
            'Serial number', 'OS', 'More Info…', 'Report a Bug…'}
assert expected <= texts, f'Missing labels: {expected - texts}'
window = engine.rootObjects()[0]
surface = window.findChild(QQuickItem, 'aboutGlassSurface')
highlight = window.findChild(QQuickItem, 'aboutGlassHighlight')
assert surface is not None and highlight is not None
for mode, foreground in [('white', 255), ('black', 0)]:
    expression = QQmlExpression(engine.contextForObject(window), window,
                               'Kirigami.Theme.backgroundColor = '+repr(mode))
    expression.evaluate()
    assert not expression.hasError(), expression.error().toString()
    app.processEvents()
    assert abs(window.property('secondaryTextColor').alphaF() - .85) < .005
    fill = surface.property('color')
    clear = sys.argv[2] == 'MacGoldenGate'
    assert fill.red() == fill.green() == fill.blue() == (255 if clear else foreground)
    assert abs(fill.alphaF() - (.01 if clear else .48 if foreground == 0 else .55)) < .005
    assert QQmlProperty(surface, 'border.width').read() == .75
    assert QQmlProperty(highlight, 'border.width').read() == .75
    outer = QQmlProperty(surface, 'border.color').read()
    inner = QQmlProperty(highlight, 'border.color').read()
    assert outer.red() == 0 and abs(outer.alphaF() - .18) < .005
    assert inner.red() == 255 and abs(inner.alphaF() - .22) < .005
    assert highlight.property('radius') == surface.property('radius') - .75
'''
    qml = repo / 'src/offline/plasmoids/org.kde.mac.tahoe.liquid.globalmenu/qml/AboutWindow.qml'
    name = 'MacTahoeLiquidKde-Dark'
    theme = tmp_path / 'data/plasma/desktoptheme' / name
    shutil.copytree(repo / 'src/offline/plasma-theme' / name, theme)
    monkeypatch.setattr(glass_surfaces, 'default_wallpaper', lambda: edition)
    glass_surfaces.apply_plasma_surface_defaults(theme)
    (tmp_path / 'plasmarc').write_text('[Theme]\nname=' + name + '\n')
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
               LANGUAGE='en', LC_ALL='C.UTF-8', HOME=str(tmp_path),
               XDG_DATA_HOME=str(tmp_path / 'data'),
               XDG_CONFIG_HOME=str(tmp_path), DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent')
    result = subprocess.run([sys.executable, '-c', probe, str(qml), edition], env=env,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
