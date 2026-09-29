#!/usr/bin/env python3
"""Google Drive コネクタの模擬実装（評価用）。

実コネクタ（2026-09 時点の search_files などを持つもの）で観測した挙動をまねる:
- 返却フィールド: id, title, mimeType, fileExtension, fileSize, createdTime, modifiedTime,
  viewedByMeTime, owner, parentId, viewUrl, canAddChildren（パス・チェックサム・trashed は返らない）
- pageSize: 既定 10。40 を超える指定では 5 件しか返さない
- スニペット: 既定 DETAILED（約 5000 文字）、ファイル先頭からのエスケープ表現
- title contains: 日本語は部分一致、英数字は語の前方一致、記号は無視
- read_file_content: Markdown 記号をエスケープし、改行を「  \\n」にした表現
- download_file_content: 原文の base64
- update_file: title と parentId のみ
- 本文を更新するツールはない

使い方:
    python3 mockdrive.py --state STATE_DIR TOOL_NAME '{"json": "args"}'

STATE_DIR には fixture.json（初期状態のコピー）を置く。書き込み系の操作は STATE_DIR/fixture.json を更新し、
すべての呼び出しを STATE_DIR/calls.jsonl に記録する。
"""

import argparse
import base64
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

FOLDER = "application/vnd.google-apps.folder"
SHORTCUT = "application/vnd.google-apps.shortcut"
NATIVE = "application/vnd.google-apps."
TEXT_LIKE = ("text/", "application/json")
READABLE_NATIVE = (
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
)
READABLE_BINARY_TEXT = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
)
SNIPPET_LIMITS = {"BRIEF": 1000, "MEDIUM": 2500, "DETAILED": 5000, "MAX_ALLOWED": 10000, "UNSPECIFIED": 5000}
DEFAULT_PAGE = 10
MAX_PAGE = 40
OVER_MAX_PAGE = 5
DOWNLOAD_LIMIT = 1_000_000

CJK = re.compile(r"[぀-ヿ㐀-鿿豈-﫿ｦ-ﾟ]")


class ToolError(Exception):
    pass


# ---------------------------------------------------------------- 状態

class Drive:
    def __init__(self, state_dir):
        self.dir = Path(state_dir)
        self.path = self.dir / "fixture.json"
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.files = {f["id"]: f for f in self.data["files"]}
        self.me = self.data["me"]
        self.root = self.data["root_id"]

    def save(self):
        self.data["files"] = list(self.files.values())
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")

    def live(self):
        return [f for f in self.files.values() if not f.get("trashed")]

    def get(self, file_id):
        f = self.files.get(file_id)
        if not f or f.get("trashed"):
            raise ToolError(f"File not found: {file_id}")
        return f

    def now(self):
        base = datetime.fromisoformat(self.data["now"].replace("Z", "+00:00"))
        self.data["clock"] = self.data.get("clock", 0) + 1
        return (base + timedelta(seconds=self.data["clock"])).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def new_id(self, seed):
        self.data["counter"] = self.data.get("counter", 0) + 1
        return "1" + hashlib.sha1(f"new-{self.data['counter']}-{seed}".encode()).hexdigest()[:32]


def raw_bytes(f):
    if f.get("content") is not None and not f.get("binary"):
        return f["content"].encode("utf-8")
    key = f.get("content_key") or f["id"]
    size = int(f.get("size") or 0)
    out = bytearray()
    counter = 0
    while len(out) < min(size, DOWNLOAD_LIMIT + 1):
        out += hashlib.sha256(f"{key}-{counter}".encode()).digest()
        counter += 1
    return bytes(out[:size])


def file_size(f):
    if f["mimeType"] == FOLDER or f["mimeType"] == SHORTCUT:
        return None
    if f.get("size") is not None:
        return int(f["size"])
    if f.get("content") is not None:
        n = len(f["content"].encode("utf-8"))
        return n * 3 + 1024 if f["mimeType"].startswith(NATIVE) else n
    return 0


def extension(f):
    if f["mimeType"].startswith(NATIVE):
        return None
    m = re.search(r"\.([A-Za-z0-9]{1,8})$", f["title"])
    return m.group(1).lower() if m else ""


def view_url(f):
    if f["mimeType"] == FOLDER:
        return f"https://drive.google.com/drive/folders/{f['id']}"
    if f["mimeType"] == "application/vnd.google-apps.document":
        return f"https://docs.google.com/document/d/{f['id']}/edit?usp=drivesdk"
    return f"https://drive.google.com/file/d/{f['id']}/view?usp=drivesdk"


# ---------------------------------------------------------------- 表現

ESCAPE_ANYWHERE = set("\\#*_[]!<>`")


