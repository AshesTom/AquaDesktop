"""Shared glass surfaces preserve masks, shadows and opaque accessibility fills."""
import gzip
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from theme_variants import generate

ROOT = Path(__file__).resolve().parents[1] / "src/offline/plasma-theme"


def _xml(path):
    return ET.fromstring(gzip.decompress(path.read_bytes()))


@pytest.mark.parametrize("mode", ["Light", "Dark"])
def test_glass_surfaces_generate_accessible_variants_without_changing_geometry(tmp_path, mode):
    source = ROOT / f"MacTahoeLiquidKde-{mode}"
    paths = [source / p for p in ("dialogs/background.svgz", "dialogs/launcher-search.svgz",
                                 "widgets/panel-background.svgz")]
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    reduced = tmp_path / "reduced"
    generate(source, reduced, "plasma")
    for path in paths:
        regular = _xml(path)
        accessible = _xml(reduced / path.relative_to(source))
        ids = {n.get("id"): n for n in accessible.iter() if n.get("id")}
        for node in regular.iter():
            identifier = node.get("id", "")
            if identifier.startswith(("mask-", "shadow-", "hint-")):
                assert ET.tostring(ids[identifier]) == ET.tostring(node)
        center = next(n for n in regular.iter() if n.get("id") == "center")
        assert ET.tostring(center) != ET.tostring(ids["center"])
        assert b"0.96" in ET.tostring(ids["center"])
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]


@pytest.mark.parametrize("mode", ["Light", "Dark"])
def test_shared_dialog_fills_leave_room_for_glass_and_keep_top_bar_clear(mode):
    source = ROOT / f"MacTahoeLiquidKde-{mode}"
    for file in ("dialogs/background.svgz", "dialogs/launcher-search.svgz"):
        root = _xml(source / file)
        center = next(n for n in root.iter() if n.get("id") == "center")
        for node in center.iter():
            if node.tag.endswith("}rect"):
                style = dict(part.split(":", 1) for part in node.get("style", "").split(";") if ":" in part)
                assert 0 < float(style.get("opacity", node.get("opacity", "1"))) <= 0.3
        # The preset owns the colored gradient. The capsule may retain only
        # a faint edge reflection; a baked dark cap would also affect Clear.
        for node in root.iter():
            if node.get("id") in ("top-surface", "bottom-surface"):
                assert all(float(stop.get("stop-opacity", "1")) <= 0.08 for stop in node)
    panel = _xml(source / "widgets/panel-background.svgz")
    top = next(n for n in panel.iter() if n.get("id") == "north-center")
    assert "fill:none" in top.get("style", "")
