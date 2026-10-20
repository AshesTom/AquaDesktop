"""Fail-closed, repeatable backport application to the pinned online source."""
import os
import shutil
import tarfile
from pathlib import Path

import pytest
from rounded_corners_compat import apply
from steps import rounded_corners as rounded


def test_unexpected_source_aborts_before_any_write(tmp_path):
    source = tmp_path / 'src'
    source.mkdir()
    shader = source / 'Shader.cpp'
    shader.write_text('// An incompatible future upstream source.\n')
    before = shader.read_bytes()
    with pytest.raises(ValueError, match='does not match'):
        apply(tmp_path)
    assert shader.read_bytes() == before


def test_build_does_not_compile_an_unpatched_source(tmp_path, monkeypatch):
    (tmp_path / 'CMakeLists.txt').touch()
    monkeypatch.setattr(rounded, 'SOURCE', tmp_path)
    failures = []
    monkeypatch.setattr(rounded, 'fail', failures.append)
    monkeypatch.setattr(rounded, 'cmake_build', lambda *a: pytest.fail('unsafe build'))
    rounded.build()
    assert len(failures) == 1
    assert 'compatibility patch failed' in failures[0]


@pytest.mark.skipif(not os.environ.get('MTTKDE_ROUNDED_CORNERS_ARCHIVE'),
                    reason='requires the verified upstream release archive')
def test_patch_applies_to_pinned_release_and_is_idempotent(tmp_path):
    archive = Path(os.environ['MTTKDE_ROUNDED_CORNERS_ARCHIVE'])
    assert rounded._archive_is_valid(archive)
    with tarfile.open(archive) as tar:
        tar.extractall(tmp_path, filter='data')
    source = tmp_path / f'KDE-Rounded-Corners-{rounded.UPSTREAM_VERSION}'
    apply(source)
    first = {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
    apply(source)
    assert all(p.read_bytes() == data for p, data in first.items())
    shader = (source / 'src/Shader.cpp').read_text()
    assert 'ShaderTrait::RoundedCorners' in shader
    assert 'QT_VERSION_CHECK(6, 7, 90)' in shader
    variables = (source / 'src/shaders/variables.glsl').read_text()
    assert 'dFdy(position0.y)' in variables
    assert 'yInverted ? uv.y : 1.0 - uv.y' in variables
    # A damaged second file must not partially patch the first.
    shutil.rmtree(source)
    with tarfile.open(archive) as tar:
        tar.extractall(tmp_path, filter='data')
    (source / 'src/shaders/shapecorners_qt6_core.frag').write_text('unexpected')
    original = (source / 'src/Shader.cpp').read_bytes()
    with pytest.raises(ValueError):
        apply(source)
    assert (source / 'src/Shader.cpp').read_bytes() == original
