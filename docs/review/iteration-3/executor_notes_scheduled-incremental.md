# notes.md（scheduled-incremental / with_skill）

## 行った手順（簡潔に）
1. SKILL.md と TOOLS.md を読み、SKILL の指示で references/drive-connector.md、scheduled.md、templates.md、obsidian.md を読んだ。scripts/find_candidates.py は、インベントリが 45 件で 300 件以下なので使っていない。
2. 実行開始時刻を 2026-09-29T09:00:00Z と控えた（今回の last_scan）。
3. マイドライブ直下を一覧（search_files, parentId = 'root'）し、_drive-organizer-logs を特定。その子を一覧し、最新のログ 2026-09-15_0900 だけを read_file_content で読んだ（状態ブロック version 1）。
4. 差分検索（owner = 'me' and (modifiedTime > last_scan or createdTime > last_scan)）で 7 件。範囲外・除外（ログ、.obsidian/workspace.json）を除いた 5 件が対象。
5. scope フォルダと Vault ルートの子を OR で 1 回、Vault のサブフォルダ（人物・章・原稿・設定・メモ・資料）の子を OR で 1 回一覧し、インベントリ 45 件を得た（親の判定、同名・同じ基本名の既存ファイルの確認、前回の pending・open_items の存在と未更新の確認に使った）。
6. 新規・重複候補 5 件の先頭を BRIEF で 1 回取得（第03章.md、第03章 (1).md、第04章.md、イェレナ.md、無題のドキュメント）。
7. 第03章 (1).md に get_file_permissions（共有なし）。
8. 全文の読み取り 4 件: 六炎_第1部_最新版、最終版2（Q1 の再判定）、最終版（同じ基本名の既存ファイル）、無題のドキュメント（空）。
9. 判定: D2 新規（完全一致、高）、R1・R2 新規（旧版の改名。Q1 は解消）、Q3 新規、Q2 継続、D1 継続。イェレナ.md・第04章.md は変更なし。
10. ログ（整理案 + 作業ログ + 状態ブロック version 2）を create_file で _drive-organizer-logs に保存（text/markdown、disableConversionToGoogleType: true、返り値の mimeType と parentId を確認）。ID 1f76ebc2a267910f8be8da4dfdc9760a1。
11. 更新・移動・ゴミ箱移動は一切実行していない。Drive への書き込みはログの作成 1 回だけ。

## 読んだ Skill のファイル
- SKILL.md
- references/drive-connector.md
- references/scheduled.md
- references/templates.md
- references/obsidian.md（新規ノート 2 件の Frontmatter・命名を規約と照合する案を作るため）
- （evals/harness/TOOLS.md も指示どおり読んだ）

## わかりにくい・矛盾・従わなかった点
- 状態ブロックに `keep_modified`（正本の更新日時）と、R2 の `note` を足した。templates.md §3 の pending の書式にない欄。SKILL §6-2 が「正本が更新されていれば D を保留」と求めるので、実行時に正本の更新日時と比べる材料が要ると判断した。書式に「正本の更新日時」欄があると迷わない。
- 前回の状態ブロックは version 1 で `log_folder`・`trashed_in_search`・`reviewed` がなかった。scheduled.md §1-4 に従い空で加えたが、`log_folder` は今回の一覧で確かめた実際の値を入れた（推測ではない）。`reviewed` が空なので、差分の外の重複らしき組（企画書.docx の組、鉱物図鑑の組など）が検討済みかどうかがわからない。scheduled.md §2 に従い、ID なしの確度「低」の観察として報告するだけにした。
- Q1 の再判定（SKILL §4-3）: 最新版が 9/25 に更新され、最終版2 の全場面を含み追記もあるが、1 文だけ具体的な描写が言い換えで薄まっている（「採掘をやめさせた」→「段取りが変わった」）。「言い換えは改稿」「包含は記述の有無（事実・場面・項目）で見る」に従えば別バージョンだが、「事実」がどこまで落ちたら分岐かの線引きが書かれていない。確度を「中」にして R2 に根拠を書いた。
- 非 Obsidian ファイルの旧版の扱い（§4-1 分類 3、§2 Phase 4）: アーカイブ用フォルダがないので `_v01` への改名を提案した。ただし複数の旧版があるとき、連番の付け方（古い順に v01, v02）と、最新版の名前（「最新版」のまま残す）についての指示がない。古い順の連番にして、最新版は変えなかった。
- 最終版（6/1）は最終版2 に一字一句含まれるので、§4-1 の注記ではゴミ箱の案を選択肢にできる可能性があるが、§4-4 の確認（共有の確認など）を追加で行う必要があり、定期実行では実行もしないので、ゴミ箱の案にはせず改名だけにした。
- §0-3「条件なしで Drive 全体を検索しない」と、scheduled.md §2 の差分検索（`owner = 'me' and …`、親を指定しない）は一見食い違う。後者は日時の条件があるので、条件なしの全体検索には当たらないと解釈し、結果の親で範囲を判定した。名前指定の BRIEF 取得（title = '…' の OR）も、親を指定せずに行った（該当は範囲内の 5 件だけだった）。
- 差分検索は `owner = 'me'` なので、他人がオーナーのファイルの変化を見られない。scheduled.md にこの限界の記述がなく、報告に書いた。
- 状態ブロックの `last_scan` は「開始した時刻」だが、模擬環境では時計が 09:00:00Z 固定なので、タスクに書かれた時刻を使った。
- 見出し: templates.md では整理案が `# Drive 整理案`、作業ログが `# 作業ログ` と別の見出しだが、SKILL §8 は「毎回新しいファイル 1 件」に保存するとある。1 ファイルにまとめ、見出しは `# 作業ログ・整理案（日時）` にし、状態ブロックを見出しの直後に置いた（scheduled.md §1-3 の読み戻しに合わせた）。
- create_file の引数は長い JSON なので、Python で JSON ファイルにしてから `"$(cat …)"` で渡した（1 回の drive 呼び出しのまま。パイプやループはしていない）。
- 使えなかったもの: 特になし（更新・ゴミ箱・共有確認のツールはあったが、定期実行のルールで書き込みを行わなかった）。
- Q2（アイデア断片.md）は更新がないので読み直していない。新規ノート（イェレナ、第04章）との関連を確かめる価値はあったが、差分の調査範囲を広げないため見送った。
