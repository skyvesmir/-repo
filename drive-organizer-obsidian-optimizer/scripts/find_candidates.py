#!/usr/bin/env python3
"""Drive のインベントリ（TSV）から、重複・命名の「候補」を機械的に抽出する。

判定はしない。出力はすべて本文確認の前の候補であり、SKILL.md の §4（重複判定）で扱う。

使い方:
    python3 find_candidates.py inventory.tsv [--me you@example.com] [--json]

TSV（1 行目はヘッダー、タブ区切り、引用符なし）。インベントリが 300 件を超えるときだけ作り、下の列だけを書く:
    必須: id, title, mimeType（略さない）, size（fileSize。なければ空）, modifiedTime, parentId
    任意: createdTime, path（組み立てたパス。出力が読みやすくなる）, owner
    id と parentId は、重ならない範囲で先頭 10 文字程度に縮めてよい。

候補の種類:
    S  同じ MIME・サイズ・更新日時（同じ元ファイルのコピーの可能性が高い）
    N  正規化した名前が同じ（同じフォルダ内も含む）。Drive 外の形式でサイズがすべて違うものは「弱い N」として名前だけ出す
    V  コピー・版・派生の印を除くと同じ基本名
    P  同じフォルダで名前が非常に近い（数字だけの違いは連番として除く）
    Z  同じ MIME・サイズ（1KB 以上）で名前が違う
    F  フォルダ複製の疑い（同じ 2 フォルダの間に、サイズも同じ S/N の組が多数）
    T  同じ語を名前に含むまとまり（同一テーマの大量ファイル。重複ではなく一貫性の確認用）
    L  命名の問題
    X  空のファイル（0 バイト）
"""

import argparse
import difflib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from itertools import combinations

NATIVE_PREFIX = "application/vnd.google-apps."
FOLDER = "application/vnd.google-apps.folder"
SHORTCUT = "application/vnd.google-apps.shortcut"
REQUIRED = ("id", "title", "mimeType", "size", "modifiedTime", "parentId")

# 版・状態を表す語。区切り（空白・_・-）の後ろか、括弧の中にあるときだけ印とみなす。
VERSION_WORDS = (
    r"最終版|最新版|最終稿|完成版|確定版|改訂版|修正版|決定版|旧版|最終|最新|新規|"
    r"final|latest|new|old"
)
# 区切りなしで名前に直接付いていても印とみなす語（「企画書最終版」など）。
ATTACHED_WORDS = r"最終版|最新版|最終稿|完成版|確定版|改訂版|修正版|決定版|旧版"
# 派生を表す語（原本と派生の候補になる）。
DERIVED_WORDS = r"要約|抜粋|あらすじ|圧縮版|圧縮|英語版|英訳|和訳|翻訳|書き出し|エクスポート|summary|excerpt|export"
SEP = r"[\s_\-－・]+"
OPEN, CLOSE = r"[（(【\[]", r"[）)】\]]"

MARKERS = [
    ("コピー", r"^copy of\s+"),
    ("コピー", r"^コピー\s*[-－~〜]?\s*"),
    ("コピー", r"\s*の\s*コピー$"),
    ("コピー", r"\s*[-－]\s*コピー$"),
    ("コピー番号", r"\s*\(\d+\)$"),
    ("コピー番号", r"\s*（\d+）$"),
    ("コピー", SEP + r"copy(\s*\d+)?$"),
    ("版", r"\s*" + OPEN + r"\s*(" + VERSION_WORDS + r"|コピー|copy|v\d+(\.\d+)*)\s*\d*\s*" + CLOSE + r"$"),
    ("版", r"^" + OPEN + r"\s*(" + VERSION_WORDS + r")\s*" + CLOSE + r"\s*"),
    ("版", SEP + r"(" + VERSION_WORDS + r")\s*\d*$"),
    ("版", r"(?<=\S)(" + ATTACHED_WORDS + r")\d*$"),
    ("版", r"^(" + VERSION_WORDS + r")" + SEP),
    ("版番号", SEP + r"v(er)?\.?\d+(\.\d+)*$"),
    ("派生", r"\s*" + OPEN + r"\s*(" + DERIVED_WORDS + r")\s*" + CLOSE + r"$"),
    ("派生", SEP + r"(" + DERIVED_WORDS + r")$"),
]
TIME_RELATIVE = re.compile(
    r"(" + ATTACHED_WORDS + r")|\b(final|latest|copy)\b|のコピー|^コピー|" + SEP + r"(最終|最新|新規)$|"
    + OPEN + r"\s*(最終|最新|新規|new)\s*" + CLOSE,
    re.IGNORECASE,
)
UNTITLED = re.compile(r"^(無題|untitled)", re.IGNORECASE)
NOTION_ID = re.compile(r"\s[0-9a-f]{32}$")
OBSIDIAN_BAD = set('#^[]|\\/:*?"<>')
LONG_NAME = 60
MIN_SIZE_FOR_SIZE_MATCH = 1024
MAX_GROUP_LISTED = 10
SIMILARITY = 0.85
MAX_FOLDER_FOR_SIMILARITY = 400
FOLDER_DUP_MIN_PAIRS = 5
# T: 語の出現ファイル数がこの範囲のものだけを出す（多すぎる語は一般語とみなす）
THEME_MIN_FILES, THEME_MAX_FILES, THEME_LISTED = 3, 50, 15
# 文字種の連なりで名前を語に分ける（形態素解析の代わりの粗い方法）
TOKEN_RUNS = re.compile(r"[\u30a1-\u30fa\u30fc-\u30ff]+|[\u4e00-\u9fff々]+|[a-z][a-z0-9]*")


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
    """印を取り除いた基本名と、取り除いた印の種類を返す。"""
    current = normalize(base)
    found = []
    for _ in range(4):
        before = current
        for kind, pattern in MARKERS:
            candidate = re.sub(pattern, "", current, flags=re.IGNORECASE).strip(" _-－・")
            if candidate and candidate != current:
                current = candidate
                found.append(kind)
        if current == before:
            break
    return current, found