def escape_line(line):
    out = []
    for i, ch in enumerate(line):
        if ch in ESCAPE_ANYWHERE:
            out.append("\\" + ch)
        elif i == 0 and ch in "-=+":
            out.append("\\" + ch)
        else:
            out.append(ch)
    s = "".join(out)
    s = re.sub(r"^(\d+)\. ", r"\1\\. ", s)
    return s


def representation(text):
    return "  \n".join(escape_line(line) for line in text.split("\n"))


def readable_text(f):
    mime = f["mimeType"]
    if mime == FOLDER:
        raise ToolError("Cannot read content of a folder")
    if mime == SHORTCUT:
        raise ToolError("Cannot read content of a shortcut")
    if not f.get("binary"):
        return f.get("content") or ""
    if mime.startswith("image/"):
        return "[画像ファイル。テキストとして表現できる内容はありません]"
    if mime in READABLE_BINARY_TEXT:
        return f.get("text") or ""
    raise ToolError(f"Unsupported mime type for text representation: {mime}")


def indexed_text(f):
    if f["mimeType"] in (FOLDER, SHORTCUT):
        return ""
    return f.get("text") or "" if f.get("binary") else f.get("content") or ""


def snippet(f, verbosity):
    text = indexed_text(f)
    if not text:
        return None
    limit = SNIPPET_LIMITS.get(verbosity or "DETAILED", 5000)
    rep = representation(text)
    return rep if len(rep) <= limit else rep[:limit] + "..."


def meta(f, drive, with_snippet=False, verbosity=None):
    d = {"canAddChildren": f["mimeType"] == FOLDER and f.get("owner", drive.me) == drive.me}
    if with_snippet:
        s = snippet(f, verbosity)
        if s:
            d["contentSnippet"] = s
    d["createdTime"] = f["createdTime"]
    ext = extension(f)
    if ext is not None and f["mimeType"] != FOLDER:
        d["fileExtension"] = ext
    size = file_size(f)
    if size is not None:
        d["fileSize"] = str(size)
    d["id"] = f["id"]
    d["mimeType"] = f["mimeType"]
    d["modifiedTime"] = f["modifiedTime"]
    d["owner"] = f.get("owner", drive.me)
    d["parentId"] = f["parentId"]
    d["title"] = f["title"]
    d["viewUrl"] = view_url(f)
    if f.get("owner", drive.me) == drive.me:
        d["viewedByMeTime"] = f.get("viewedByMeTime", f["createdTime"])
    return d


# ---------------------------------------------------------------- クエリ

TOKEN = re.compile(r"\s*(?:(\()|(\))|('(?:\\'|[^'])*')|(!=|<=|>=|=|<|>)|([A-Za-z_]+))")
FIELDS = {"title", "fullText", "mimeType", "modifiedTime", "viewedByMeTime", "createdTime",
          "parentId", "owner", "sharedWithMe"}


def tokenize(q):
    pos, out = 0, []
    while pos < len(q):
        if q[pos:].strip() == "":
            break
        m = TOKEN.match(q, pos)
        if not m:
            raise ToolError(f"Invalid query near: {q[pos:pos + 20]!r}")
        pos = m.end()
        lp, rp, s, op, word = m.groups()
        if lp:
            out.append(("(", "("))
        elif rp:
            out.append((")", ")"))
        elif s:
            out.append(("str", s[1:-1].replace("\\'", "'")))
        elif op:
            out.append(("op", op))
        else:
            out.append(("word", word))
    return out


class Parser:
    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def parse(self):
        node = self.or_expr()
        if self.i != len(self.t):
            raise ToolError(f"Unexpected token: {self.peek()[1]}")
        return node

    def or_expr(self):
        node = self.and_expr()
        while self.peek() == ("word", "or"):
            self.take()
            node = ("or", node, self.and_expr())
        return node

    def and_expr(self):
        node = self.not_expr()
        while self.peek() == ("word", "and"):
            self.take()
            node = ("and", node, self.not_expr())
        return node

    def not_expr(self):
        if self.peek() == ("word", "not"):
            self.take()
            return ("not", self.not_expr())
        return self.primary()

    def primary(self):
        kind, val = self.take()
        if kind == "(":
            node = self.or_expr()
            if self.take()[0] != ")":
                raise ToolError("Missing closing parenthesis")
            return node
        if kind != "word" or val not in FIELDS:
            raise ToolError(f"Unsupported query term: {val}")
        field = val
        kind, op = self.take()
        if kind == "word" and op == "contains":
            op = "contains"
        elif kind != "op":
            raise ToolError(f"Expected operator after {field}")
        kind, value = self.take()
        if kind == "word" and value in ("true", "false"):
            value = value == "true"
        elif kind != "str":
            raise ToolError(f"Expected quoted value for {field}")
        return ("term", field, op, value)


