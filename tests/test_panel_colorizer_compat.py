"""Exercise the bundled override defaults and both optional plugin APIs."""
import shutil
import subprocess

import pytest


def test_override_states_start_disabled(repo):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required for the bundled JavaScript defaults')
    globals_js = repo / 'src/offline/plasmoids/luisbocanegra.panel.colorizer/contents/ui/code/globals.js'
    code = globals_js.read_text()
    code += '''
for (const state of ['normal', 'busy', 'hovered', 'needsAttention', 'expanded']) {
    if (baseOverrideConfig[state].enabled !== false) throw Error(state);
}
'''
    subprocess.run([node, '-e', code], check=True, timeout=10)


@pytest.mark.parametrize('modern', [False, True])
def test_region_removal_supports_system_plugin_versions(repo, modern):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required for QML handler JavaScript')
    text = (repo / 'src/offline/plasmoids/luisbocanegra.panel.colorizer/contents/ui/components/CustomBackground.qml').read_text()
    handler = text.split('Component.onDestruction: {', 1)[1].split('main.recolorCountChanged', 1)[0]
    api = 'removeMaskRegion: id => { if (id !== 42) throw Error(id); calls++; }' if modern else 'popLastVisibleMaskRegion: () => calls++'
    script = 'let calls = 0; const maskIndex = 42; const main = {panelColorizer: {' + api + '}};\n' + handler
    script += '\nif (calls !== 1) throw Error(calls);'
    subprocess.run([node, '-e', script], check=True, timeout=10)
