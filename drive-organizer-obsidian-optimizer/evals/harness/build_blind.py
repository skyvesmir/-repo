#!/usr/bin/env python3
"""盲検採点用のパケットを作る。

iteration-1 の Skill あり・なしと、iteration-3（最終版）の Skill ありの 3 本を、評価ごとに run_A/B/C へ無作為に割り当てる。
採点者に構成が分からないよう、回答中の Skill への言及（「SKILL.md」「§4-3」など）だけを除く。原本は変えない。
"""
import json
import random
import re
import shutil
from pathlib import Path

WS = Path("/home/user/-repo/drive-organizer-obsidian-optimizer-workspace")
OUT = WS / "grading-blind"
MAP = WS / "blind_map_v2.json"  # 対応表（採点が終わるまで採点者に見せない）
EVALS = ["creative-plan", "large-dup-survey", "scheduled-incremental", "approved-execution"]
SOURCES = [("iteration-1", "with_skill"), ("iteration-1", "without_skill"), ("iteration-3", "with_skill")]


def scrub(text):
    text = re.sub(r"[（(]\s*(SKILL\.md\s*)?§\s*\d+(-\d+)?\s*[）)]", "", text)
    text = re.sub(r"SKILL\.md\s*§\s*\d+(-\d+)?", "判断基準", text)
    text = re.sub(r"§\s*\d+(-\d+)?", "", text)
    text = re.sub(r"references/[\w\-./]+", "", text)
    text = re.sub(r"(?i)\bskill\b", "", text)
    return text


def main():
    rng = random.Random(20260929)
    if OUT.exists():
        shutil.rmtree(OUT)
    mapping = {}
    for ev in EVALS:
        meta = json.loads((WS / "iteration-1" / ev / "eval_metadata.json").read_text(encoding="utf-8"))
        judge = [a for a in meta["assertions"] if a.startswith("[judge]")]
        labels = ["run_A", "run_B", "run_C"]
        order = SOURCES[:]
        rng.shuffle(order)
        (OUT / ev).mkdir(parents=True)
        old = json.loads((WS / "iteration-1" / "grading" / ev / "expectations.json").read_text(encoding="utf-8"))
        (OUT / ev / "expectations.json").write_text(json.dumps(
            {"prompt": meta["prompt"], "expected_output": old.get("expected_output", ""), "judge_expectations": judge},
            ensure_ascii=False, indent=2), encoding="utf-8")
        for label, (it, cfg) in zip(labels, order):
            src = WS / it / ev / cfg / "outputs"
            dst = OUT / ev / label
            dst.mkdir()
            (dst / "response.md").write_text(scrub((src / "response.md").read_text(encoding="utf-8")), encoding="utf-8")
            shutil.copy(src / "call_summary.md", dst / "call_summary.md")
            mapping[f"{ev}/{label}"] = f"{it}/{cfg}"
    MAP.write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    print("パケットを作成しました:", OUT)


if __name__ == "__main__":
    main()
