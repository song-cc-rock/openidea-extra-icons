"""从固定的 Extra Icons 开源快照生成 OpenIDEA 图标主题（仅使用 Python 标准库）。"""

import json
from pathlib import Path
import re
import subprocess
import sys

SOURCE_COMMIT = "db74001c49d45832f4caefe5cf96ac29079c797f"
ROOT = Path(__file__).resolve().parents[1]
JAVA_STRING = r'"(?:\\.|[^"\\])*"'
CALL = re.compile(r'\.(\w+)\(((?:' + JAVA_STRING + r'|[^)])*)\)')
SVG_STYLE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S)
SVG_ALTERNATIVES = {
    "extra-icons/docker_.svg": "extra-icons/docker_alt.svg",
    "extra-icons/dockercompose_.svg": "extra-icons/dockercompose_alt.svg",
    "extra-icons/dockerignore.svg": "extra-icons/dockerignore_alt2.svg",
}


def strings(value, constants):
    value = value.strip()
    if value in constants:
        return constants[value]
    return [json.loads(item) for item in re.findall(JAVA_STRING, value)]


def models(source):
    text = source.read_text(encoding="utf-8")
    # 只删除字符串外的行注释，避免破坏正则和图标说明中的括号。
    text = re.sub(JAVA_STRING + r"|//[^\n]*", lambda m: "" if m[0].startswith("//") else m[0], text)
    constants = {name: strings(value, {}) for name, value in
                 re.findall(r"String\[\]\s+(\w+)\s*=\s*new String\[\]\{([^}]+)\}", text)}
    text = text.split(".flatMap(", 1)[0]
    starts = list(re.finditer(r"\b(ofFile|ofDir|ofIcon)\(((?:" + JAVA_STRING + r"|[^)])*)\)", text))
    for index, match in enumerate(starts):
        args = strings(match[2], constants)
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        calls = [(name, strings(value, constants)) for name, value in CALL.findall(text[match.end():end])]
        yield match[1], args, dict(calls)


def alternation(items):
    return "(" + "|".join(re.escape(item) for item in items) + ")"


def pattern_for(calls):
    if "regex" in calls:
        expression = calls["regex"][0]
        # 上游使用绝对路径；此处同时接受宿主传入的工作区相对路径。
        if expression.startswith(".*/"):
            return "(^|/)(" + expression[3:] + ")$", True
        if expression.startswith("^"):
            return expression + ("" if expression.endswith("$") else "$"), True
        return "^(" + expression + ")$", True
    names = calls.get("eq", calls.get("start", []))
    ends = calls.get("end", calls.get("mayEnd", []))
    if "eq" in calls:
        expression = alternation(names)
        if ends:
            expression += alternation(ends) + ("?" if "mayEnd" in calls else "")
    elif "start" in calls:
        expression = alternation(names) + ("[^.]*" if "noDot" in calls else ".*")
        # ModelCondition 对 start + mayEnd 的语义就是任意后缀。
        if "end" in calls:
            expression += alternation(ends)
    elif ends:
        expression = ".*" + alternation(ends)
    else:
        raise ValueError("缺少可转换的文件名条件")
    path = "parents" in calls
    if path:
        expression = expression.replace(".*", "[^/]*")
        return "(^|/)" + alternation(calls["parents"]) + "/" + expression + "$", True
    return "^" + expression + "$", path


def inline_styles(text):
    rules = []
    for block in SVG_STYLE.findall(text):
        for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", block):
            selector = selector.strip()
            if not re.fullmatch(r"\.[\w-]+|[a-zA-Z]+", selector):
                raise ValueError("尚未支持的 SVG 样式选择器：" + selector)
            rules.append((selector, declarations.strip().rstrip(";")))
    text = SVG_STYLE.sub("", text)

    def apply(match):
        tag, attrs = match[1], match[2]
        classes = re.search(r'\bclass="([^"]*)"', attrs)
        classes = classes[1].split() if classes else []
        declarations = [value for selector, value in rules
                        if selector == tag or selector.startswith(".") and selector[1:] in classes]
        if not declarations:
            return match[0]
        # 内联 style 高于样式表；已存在的 style 放在最后保留覆盖顺序。
        style = re.search(r'\bstyle="([^"]*)"', attrs)
        if style:
            declarations.append(style[1])
            attrs = attrs[:style.start()] + attrs[style.end():]
        return "<" + tag + ' style="' + ";".join(declarations) + '"' + attrs + ">"

    return re.sub(r"<([a-zA-Z]+)(\s[^<>]*?)?>", lambda m: apply(m) if m[2] else m[0], text)


