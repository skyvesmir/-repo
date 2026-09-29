#!/usr/bin/env python3
"""Drive のインベントリ（TSV）から、重複・命名の「候補」を機械的に抽出する。

判定はしない。出力はすべて本文確認の前の候補であり、SKILL.md の §4（重複判定）で扱う。

使い方:
    python3 find_candidates.py inventory.tsv [--me you@example.com] [--json]

TSV（1 行目はヘッダー、タブ区切り）:
    必須: id, title, mimeType, size, modifiedTime, parentId
    任意: createdTime, path, owner
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict

NATIVE_PREFIX = "application/vnd.google-apps."
FOLDER = "application/vnd.google-apps.folder"
SHORTCUT = "application/vnd.google-apps.shortcut"

# 1 回の置換で取り除く「コピーの印」。基本名が空になる置換は採用しない。
COPY_MARKERS = [
    r"^copy of\s+",
    r"^コピー\s*[-－~〜]?\s*",
    r"\s*の\s*コピー$",
    r"\s*[-－]\s*コピー$",
    r"[\s_-]*\(\d+\)$",
    r"[\s_-]*（\d+）$",
    r"[\s_-]+copy(\s*\d+)?$",
]
VERSION_WORDS = (
    r"(最終版|最新版|最終稿|完成版|確定版|改訂版|修正版|決定版|最終|最新|新規|旧版|"
    r"final|latest|new|old)"
)
VERSION_MARKERS = [
    r"[\s_-]*" + VERSION_WORDS + r"[\s_-]*\d*$",
    r"^" + VERSION_WORDS + r"[\s_-]+",
    r"[\s_-]*v(er)?\.?\d+(\.\d+)*$",
]
# 命名の問題として印を付ける語（new/old は一般的な英単語でもあるため、ここでは対象にしない）
TIME_RELATIVE = re.compile(
    r"(最終版|最新版|最終稿|完成版|確定版|改訂版|修正版|決定版|最終|最新|新規|旧版|final|latest|copy|コピー)",
    re.IGNORECASE,
)
UNTITLED = re.compile(r"^(無題|untitled)", re.IGNORECASE)
NOTION_ID = re.compile(r"\s[0-9a-f]{32}$")
OBSIDIAN_BAD = set('#^[]|\\/:*?"<>')
LONG_NAME = 60
MIN_SIZE_FOR_SIZE_MATCH = 1024
MAX_GROUP_LISTED = 10


def normalize(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", " ", text).strip()


def split_ext(title, mime):
    """Drive 外から来たファイルだけ拡張子を分ける（ネイティブ形式は拡張子を持たない）。"""
    if not mime.startswith(NATIVE_PREFIX):
        m = re.match(r"^(.*?)(\s*)(\.[A-Za-z0-9]{1,8}(?:\.md)?)$", title)
        if m and m.group(1):
            return m.group(1), m.group(3), bool(m.group(2))
    return title, "", False


def strip_markers(base):
    """印を取り除いた基本名と、取り除いた印の有無を返す。"""
    current = normalize(base)
    changed = False
    for _ in range(4):
        before = current
        for pattern in COPY_MARKERS + VERSION_MARKERS:
            candidate = re.sub(pattern, "", current, flags=re.IGNORECASE).strip()
            if candidate and candidate != current:
                current = candidate
        if current == before:
            break
        changed = True
    return current, changed


def load(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    required = {"id", "title", "mimeType", "size", "modifiedTime", "parentId"}
    missing = required - set(rows[0].keys() if rows else required)
    if missing:
        sys.exit(f"TSV に必須列がありません: {', '.join(sorted(missing))}")
    return [r for r in rows if r.get("mimeType") not in (FOLDER,)]


def label(row):
    where = row.get("path") or f"parent={row['parentId']}"
    size = row.get("size") or "-"
    return f"{row['title']} | {where} | {size} B | mod {row['modifiedTime']} | id {row['id']}"


def find(rows, me=None):
    groups = {"S": [], "N": [], "V": [], "Z": []}
    naming = []
    empty = []
    others = []

    comparable = [
        r for r in rows
        if not r["mimeType"].startswith(NATIVE_PREFIX) and (r.get("size") or "0").isdigit()
        and int(r.get("size") or 0) > 0
    ]

    # S: 同じ MIME・同じサイズ・同じ更新日時
    by_smt = defaultdict(list)
    for r in comparable:
        by_smt[(r["mimeType"], r["size"], r["modifiedTime"])].append(r)
    s_ids = set()
    for members in by_smt.values():
        if len(members) > 1:
            groups["S"].append(members)
            s_ids.update(m["id"] for m in members)

    # N: 正規化した名前が同じで、フォルダが違う（同じフォルダ内の同名も含める）
    by_name = defaultdict(list)
    for r in rows:
        if r["mimeType"] != SHORTCUT:
            by_name[normalize(r["title"])].append(r)
    for members in by_name.values():
        if len(members) > 1:
            groups["N"].append(members)

    # V: 印を除いた基本名が同じ（少なくとも 1 件に印がある）
    by_base = defaultdict(list)
    marked = {}
    for r in rows:
        if r["mimeType"] == SHORTCUT:
            continue
        base, ext, _ = split_ext(r["title"], r["mimeType"])
        stripped, changed = strip_markers(base)
        by_base[(stripped, ext.lower())].append(r)
        marked[r["id"]] = changed
    s_sets = [{m["id"] for m in g} for g in groups["S"]]
    for members in by_base.values():
        if len(members) > 1 and any(marked[m["id"]] for m in members):
            ids = {m["id"] for m in members}
            if len({normalize(m["title"]) for m in members}) > 1 and ids not in s_sets:
                groups["V"].append(members)

    # Z: 同じ MIME・同じサイズ（1KB 以上）で名前が違う（S と完全に重なるものは除く）
    by_size = defaultdict(list)
    for r in comparable:
        if int(r["size"]) >= MIN_SIZE_FOR_SIZE_MATCH:
            by_size[(r["mimeType"], r["size"])].append(r)
    for members in by_size.values():
        names = {strip_markers(split_ext(m["title"], m["mimeType"])[0])[0] for m in members}
        if len(members) > 1 and len(names) > 1 and not all(m["id"] in s_ids for m in members):
            groups["Z"].append(members)

    # L: 命名の問題
    for r in rows:
        title = r["title"]
        base, ext, space_before_ext = split_ext(title, r["mimeType"])
        issues = []
        if UNTITLED.match(normalize(base)):
            issues.append("無題")
        if title != title.strip() or space_before_ext or "  " in title:
            issues.append("余分な空白")
        if ext.lower() == ".md" and OBSIDIAN_BAD & set(base):
            issues.append("Obsidian で問題になる文字: " + "".join(sorted(OBSIDIAN_BAD & set(base))))
        if NOTION_ID.search(base):
            issues.append("Notion 書き出しの ID")
        if len(base) > LONG_NAME:
            issues.append(f"長い名前（{len(base)} 文字）")
        if TIME_RELATIVE.search(normalize(base)):
            issues.append("時間で意味が変わる語・コピーの印")
        if issues:
            naming.append((r, issues))
        if not r["mimeType"].startswith(NATIVE_PREFIX) and (r.get("size") or "") == "0":
            empty.append(r)
        if me and r.get("owner") and r["owner"] != me:
            others.append(r)

    return groups, naming, empty, others


GROUP_TITLES = {
    "S": "S: 同じ MIME・サイズ・更新日時（同じ元ファイルのコピーの可能性が高い）",
    "N": "N: 同じ名前（正規化後）",
    "V": "V: コピー・版の印を除くと同じ基本名",
    "Z": "Z: 同じ MIME・サイズで名前が違う",
}


def render_markdown(groups, naming, empty, others, total):
    out = [
        "# 候補一覧（判定ではない）",
        "",
        f"- 入力: {total} 件（フォルダを除く）",
    ]
    for key in "SNVZ":
        out.append(f"- {GROUP_TITLES[key]}: {len(groups[key])} グループ")
    out.append(f"- L: 命名の問題: {len(naming)} 件")
    if empty:
        out.append(f"- X: 空のファイル（0 バイト）: {len(empty)} 件")
    if others:
        out.append(f"- 他人がオーナー: {len(others)} 件（変更対象外）")
    for key in "SNVZ":
        if not groups[key]:
            continue
        out += ["", f"## {GROUP_TITLES[key]}"]
        for i, members in enumerate(sorted(groups[key], key=len, reverse=True), 1):
            out.append("")
            out.append(f"### {key}{i}（{len(members)} 件）")
            for m in members[:MAX_GROUP_LISTED]:
                out.append(f"- {label(m)}")
            if len(members) > MAX_GROUP_LISTED:
                out.append(f"- ほか {len(members) - MAX_GROUP_LISTED} 件")
    if naming:
        out += ["", "## L: 命名の問題"]
        for r, issues in naming:
            out.append(f"- {label(r)} → {'、'.join(issues)}")
    if empty:
        out += ["", "## X: 空のファイル（0 バイト）"]
        for r in empty:
            out.append(f"- {label(r)}")
    if others:
        out += ["", "## 他人がオーナー（変更対象外）"]
        for r in others:
            out.append(f"- {label(r)} | owner {r['owner']}")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inventory", help="インベントリ TSV")
    parser.add_argument("--me", help="自分のメールアドレス（他人がオーナーのファイルに印を付ける）")
    parser.add_argument("--json", action="store_true", help="JSON で出力する")
    args = parser.parse_args()

    rows = load(args.inventory)
    groups, naming, empty, others = find(rows, args.me)
    if args.json:
        payload = {
            "total": len(rows),
            "groups": {k: [[m["id"] for m in g] for g in v] for k, v in groups.items()},
            "naming": [{"id": r["id"], "title": r["title"], "issues": i} for r, i in naming],
            "empty": [r["id"] for r in empty],
            "others": [r["id"] for r in others],
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_markdown(groups, naming, empty, others, len(rows)))


if __name__ == "__main__":
    main()
