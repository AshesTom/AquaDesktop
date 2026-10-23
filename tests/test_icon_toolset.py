"""Offline generation, artwork preservation and bundle boundary regressions."""
import io
import json
import shutil
import sys
import tarfile
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/scripts"))
from icon_materials import prepare_source, render, svg_input, validate_svg
from icon_sources import digest, unpack
from icon_toolset import BASE, color, main, theme_name, verify


ARTWORK = b'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">
<rect x="4" y="4" width="56" height="56" rx="13" fill="#f8f8f8"/>
<circle cx="32" cy="32" r="12" fill="#f05020"/>
<circle cx="32" cy="32" r="5" fill="#ffffff"/>
</svg>'''


@pytest.fixture
def source(tmp_path):
    archive = tmp_path / "base.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name, data in [
            (BASE + "/index.theme", b"[Icon Theme]\nName=Base\n"),
            (BASE + "-dark/index.theme", b"[Icon Theme]\nName=Dark\n"),
            (BASE + "/COPYING", b"Original asset notice\n"),
            (BASE + "/apps/scalable/demo.svg", ARTWORK),
        ]:
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            tar.addfile(entry, io.BytesIO(data))
        alias = tarfile.TarInfo(BASE + "/apps/scalable/org.example.Demo.svg")
        alias.type = tarfile.SYMTYPE
        alias.linkname = "demo.svg"
        tar.addfile(alias)
    return archive


@pytest.fixture
def built(source, tmp_path):
    if not shutil.which("rsvg-convert"):
        pytest.skip("rsvg-convert is required for material rendering")
    output = tmp_path / "bundle"
    assert main(["build", "--source", str(source), "--output", str(output), "--sizes", "64"]) == 0
    return output


def test_build_preserves_base_and_aliases_and_verifies(built):
    manifest = verify(built)
    assert len(manifest["variants"]) == 8
    assert manifest["icons"]["demo"]["classification"] == "vector-light"
    assert (built / "themes" / BASE / "COPYING").read_bytes() == b"Original asset notice\n"
    for variant in manifest["variants"]:
        path = built / "themes" / theme_name(variant) / "apps/64/org.example.Demo.png"
        assert path.is_symlink()
        assert path.resolve().name == "demo.png"


def test_materials_preserve_color_detail_and_glass_alpha(built):
    def icon(variant):
        return Image.open(built / "themes" / theme_name(variant) / "apps/64/demo.png").convert("RGBA")
    light, dark, glass = icon("light"), icon("dark"), icon("clear-dark")
    # Neutral tile changes, saturated logo keeps its identity and white inset remains white.
    assert light.getpixel((32, 9))[0] > 220
    assert dark.getpixel((32, 9))[0] < 70
    assert light.getpixel((32, 32))[:3] == (255, 255, 255)
    for image in (light, dark):
        red = image.getpixel((32, 24))
        assert red[0] > red[1] * 2
    assert 0 < glass.getpixel((32, 9))[3] < 180
    assert glass.getpixel((32, 24))[3] > 240
    assert glass.getpixel((0, 0))[3] < 8
    assert icon("black").getpixel((32, 24))[:3] != icon("black").getpixel((32, 32))[:3]


def test_verify_rejects_changes_extra_files_and_escaping_links(built, tmp_path):
    extra = built / "unexpected"
    extra.write_text("tamper")
    with pytest.raises(ValueError, match="integrity"):
        verify(built)
    extra.unlink()
    extra.symlink_to(tmp_path)
    with pytest.raises(ValueError, match="escapes"):
        verify(built)


def test_pack_is_reproducible_and_sample_requires_opt_in(built, tmp_path):
    first, second = tmp_path / "first.tar.gz", tmp_path / "second.tar.gz"
    assert main(["pack", str(built), "--output", str(first)]) == 0
    assert main(["pack", str(built), "--output", str(second)]) == 0
    assert digest(first) == digest(second)
    path = built / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["partial"] = True
    path.write_text(json.dumps(manifest))
    assert main(["pack", str(built), "--output", str(tmp_path / "sample.tar.gz")]) == 1
    assert main(["pack", str(built), "--output", str(tmp_path / "sample.tar.gz"), "--allow-partial"]) == 0


def test_build_is_reproducible_and_never_overwrites(source, built, tmp_path):
    second = tmp_path / "second"
    assert main(["build", "--source", str(source), "--output", str(second), "--sizes", "64"]) == 0
    assert (built / "manifest.json").read_bytes() == (second / "manifest.json").read_bytes()
    before = digest(built / "manifest.json")
    assert main(["build", "--source", str(source), "--output", str(built)]) == 1
    assert digest(built / "manifest.json") == before


@pytest.mark.parametrize("name,target,kind", [
    ("../outside", None, "file"), ("/absolute", None, "file"),
    ("theme/escape", "../../outside", "link"),
    ("theme/escape", "/etc/passwd", "link"),
    ("theme/loop", "loop", "link"),
    ("theme/pipe", None, "fifo"),
])
def test_archive_boundaries(tmp_path, name, target, kind):
    archive = tmp_path / "unsafe.tar"
    with tarfile.open(archive, "w") as tar:
        member = tarfile.TarInfo(name)
        if kind == "link":
            member.type, member.linkname = tarfile.SYMTYPE, target
        elif kind == "fifo":
            member.type = tarfile.FIFOTYPE
        tar.addfile(member)
    with pytest.raises(ValueError):
        unpack(archive, tmp_path / "out")
    assert not (tmp_path.parent / "outside").exists()


def test_archive_link_parent_is_rejected_before_extraction(tmp_path):
    archive = tmp_path / "unsafe.tar"
    with tarfile.open(archive, "w") as tar:
        link = tarfile.TarInfo("theme/link")
        link.type, link.linkname = tarfile.SYMTYPE, "target"
        tar.addfile(link)
        tar.addfile(tarfile.TarInfo("theme/link/child"))
    with pytest.raises(ValueError, match="non-directory"):
        unpack(archive, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("body", [
    '<image href="file:///etc/passwd"/>', '<image href="https://example.com/icon.png"/>',
    '<rect fill="url(https://example.com/a)"/>', '<style>@import "remote.css";</style>',
    '<script>alert(1)</script>', '<foreignObject/>',
])
def test_svg_external_resources_rejected(body):
    with pytest.raises(ValueError):
        validate_svg(('<svg xmlns="http://www.w3.org/2000/svg">'+body+'</svg>').encode())


def test_override_adds_missing_glyph_and_carries_notice(source, tmp_path):
    if not shutil.which("rsvg-convert"):
        pytest.skip("rsvg-convert required")
    (tmp_path / "glyph.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><circle cx="32" cy="32" r="20" fill="red"/></svg>')
    (tmp_path / "NOTICE").write_text("Local fixture artwork")
    overrides = tmp_path / "overrides.json"
    overrides.write_text(json.dumps({"new-app": {"source": "glyph.svg", "kind": "glyph", "notice": "NOTICE"}}))
    output = tmp_path / "generated"
    assert main(["build", "--source", str(source), "--output", str(output), "--overrides", str(overrides),
                 "--icons", "new-app", "--sizes", "64"]) == 0
    manifest = verify(output)
    assert manifest["partial"]
    assert manifest["icons"]["new-app"]["classification"] == "glyph"
    assert (output / "overrides/new-app/NOTICE").read_text() == "Local fixture artwork"
    assert main(["preview", str(output), "--output", str(tmp_path / "preview.png")]) == 0
    assert (tmp_path / "preview.png").is_file()


@pytest.mark.parametrize("tint", ["#000000", "#ffffff", "#ff0000", "#00ff00", "#0000ff", "#fF7a18", "#123456"])
def test_arbitrary_rgb_tints_preserve_glyph_and_translucency(tmp_path, tint):
    if not shutil.which("rsvg-convert"):
        pytest.skip("rsvg-convert required")
    path = tmp_path / "demo.svg"
    path.write_bytes(ARTWORK)
    prepared = prepare_source(path, 64)
    for variant in ("tinted-light", "tinted-dark"):
        image = render(prepared, variant, color(tint))
        assert 0 < image.getpixel((32, 9))[3] < 180
        assert image.getpixel((32, 24))[3] > 240
        assert image.getpixel((32, 9))[:3] != image.getpixel((32, 24))[:3]


def test_unavailable_external_image_is_removed_and_reported(tmp_path):
    data = ARTWORK.replace(b"</svg>", b'<image href="http://localhost:6080/missing"/></svg>')
    cleaned, removed = svg_input(data)
    assert removed == 1
    assert b"localhost" not in cleaned
    assert b"circle" in cleaned


def test_punctuation_in_base_aliases_is_preserved(source, tmp_path):
    if not shutil.which("rsvg-convert"):
        pytest.skip("rsvg-convert required")
    overrides = tmp_path / "overrides.json"
    (tmp_path / "art.svg").write_bytes(ARTWORK)
    (tmp_path / "NOTICE").write_text("fixture")
    overrides.write_text(json.dumps({"garry's-mod": {"source": "art.svg", "notice": "NOTICE", "kind": "icon"}}))
    output = tmp_path / "bundle"
    assert main(["build", "--source", str(source), "--output", str(output), "--overrides", str(overrides),
                 "--icons", "garry's-mod", "--sizes", "64", "--variants", "dark"]) == 0
    assert "garry's-mod" in verify(output)["icons"]


def test_manifest_source_provenance_and_output_boundaries(built):
    for command, filename in (("preview", "preview.png"), ("pack", "pack.tar.gz")):
        assert main([command, str(built), "--output", str(built / filename)]) == 1
        assert not (built / filename).exists()
    path = built / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["icons"]["demo"]["source_sha256"] = "0" * 64
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="provenance"):
        verify(built)