def compatible_svg(text, resource):
    if resource == "extra-icons/cache2k.svg":
        # 上游 marker 确实用于四个箭头，按原端点、strokeWidth 和 .4 缩放展开。
        text, count = re.subn(r"<defs><marker\b.*?</marker></defs>", "", text, flags=re.S)
        assert count == 1

        def arrow(match):
            x, y, length = map(float, re.fullmatch(r"M([\d.]+) ([\d.]+)h([\d.]+)", match[1]).groups())
            line = match[0].replace(";marker-end:url(#a)", "")
            return line + (f'<path d="m5.77 0-8.65 5V-5Z" transform="translate({x + length:.6f} {y})scale(.1907592)" '
                           'style="fill:#fff;fill-rule:evenodd;stroke:#fff;stroke-width:1pt"/>')

        text, count = re.subn(r'<path d="([^"]+)"[^>]*marker-end:url\(#a\)[^>]*/>', arrow, text)
        assert count == 4
        text = '<!-- OpenIDEA 适配：将 marker 展开为等价的路径箭头。 -->\n' + text

    def attributes(match):
        tag = match[0]
        moved = []
        for attr in ("overflow", "word-spacing"):
            def move(value):
                moved.append(attr + ":" + value[1])
                return ""
            tag = re.sub(r'\s' + attr + r'="([^"]*)"', move, tag)
        if moved:
            style = re.search(r'\bstyle="([^"]*)"', tag)
            if style:
                tag = tag[:style.start()] + 'style="' + ";".join(moved) + ";" + tag[style.start() + 7:]
            else:
                tag = tag.replace(match[1], match[1] + ' style="' + ";".join(moved) + '"', 1)
        return tag

    return re.sub(r"<([a-zA-Z]+)\b[^<>]*>", attributes, text)


def main(source):
    commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if commit != SOURCE_COMMIT:
        raise ValueError("请将上游仓库检出到固定提交：" + SOURCE_COMMIT)
    java = source / "src/main/java/lermitage/intellij/extra/icons/ExtraIconProvider.java"
    resources = source / "src/main/resources"
    theme_path = ROOT / "icons/theme.json"
    previous_resources = set()
    if theme_path.is_file():
        previous_theme = json.loads(theme_path.read_text(encoding="utf-8"))
        previous_resources = {path for definition in previous_theme["iconDefinitions"].values()
                              for path in definition.values()}
    definitions, patterns, skipped = {}, [], {}
    copied = set()
    allowed = {"eq", "end", "mayEnd", "start", "noDot", "parents", "regex", "altIcons", "tags",
               "autoLoadNewUIIconVariant", "iconEnabler", "facets", "inProjectRootFolder"}
    for kind, args, calls in models(java):
        ident, icon = args[:2]
        ident = ident.lower()
        assert not set(calls) - allowed, (ident, calls)
        reason = ("JetBrains IDE 图标覆盖" if kind == "ofIcon" else
                  "依赖文件内容、项目上下文或 Git 状态" if "iconEnabler" in calls else
                  "依赖项目 facet" if "facets" in calls else
                  "要求位于工作区根目录" if "inProjectRootFolder" in calls else
                  "JetBrains 专用 workaround，正则超过宿主复杂度限制" if ident.startswith("ide_java_") else
                  "上游正则锚点互相矛盾，不能命中" if ident == "nodemon" else None)
        if reason:
            skipped[ident] = reason
            continue
        if ident == "ext_http":
            icon = calls["altIcons"][0]  # 上游默认是 PNG，改用其自带 SVG 备选图标。
        if "autoLoadNewUIIconVariant" in calls:
            icon = icon.replace("extra-icons/", "extra-icons/newui/")
        # 默认 Docker SVG 超过宿主的 64 KiB 限制，选择上游自带的精简备选图标。
        icon = SVG_ALTERNATIVES.get(icon, icon)
        variants = {"light": icon}
        dark = icon.removesuffix(".svg") + "_dark.svg"
        if (resources / dark).is_file():
            variants["dark"] = dark
        definition = {}
        for mode, path in variants.items():
            assert path.endswith(".svg"), path
            relative = "icons/" + path.removeprefix("extra-icons/")
            definition[mode] = relative
            target = ROOT / relative
            if relative not in copied:
                text = (resources / path).read_text(encoding="utf-8")
                text = inline_styles(text)
                text = compatible_svg(text, path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n", encoding="utf-8", newline="\n")
                copied.add(relative)
        definitions[ident] = definition
        pattern, path = pattern_for(calls)
        patterns.append({"pattern": pattern, "icon": ident, "ignoreCase": True,
                         "target": "folder" if kind == "ofDir" else "file", "path": path})
    theme = {"iconDefinitions": definitions, "fileNames": {}, "fileExtensions": {}, "patterns": patterns,
             "settings": [{"title": "图标", "items": [{"option": "iconSize", "label": "图标大小", "default": 16}]}]}
    theme_path.write_text(json.dumps(theme, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    # 此目录由本脚本生成；只清理旧主题中曾引用、现在已不引用的 SVG。
    for relative in previous_resources - copied:
        previous = (ROOT / relative).resolve()
        previous.relative_to((ROOT / "icons").resolve())
        previous.unlink(missing_ok=True)
    print(json.dumps({"规则": len(patterns), "文件规则": sum(p["target"] == "file" for p in patterns),
                      "文件夹规则": sum(p["target"] == "folder" for p in patterns), "SVG": len(copied),
                      "跳过": skipped}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