def norm(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[\[\]()#*_!|<>{}`~^\"'.,:;/\\=+\-「」『』（）【】、。・：]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def ascii_tokens(text):
    return re.findall(r"[a-z]+|[0-9]+", text)


def contains(haystack, needle):
    h, n = norm(haystack), norm(needle)
    if not n:
        return False
    if CJK.search(n):
        return n.replace(" ", "") in h.replace(" ", "")
    htoks = ascii_tokens(h)
    return all(any(t.startswith(q) for t in htoks) for q in ascii_tokens(n))


def parse_time(v):
    return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(timezone.utc)


def compare(a, op, b):
    return {"=": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]


def evaluate(node, f, drive):
    kind = node[0]
    if kind == "and":
        return evaluate(node[1], f, drive) and evaluate(node[2], f, drive)
    if kind == "or":
        return evaluate(node[1], f, drive) or evaluate(node[2], f, drive)
    if kind == "not":
        return not evaluate(node[1], f, drive)
    _, field, op, value = node
    if field == "title":
        if op == "contains":
            return contains(f["title"], value)
        if op in ("=", "!="):
            return compare(f["title"], op, value)
        raise ToolError("title supports contains, =, !=")
    if field == "fullText":
        if op != "contains":
            raise ToolError("fullText supports contains only")
        return contains(f["title"] + " " + indexed_text(f), value)
    if field == "mimeType":
        if op == "contains":
            return value in f["mimeType"]
        return compare(f["mimeType"], op, value)
    if field in ("modifiedTime", "createdTime", "viewedByMeTime"):
        own = f.get(field) or (f["createdTime"] if field == "viewedByMeTime" else None)
        if own is None:
            return False
        return compare(parse_time(own), op, parse_time(value))
    if field == "parentId":
        target = drive.root if value == "root" else value
        return compare(f["parentId"], op, target)
    if field == "owner":
        target = drive.me if value == "me" else value
        return compare(f.get("owner", drive.me), op, target)
    if field == "sharedWithMe":
        shared = f.get("owner", drive.me) != drive.me
        return compare(shared, op, value)
    raise ToolError(f"Unsupported term {field}")


# ---------------------------------------------------------------- ページング

def page(items, args, drive, with_snippets, verbosity, key):
    size = args.get("pageSize") or DEFAULT_PAGE
    size = int(size)
    if size > MAX_PAGE:
        size = OVER_MAX_PAGE
    if size < 1:
        size = DEFAULT_PAGE
    start = 0
    token = args.get("pageToken")
    if token:
        m = re.match(r"^~!!~(\d+)~([0-9a-f]{8})$", token)
        if not m or m.group(2) != key:
            raise ToolError("Invalid page token")
        start = int(m.group(1))
    chunk = items[start:start + size]
    out = {"files": [meta(f, drive, with_snippets, verbosity) for f in chunk]}
    if start + size < len(items):
        out["nextPageToken"] = f"~!!~{start + size}~{key}"
    return out


# ---------------------------------------------------------------- ツール

def t_search_files(drive, args):
    query = args.get("query") or ""
    tree = Parser(tokenize(query)).parse() if query.strip() else None
    hits = [f for f in drive.live() if tree is None or evaluate(tree, f, drive)]
    hits.sort(key=lambda f: f["modifiedTime"], reverse=True)
    key = hashlib.md5(query.encode()).hexdigest()[:8]
    return page(hits, args, drive, not args.get("excludeContentSnippets"), args.get("snippetVerbosity"), key)


def t_list_recent_files(drive, args):
    order = args.get("orderBy") or "recency"
    items = drive.live()
    if order == "lastModifiedByMe":
        items = [f for f in items if f.get("owner", drive.me) == drive.me]
        items.sort(key=lambda f: f["modifiedTime"], reverse=True)
    elif order == "lastModified":
        items.sort(key=lambda f: f["modifiedTime"], reverse=True)
    else:
        items.sort(key=lambda f: max(f["modifiedTime"], f["createdTime"], f.get("viewedByMeTime", "")), reverse=True)
    key = hashlib.md5(("recent" + order).encode()).hexdigest()[:8]
    return page(items, args, drive, not args.get("excludeContentSnippets"), args.get("snippetVerbosity"), key)


def t_get_file_metadata(drive, args):
    f = drive.get(args["fileId"])
    return meta(f, drive, not args.get("excludeContentSnippets"), args.get("snippetVerbosity"))


def t_read_file_content(drive, args):
    f = drive.get(args["fileId"])
    text = readable_text(f)
    return {"fileContent": representation(text), "title": f["title"], "viewUrl": view_url(f)}


def t_download_file_content(drive, args):
    f = drive.get(args["fileId"])
    if f["mimeType"] == FOLDER:
        raise ToolError("Cannot download a folder")
    data = raw_bytes(f)
    if len(data) > DOWNLOAD_LIMIT:
        raise ToolError(f"File too large to return inline ({len(data)} bytes)")
    return {"content": base64.b64encode(data).decode(), "id": f["id"], "mimeType": f["mimeType"], "title": f["title"]}


def require_owner(drive, f):
    if f.get("owner", drive.me) != drive.me:
        raise ToolError("The user does not have sufficient permissions for this file.")


def t_update_file(drive, args):
    f = drive.get(args["fileId"])
    require_owner(drive, f)
    if "title" not in args and "parentId" not in args:
        raise ToolError("Nothing to update")
    if "title" in args:
        if not args["title"]:
            raise ToolError("title must not be empty")
        f["title"] = args["title"]
    if "parentId" in args:
        target = drive.root if args["parentId"] in ("root", drive.root) else args["parentId"]
        if not target:
            raise ToolError("parentId must not be empty")
        if target != drive.root and drive.get(target)["mimeType"] != FOLDER:
            raise ToolError("parentId must be a folder")
        f["parentId"] = target
    drive.save()
    return meta(f, drive)


def t_create_file(drive, args):
    title = args.get("title")
    if not title:
        raise ToolError("title is required")
    mime = args.get("contentMimeType") or args.get("mimeType")
    parent = args.get("parentId") or drive.root
    if parent != drive.root:
        p = drive.get(parent)
        if p["mimeType"] != FOLDER:
            raise ToolError("parentId must be a folder")
    now = drive.now()
    f = {"id": drive.new_id(title), "title": title, "parentId": parent, "createdTime": now,
         "modifiedTime": now, "owner": drive.me}
    if mime == FOLDER:
        f["mimeType"] = FOLDER
    elif args.get("textContent") is not None or args.get("base64Content") or args.get("content"):
        if not mime:
            raise ToolError("contentMimeType is required when content is provided")
        if args.get("textContent") is not None:
            text = args["textContent"]
        else:
            text = base64.b64decode(args.get("base64Content") or args.get("content")).decode("utf-8", "replace")
        f["content"] = text
        convert = not args.get("disableConversionToGoogleType")
        if convert and mime in ("text/plain", "text/markdown", "text/html"):
            f["mimeType"] = "application/vnd.google-apps.document"
        else:
            f["mimeType"] = mime
    else:
        f["mimeType"] = mime or "application/vnd.google-apps.document"
        f["content"] = ""
    drive.files[f["id"]] = f
    drive.save()
    return meta(f, drive)


def t_copy_file(drive, args):
    src = drive.get(args["fileId"])
    now = drive.now()
    f = dict(src)
    f.update({"id": drive.new_id(src["id"]), "title": args.get("title") or f"Copy of {src['title']}",
              "parentId": args.get("parentId") or src["parentId"], "createdTime": now,
              "modifiedTime": now, "owner": drive.me})
    drive.files[f["id"]] = f
    drive.save()
    return meta(f, drive)


def t_trash_file(drive, args):
    f = drive.get(args["fileId"])
    require_owner(drive, f)
    f["trashed"] = True
    drive.save()
    return {}


def t_get_file_permissions(drive, args):
    f = drive.get(args["fileId"])
    perms = [{"role": "owner", "type": "user", "emailAddress": f.get("owner", drive.me)}]
    perms += f.get("permissions", [])
    return {"permissions": perms}


TOOLS = {
    "search_files": t_search_files,
    "list_recent_files": t_list_recent_files,
    "get_file_metadata": t_get_file_metadata,
    "read_file_content": t_read_file_content,
    "download_file_content": t_download_file_content,
    "update_file": t_update_file,
    "create_file": t_create_file,
    "copy_file": t_copy_file,
    "trash_file": t_trash_file,
    "get_file_permissions": t_get_file_permissions,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("tool")
    ap.add_argument("args", nargs="?", default="{}")
    ns = ap.parse_args()
    drive = Drive(ns.state)
    log = Path(ns.state) / "calls.jsonl"
    try:
        args = json.loads(ns.args)
        if ns.tool not in TOOLS:
            raise ToolError(f"Unknown tool: {ns.tool}. Available: {', '.join(TOOLS)}")
        result = TOOLS[ns.tool](drive, args)
        text = json.dumps(result, ensure_ascii=False)
        ok, err = True, None
    except (ToolError, KeyError, json.JSONDecodeError, ValueError) as e:
        text = json.dumps({"error": str(e) if not isinstance(e, KeyError) else f"Missing argument: {e}"},
                          ensure_ascii=False)
        ok, err = False, text
        args = locals().get("args", ns.args)
    ids = re.findall(r'"id": "([^"]+)"', text) if ok else []
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"tool": ns.tool, "args": args, "ok": ok, "error": err,
                             "response_chars": len(text), "ids": ids}, ensure_ascii=False) + "\n")
    print(text)


if __name__ == "__main__":
    main()
