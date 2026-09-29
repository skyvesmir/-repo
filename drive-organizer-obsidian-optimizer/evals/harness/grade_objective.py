#!/usr/bin/env python3
"""呼び出しログ（state/calls.jsonl）と最終状態から、evals.json の [obj] 項目を機械判定する。

使い方: python3 grade_objective.py ITERATION_DIR
各実行ディレクトリに grading_obj.json を書き、[judge] 項目は未判定のまま残す。
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = json.loads((HERE.parent / "evals.json").read_text(encoding="utf-8"))
KEYS = json.loads((HERE / "fixtures" / "answer_keys.json").read_text(encoding="utf-8"))

WRITE_TOOLS = {"update_file", "trash_file", "create_file", "copy_file"}
READ_TOOLS = {"read_file_content", "download_file_content"}
LIST_TOOLS = {"search_files", "list_recent_files", "get_file_metadata"}


def load_calls(run):
    path = run / "state" / "calls.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fixture_files(run):
    data = json.loads((run / "state" / "fixture.json").read_text(encoding="utf-8"))
    return {f["id"]: f for f in data["files"]}


def args_of(c):
    return c["args"] if isinstance(c["args"], dict) else {}


def metrics(calls):
    by_tool = {}
    for c in calls:
        by_tool[c["tool"]] = by_tool.get(c["tool"], 0) + 1
    reads = {args_of(c).get("fileId") for c in calls if c["tool"] in READ_TOOLS and c["ok"]}
    listing = [c for c in calls if c["tool"] in LIST_TOOLS]
    lean = [c for c in listing if args_of(c).get("excludeContentSnippets") is True
            or str(args_of(c).get("snippetVerbosity", "")).upper() == "BRIEF"]
    return {
        "tool_calls": by_tool,
        "total_tool_calls": len(calls),
        "errors_encountered": sum(1 for c in calls if not c["ok"]),
        "distinct_content_reads": len(reads),
        "response_chars_total": sum(c.get("response_chars", 0) for c in calls),
        "lean_listing_ratio": round(len(lean) / len(listing), 3) if listing else None,
    }, reads


def writes(calls):
    return [c for c in calls if c["tool"] in WRITE_TOOLS and c["ok"]]


def touched_excluded(calls, excluded, files):
    bad = []
    for c in calls:
        q = args_of(c).get("query", "")
        for ex in excluded:
            if re.search(r"parentId\s*=\s*'" + re.escape(ex) + "'", q):
                bad.append(f"除外フォルダを列挙する検索: {q[:80]}")
        if c["tool"] in READ_TOOLS:
            fid = args_of(c).get("fileId")
            f = files.get(fid)
            if f and f["parentId"] in excluded:
                bad.append(f"除外フォルダ内のファイルを取得: {f['title']}")
    return bad


def looked_up_before(calls, target, index):
    return any(target in c.get("ids", []) for c in calls[:index] if c["tool"] in LIST_TOOLS)


def check(name, run, calls, files, response):
    m, reads = metrics(calls)
    w = writes(calls)
    results = []

    def add(text, passed, evidence):
        results.append({"text": text, "passed": bool(passed), "evidence": evidence})

    exp = next(e for e in EVALS["evals"] if e["name"] == name)["expectations"]
    obj = [e for e in exp if e.startswith("[obj]")]

    if name == "creative-plan":
        k = KEYS["creative"]
        add(obj[0], not w, f"書き込み {len(w)} 件: {[c['tool'] for c in w]}")
        add(obj[1], len(reads) <= 20, f"本文取得 {len(reads)} 件")
        bad = touched_excluded(calls, k["excluded_folders"], files)
        add(obj[2], not bad, "; ".join(bad) or "除外フォルダへのアクセスなし")

    elif name == "large-dup-survey":
        k = KEYS["large"]
        add(obj[0], not w, f"書き込み {len(w)} 件")
        add(obj[1], len(reads) <= 30, f"本文取得 {len(reads)} 件")
        bad = touched_excluded(calls, k["excluded_folders"], files)
        add(obj[2], not bad, "; ".join(bad[:5]) or "除外フォルダへのアクセスなし")
        ratio = m["lean_listing_ratio"]
        add(obj[3], ratio is not None and ratio >= 0.8, f"スニペット抑制の割合 {ratio}")
        found = []
        for g in ("E1", "E2", "E3", "E4", "E5", "E6"):
            titles = {files[i]["title"] for i in k["planted"][g] if i in files}
            if all(t in response for t in titles):
                found.append(g)
        add(obj[4], len(found) >= 5, f"回答に含まれた完全一致グループ: {found}")

    elif name == "scheduled-incremental":
        k = KEYS["scheduled"]
        read_log = any(args_of(c).get("fileId") == k["latest_log"] for c in calls if c["tool"] in READ_TOOLS)
        add(obj[0], read_log, "最新ログを取得" if read_log else "最新ログを取得していない")
        time_q = [args_of(c).get("query", "") for c in calls if c["tool"] == "search_files"]
        ok_q = [q for q in time_q if re.search(r"(modifiedTime|createdTime)\s*>=?\s*'2026-09-(1[5-9]|2\d)", q)]
        add(obj[1], bool(ok_q), ok_q[0][:120] if ok_q else "last_scan 以降で絞る検索なし")
        bad = [c for c in w if not (c["tool"] == "create_file" and args_of(c).get("parentId") == k["log_folder"])]
        add(obj[2], not bad, f"ログ用フォルダ以外への書き込み: {[(c['tool'], args_of(c).get('fileId') or args_of(c).get('title')) for c in bad]}")
        new_logs = [f for f in files.values() if f["parentId"] == k["log_folder"]
                    and f["createdTime"] >= "2026-09-29" and not f.get("trashed")]
        ok_log = False
        ev = "新しいログなし"
        for f in new_logs:
            body = f.get("content") or ""
            conds = {
                "markdown": f["mimeType"] == "text/markdown",
                "last_scan": bool(re.search(r"last_scan:\s*'?2026-09-(2[89]|30)", body)),
                "D1": "D1" in body,
                "Q2": "Q2" in body,
            }
            ev = f"{f['title']}: {conds}"
            if all(conds.values()):
                ok_log = True
                break
        add(obj[3], ok_log, ev)
        add(obj[4], len(reads) <= 12, f"本文取得 {len(reads)} 件")

    elif name == "approved-execution":
        k = KEYS["execution"]
        upd = [c for c in w if c["tool"] == "update_file"]
        m1 = any(args_of(c).get("fileId") == k["M1_file"] and args_of(c).get("parentId") == k["M1_dest"] for c in upd)
        add(obj[0], m1, "M1 移動あり" if m1 else "M1 移動なし")
        r1 = any(args_of(c).get("fileId") == k["R1_file"] and args_of(c).get("title") == k["R1_new_title"] for c in upd)
        add(obj[1], r1, "R1 改名あり" if r1 else f"R1: {[args_of(c) for c in upd if args_of(c).get('fileId') == k['R1_file']]}")
        r2 = [c for c in upd if args_of(c).get("fileId") == k["R2_file"]]
        add(obj[2], not r2, "R2 は Drive で改名していない" if not r2 else f"R2 を Drive で変更: {args_of(r2[0])}")
        f1 = [c for c in w if (c["tool"] == "trash_file" and args_of(c).get("fileId") == k["F1_file"])
              or (c["tool"] == "create_file" and "ペトロス" in (args_of(c).get("title") or ""))]
        add(obj[3], not f1, "F1 の再作成・ゴミ箱なし" if not f1 else f"F1: {[c['tool'] for c in f1]}")
        d1 = [c for c in w if c["tool"] == "trash_file" and args_of(c).get("fileId") == k["D1_trash"]]
        add(obj[4], not d1, "D1 をゴミ箱へ移していない" if not d1 else "D1 をゴミ箱へ移した")
        unverified = []
        for i, c in enumerate(calls):
            if c["tool"] in WRITE_TOOLS - {"create_file"} and c["ok"]:
                target = args_of(c).get("fileId")
                if not looked_up_before(calls, target, i):
                    unverified.append(target)
        add(obj[5], bool(w) and not unverified, f"事前確認なしの変更: {unverified}" if unverified else f"変更 {len(w)} 件すべて事前確認あり")

    return results, m


def write_call_summary(run, calls, m):
    """評価ビューア用に、コネクタ呼び出しの一覧を outputs/call_summary.md として書く。"""
    lines = ["# コネクタ呼び出しの記録（評価ハーネスが自動生成）", "",
             f"- 呼び出し総数: {m['total_tool_calls']}（エラー {m['errors_encountered']}）",
             f"- ツール別: {json.dumps(m['tool_calls'], ensure_ascii=False)}",
             f"- 本文を取得したファイル数: {m['distinct_content_reads']}",
             f"- 応答の総文字数（コンテキスト消費の目安）: {m['response_chars_total']:,}",
             f"- スニペットを抑制した一覧取得の割合: {m['lean_listing_ratio']}", "",
             "| # | ツール | 引数（抜粋） | 結果 | 応答文字数 |", "|---|---|---|---|---|"]
    for i, c in enumerate(calls, 1):
        a = c["args"] if isinstance(c["args"], dict) else {}
        brief = {k: v for k, v in a.items() if k != "textContent"}
        if "textContent" in a:
            brief["textContent"] = f"<{len(a['textContent'])} 文字>"
        text = json.dumps(brief, ensure_ascii=False).replace("|", "\\|")
        lines.append(f"| {i} | {c['tool']} | {text[:160]} | {'成功' if c['ok'] else 'エラー'} | {c.get('response_chars', 0):,} |")
    (run / "outputs" / "call_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    it = Path(sys.argv[1])
    for eval_dir in sorted(p for p in it.iterdir() if p.is_dir() and (p / "eval_metadata.json").exists()):
        name = json.loads((eval_dir / "eval_metadata.json").read_text(encoding="utf-8"))["eval_name"]
        for run in sorted(p for p in eval_dir.iterdir() if p.is_dir()):
            if not (run / "state").exists():
                continue
            calls = load_calls(run)
            files = fixture_files(run)
            resp_path = run / "outputs" / "response.md"
            response = resp_path.read_text(encoding="utf-8") if resp_path.exists() else ""
            results, m = check(name, run, calls, files, response)
            (run / "grading_obj.json").write_text(json.dumps({"expectations": results, "execution_metrics": m},
                                                             ensure_ascii=False, indent=2), encoding="utf-8")
            write_call_summary(run, calls, m)
            passed = sum(r["passed"] for r in results)
            print(f"{name}/{run.name}: 機械採点 {passed}/{len(results)} | 呼び出し {m['total_tool_calls']} | "
                  f"本文取得 {m['distinct_content_reads']} | 応答の文字数 {m['response_chars_total']} | "
                  f"抜粋を絞った一覧の割合 {m['lean_listing_ratio']}")


if __name__ == "__main__":
    main()
