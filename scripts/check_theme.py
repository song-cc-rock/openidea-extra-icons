"""检查图标资源和代表性规则，运行方式：python scripts/check_theme.py。"""
import json
from pathlib import Path
import re
import tomllib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
manifest = tomllib.loads((ROOT / "plugin.toml").read_text(encoding="utf-8"))
theme = json.loads((ROOT / manifest["contributes"]["iconThemes"][0]["path"]).read_text(encoding="utf-8"))
definitions = theme["iconDefinitions"]
patterns = theme["patterns"]
assert manifest["id"] == "song-cc-rock.extra-icons"
assert "wasm" not in manifest and not manifest.get("capabilities")
assert theme["settings"][0]["items"][0]["default"] == 16
assert len(patterns) == 387, "移植规则数量发生变化，请核实源快照及覆盖范围"
assets = set()
for ident, variants in definitions.items():
    assert re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", ident) and not ident.endswith("_dark"), ident
    assert "light" in variants
    for relative in variants.values():
        asset = (ROOT / relative).resolve()
        assert asset.is_relative_to(ROOT) and asset.suffix == ".svg", relative
        assert asset.stat().st_size <= 65536, relative
        svg = ET.parse(asset).getroot()
        assert svg.tag == "{http://www.w3.org/2000/svg}svg", relative
        assert svg.get("width") == svg.get("height") == "16", relative
        assert not any(node.tag.rsplit("}", 1)[-1] in {"script", "style", "foreignObject"}
                       for node in svg.iter()), relative
        assets.add(relative)
for item in patterns:
    assert item["icon"] in definitions
    assert item["target"] in {"file", "folder"}
    re.compile(item["pattern"])
assert assets == {str(path.relative_to(ROOT)).replace("\\", "/") for path in (ROOT / "icons").rglob("*.svg")}


def resolve(path, target="file"):
    for item in patterns:
        if item["target"] != target:
            continue
        value = path if item.get("path") else path.rsplit("/", 1)[-1]
        if re.search(item["pattern"], value, re.I if item.get("ignoreCase") else 0):
            return item["icon"]
    return None


for path, target, expected in [
    ("app/Dockerfile", "file", "docker"),
    ("app/docker-compose.yml", "file", "dockercompose"),
    ("app/.GITIGNORE", "file", "git"),
    ("app/package.json", "file", "packagejson"),
    ("app/build.gradle.kts", "file", "gradle_kotlin"),
    ("app/.github/workflows/check.yml", "file", "githubactions"),
    ("app/.github/dependabot.yml", "file", "dependabot_github"),
    ("app/node_modules", "folder", "dir_node_modules"),
    ("app/.github", "folder", "dir_github"),
    ("app/unknown.zzz", "file", None),
    ("app/unknown", "folder", None),
    ("app/xpackage.json", "file", None),
    ("app/definitions/blueprint.json", "file", "onap_cba_blueprint"),
    ("app/definitions/nested/blueprint.json", "file", None),
    ("app/definitions/nested/data_types.json", "file", None),
    ("app/tosca-metadata/nested/tosca.meta", "file", None),
]:
    assert resolve(path, target) == expected, (path, resolve(path, target), expected)
assert "dark" in definitions["githubactions"]
print(f"通过：{len(patterns)} 条映射、{len(assets)} 个 SVG、16 个匹配/回退样例。")
