"""Golden Gate surface staging must preserve shapes and accessibility variants."""
import gzip
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

from steps.plasma_theme import _prepare_golden_dark
from theme_variants import generate

SOURCE = Path(__file__).resolve().parents[1] / 'src/offline/plasma-theme/MacTahoeLiquidKde-Dark'


def _xml(path):
    return ET.fromstring(gzip.decompress(path.read_bytes()))


def test_golden_material_preserves_sources_masks_and_shadows(tmp_path):
    original = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE / 'dialogs').glob('*.svgz')}
    staged = tmp_path / 'glass'
    _prepare_golden_dark(SOURCE, staged)
    for name in ('background.svgz', 'launcher-search.svgz'):
        before = _xml(SOURCE / 'dialogs' / name)
        after = _xml(staged / 'dialogs' / name)
        ids = {node.get('id'): node for node in after.iter() if node.get('id')}
        for node in before.iter():
            identifier = node.get('id', '')
            if identifier.startswith(('mask-', 'shadow-', 'hint-')):
                assert ET.tostring(ids[identifier]) == ET.tostring(node)
        assert gzip.decompress((staged / 'dialogs' / name).read_bytes()) != gzip.decompress((SOURCE / 'dialogs' / name).read_bytes())
    assert original == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE / 'dialogs').glob('*.svgz')}


def test_golden_material_still_generates_reduced_transparency(tmp_path):
    staged, reduced = tmp_path / 'glass', tmp_path / 'reduced'
    _prepare_golden_dark(SOURCE, staged)
    generate(staged, reduced, 'plasma')
    for name in ('background.svgz', 'launcher-search.svgz'):
        regular = _xml(staged / 'dialogs' / name)
        accessible = _xml(reduced / 'dialogs' / name)
        def center(root):
            return next(node for node in root.iter() if node.get('id') == 'center')
        assert ET.tostring(center(regular)) != ET.tostring(center(accessible))
        regular_masks = [ET.tostring(n) for n in regular.iter() if n.get('id', '').startswith('mask-')]
        reduced_masks = [ET.tostring(n) for n in accessible.iter() if n.get('id', '').startswith('mask-')]
        assert regular_masks == reduced_masks
