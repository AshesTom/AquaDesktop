"""Regressions for the Plasma 6.8 ownership and QML API transition."""
import re
import shutil
import subprocess

import pytest


@pytest.mark.parametrize('unique_ownership', [False, True])
def test_tray_transfers_loaded_applets_with_both_plasma_apis(offline, tmp_path, unique_ownership):
    compiler = shutil.which('g++') or shutil.which('clang++')
    if not compiler:
        pytest.skip('C++ compiler unavailable')
    source = (offline / 'plasmoids/org.kde.mac.tahoe.liquid.systemtray/systemtray.cpp').read_text()
    method = source[source.index('void SystemTray::startApplet('):]
    # Compile the actual loading branch against both API generations. Test
    # success, ownership/destruction, and the missing-plugin return path.
    branch = re.search(r'        (?:auto|Applet \*)\s*applet\s*=.*?\n\s*addApplet\([^;]+;', method, re.S)
    assert branch
    program = r'''
#include <cassert>
#include <memory>
#include <string>
#include <utility>
#include <vector>
using QString = std::string;
using QVariantList = std::vector<int>;
struct Log { template<class T> Log& operator<<(const T&) { return *this; } };
#define qCWarning(...) Log{}
struct Applet {
    inline static int alive = 0;
    bool forced = false;
    Applet() { ++alive; }
    ~Applet() { --alive; }
    void setProperty(const char*, bool value) { forced = value; }
};
namespace Plasma {
struct PluginLoader {
    inline static bool missing = false;
    static PluginLoader* self() { static PluginLoader p; return &p; }
#if UNIQUE_OWNERSHIP
    std::unique_ptr<Applet> loadApplet(const QString&, int, const QVariantList&) {
        return missing ? nullptr : std::make_unique<Applet>();
    }
#else
    Applet* loadApplet(const QString&, int, const QVariantList&) {
        return missing ? nullptr : new Applet;
    }
#endif
};
}
struct Tray {
    struct Config { int value(const QString&) { return 1; } } m_configGroupIds;
    std::unique_ptr<Applet> installed;
#if UNIQUE_OWNERSHIP
    void addApplet(std::unique_ptr<Applet>&& applet) { installed = std::move(applet); }
#else
    void addApplet(Applet* applet) { installed.reset(applet); }
#endif
    void start(const QString& pluginId) {
''' + branch.group() + r'''
    }
};
int main() {
    Tray tray;
    tray.start("test");
    assert(Applet::alive == 1 && tray.installed && tray.installed->forced);
    tray.installed.reset();
    assert(Applet::alive == 0);
    Plasma::PluginLoader::missing = true;
    tray.start("missing");
    assert(!tray.installed && Applet::alive == 0);
}
'''
    cpp = tmp_path / 'ownership.cpp'
    cpp.write_text(program)
    executable = tmp_path / 'ownership'
    result = subprocess.run([compiler, '-std=c++17', f'-DUNIQUE_OWNERSHIP={int(unique_ownership)}',
                             str(cpp), '-o', str(executable)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    subprocess.run([str(executable)], check=True, timeout=5)
