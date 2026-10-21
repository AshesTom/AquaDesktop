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


# AquaDesktop keeps its own About window: upstream's glass-surface label
# check does not apply.

def test_capture_refuses_host_before_switch(capture_module, monkeypatch):
    import screenshot_checks as checks
    monkeypatch.setattr(checks.subprocess, 'run', lambda *a, **kw:
                        subprocess.CompletedProcess(a, 1, 'none\n', ''))
    monkeypatch.setattr(capture_module, '_switch_theme', lambda _: pytest.fail('Host theme changed'))
    with pytest.raises(RuntimeError, match='disposable VM'):
        capture_module.main(['about'])
