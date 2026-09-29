# Google Drive コネクタ（模擬）の使い方

この評価環境では、Google Drive コネクタを次のコマンドで呼び出す（実コネクタと同じツール名・引数・応答形式）。

```bash
<RUN_DIR>/drive TOOL_NAME '<JSON 引数>'
```

例:

```bash
<RUN_DIR>/drive search_files '{"query": "parentId = '\''root'\''", "excludeContentSnippets": true}'
```

1 回のコマンド実行 = コネクタの 1 回のツール呼び出しとして扱うこと。複数のツール呼び出しを 1 つのシェルスクリプトやループにまとめて実行してはいけない（実環境ではできないため）。コマンドの出力（JSON）がツールの応答。

以下は実コネクタのツール説明（原文の要約ではなく、そのまま）。

---

## search_files

Search for Drive files using a structured query (syntax: `query_term operator values`). Only terms in this list are supported.
Combine clauses with `and`, `or`, `not`, and parentheses. String values must be single-quoted; escape embedded quotes as `\'`.
Context window token management can be tuned via `snippetVerbosity` (default is `SnippetVerbosity.DETAILED`) or if only metadata is needed, use `excludeContentSnippets`.

Query terms & operators:

- `title` (ops: contains, =, !=) — file title
- `fullText` (ops: contains) — title or body text
- `mimeType` (ops: contains, =, !=) — MIME type
- `modifiedTime`, `viewedByMeTime`, `createdTime` (ops: `<=`, `<`, `=`, `!=`, `>`, `>=`). Use RFC 3339 UTC, e.g., `2012-06-04T12:00:00-08:00`.
- `parentId` (ops: `=`, `!=`). Use `'root'` for the user's "My Drive".
- `owner` (ops: `=`, `!=`). Use `'me'` for the requesting user.
- `sharedWithMe` (ops: `=`, `!=`). Values: `true` or `false`.

Use `next_page_token` to paginate. An empty response means no more results.

Parameters: `query` (string), `pageSize` (int), `pageToken` (string), `excludeContentSnippets` (bool), `snippetVerbosity` (`BRIEF` ≈1000 chars | `MEDIUM` ≈2500 | `DETAILED` ≈5000 | `MAX_ALLOWED`)

## list_recent_files

Find recent files for a user-specified sort order (`recency` default, `lastModified`, `lastModifiedByMe`). The default page size is 10. Utilize `next_page_token` to paginate.
Parameters: `orderBy`, `pageSize`, `pageToken`, `excludeContentSnippets`, `snippetVerbosity`

## get_file_metadata

Find general metadata about a user's Drive file. Parameters: `fileId` (required), `excludeContentSnippets`, `snippetVerbosity`

## read_file_content

Fetch a natural language representation of a known Drive file. `fileId` is required and must be an exact ID returned by a previous discovery tool. The file content may be incomplete for very large files. The text representation will change over time, so don't make assumptions about the particular format of the text returned by this tool.
Supported: Google Docs/Slides/Sheets, PDF, Word, Excel, PowerPoint, ODF, PNG, JPEG.
Parameters: `fileId` (required), `includeComments`

## download_file_content

Download the content of a Drive file as a base64 encoded string. For Google first-party types, `exportMimeType` selects the export type (defaults to plain text). If the user wants a natural language representation, use `read_file_content` instead.
Parameters: `fileId` (required), `exportMimeType`, `revisionId`

## update_file

Update the metadata of a Google Drive file (currently only title and parent_id are supported). If `parentId` is provided and the file has an existing parent, it will be replaced, resulting in a folder move.
Parameters: `fileId` (required), `title`, `parentId`

## create_file

Create or upload a file. Prefer `textContent` for text. When uploading content, `contentMimeType` is required. By default, supported content will be converted to Google first-party mime types; set `disableConversionToGoogleType` to true to keep the given type. Folders can be created by setting the mime type to `application/vnd.google-apps.folder`.
Parameters: `title` (required), `parentId`, `textContent`, `base64Content`, `contentMimeType`, `disableConversionToGoogleType`

## copy_file

Copy an existing file. Parameters: `fileId` (required), `title`, `parentId`

## trash_file

Move a file to the user's trash. It does not permanently delete the file. Parameters: `fileId` (required)

## get_file_permissions

List the permissions of a file. Parameters: `fileId` (required)
