"""Pin integrity and build-time asset assembly for the declarative path (#86)."""
import json
import re
import subprocess
import sys


def test_nix_inputs_are_locked_and_share_nixpkgs(repo):
    nodes = json.loads((repo / "flake.lock").read_text())["nodes"]
    for name in ("nixpkgs", "home-manager"):
        assert re.fullmatch(r"[0-9a-f]{40}", nodes[name]["locked"]["rev"])
        assert nodes[name]["locked"]["narHash"].startswith("sha256-")
    assert nodes["home-manager"]["inputs"]["nixpkgs"] == ["nixpkgs"]
    assert "plasma-manager" not in nodes  # supplied only by consumers who want panels


def test_nix_asset_assembly_matches_runtime_theme_names(repo, tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(repo / "src/scripts"))
    subprocess.run([sys.executable, str(repo / "nix/install-assets.py"),
                    str(repo / "src/offline"), str(tmp_path)], check=True)
    share = tmp_path / "share"
    for mode in ("Light", "Dark"):
        name = f"MacTahoeLiquidKde-{mode}"
        assert (share / "aurorae/themes" / name / f"{name}rc").is_file()
        assert (share / "plasma/look-and-feel" /
                f"org.kde.mac-tahoe-liquid-kde.{mode.lower()}" / "metadata.json").is_file()
        assert (share / "themes" / (name + "-ReducedTransparency") / "gtk-3.0/gtk.css").is_file()
    assert not (share / "fonts").exists()
    assert not (share / "wallpapers").exists()
    assert not (share / "sounds").exists()
