# Google Drive コネクタの実測メモとクエリ集

2026-09 に Google Drive コネクタ（`search_files` などを持つもの）で確認した挙動。コネクタは更新されうるので、結果が下の記述と食い違ったら、実際の結果を優先して判断を修正する。

## 目次

1. 返ってくる情報・返ってこない情報
2. 検索の挙動
3. 本文の取得
4. 書き込み系ツール
5. クエリ集
6. インベントリ TSV の形式

---

## 1. 返ってくる情報・返ってこない情報

`search_files`・`list_recent_files`・`get_file_metadata` は同じ項目を返す。

- **返る**: `id`, `title`, `mimeType`, `fileExtension`（Drive 外から来たファイル）, `fileSize`, `createdTime`, `modifiedTime`, `viewedByMeTime`, `owner`（メールアドレス）, `parentId`（1 つ）, `viewUrl`, `canAddChildren`（フォルダへの書き込み可否）, ときどき `description`
- **返らない**: フルパス、MD5 などのチェックサム、ゴミ箱に入っているかどうか、共有の概要、版の一覧

帰結:

- パスは `parentId` をたどって自分で組み立てる。フォルダ ID → 名前・親の対応表を Phase 1 で作っておく。`parentId = 'root'` で取得した結果の `parentId` には、`'root'` ではなくマイドライブの実際の ID が入る。これをマイドライブの ID として対応表に登録する。
- 「バイト単位で同一」をメタデータだけで確かめる方法はない。同一サイズ・同一更新日時は強い手がかりだが、確定には本文比較が要る。
- `get_file_metadata` は検索結果以上の情報を返さない。検索で取得済みのファイルに対して呼ぶ意味はない。
- 他人がオーナーのファイル（共有されたもの、自分のフォルダに他人が置いたもの）やショートカット（`application/vnd.google-apps.shortcut`）も結果に混ざる。`owner` と `mimeType` で見分ける。
- Drive 外からアップロードしたファイルは、元の更新日時が `modifiedTime` に残り、`createdTime` はアップロード時刻になる。別フォルダに同名・同サイズ・同じ `modifiedTime` のファイルがあれば、同じ元ファイルを複数回アップロードした可能性が高い。

## 2. 検索の挙動

- **pageSize**: 20 と 30 は指定どおりの件数が返った。50 や 100 を指定すると 5 件しか返らなかった。**30 を使う。** 指定より大幅に少ない件数と `nextPageToken` が返ったら、上限を超えている可能性があるので値を下げる。`nextPageToken` がなくなるか、空の応答で終わり。
- **スニペット**: 既定は `DETAILED`（約 5000 文字）。一覧取得では必ず `excludeContentSnippets: true` にする。先頭部分が必要なときは `snippetVerbosity: 'BRIEF'`（約 1000 文字）。
- **スニペットの中身**: ファイルの**先頭**からの抜粋だった（`fullText` の検索でも、ヒット箇所ではなく先頭）。Markdown の Frontmatter の確認に使える。表現は §3 と同じくエスケープされる。
- **`title contains`**: 日本語は文字列の途中にも一致した（例: `'最新'` が「…最新システム…」に一致）。英数字は語の前方一致に近い（`'protagonist'` が `01_protagonist.md` に一致）。**記号は無視される**（`'(1)'` は「1」を含む多数の名前に一致した）。コピー番号などの記号の判定は、取得済みの一覧に対して行う。
- **`fullText contains`**: Markdown の本文にも一致した。ヒットは候補であり、ヒットしないことは「含まれない」ことの証明にならない。
- 文字列は単引用符で囲み、名前に含まれる `'` は `\'` とエスケープする。
- 並び順は指定できない（`search_files` に並び替えの引数はない）。新しい順が必要なら `list_recent_files`（`orderBy: lastModified` など）を使うが、こちらはクエリで絞れない。
- ゴミ箱内のファイルを除く条件はクエリに書けない。

## 3. 本文の取得

