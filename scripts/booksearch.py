#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""booksearch — 跨数据库文献聚合检索

复刻自 Chrome 扩展 BookSearch_Extension（manifest v3）的 popup.js。
输入一个检索词，按选定的分区把各站点的检索 URL 全部生成出来；
默认只打印链接清单，加 --open 才用默认浏览器批量打开。

编码规则与扩展保持一致：
  {0} -> application/x-www-form-urlencoded（空格变 %20）
  {1} -> 表单编码后再把 %20 换成 +（空格变 +）
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from urllib.parse import quote

# 检索词长度上限：超过后 URL 会被站点拒绝，也会把终端刷爆
MAX_QUERY_LEN = 500

# ---------------------------------------------------------------------------
# 站点表：逐条照搬 popup.js，模板里的 {0}/{1} 占位符原样保留
# ---------------------------------------------------------------------------

GROUPS: dict[str, dict[str, str]] = {
    # 1. 图书馆与 OPAC 检索区
    "search": {
        "WorldCat": "https://www.worldcat.org/search?q={1}",
        "中国国家图书馆 (文津)": (
            "http://find.nlc.cn/search/doSearch?query={0}&secQuery=&actualQuery={0}"
            "&searchType=2&docType=%E5%85%A8%E9%83%A8&isGroup=isGroup"
            "&targetFieldLog=%E5%85%A8%E9%83%A8%E5%AD%97%E6%AE%B5&orderBy=RELATIVE&fromHome=true"
        ),
        "CALIS搜索": (
            "https://opac2.calis.edu.cn/search?searchType=bibliography"
            "&searchField=cql.anywhere&searchWord={1}"
        ),
        "美国国会图书馆": "https://search.catalog.loc.gov/search?option=keyword&query={1}",
        "大英图书馆": (
            "https://catalogue.bl.uk/nde/search?query={0}&tab=Everything"
            "&search_scope=MyInst_and_CI&vid=44BL_MAIN:BLL01_NDE&lang=en"
        ),
        "德国柏林图书馆": "https://stabikat.de/Search/Results?lookfor={1}&type=AllFields",
        "意大利国家OPAC (SBN)": (
            "https://opac.sbn.it/en/risultati-ricerca-avanzata"
            "?fieldstruct%5B1%5D=ricerca.parole_tutte%3A4%3D6"
            "&struct%3A1001=ricerca.parole_almeno_una%3A%40or%40"
            "&fieldvalue%5B1%5D={1}&fieldaccess%5B1%5D=Keywords%3A1016"
        ),
        "法国国家图书馆 (BnF)": "https://catalogue.bnf.fr/search.do?motRecherche={1}",
        "KVK (德国卡尔斯鲁厄虚拟目录)": (
            "https://kvk.bibliothek.kit.edu/?kataloge=K10PLUS&kataloge=BVB"
            "&kataloge=NRW&kataloge=HEBIS&kataloge=KOBV_SOLR&kataloge=DDB"
            "&kataloge=STABI_BERLIN&digitalOnly=0&embedFulltitle=0&newTab=0&TI={0}"
        ),
        "巴伐利亚国家图书馆 (BSB)": (
            "https://opacplus.bsb-muenchen.de/discovery/search"
            "?vid=49BVB_BSB:VU1&lang=en&tab=Everything&search_scope=MyInst_and_CI"
            "&offset=0&query=any,contains,{0}"
        ),
        "CiNii搜索": "https://cir.nii.ac.jp/all?q={0}",
        "早稻田大学": (
            "https://waseda.primo.exlibrisgroup.com/discovery/search"
            "?query=any,contains,{0}&vid=81SOKEI_WUNI:WINE&lang=ja"
        ),
    },
    # 2. 核心下载区（电子书获取）
    "dl-core": {
        "安娜的档案": "https://annas-archive.gd/search?q={0}",
        "Z-Library": "https://z-library.sk/s/{0}",
    },
    # 3. 其他文献获取与数字档案区
    "dl-other": {
        "Academia.edu": "https://www.academia.edu/search?q={0}",
        "Byterfly": (
            "https://www.byterfly.eu/islandora/search/{0}"
            "?type=dismax&mm=5&islandora_solr_search_navigation=0"
        ),
        "找书网": "https://findbooks.eu.org/index.php?ebook-search-keyword-{0}",
    },
    # 4. 论文检索区
    "paper": {
        "谷歌学术": "https://scholar.google.com/scholar?q={1}",
        "中国知网": "https://kns.cnki.net/kns8s/defaultresult/index?kw={0}",
        "Semantic Scholar": "https://www.semanticscholar.org/search?q={1}",
        "CALIS CCC": (
            "https://ccc2.calis.edu.cn/ccc/searchList"
            "?searchType=simple&queryValue={0}&queryKey=&nav=common"
        ),
    },
}

# 分区中文名，用于 CLI 显示
GROUP_LABELS = {
    "search": "图书馆馆藏与 OPAC",
    "dl-core": "核心电子书获取",
    "dl-other": "其他文献与档案",
    "paper": "期刊与学术引擎",
}