def load(path):
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.read().splitlines()
    if not lines:
        sys.exit("TSV が空です")
    header = lines[0].split("\t")
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        sys.exit(f"TSV に必須列がありません: {', '.join(missing)}")
    rows, broken = [], []
    for n, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) != len(header):
            broken.append(n)
            continue
        rows.append(dict(zip(header, cells)))
    if broken:
        print(f"警告: 列数が合わない行を {len(broken)} 行とばしました（行番号: {broken[:10]}）", file=sys.stderr)
    return [r for r in rows if r["mimeType"] != FOLDER], len(broken)


def theme_tokens(base):
    """カタカナ・漢字は 2 文字以上、英字は 3 文字以上の語を返す（ひらがなと数字は捨てる）。"""
    out = set()
    for tok in TOKEN_RUNS.findall(base):
        if tok[0].isascii():
            if len(tok) >= 3:
                out.add(tok)
        elif len(tok) >= 2:
            out.add(tok)
    return out


def label(row):
    where = row.get("path") or f"parent={row['parentId']}"
    size = row.get("size") or "-"
    return f"{row['title']} | {where} | {size} B | mod {row['modifiedTime']} | id {row['id']}"


def group_by(rows, key):
    out = defaultdict(list)
    for r in rows:
        out[key(r)].append(r)
    return [g for g in out.values() if len(g) > 1]


