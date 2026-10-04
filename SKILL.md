---
name: booksearch
description: 跨数据库文献聚合检索，一次检索词批量生成 21 个图书馆馆藏、电子书下载站、数字档案与学术引擎的检索链接。这是一个可直接执行的命令行工具，来自 Chrome 扩展 BookSearch_Extension 的复刻。TRIGGER：用户说「跨库检索」「多库检索」「一键搜这些网站」「文献聚合搜索」「批量检索文献」「booksearch」「用 BookSearch 搜」「同时搜 Google Scholar 和安娜的档案 / Z-Library / WorldCat / 国图 / CNKI」「找这本书 / 这篇论文在哪些库里有」，或给出一本书名 / 一个人名 / 一个主题词并希望一次性到多个学术库与电子书站查一查时，即使没有点名本技能也要用。DO NOT TRIGGER：只针对单一已知站点提问、用 zotero-cli 搜本地文献库、用 scansci-pdf 下载已知 DOI 的论文、或讨论文献本身而非检索。
---

# booksearch — 跨数据库文献聚合检索

`BookSearch_Extension` 是本人写的 Chrome 扩展（Manifest V3），
弹窗里放一个检索框、四个可勾选分区，点「一键搜索」就为每个勾中的站点开一个标签页。
本技能把它复刻成命令行工具，不装扩展也能用，且更适合 agent 调用。

## 适用与不适用

用本技能：给一个检索词，想知道它在**哪些库**能搜到——图书馆馆藏、电子书下载站、
数字档案、学术引擎，一次性铺开。这是「广撒网」式的检索入口，不是精确定位某个资源。

不用本技能：
- 已知 DOI / arXiv ID，要下论文 → 用 `scansci-pdf`。
- 搜本地已存的文献库、读 PDF 全文 → 用 `zotero-cli`。
- 只查 CNKI 单库 → 用 `cnki-search` 系列。
- 问某本书「讲了什么」而不是「去哪找」→ 直接答即可。

## 工具与用法

脚本位置：本技能目录下的 `scripts/booksearch.py`。

```bash
python "<skill>/scripts/booksearch.py" "<检索词>" [选项]
```

| 选项 | 作用 |
|------|------|
| `<检索词>` | 必填。书名 / 人名 / 主题词，中英文均可 |
| `--groups, -g` | 分区：`all`（默认）/ `download` / `search` / `dl-core` / `dl-other` / `paper`，可逗号组合，如 `-g paper,dl-core` |
| `--open` | 用**默认浏览器**打开全部命中链接（默认只打印清单，不打开） |
| `--open-only` | 只打开指定站点，按清单里的名称或序号，逗号分隔，如 `--open-only 谷歌学术,安娜的档案` |
| `--names-only` | 只列站点名，不展开 URL |

**默认行为是只打印链接清单、不打开浏览器。** 这是刻意的：本扩展一次会开十几个标签页，
agent 场景里通常只需要把那串链接交给用户或做后续判断。只有用户明确说「帮我打开」
或明确要跳转时才加 `--open` / `--open-only`。

## 四个分区（共 21 个站点）

- **search｜图书馆馆藏与 OPAC**（12）：WorldCat、中国国家图书馆(文津)、CALIS搜索、
  美国国会图书馆、大英图书馆、德国柏林图书馆、意大利国家OPAC(SBN)、
  法国国家图书馆(BnF)、KVK、巴伐利亚国家图书馆(BSB)、CiNii、早稻田大学
- **dl-core｜核心电子书获取**（2）：安娜的档案、Z-Library
- **dl-other｜其他文献与档案**（3）：Academia.edu、Byterfly、找书网
- **paper｜期刊与学术引擎**（4）：谷歌学术、中国知网、Semantic Scholar、CALIS CCC

`download` 是 `dl-core,dl-other` 的别名。想加/删站点或改 URL 模板，直接编辑脚本顶部的
`GROUPS` 字典；每个模板里的 `{0}` / `{1}` 是检索词占位符，**保持与扩展一致**——
`{0}` 编码成 `%20`，`{1}` 先把空格换成 `+`。加完站点记得同步更新本文件的分区清单。

## 典型工作流

1. **用户给一个词要「到处查查」**（最常见）
   ```bash
   python "<skill>/scripts/booksearch.py" "On the Origin of Species"
   ```
   把打印出的分组清单直接呈现给用户，让他挑想去哪几个。

2. **只要电子书或只要论文**
   ```bash
   python "<skill>/scripts/booksearch.py" "Leopardi Canti" -g download
   python "<skill>/scripts/booksearch.py" "Galiani 1770" -g paper
   ```

3. **用户明确要跳转**
   ```bash
   python "<skill>/scripts/booksearch.py" "社会契约论" --open-only 谷歌学术,安娜的档案
   ```

## 注意

- 脚本只用标准库（`argparse` / `urllib.parse` / `webbrowser`），无需装依赖。
- 检索词长度上限 500 字符；超长会被直接拦下并提示精简（站点本身也吃不下那么长的查询）。
- `--open` 与 `--open-only` 同时给出时，按更具体的 `--open-only` 处理，只打开指定站点。
- 退出码：正常 0；检索词为空或过长 1；`--open-only` 指定的站点一个都没匹配到 2。
- 谷歌学术、知网等站点在国内可能需代理，且对无头访问有反爬；本工具只负责**生成正确的检索
  URL 并交给你**，不抓取结果页。
- 输出里的链接是按扩展原文照搬的，个别站点（如 CALIS 外文期刊网、SBN）接口可能随对方
  改版失效——若用户反馈某站打不开，去脚本的 `GROUPS` 里更新该条模板即可。
- 想要 tag、别名或触发词调整，改本文件的 frontmatter；想要站点增减，改脚本。