def build_url(template: str, query: str) -> str:
    """按扩展的规则把占位符替换成编码后的检索词。"""
    q_quote = quote(query, safe="")          # {0}：空格 -> %20
    q_plus = q_quote.replace("%20", "+")     # {1}：空格 -> +
    return template.replace("{0}", q_quote).replace("{1}", q_plus)


def select_groups(selector: str) -> list[str]:
    """把 --groups 参数解析成有序的分区名列表。"""
    selector = (selector or "all").strip().lower()
    if selector in ("all", ""):
        return list(GROUPS.keys())
    if selector in ("download", "dl"):
        return ["dl-core", "dl-other"]
    wanted = [g.strip() for g in selector.replace(";", ",").split(",") if g.strip()]
    unknown = [g for g in wanted if g not in GROUPS]
    if unknown:
        raise SystemExit(
            f"未知分区: {', '.join(unknown)}\n可选: {', '.join(GROUPS)} "
            f"(或 all / download)"
        )
    # 去重并保持 GROUPS 的固定顺序
    return [g for g in GROUPS if g in set(wanted)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="booksearch",
        description="跨数据库文献聚合检索：生成各站点检索链接（默认仅打印，加 --open 才打开）",
    )
    parser.add_argument("query", help="检索词，例如 'Ferdinando Galiani'")
    parser.add_argument(
        "--groups", "-g",
        default="all",
        help="分区：all / download / search / dl-core / dl-other / paper，"
             "可用逗号组合，默认 all",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="用默认浏览器打开生成的全部链接（默认只打印清单）",
    )
    parser.add_argument(
        "--open-only", metavar="站点名或序号", default=None,
        help="只打开指定的站点（按清单中的名称或序号，逗号分隔），仍会打印全部链接",
    )
    parser.add_argument(
        "--names-only", action="store_true",
        help="只列出站点名，不展开 URL",
    )
    args = parser.parse_args(argv)

    query = args.query.strip()
    if not query:
        print("请输入有效的检索词！", file=sys.stderr)
        return 1
    # 检索词过长时几乎所有站点都会拒绝该 URL，且会把终端/日志刷爆，提前拦掉
    if len(query) > MAX_QUERY_LEN:
        print(
            f"检索词过长（{len(query)} 字符，上限 {MAX_QUERY_LEN}）；"
            f"学术站点无法处理这种长度的查询，请精简后重试。",
            file=sys.stderr,
        )
        return 1

    # --open 是「全开」，--open-only 是「只开指定」。二者语义冲突，
    # 同时给出时以更具体的 --open-only 为准，避免用户以为只开一个却弹出一整屏。
    if args.open and args.open_only:
        print(
            "提示：--open 与 --open-only 同时给出，按 --open-only 处理（只打开指定站点）。",
            file=sys.stderr,
        )
        args.open = False

    groups = select_groups(args.groups)

    # 汇总全部命中站点：(组, 站点名, URL)
    count = 0
    entries: list[tuple[str, str, str]] = []
    for group in groups:
        for name, template in GROUPS[group].items():
            entries.append((group, name, build_url(template, query)))

    # 打印清单
    current_group = None
    for i, (group, name, url) in enumerate(entries, 1):
        if group != current_group:
            current_group = group
            print(f"\n【{GROUP_LABELS[group]}】")
        if args.names_only:
            print(f"  {i:>2}. {name}")
        else:
            print(f"  {i:>2}. {name}")
            print(f"      {url}")
        count += 1

    print(f"\n共 {count} 个站点（检索词：{query}）")

    # 决定要打开哪些
    to_open: list[str] = []
    unmatched = 0
    if args.open:
        to_open = [url for _, _, url in entries]
    elif args.open_only:
        tokens = [t.strip() for t in args.open_only.replace(";", ",").split(",") if t.strip()]
        for token in tokens:
            matched = None
            if token.isdigit():
                idx = int(token)
                if 1 <= idx <= len(entries):
                    matched = entries[idx - 1][2]
            else:
                for _, name, url in entries:
                    if name == token or name.lower() == token.lower():
                        matched = url
                        break
                if matched is None:
                    for _, name, url in entries:
                        if token.lower() in name.lower():
                            matched = url
                            break
            if matched:
                to_open.append(matched)
            else:
                unmatched += 1
                print(f"  [跳过] 未匹配到站点: {token}", file=sys.stderr)

    if to_open:
        # 逐条打开；webbrowser 对多数浏览器会复用已有窗口开新标签页
        opened = 0
        for url in to_open:
            try:
                if webbrowser.open_new_tab(url):
                    opened += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  [打开失败] {url} -> {exc}", file=sys.stderr)
        print(f"已在默认浏览器打开 {opened}/{len(to_open)} 个链接")
    elif not args.names_only:
        print("（未打开浏览器；如需打开，加 --open 或 --open-only <站点>）")

    # 用户明确要求打开某些站点却一个都没匹配上，用非零退出码让调用方感知
    if args.open_only and not to_open:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
