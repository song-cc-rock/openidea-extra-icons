# Extra Icons for OpenIDEA

为 OpenIDEA 提供 Extra Icons 开源版风格的文件和文件夹图标，保留原始 SVG 图形、浅色与深色变体，默认显示尺寸为 **16 像素**。

这是独立社区移植，与 JetBrains、Extra Icons 原作者及 OpenIDEA 官方没有隶属关系。图标来自仍以 MIT 许可发布的[固定开源快照](https://github.com/sksar/intellij-extra-icons/tree/db74001c49d45832f4caefe5cf96ac29079c797f)，并非当前商业版本的完整复刻。

## 安装与使用

从本仓库 [Releases](https://github.com/song-cc-rock/openidea-extra-icons/releases) 下载 `.oiplugin`，在 OpenIDEA 的 **设置 › 插件 › 齿轮菜单 › 从插件包文件安装** 中选择该文件。

安装后在 **设置 › 插件 › Extra Icons** 中应用主题，也可在 **设置 › 外观与行为 › 外观 › 文件图标主题** 中选择。主题设置页可调整图标尺寸，默认 16 像素。

需要 OpenIDEA 插件 API 1.2 或更新版本。0.2.0 新增插件列表和详情页图标，使用独立绘制的彩色图标网格，不使用上游插件商标。插件只包含清单、映射和 SVG，**没有 WASM、激活程序或权限申请**；无需网络、文件读写或进程权限。未匹配的文件和文件夹保留 OpenIDEA 默认图标；宿主为源码根目录、排除目录和模块保留其内置图标。

## 移植范围

包含 **387 条映射**（340 条文件、47 条文件夹）和 **419 个 SVG**。迁移开源快照中可用文件名、扩展名、路径和直接父目录表达的规则，保持上游的先后顺序。规则不区分大小写；深色主题自动使用可用的 `_dark.svg`，标记为新 UI 的资源采用上游的新 UI 版本。

依赖 JetBrains 项目上下文、文件内容、Git 状态、工作区根目录判断、项目 facet 或内部 IDE 图标 ID 的规则不迁移；另外跳过两条 JetBrains 异常类兼容规则和一条原本无法命中的正则，共跳过 64 条源规则。备选图标选择器、商业版本新增资源和其他 JetBrains 专属功能不在本次移植范围内。转换时会逐项输出跳过原因。

Docker、Docker Compose、Docker Ignore 的默认资源超过宿主单个 SVG 的 64 KiB 限制，改用上游自带的备选 SVG；HTTP 文件的默认 PNG 也改用其 SVG 备选资源。具体文件与许可证见 NOTICE.md。

## 检查与打包

本地检查只使用 Python 3.11 标准库：

```sh
python scripts/check_theme.py
```

按 [OpenIDEA 官方文档](https://openidea.sh/zh/plugins/guides/icon-themes)安装 `openidea-plugin`，然后检查并打包：

```sh
openidea-plugin check .
openidea-plugin keygen /安全目录/song-cc-rock.key
openidea-plugin pack . --key /安全目录/song-cc-rock.key --publisher song-cc-rock
openidea-plugin check song-cc-rock.extra-icons-0.2.0.oiplugin
```

发布者密钥只生成一次并妥善保存，不能提交到仓库。GitHub Actions 使用 OpenIDEA v0.1.40 官方工具检查源目录及打包结果。

## 更新图标资源

转换器只接受固定提交，避免引入后续已改变许可的资源：

```sh
git clone https://github.com/sksar/intellij-extra-icons.git ../extra-icons-reference
git -C ../extra-icons-reference checkout db74001c49d45832f4caefe5cf96ac29079c797f
python scripts/import_icons.py ../extra-icons-reference
python scripts/check_theme.py
```

重新生成后还需运行官方 `openidea-plugin check .`。SVG 中的样式表转换为内联样式，以满足宿主的 SVG 净化规则。

## 许可证

移植代码采用 MIT。上游图标的 MIT 版权声明、个别 SVG 自带的 Apache 2.0 声明及许可证全文保留在 [NOTICE.md](NOTICE.md) 和对应 SVG 中；`NOTICE.md` 会随安装包分发。
