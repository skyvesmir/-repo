# 実行担当（Sonnet）への指示文の雛形

`{RUN_DIR}` は `/home/user/-repo/drive-organizer-obsidian-optimizer-workspace/iteration-N/<評価名>/with_skill`。`{依頼文}` は `evals.json` の `prompt`（approved-execution は整理案を含む全文）。Agent は `model: sonnet`、`run_in_background: true` で起動する。Skill なしで走らせるときは「SKILL:」の段落を除き、「Skill の指示のうち…」の記述をメモの項目から外す。

## 対話のシナリオ（creative-plan / large-dup-survey / approved-execution）

```text
あなたは Claude Skill の評価のうち、テストケース 1 件を実行します。Google Drive コネクタがある Claude アプリのセッション（Cowork に近い環境: 作業用のファイルシステムがあり、自分で書いたファイルに対して Python を実行できる）で、実際のユーザーを手伝うときの Claude とまったく同じように振る舞ってください。

安全（絶対）: mcp__Google_Drive__* のツールや、その他の MCP・コネクタのツールは決して呼ばないこと。実在の人のアカウントにつながっています。触ってよい Google Drive は下の模擬環境だけです。サブエージェント、Web アクセス、Skill ツールも使わないこと。

SKILL: まず /home/user/-repo/drive-organizer-obsidian-optimizer/SKILL.md を読み、それに従うこと。SKILL.md が読むよう指示する参照ファイルやスクリプトも、指示された条件のときに使うこと（Skill 内のパスは /home/user/-repo/drive-organizer-obsidian-optimizer/ からの相対パス）。

GOOGLE DRIVE コネクタ（模擬）: /home/user/-repo/drive-organizer-obsidian-optimizer/evals/harness/TOOLS.md を読むこと。<RUN_DIR> は {RUN_DIR} です。ルール:
- ツールは 1 回の Bash コマンドで呼ぶ: {RUN_DIR}/drive TOOL '<json>'。表示される JSON がツールの応答です。
- 1 コマンド = 1 回のツール呼び出し。複数の drive 呼び出しを 1 コマンドにつなげたり、ループで回したり、出力をパイプで加工したりしないこと（実際のコネクタの応答は、そのままコンテキストに入るため）。
- <RUN_DIR>/state/ の中は読まないこと。ハーネスのディレクトリ（evals/harness/）も、TOOLS.md 以外は読まないこと。Drive には drive コマンドでだけアクセスできます。
- 自分の作業ファイルは <RUN_DIR>/outputs/work/ に書いてよい。
（approved-execution のみ次の 1 行を足す）
- この環境には Obsidian Vault のローカルコピーはありません。Vault は Google Drive の中にだけあります。

前提: 現在の日時は 2026-09-29 09:00 UTC。ユーザーの Google アカウントは writer@example.com。

ユーザーのメッセージ:
<<<
{依頼文}
>>>

この実行中、ユーザーは返信できません。質問をしたり承認を待ったりする場面になったら、そこで止め、そのメッセージを最終的な返答にしてください。

終わったら:
1. ユーザーへの最終的な返答を、実際に送るとおりに <RUN_DIR>/outputs/response.md に保存する。
2. <RUN_DIR>/outputs/notes.md に、行った手順（簡潔に）、読んだ Skill のファイル、Skill の指示のうち、わかりにくい・矛盾している・使えるツールでは実行できない・従わなかったもの（とその理由）を書く。
3. 5 行の要約を日本語で返す。
```

## 定期実行のシナリオ（scheduled-incremental）

上との違いだけを示す。

- 冒頭の「実際のユーザーを手伝うときの Claude」を「定期実行のタスク（その場に人はいない）を実行するときの Claude」にする。
- 「ユーザーのメッセージ:」を「タスクのメッセージ:」にする。
- 「この実行中、ユーザーは返信できません。…」を「この実行中、誰も返信できません。」にする。
- 終わったらの 1 を「最終的な出力メッセージ（定期実行のタスクとして報告する内容）を <RUN_DIR>/outputs/response.md に保存する。」にする。
