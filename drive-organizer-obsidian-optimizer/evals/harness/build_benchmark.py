#!/usr/bin/env python3
"""skill-creator の集計（aggregate_benchmark.py）と閲覧用 HTML（generate_review.py）の形に、評価結果を並べ替える。

with_skill = iteration-3（最終版）の Skill あり、without_skill = iteration-1 の Skill なし。
grading.json は、機械採点（grading_obj.json）と盲検採点（grading-blind/<評価名>/run_X/grading_judge.json）を合わせて作る。

使い方: python3 build_benchmark.py 対応表のパス 出力先
"""
import json
import shutil
import sys
from pathlib import Path

WS = Path("/home/user/-repo/drive-organizer-obsidian-optimizer-workspace")
BLIND = WS / "grading-blind"
CONFIGS = {"with_skill": ("iteration-3", "with_skill"), "without_skill": ("iteration-1", "without_skill")}
COPY_OUTPUTS = ["response.md", "notes.md", "call_summary.md"]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    mapping = load(sys.argv[1])
    out = Path(sys.argv[2])
    if out.exists():
        shutil.rmtree(out)
    for ev_dir in sorted(p for p in (WS / "iteration-3").iterdir() if (p / "eval_metadata.json").exists()):
        meta = load(ev_dir / "eval_metadata.json")
        ev = meta["eval_name"]
        eval_out = out / f"eval-{meta['eval_id']}"
        eval_out.mkdir(parents=True)
        (eval_out / "eval_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        for config, (it, cfg) in CONFIGS.items():
            src = WS / it / ev / cfg
            run = eval_out / config / "run-1"
            (run / "outputs").mkdir(parents=True)
            for name in COPY_OUTPUTS:
                if (src / "outputs" / name).exists():
                    shutil.copy(src / "outputs" / name, run / "outputs" / name)
            shutil.copy(src / "timing.json", run / "timing.json")
            shutil.copy(ev_dir / "eval_metadata.json", run / "eval_metadata.json")

            obj = load(src / "grading_obj.json")
            # 対応表は「評価名/run_X」→「iteration-N/構成」。逆引きして盲検の記号を得る
            label = next(k for k, v in mapping.items() if k.startswith(ev + "/") and v == f"{it}/{cfg}")
            judge = load(BLIND / label / "grading_judge.json")
            graded = {e["text"]: e for e in obj["expectations"] + judge["expectations"]}
            expectations = []
            for text in meta["assertions"]:
                if text not in graded:
                    raise SystemExit(f"採点が見つかりません: {ev} {config} {text}")
                e = graded[text]
                expectations.append({"text": text, "passed": bool(e["passed"]), "evidence": e.get("evidence", "")})
            passed = sum(e["passed"] for e in expectations)
            grading = {
                "expectations": expectations,
                "summary": {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations),
                            "pass_rate": round(passed / len(expectations), 4)},
                "execution_metrics": obj["execution_metrics"],
                "blind_label": label,
            }
            (run / "grading.json").write_text(json.dumps(grading, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{ev:24} {config:14} {passed}/{len(expectations)}  （盲検の記号 {label}）")


if __name__ == "__main__":
    main()
