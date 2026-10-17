"""Run the actual blur-region method with real Qt regions and small window doubles."""
import shlex
import shutil
import subprocess

import pytest


def test_client_regions_only_move_for_server_decorations(repo, tmp_path):
    if not shutil.which('c++') or not shutil.which('pkg-config'):
        pytest.skip('C++ and Qt6 development files required')
    flags = subprocess.run(['pkg-config', '--cflags', '--libs', 'Qt6Core', 'Qt6Gui'],
                           capture_output=True, text=True)
    if flags.returncode:
        pytest.skip('Qt6 development files required')
    text = (repo / 'src/offline/kwin-effects/acrylic-glass/src/effect.cpp').read_text()
    method = text[text.index('Region BlurEffect::blurRegion('):text.index('// Per-frame entry points')]
    source = tmp_path / 'regions.cpp'
    source.write_text('''
#include <QRegion>
#include <QRectF>
#include <optional>
#include <unordered_map>
#include <cassert>
using Region = QRegion;
using Rect = QRect;
struct EffectWindow {
    bool decorated = false;
    QRectF contentsRect() const { return QRectF(10, 20, 100, 80); }
    bool decoration() const { return decorated; }
};
struct BlurEffectData { std::optional<Region> content, frame; };
struct BlurEffect {
    std::unordered_map<EffectWindow*, BlurEffectData> m_windows;
    Region blurRegion(EffectWindow*) const;
};
''' + method + '''
int main() {
    BlurEffect effect;
    EffectWindow window;
    auto& state = effect.m_windows[&window];
    state.content = Region(QRect(10, 20, 30, 20));
    assert(effect.blurRegion(&window) == Region(QRect(10, 20, 30, 20)));
    window.decorated = true;
    assert(effect.blurRegion(&window) == Region(QRect(20, 40, 30, 20)));
    state.content = Region();
    assert(effect.blurRegion(&window) == Region(QRect(10, 20, 100, 80)));
    state.content.reset();
    state.frame = Region(QRect(0, 0, 120, 20));
    assert(effect.blurRegion(&window) == *state.frame);
    state.content = Region(QRect(0, 0, 200, 200));
    assert(effect.blurRegion(&window) == (*state.frame | Region(QRect(10, 20, 100, 80))));
}
''')
    binary = tmp_path / 'regions'
    subprocess.run(['c++', '-std=c++20', '-fPIC', str(source), '-o', str(binary),
                    *shlex.split(flags.stdout)], check=True, capture_output=True, timeout=60)
    subprocess.run([str(binary)], check=True, capture_output=True, timeout=10)
