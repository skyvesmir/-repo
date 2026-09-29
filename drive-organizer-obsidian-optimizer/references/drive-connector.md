# Google Drive コネクタの実測メモとクエリ集

2026-09 に Google Drive コネクタ（`search_files` などを持つもの）で確認した挙動。コネクタは更新されうるので、結果がこの記述と食い違ったら、実際の結果を優先する。

## 1. 返ってくる情報・返ってこない情報

`search_files`・`list_recent_files`・`get_file_metadata` は同じ項目を返す。

- **返る**: `id`, `title`, `mimeType`, `fileExtension`（Drive 外から来たファイル）, `fileSize`, `createdTime`, `modifiedTime`, `viewedByMeTime`, `owner`（メールアドレス）, `parentId`（1 つ）, `viewUrl`, `canAddChildren`, ときどき `description`
- **返らない**: フルパス、チェックサム、ゴミ箱に入っているかどうか、共有の概要、版の一覧、ショートカットの参照先

帰結:

- パスは `parentId` をたどって自分で組み立てる。`parentId = 'root'` で取った結果の `parentId` には、マイドライブの実際の ID が入る。
- 「バイト単位で同一」をメタデータだけで確かめる方法はない。
- `get_file_metadata` は検索結果以上の情報を返さない。
- 他人がオーナーのファイルやショートカット（`application/vnd.google-apps.shortcut`）も結果に混ざる。`owner` と `mimeType` で見分ける。
- Drive 外からアップロードしたファイルは、元の更新日時が `modifiedTime` に残り、`createdTime` はアップロード時刻になる。

## 2. 検索の挙動

- **pageSize**: 20 と 30 は指定どおりの件数が返った。50 や 100 では 5 件しか返らなかった。**30 を使う。** `nextPageToken` がなくなるか、空の応答で終わり。
- **スニペット**: 既定は `DETAILED`（約 5000 文字）。一覧取得では必ず `excludeContentSnippets: true` にする。先頭が必要なときは `snippetVerbosity: 'BRIEF'`（約 1000 文字）。
- **スニペットの中身**: ファイルの**先頭**からの抜粋（`fullText` の検索でも、ヒット箇所ではなく先頭）。表現は §3 と同じくエスケープされる。
- **`title contains`**: 日本語は文字列の途中にも一致する（`'最新'` が「…最新システム…」に一致）。英数字は語の前方一致に近い（`'protagonist'` が `01_protagonist.md` に一致）。**記号は無視される**（`'(1)'` は「1」を含む多数の名前に一致した）。
- **`fullText contains`**: タイトルと本文の両方に一致する。ヒットは候補であり、ヒットしないことは「含まれない」ことの証明にならない。
- 文字列は単引用符で囲み、名前に含まれる `'` は `\'` とエスケープする。
- 並び順は指定できない。新しい順が必要なら `list_recent_files` を使うが、こちらはクエリで絞れない。
- ゴミ箱内のファイルを除く条件は書けない。**ゴミ箱内のファイルが検索に出るかは未確認**（SKILL.md §6-2 の手順 4 で確かめ、状態ブロックの `trashed_in_search` に記録する）。

## 3. 本文の取得

- `read_file_content` は `text/markdown` も読めるが、**読み取り用の表現**で返る。
  - Markdown の記号がエスケープされる（`\#`, `\-`, `\*\*`, `\_`, `\[`, `\!`, `\<`, `\>`, `` \` ``, `\---`）。改行は `  \n` になる。絵文字などが文字化けすることがある。
  - 内容の理解と比較には使えるが、原文ではない。書き戻しや原文とのバイト比較に使わない。比べるときは両方を同じ方法で取る。
  - ログの状態ブロックを読み戻すときは、ID やパスに付いたバックスラッシュ（`\_` `\-`）を外す。Drive の ID には `_` や `-` が含まれる。
- `download_file_content` は原文を base64 で返す。長い base64 を頭の中で復号するのは誤りやすいので、小さなテキスト（目安 50KB 以下）で原文そのものが必要なときだけ使う。
- Google ドキュメント・スライド・スプレッドシート、PDF、Office 形式、画像は `read_file_content` で読める。取得する長さを指定する引数はない。
- 版の一覧を取るツールはない。

## 4. 書き込み系ツール

- `update_file`: 変更できるのは `title` と `parentId` だけ。`parentId` を指定すると移動になる。Markdown の改名では `title` に `.md` を含める。
- `trash_file`: ゴミ箱へ移すだけ。完全削除と復元のツールはない。
- `create_file`: `textContent` と `contentMimeType` で作成する。Markdown を `.md` のまま保存するには `disableConversionToGoogleType: true` を付ける。フォルダは MIME タイプ `application/vnd.google-apps.folder` で作る。作成後は戻り値の `mimeType` と `parentId` を確かめる。
- `copy_file`: 整理では使わない（重複を増やすため）。
- 本文を更新するツールはない。

## 5. クエリ集

```text
# マイドライブ直下（フォルダもファイルも）
parentId = 'root'

# 複数フォルダの子をまとめて（10〜20 フォルダずつ）。実行前の事前確認にも使う
parentId = 'FOLDER_A' or parentId = 'FOLDER_B' or parentId = 'FOLDER_C'

# 自分がオーナーのファイルだけ（結果の owner の値は find_candidates.py の --me に使える）
owner = 'me' and (parentId = 'FOLDER_A' or parentId = 'FOLDER_B')

# フォルダ内の Markdown の先頭（snippetVerbosity: 'BRIEF' と組み合わせる）
parentId = 'FOLDER_A' and (mimeType contains 'markdown' or title contains '.md')

# 特定の複数ファイル（名前で）
title = '企画書.docx' or title = '企画書 のコピー.docx'

# 被リンク候補（1 つの名前につき 1 回。結果の扱いは references/obsidian.md §6-1）
fullText contains 'シューニャ' and (mimeType contains 'markdown' or title contains '.md' or title contains '.canvas')

# 特徴的な一節で派生・転記を探す
fullText contains 'アクエラの街は、水の匂いより先に'

# 前回以降の変更（定期実行）
owner = 'me' and (modifiedTime > '2026-09-01T00:00:00Z' or createdTime > '2026-09-01T00:00:00Z')

# ネイティブ形式を除く（サイズ比較の対象を絞る）
not mimeType contains 'application/vnd.google-apps.'
```
