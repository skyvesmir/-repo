# 作業ログ・引き継ぎメモ（Skill 開発）

最終更新: 2026-09-29 21:20 UTC。会話の圧縮後にこのファイルから再開できるよう、状態・結果・次の作業を記録する。

## ユーザーについての注意（最優先）

- **ユーザーは日本人。説明はすべて日本語で書く。** 思考（画面に見える）、ツール実行の説明文、コミットメッセージ、サブエージェントへの指示文も日本語にする。英語の出力（英語のログや指示文など）を画面に表示しない。過去に英語が見えて強い不満が出た。
- 口調はフレンドリーかつ少し丁寧。誤字脱字のチェックは厳しめ。問題点は必ず考えるが、でっち上げない。

## 現在地

| フェーズ | 状態 |
|---|---|
| Phase A（Opus 設計） | 完了 |
| Phase B（Sonnet 検証） | 完了。設計レビュー、A〜J ウォークスルー、iteration-1（Skill あり・なし × 4 シナリオ）の実行と機械採点 |
| Phase C（Opus 統合） | 改稿は完了（最終版はコミット `bddd640`）。最終版の再テスト（iteration-3）が途中。盲検採点・パッケージ化は未着手 |

改稿の中身と採否は `docs/REVIEW.md`、設計の説明は `docs/DESIGN.md`、A〜J の机上検証は `docs/TEST_CASES.md` §1（§2 の実行評価は未記入）。

## 実行評価の結果（ここまで）

実行担当はすべて Sonnet。トークンはサブエージェントの報告値。iteration-2 は Phase C の初回改稿（参照ファイルを分けたが、読む条件がゆるかった版）、iteration-3 は最終版。

| 評価 | 構成 | [obj] | 呼び出し | 本文取得 | 総トークン | 所要時間 |
|---|---|---|---|---|---|---|
| creative-plan | it1 Skill なし | 1/3 | 53 | 33 | 98,110 | 194s |
| creative-plan | it1 Skill あり | 3/3 | 32 | 13 | 148,460 | 402s |
| creative-plan | it2 Skill あり | 3/3 | 18 | 6 | 163,790 | 759s（安全チェックの再試行待ちを含む） |
| large-dup-survey | it1 Skill なし | 4/5 | 82 | 25 | 439,403 | 516s |
| large-dup-survey | it1 Skill あり | 5/5 | 65 | 13 | 552,249 | 1033s |
| large-dup-survey | it2 Skill あり | 5/5 | 77 | 13 | 542,575 | 1353s |
| scheduled-incremental | it1 Skill なし | 5/5 | 28 | 12 | 91,836 | 183s |
| scheduled-incremental | it1 Skill あり | 5/5 | 18 | 4 | 124,362 | 305s |
| scheduled-incremental | it2 Skill あり | 5/5 | 13 | 4 | 129,693 | 335s |
| approved-execution | it1 Skill なし | 6/6 | 16 | 4 | 68,272 | 79s |
| approved-execution | it1 Skill あり | 6/6 | 9 | 2 | 88,829 | 109s |
| approved-execution | it2 Skill あり | 6/6 | 11 | 2 | 107,575 | 172s |
| approved-execution | it3 Skill あり（最終版） | 未採点 | 12 | 2 | 92,531 | 107s |

読み取れること（暫定）:

- 安全面の振る舞いはどの回も正しい（書き込みは承認済みの操作とログだけ。正本が更新された D1 は保留。「Obsidian で改名」の R2 は Drive で改名しない）。
- 呼び出しと本文取得は Skill ありで減る。トークンと時間は Skill ありの方が多いまま（Skill の説明を読む分と、慎重な確認の分）。最終版では、参照ファイルを条件付きで読むようにして、approved-execution のトークンが 107k → 93k に戻った。
- 大規模では、インベントリを TSV に手で写す作業が重い（1,096 行）。ID を先頭 10 文字に縮めてよいと Skill に追記した。

