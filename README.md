# booksearch

跨数据库文献聚合检索：输入一个检索词，一次生成 **21 个**图书馆馆藏、电子书下载站、数字档案与
学术引擎的检索链接。

本项目包含：

- `scripts/booksearch.py` — 命令行工具（纯 Python 标准库，无第三方依赖）
- `SKILL.md` — 给 AI agent（OpenCode / Claude Code 等）使用的技能定义文件

## 来源

本工具是 Chrome 扩展 **BookSearch_Extension**（Manifest V3）命令行复刻。
原扩展在弹窗里放一个检索框和四个可勾选分区，点「一键搜索」就为每个勾中的站点开一个标签页；
本工具把同一套站点表和编码规则搬到命令行，不装扩展也能用，且更适合脚本或 agent 调用。

## 安装

无需安装，克隆即可用。要求 Python 3.9+（用到 `dict[str, str]` 内建泛型注解）。

```bash
git clone <repo-url>
cd booksearch
```

## 用法

```bash
python scripts/booksearch.py "<检索词>" [选项]
```

| 选项 | 作用 |
|------|------|
| `<检索词>` | 必填。书名 / 人名 / 主题词，中英文均可 |
| `--groups, -g` | 分区：`all`（默认）/ `download` / `search` / `dl-core` / `dl-other` / `paper`，可逗号组合 |
| `--open` | 用默认浏览器打开全部命中链接（默认只打印清单，不打开） |
| `--open-only` | 只打开指定站点，按清单里的名称或序号，逗号分隔 |
| `--names-only` | 只列站点名，不展开 URL |

### 例子

```bash
# 全部分区，只打印链接清单
python scripts/booksearch.py "On the Origin of Species"

# 只要电子书下载站
python scripts/booksearch.py "Leopardi Canti" -g download

# 只要学术引擎
python scripts/booksearch.py "Galiani 1770" -g paper

# 只打开指定站点（其余仍会打印）
python scripts/booksearch.py "社会契约论" --open-only 谷歌学术,安娜的档案

# 组合分区
python scripts/booksearch.py "休谟 人性论" -g search,paper
```

## 站点清单（共 21 个）

- **图书馆馆藏与 OPAC**（12）：WorldCat、中国国家图书馆(文津)、CALIS搜索、美国国会图书馆、
  大英图书馆、德国柏林图书馆、意大利国家OPAC(SBN)、法国国家图书馆(BnF)、KVK、
  巴伐利亚国家图书馆(BSB)、CiNii、早稻田大学
- **核心电子书获取**（2）：安娜的档案、Z-Library
- **其他文献与档案**（3）：Academia.edu、Byterfly、找书网
- **期刊与学术引擎**（4）：谷歌学术、中国知网、Semantic Scholar、CALIS CCC

## 行为说明

- **默认只打印链接，不打开浏览器。** 只有显式加 `--open` / `--open-only` 才跳转。
- `--open` 与 `--open-only` 同时给出时，按更具体的 `--open-only` 处理，只打开指定站点。
- 检索词长度上限 500 字符，超长直接拦下并提示精简。
- 退出码：正常 `0`；检索词为空或过长 `1`；`--open-only` 指定的站点一个都没匹配到 `2`。
- 编码规则与原扩展一致：模板中 `{0}` 编码为 `%20` 空格，`{1}` 编码为 `+` 空格。
- 本工具只负责**生成正确的检索 URL**，不抓取结果页。谷歌学术、知网等站点在国内可能需代理。

## 自定义站点

编辑 `scripts/booksearch.py` 顶部的 `GROUPS` 字典即可增删站点或修改 URL 模板。
模板中的 `{0}` / `{1}` 是检索词占位符，保持与原扩展一致。改完记得同步更新 `SKILL.md`
里的分区清单。

## 许可

MIT，见 `LICENSE`。