def union_groups(pairs):
    parent = {}

    def root(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        parent[root(a)] = root(b)
    groups = defaultdict(set)
    for x in list(parent):
        groups[root(x)].add(x)
    return list(groups.values())


def find(rows, me=None):
    by_id = {r["id"]: r for r in rows}
    real = [r for r in rows if r["mimeType"] != SHORTCUT]
    comparable = [r for r in real if not r["mimeType"].startswith(NATIVE_PREFIX)
                  and r.get("size", "").isdigit() and int(r["size"]) > 0]

    groups = {}
    groups["S"] = group_by(comparable, lambda r: (r["mimeType"], r["size"], r["modifiedTime"]))
    groups["N"] = group_by(real, lambda r: normalize(r["title"]))

    stripped = {}
    for r in real:
        base, ext, _ = split_ext(r["title"], r["mimeType"])
        stripped[r["id"]] = (*strip_markers(base), ext.lower())
    s_sets = [{m["id"] for m in g} for g in groups["S"]]
    groups["V"] = []
    for g in group_by(real, lambda r: (stripped[r["id"]][0], stripped[r["id"]][2])):
        ids = {m["id"] for m in g}
        if any(stripped[m["id"]][1] for m in g) and len({normalize(m["title"]) for m in g}) > 1 and ids not in s_sets:
            groups["V"].append(g)

    # P: 同じフォルダで名前が非常に近い（数字だけの違いは連番として除く）
    v_members = {m["id"] for g in groups["V"] for m in g}
    pairs = []
    for folder_rows in group_by(real, lambda r: r["parentId"]):
        if len(folder_rows) > MAX_FOLDER_FOR_SIMILARITY:
            continue
        for a, b in combinations(folder_rows, 2):
            na, nb = stripped[a["id"]][0], stripped[b["id"]][0]
            if na == nb or min(len(na), len(nb)) < 4:
                continue
            if re.sub(r"\d", "#", na) == re.sub(r"\d", "#", nb):
                continue
            if a["id"] in v_members and b["id"] in v_members:
                continue
            if difflib.SequenceMatcher(None, na, nb).ratio() >= SIMILARITY:
                pairs.append((a["id"], b["id"]))
    groups["P"] = [[by_id[i] for i in sorted(g)] for g in union_groups(pairs)]

    s_ids = {m["id"] for g in groups["S"] for m in g}
    groups["Z"] = []
    for g in group_by([r for r in comparable if int(r["size"]) >= MIN_SIZE_FOR_SIZE_MATCH],
                      lambda r: (r["mimeType"], r["size"])):
        names = {stripped[m["id"]][0] for m in g}
        if len(names) > 1 and not all(m["id"] in s_ids for m in g):
            groups["Z"].append(g)

    # N のうち、Drive 外の形式ですべてサイズが違うものは別内容の可能性が高いので「弱い N」に分ける
    def weak(g):
        if any(m["mimeType"].startswith(NATIVE_PREFIX) for m in g):
            return False
        sizes = [m.get("size") for m in g]
        return len(set(sizes)) == len(sizes)

    groups["N_weak"] = [g for g in groups["N"] if weak(g)]
    groups["N"] = [g for g in groups["N"] if not weak(g)]

    # F: 同じ 2 フォルダの間に、内容も同じらしい組（S、またはサイズも同じ N。ネイティブ形式は除く）が多数ある
    folder_pairs = defaultdict(int)
    for g in groups["S"] + groups["N"]:
        seen = set()
        for a, b in combinations(g, 2):
            if a.get("size") != b.get("size") or not a.get("size"):
                continue
            # ネイティブ形式のサイズは本文量と対応しないので、同じサイズでも根拠にしない
            if a["mimeType"].startswith(NATIVE_PREFIX) or b["mimeType"].startswith(NATIVE_PREFIX):
                continue
            if a["parentId"] != b["parentId"]:
                key = tuple(sorted((a["parentId"], b["parentId"])))
                if key not in seen:
                    folder_pairs[key] += 1
                    seen.add(key)
    paths = {r["parentId"]: (r.get("path") or "").rsplit("/", 1)[0] for r in rows}
    folder_dups = [{"folders": list(k), "paths": [paths.get(k[0], ""), paths.get(k[1], "")], "pairs": n}
                   for k, n in sorted(folder_pairs.items(), key=lambda kv: -kv[1]) if n >= FOLDER_DUP_MIN_PAIRS]

    # T: 同じ語を名前に含むファイルのまとまり。複数のフォルダにまたがる語を先に出す
    by_token = defaultdict(list)
    for r in real:
        for tok in theme_tokens(stripped[r["id"]][0]):
            by_token[tok].append(r)
    themes = []
    for tok, members in by_token.items():
        # 語を除いた残り（数字と区切りも除く）が 1 種類しかなければ、連番や同名の並びなので出さない
        contexts = {re.sub(r"[\d\s_\-－・.]+", "", stripped[m["id"]][0].replace(tok, "")) for m in members}
        if THEME_MIN_FILES <= len(members) <= THEME_MAX_FILES and len(contexts) >= 2:
            themes.append((tok, members, len({m["parentId"] for m in members})))
    themes.sort(key=lambda t: (-t[2], -len(t[1]), t[0]))
    groups["T"] = themes[:THEME_LISTED]

    naming, empty, others = [], [], []
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
            issues.append("時間で意味が変わる語・コピーの印（主題の一部なら問題なし）")
        if issues:
            naming.append((r, issues))
        if not r["mimeType"].startswith(NATIVE_PREFIX) and r.get("size") == "0":
            empty.append(r)
        if me and r.get("owner") and r["owner"] != me:
            others.append(r)

    markers = {i: v[1] for i, v in stripped.items() if v[1]}
    return groups, folder_dups, naming, empty, others, markers


GROUP_TITLES = {
    "S": "S: 同じ MIME・サイズ・更新日時（同じ元ファイルのコピーの可能性が高い）",
    "N": "N: 同じ名前（正規化後。同じフォルダ内も含む）",
    "V": "V: コピー・版・派生の印を除くと同じ基本名",
    "P": "P: 同じフォルダで名前が非常に近い",
    "Z": "Z: 同じ MIME・サイズで名前が違う",
}


def render_markdown(groups, folder_dups, naming, empty, others, markers, total, broken):
    out = ["# 候補一覧（判定ではない）", "", f"- 入力: {total} 件（フォルダを除く）"]
    if broken:
        out.append(f"- 読み込めなかった行: {broken} 件（TSV を確認すること）")
    for key in "SNVPZ":
        out.append(f"- {GROUP_TITLES[key]}: {len(groups[key])} グループ")
    out.append(f"- N（弱）: 同じ名前だがサイズがすべて違う: {len(groups['N_weak'])} グループ（名前だけ列挙）")
    out.append(f"- F: フォルダ複製の疑い: {len(folder_dups)} 組")
    out.append(f"- T: 同じ語を名前に含むまとまり: {len(groups['T'])} 語（上位のみ。重複の候補ではない）")
    out.append(f"- L: 命名の問題: {len(naming)} 件")
    out.append(f"- X: 空のファイル（0 バイト）: {len(empty)} 件")
    if others:
        out.append(f"- 他人がオーナー: {len(others)} 件（変更対象外）")
    if folder_dups:
        out += ["", "## F: フォルダ複製の疑い（個別に提案せず、まとめて 1 件の要確認にする）"]
        for d in folder_dups:
            out.append(f"- {d['paths'][0] or d['folders'][0]} ⇔ {d['paths'][1] or d['folders'][1]}: {d['pairs']} 組")
    for key in "SNVPZ":
        if not groups[key]:
            continue
        out += ["", f"## {GROUP_TITLES[key]}"]
        for i, members in enumerate(sorted(groups[key], key=len, reverse=True), 1):
            out += ["", f"### {key}{i}（{len(members)} 件）"]
            for m in members[:MAX_GROUP_LISTED]:
                mark = f" | 印: {'・'.join(markers[m['id']])}" if key == "V" and m["id"] in markers else ""
                out.append(f"- {label(m)}{mark}")
            if len(members) > MAX_GROUP_LISTED:
                out.append(f"- ほか {len(members) - MAX_GROUP_LISTED} 件")
    if groups["T"]:
        out += ["", "## T: 同じ語を名前に含むまとまり（一貫性の確認用。役割は内容で判断する）"]
        for tok, members, folders in groups["T"]:
            names = "、".join(m["title"] for m in members[:MAX_GROUP_LISTED])
            more = f" ほか {len(members) - MAX_GROUP_LISTED} 件" if len(members) > MAX_GROUP_LISTED else ""
            out.append(f"- 「{tok}」: {len(members)} 件・{folders} フォルダ — {names}{more}")
    if groups["N_weak"]:
        out += ["", "## N（弱）: 同じ名前だがサイズがすべて違う（別内容の可能性が高い。重複として扱わない）"]
        out += [f"- {g[0]['title']} × {len(g)}" for g in groups["N_weak"]]
    if naming:
        out += ["", "## L: 命名の問題"]
        out += [f"- {label(r)} → {'、'.join(issues)}" for r, issues in naming]
    if empty:
        out += ["", "## X: 空のファイル（0 バイト）"]
        out += [f"- {label(r)}" for r in empty]
    if others:
        out += ["", "## 他人がオーナー（変更対象外）"]
        out += [f"- {label(r)} | owner {r['owner']}" for r in others]
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inventory", help="インベントリ TSV")
    parser.add_argument("--me", help="自分のメールアドレス（owner = 'me' で検索した結果の owner の値）。他人がオーナーのファイルに印を付ける")
    parser.add_argument("--json", action="store_true", help="JSON で出力する")
    args = parser.parse_args()

    rows, broken = load(args.inventory)
    groups, folder_dups, naming, empty, others, markers = find(rows, args.me)
    if args.json:
        payload = {
            "total": len(rows),
            "broken_rows": broken,
            "groups": {k: [[m["id"] for m in g] for g in v] for k, v in groups.items() if k != "T"},
            "themes": [{"token": t, "ids": [m["id"] for m in ms], "folders": n} for t, ms, n in groups["T"]],
            "folder_duplicates": folder_dups,
            "naming": [{"id": r["id"], "title": r["title"], "issues": i} for r, i in naming],
            "empty": [r["id"] for r in empty],
            "others": [r["id"] for r in others],
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_markdown(groups, folder_dups, naming, empty, others, markers, len(rows), broken))


if __name__ == "__main__":
    main()
