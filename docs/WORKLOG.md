# 作業ログ・引き継ぎメモ（Skill 開発）

最終更新: 2026-09-29 22:00 UTC。会話の圧縮後にこのファイルから再開できるよう、状態・結果・次の作業を記録する。

## ユーザーについての注意（最優先）

- **ユーザーは日本人。説明はすべて日本語で書く。** 思考（画面に見える）、ツール実行の説明文、コミットメッセージ、サブエージェントへの指示文も日本語にする。英語の出力（英語のログや指示文など）を画面に表示しない。過去に英語が見えて強い不満が出た。
- 口調はフレンドリーかつ少し丁寧。誤字脱字のチェックは厳しめ。問題点は必ず考えるが、でっち上げない。

## 現在地

| フェーズ | 状態 |
|---|---|
| Phase A（Opus 設計） | 完了 |
| Phase B（Sonnet 検証） | 完了。設計レビュー、A〜J ウォークスルー、iteration-1（Skill あり・なし × 4 シナリオ）の実行と機械採点 |
| Phase C（Opus 統合） | 完了。改稿（最終版 `bddd640`）、再テスト（iteration-3）、機械採点・盲検採点・集計、再テストの指摘の反映（文言の明確化とスクリプトの改良）、資料の更新、パッケージ化（`dist/drive-organizer-obsidian-optimizer.skill`） |

改稿の中身と採否は `docs/REVIEW.md`、設計の説明は `docs/DESIGN.md`、検証の結果は `docs/TEST_CASES.md`（§1 が A〜J の机上検証、§2 が実行評価）。比較ページは `docs/eval-review.html`。

## 実行評価の結果（要約）

詳細は `docs/TEST_CASES.md` §2。合格は機械採点と盲検採点の合計（43 項目）。

| 構成 | 合格 | 呼び出し（合計） | 本文取得（合計） | トークン（平均） | 時間（平均） |
|---|---|---|---|---|---|
| 最終版 Skill（iteration-3） | 43/43 | 105 | 24 | 224,537 | 459 秒 |
| 初版 Skill（iteration-1） | 43/43 | 124 | 32 | 228,475 | 462 秒 |
| Skill なし（iteration-1） | 33/43 | 179 | 74 | 174,405 | 243 秒 |

- Skill なしは、共有ファイルをゴミ箱候補にする、`node_modules` や `.obsidian` の中を読む、確度を付けない、作業ログを残さない、などで落ちた。
- Skill ありは呼び出しと本文取得が大きく減るが、トークンと時間は増える（Skill の説明を読む固定の量と、書き込み前の確認の分）。

## 残っている作業（任意）

1. `.claude/settings.local.json`（実 Drive のツールを deny。git 管理外）は、評価が終わったので削除してよい。削除するかはユーザーに確かめる。
2. 説明文の最適化（skill-creator の `run_loop.py`）は、ユーザーの了承を得てから行う。
3. 評価を直すなら、採点担当が挙げた項目の弱さ（`docs/TEST_CASES.md` §2-4）から手を付け、各構成を複数回走らせてばらつきを見る。
4. 再テストの後に加えた文言の明確化は、Skill 全体では再テストしていない。

## 環境上の注意

- **Sonnet の利用上限にかかりやすい**。一度に起動するのは 3〜4 本まで。上限に達すると実行が途中で止まり、実行フォルダの作り直しが要る（`setup_run.py <fixture> <run_dir>`。fixture 名は creative / large / scheduled / execution）。
- コンテナの再起動でバックグラウンドの実行は失われる。作業領域（git 管理外）は今のところ残っているが、消える前提で、要る結果は `docs/` に転記する。
- `drive-organizer-obsidian-optimizer-workspace/iteration-3-interrupted/` は中断した実行の記録で、評価には使わない。
- skill-creator の場所: `/root/.claude/skills/synced/195251ac-6d0f-47ef-ba22-1c1cb2cf06f4_0cd5bcd4-7873-421b-9b09-a7406a141afd/skill-creator`
- Bash の安全チェックが一時的に「判定なし」になることがある。そのときは Read・Grep で読み取りだけ進める。
- 実行担当のメモの写し: `docs/review/iteration-2/`、`docs/review/iteration-3/`。

## 実コネクタで確認した事実

`references/drive-connector.md` に反映済み。要点: `update_file` は title/parentId のみ。検索結果に path・checksum・trashed は返らない。pageSize は 30 まで実用。スニペットはファイル先頭。`title contains` は記号を無視。`read_file_content` はエスケープされた表現。ゴミ箱内のファイルが検索に出るかは未確認。