- `read_file_content` は、ツール説明の対応形式に載っていない `text/markdown` も読めた。ただし**読み取り用の表現**で返る。
  - Markdown の記号がバックスラッシュでエスケープされる: `\#`, `\-`, `\*\*`, `\_`, `\[`, `\!`, `\<`, `\>`, `` \` ``, `\---`
  - 改行が `  \n`（行末に空白 2 つ）になる
  - 絵文字などが文字化けすることがある
  - この表現は将来変わりうる（ツール説明にもそう書かれている）
  - → 内容の理解と比較には使えるが、原文ではない。書き戻しや、原文とのバイト比較に使わない。比較するときは両方を同じ方法で取得する。
- `download_file_content` は原文を base64 で返す。長い日本語の base64 を頭の中で復号するのは誤りやすいので、原文そのものが必要な場面（ほぼない）以外では使わない。
- Google ドキュメント・スライド・スプレッドシート、PDF、Office 形式、画像は `read_file_content` で読める。画像は本文比較の対象にしない。
- 版の一覧を取るツールはない（`download_file_content` の `revisionId` は、ID を知っていても一覧が取れないので使えない）。

## 4. 書き込み系ツール

- `update_file`: 変更できるのは `title` と `parentId` だけ。`parentId` を指定すると親が置き換わる（= 移動）。Markdown の改名では `title` に `.md` を含める。
- `trash_file`: ゴミ箱へ移すだけ。完全削除と復元のツールはない。
- `create_file`: `textContent` と `contentMimeType` で作成する。Markdown を `.md` のまま保存するには `disableConversionToGoogleType: true` を付ける（付けないと Google ドキュメントに変換されうる）。フォルダは MIME タイプ `application/vnd.google-apps.folder` で作成する（ツール説明による）。作成後は戻り値の `mimeType` と `parentId` を確かめる。
- `copy_file`: 整理では基本的に使わない（重複を増やすため）。
- 本文を更新するツールはない。

## 5. クエリ集

```text
# マイドライブ直下（フォルダもファイルも）
parentId = 'root'

# 複数フォルダの子をまとめて（10〜20 フォルダずつ）
parentId = 'FOLDER_A' or parentId = 'FOLDER_B' or parentId = 'FOLDER_C'

# 自分がオーナーのファイルだけ
owner = 'me' and (parentId = 'FOLDER_A' or parentId = 'FOLDER_B')

# フォルダ内の Markdown の先頭部分（snippetVerbosity: 'BRIEF' と組み合わせる）
parentId = 'FOLDER_A' and mimeType = 'text/markdown'

# 特定の複数ファイル（名前で）
title = '企画書.docx' or title = '企画書 のコピー.docx'

# 被リンク候補（Vault 内の Markdown に絞るのは、結果の parentId で行う）
fullText contains 'シューニャ' and mimeType = 'text/markdown'

# 特徴的な一節で派生・転記を探す
fullText contains 'アクエラの街は、水の匂いより先に'

# 前回以降の変更（定期実行）
owner = 'me' and (modifiedTime > '2026-09-01T00:00:00Z' or createdTime > '2026-09-01T00:00:00Z')

# ネイティブ形式を除く（サイズ比較の対象を絞る）
not mimeType contains 'application/vnd.google-apps.'
```

## 6. インベントリ TSV の形式

`scripts/find_candidates.py` の入力。1 行目はヘッダー、タブ区切り。

| 列 | 必須 | 内容 |
|---|---|---|
| `id` | ○ | ファイル ID（検索結果からそのまま写す） |
| `title` | ○ | タイトル（拡張子込み） |
| `mimeType` | ○ | MIME タイプ |
| `size` | ○ | `fileSize`（なければ空） |
| `modifiedTime` | ○ | 更新日時 |
| `parentId` | ○ | 親フォルダ ID |
| `createdTime` | | 作成日時 |
| `path` | | 組み立てたパス（あれば出力が読みやすくなる） |
| `owner` | | オーナー（`--me` と組み合わせて他人のファイルに印を付ける） |

```bash
python3 scripts/find_candidates.py inventory.tsv --me you@example.com > candidates.md
```

ID を写し間違えると、実行時に別のファイルを指すおそれがある。実行前の事前確認（SKILL.md §6-2）で、ID から取得したタイトルと親が整理案と一致することを必ず確かめる。