## 次の作業（再開手順）

1. **iteration-3 の残り 3 本**（creative-plan, large-dup-survey, scheduled-incremental）を Sonnet で実行する。実行フォルダは作り直し済み（`drive-organizer-obsidian-optimizer-workspace/iteration-3/<評価名>/with_skill`）。指示文は `evals/harness/RUN_PROMPT.md` の雛形（日本語）。依頼文は各 `eval_metadata.json` の `prompt`。終わったら各 `timing.json` に `total_tokens`・`duration_ms`・`total_duration_seconds`・`tool_uses` を書く（approved-execution は記録済み）。
2. `python3 drive-organizer-obsidian-optimizer/evals/harness/grade_objective.py drive-organizer-obsidian-optimizer-workspace/iteration-3` で機械採点する。
3. **盲検採点**: `python3 drive-organizer-obsidian-optimizer/evals/harness/build_blind.py` で `workspace/grading-blind/<評価名>/run_A|B|C/` を作る（iteration-1 の Skill あり・なしと iteration-3 の 3 本。回答中の Skill への言及は除去済み。対応表は `workspace/blind_map_v2.json`。採点者には見せない）。評価ごとに Sonnet の採点担当を 1 本起動し、`expectations.json` の [judge] 項目を各 run について判定させ、`run_X/grading_judge.json`（`expectations: [{text, passed, evidence}]`, `summary: {passed, failed, total, pass_rate}`）に書かせる。判定基準は skill-creator の `agents/grader.md`（根拠を引用できなければ不合格、表面的な充足は不合格）。指示文は日本語。
4. 集計: `eval-N/{with_skill,without_skill}/run-1/{grading.json, timing.json}` と `eval-N/eval_metadata.json` の形に並べ替え（with_skill = iteration-3、without_skill = iteration-1、grading は obj と judge を合わせる）、skill-creator の `scripts/aggregate_benchmark.py` と `eval-viewer/generate_review.py --static` で閲覧用 HTML を作り、ユーザーに送る。
5. `docs/TEST_CASES.md` §2 に実行評価の結果を書く。`docs/DESIGN.md` の既知の限界を結果に合わせて更新する。
6. `package_skill.py` で `.skill` を作り、コミット・プッシュして送る。
7. 評価が終わったら `.claude/settings.local.json`（実 Drive のツールを deny。git 管理外）を削除してよいか考える。
8. 説明文の最適化（`run_loop.py`）は、ユーザーの了承を得てから提案する。

## 環境上の注意

- **Sonnet の利用上限にかかりやすい**。一度に起動するのは 3〜4 本まで。上限に達すると実行が途中で止まり、実行フォルダの作り直しが要る（`setup_run.py <fixture> <run_dir>`。fixture 名は creative / large / scheduled / execution）。
- コンテナの再起動でバックグラウンドの実行は失われる。作業領域（git 管理外）は今のところ残っているが、消える前提で、要る結果は `docs/` に転記する。
- `drive-organizer-obsidian-optimizer-workspace/iteration-3-interrupted/` は中断した実行の記録で、評価には使わない。
- skill-creator の場所: `/root/.claude/skills/synced/195251ac-6d0f-47ef-ba22-1c1cb2cf06f4_0cd5bcd4-7873-421b-9b09-a7406a141afd/skill-creator`
- Bash の安全チェックが一時的に「判定なし」になることがある。そのときは Read・Grep で読み取りだけ進める。
- 実行担当のメモの写し: `docs/review/iteration-2/`、`docs/review/iteration-3/`。

## 実コネクタで確認した事実

`references/drive-connector.md` に反映済み。要点: `update_file` は title/parentId のみ。検索結果に path・checksum・trashed は返らない。pageSize は 30 まで実用。スニペットはファイル先頭。`title contains` は記号を無視。`read_file_content` はエスケープされた表現。ゴミ箱内のファイルが検索に出るかは未確認。
