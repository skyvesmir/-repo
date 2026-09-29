#!/usr/bin/env python3
"""skill-creator の評価ビューアを日本語の画面にして、静的な HTML を作る。

skill-creator の eval-viewer を作業用に写し、画面に出る文字列だけを日本語に置き換えてから、
generate_review.py --static で HTML を書き出す。skill-creator の原本は変えない。

使い方: python3 build_viewer_ja.py SKILL_CREATOR_DIR BENCHMARK_DIR 出力HTML
BENCHMARK_DIR は build_benchmark.py と aggregate_benchmark.py の出力（benchmark.json を含む）。
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EVAL_NAMES = {1: "1. 創作フォルダの整理案", 2: "2. 1,500 件の重複調査", 3: "3. 定期実行（差分）", 4: "4. 承認済みの整理案の実行"}
LABELS = [("[obj] ", "【機械採点】"), ("[judge] ", "【盲検採点】")]

JA_CONFIG = '''
    function jaConfig(c) {
      return ({with_skill: "Skill あり（最終版）", without_skill: "Skill なし"})[c] || c.replace(/_/g, " ");
    }
'''

REPLACEMENTS = [
    ('<html lang="en">', '<html lang="ja">'),
    ("<title>Eval Review</title>", "<title>評価の確認</title>"),
    ("<h1>Eval Review: <span", "<h1>評価の確認: <span"),
    ("Review each output and leave feedback below. Navigate with arrow keys or buttons. When done, copy feedback and paste into Claude Code.",
     "各テストの出力を確認し、下の欄に感想を書いてください。矢印キーかボタンで移動できます。書き終わったら「すべての感想を送る」を押すと、感想がファイルとして保存されます。"),
    (">Outputs</button>", ">出力</button>"),
    (">Benchmark</button>", ">集計</button>"),
    (">Prompt <span", ">依頼文 <span"),
    ('<div class="section-header">Output</div>', '<div class="section-header">出力</div>'),
    ("No output files found", "出力ファイルがありません"),
    ("            Previous Output\n", "            前回の出力\n"),
    ("            Formal Grades\n", "            採点結果\n"),
    ("Your Feedback", "あなたの感想"),
    ('placeholder="What do you think of this output? Any issues, suggestions, or things that look great?"',
     'placeholder="この出力をどう思いますか？ 問題点、改善案、よかった点など"'),
    (">Previous feedback<", ">前回の感想<"),
    ("&#8592; Previous", "&#8592; 前へ"),
    ("Submit All Reviews", "すべての感想を送る"),
    ("Next &#8594;", "次へ &#8594;"),
    ("No benchmark data available. Run a benchmark to see quantitative results here.", "集計データがありません。"),
    ("<h2>Review Complete</h2>", "<h2>確認完了</h2>"),
    ("Your feedback has been saved. Go back to your Claude Code session and tell Claude you're done reviewing.",
     "感想を保存しました。Claude との会話に戻って、確認が終わったことを伝えてください。"),
    ("`${index + 1} of ${EMBEDDED_DATA.runs.length}`", "`${index + 1} / ${EMBEDDED_DATA.runs.length}`"),
    ('badge.textContent = config.replace(/_/g, " ");', "badge.textContent = jaConfig(config);"),
    ("'<div class=\"empty-state\">No output files</div>'", "'<div class=\"empty-state\">出力ファイルがありません</div>'"),
    ('dlBtn.textContent = "Download";', 'dlBtn.textContent = "ダウンロード";'),
    ('a.textContent = "Download " + file.name;', 'a.textContent = file.name + " をダウンロード";'),
    ('"Sheet: " + sheetName', '"シート: " + sheetName'),
    ('"Error rendering spreadsheet: "', '"表を表示できませんでした: "'),
    ("' passed, ' + (summary.failed || 0) + ' failed of ' + (summary.total || 0) + '",
     "' 件合格、' + (summary.failed || 0) + ' 件不合格（全 ' + (summary.total || 0) + ' 件）"),
    ('textContent = "Saved"', 'textContent = "保存しました"'),
    ('"Will download on submit"', '"送るときにファイルとして保存します"'),
    (">Benchmark Results</h2>", ">集計結果</h2>"),
    ('"Evals: "', '"評価: "'),
    ('" runs per configuration"', '" 回ずつ（構成ごと）"'),
    ("<th>Metric</th>", "<th>指標</th>"),
    ("<th>Delta</th>", "<th>差</th>"),
    ("<strong>Pass Rate</strong>", "<strong>合格率</strong>"),
    ("<strong>Time (s)</strong>", "<strong>時間（秒）</strong>"),
    ("<strong>Tokens</strong>", "<strong>トークン</strong>"),
    ('delta.time_seconds + "s"', 'delta.time_seconds + " 秒"'),
    (">Per-Eval Breakdown</h3>", ">評価ごとの内訳</h3>"),
    ('"Eval " + evalId', '"評価 " + evalId'),
    ("<th>Config</th><th>Run</th><th>Pass Rate</th>", "<th>構成</th><th>回</th><th>合格率</th>"),
    ('"<th>Time (s)</th>"', '"<th>時間（秒）</th>"'),
    ('"<th>Crashes During Execution</th>"', '"<th>実行中のエラー</th>"'),
    ('"<td>Avg</td>"', '"<td>平均</td>"'),
    ("<th>Assertion</th>", "<th>項目</th>"),
    ('title="Run \' + run.run_number + \': \'', 'title="\' + run.run_number + \' 回目: \''),
    (">Analysis Notes</h3>", ">分析メモ</h3>"),
]
CONFIG_LABEL = '.replace(/_/g, " ").replace(/\\b\\w/g, c => c.toUpperCase())'


def relabel(text):
    for old, new in LABELS:
        text = text.replace(old, new)
    return text


def main():
    sc, bench, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        viewer = tmp / "eval-viewer"
        shutil.copytree(sc / "eval-viewer", viewer)
        html = (viewer / "viewer.html").read_text(encoding="utf-8")
        for old, new in REPLACEMENTS:
            if old not in html:
                sys.exit(f"テンプレートに置き換え元が見つかりません（skill-creator の版が違う可能性）: {old[:60]}")
            html = html.replace(old, new)
        # 構成名（with_skill など）を日本語の表示名に変える
        for var in ("configA", "configB", "config"):
            html = html.replace(var + CONFIG_LABEL, f"jaConfig({var})")
        html = html.replace("<script>", "<script>" + JA_CONFIG, 1)
        (viewer / "viewer.html").write_text(html, encoding="utf-8")

        # 表示用の写しを作り、項目の印を日本語にし、評価名と実行回数を入れる
        data = tmp / "benchmark"
        shutil.copytree(bench, data)
        for g in data.glob("eval-*/*/run-*/grading.json"):
            g.write_text(relabel(g.read_text(encoding="utf-8")), encoding="utf-8")
        b = json.loads((data / "benchmark.json").read_text(encoding="utf-8"))
        b["metadata"]["runs_per_configuration"] = 1
        for run in b["runs"]:
            run["eval_name"] = EVAL_NAMES.get(run["eval_id"], f"評価 {run['eval_id']}")
            for e in run["expectations"]:
                e["text"] = relabel(e["text"])
        (data / "benchmark.json").write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")

        subprocess.run([sys.executable, str(viewer / "generate_review.py"), str(data), "--skill-name",
                        b["metadata"]["skill_name"], "--benchmark", str(data / "benchmark.json"), "--static", str(out)],
                       check=True, stdout=subprocess.DEVNULL)
    print("閲覧用 HTML を書き出しました:", out)


if __name__ == "__main__":
    main()
