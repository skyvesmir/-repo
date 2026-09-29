#!/usr/bin/env python3
"""評価用の模擬 Drive（fixture）を生成する。

出力:
    fixtures/creative.json   ケース A〜E, G〜J を含む創作用 Drive（約 90 件）
    fixtures/large.json      ケース F: 約 1,500 件。重複・デコイを埋め込む
    fixtures/scheduled.json  creative + 前回ログ + その後の変化（定期実行）
    fixtures/execution.json  creative + 整理案作成後の変化（承認後の実行）
    fixtures/answer_keys.json  採点用の正解（ID）
"""

import copy
import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "fixtures"
ME = "writer@example.com"
NOW = "2026-09-29T09:00:00Z"

FOLDER = "application/vnd.google-apps.folder"
GDOC = "application/vnd.google-apps.document"
GSHEET = "application/vnd.google-apps.spreadsheet"
SHORTCUT = "application/vnd.google-apps.shortcut"
MD = "text/markdown"
PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
JPG = "image/jpeg"
PNG = "image/png"
JSON = "application/json"
JS = "text/javascript"
HTML = "text/html"


def fid(path):
    return "1" + hashlib.sha1(("fixture:" + path).encode()).hexdigest()[:32]


class Builder:
    def __init__(self, root_id):
        self.root_id = root_id
        self.files = []
        self.by_path = {"": root_id}

    def folder(self, path, created="2026-01-10T09:00:00Z"):
        parent_path, _, name = path.rpartition("/")
        f = {"id": fid(path), "title": name, "mimeType": FOLDER, "parentId": self.by_path[parent_path],
             "createdTime": created, "modifiedTime": created, "owner": ME}
        self.files.append(f)
        self.by_path[path] = f["id"]
        return f

    def file(self, path, mime, created, modified, content=None, *, size=None, binary=False, text=None,
             content_key=None, owner=ME, permissions=None):
        parent_path, _, name = path.rpartition("/")
        f = {"id": fid(path), "title": name, "mimeType": mime, "parentId": self.by_path[parent_path],
             "createdTime": created, "modifiedTime": modified, "owner": owner}
        if binary:
            f["binary"] = True
            f["size"] = size
            if text is not None:
                f["text"] = text
            if content_key:
                f["content_key"] = content_key
        else:
            f["content"] = content if content is not None else ""
            if size is not None:
                f["size"] = size
        if permissions:
            f["permissions"] = permissions
        self.files.append(f)
        self.by_path[path] = f["id"]
        return f

    def fixture(self, extra=None):
        data = {"me": ME, "root_id": self.root_id, "now": NOW, "files": self.files}
        if extra:
            data.update(extra)
        return data


# ======================================================================== creative

SHUNYA = """---
type: character
tags:
  - 人物
  - 主要
aliases:
  - Shunya
---
# シューニャ

![[シューニャ_立ち絵.png]]

- 年齢: 17歳
- 出身: 北の鉱山町ノルデ
- 役割: 主人公。晶の記憶を聴く「聴律」の使い手

## 性格
無口だが観察が細かい。一度聴いた音を忘れない。

## 物語上の役割
父の死の真相を追い、静守会の隠蔽に迫る。能力の詳細は [[シューニャ設定]] を参照。

## 関係
- [[キャラ_カルタ]]とは第2章で出会う。
- [[ペトロス]]は旅の導き手。
"""

SHUNYA_OLD = """# シューニャ

- 年齢: 16歳
- 出身: 北の鉱山町ノルデ
- 役割: 主人公

## 性格
無口だが観察が細かい。
"""

SHUNYA_SETTING = """---
type: setting
tags:
  - 設定
  - 能力
---
# シューニャ設定（聴律の詳細）

[[シューニャ]] の能力「聴律」に関する設定メモ。人物像は人物ノートにまとめる。

## 発動条件
1. 素手で晶に触れる
2. 呼吸と鼓動を晶の律に合わせる

## 代償
再生のたびに晶の内側の罅が進む。強い記憶ほど晶が砕けやすい。

## 未決事項
- 聴律が遺伝するかどうか（現状は「しない」で進める）
"""

KARUTA = """# カルタ

- 元盗掘屋。地図読みの名人
- 年齢: 24歳
- 負い目: 売った地図が原因で坑道事故が起きた疑いを抱えている（第11章で自己開示）

第2章でシューニャと出会い、以後の旅に同行する。
"""

PETROS = """---
tag: 人物
Type: Character
---
# ペトロス

崖の番人を辞めて旅に同行した老人。シューニャたちの導き手。

- 年齢: 68歳
- 得意: 古い坑道図の読解
"""

MORA = """---
type: character
tags:
  - 人物
---
# モーラ

目録を焼いた火事の夜、告発せず沈黙を選んだ元書記。クラウスと鏡合わせになる「小さな隠蔽者」。
"""

WORLD = """---
type: setting
tags:
  - 設定
---
# 世界観

![[Pasted image 20240501123456.png]]

## 星脈
大陸の地下を走る結晶の鉱脈。晶は強い震えを記憶する。

## 勢力
- 教会: 遺物の認可を独占する
- 静守会: 千年紀の記録を隠蔽する機関
- 商会連合: 遺物市を仕切る

## 地理
北の鉱山町ノルデ、運河の街アクエラ、南の聖都ルーメン。
"""

WORLD_UPDATED = WORLD + """
## 歴史
千年紀の大崩落で星脈の三割が失われた。静守会はその原因を公式史から消している。
"""

RITSUJUTSU = """---
type: setting
tags:
  - 設定
---
# 晶律（しょうりつ）

本作の魔法体系。晶に律を合わせて力を引き出す技術の総称。

初期稿では「律術」と呼んでいたが、第2稿から「晶律」に改めた。旧称の「律術」は、作中の古文書と第03章の引用部分でのみ使う。

## 分類
- 聴律: 晶の記憶を聴く（シューニャのみ）
- 鳴律: 晶を震わせて音を出す
- 鎮律: 共振を鎮める
"""

GLOSSARY = """---
type: reference
tags:
  - 設定
  - 用語
---
# 用語集

| 用語 | 読み | 意味 |
|---|---|---|
| 晶 | しょう | 星脈から採れる結晶 |
| 晶律 | しょうりつ | 魔法体系（旧称: 律術） |
| 軋み鳴き | きしみなき | 坑道が崩れる前の音 |
"""

CH1 = """---
type: chapter
tags:
  - 本文
---
# 第01章 沈黙の夜の呼び名

北の山あいの町ノルデに、秋は音から訪れる。

[[シューニャ]]は、その朝も第三坑の奥にいた。灯り晶のほのかな光が坑道の壁を照らしている。

（本文続く。舞台設定は [[世界観]] を参照）
"""

CH2 = """---
type: chapter
tags:
  - 本文
---
# 第02章 水の街の地図屋

アクエラの街は、水の匂いより先に、音で分かった。

裏路地の戸板の店で、[[シューニャ]]は一人の地図屋に出会う。[[キャラ_カルタ]]と名乗ったその若者は、坑道図を一目見るなり眉をひそめた。
"""

CH3 = """---
type: chapter
tags:
  - 本文
---
# 第03章 古文書の律

古文書にはこうあった。「[[律術]]を修めし者、晶の声を畏れよ」。

[[モーラ]]はその一節を指でなぞり、黙り込んだ。
"""

CH4 = """---
type: chapter
tags:
  - 本文
---
# 第04章 遺物市の裏

[[キャラ_カルタ]]は戸板の裏で静守会の使いと目を合わせ、すぐに逸らした。

[[ペトロス]]だけが、その一瞬を見ていた。
"""

UNTITLED_MEMO = """第4章のアイデア

- 遺物市の裏で静守会の使いと接触する
- ペトロスが古い坑道図の誤りに気づく
- 章の終わりでカルタの負い目を匂わせる
"""

MEETING_MEMO = """2024年5月3日 編集者との打ち合わせ

- 第1部の締切は8月末
- 用語集を巻末に付ける
- 「律術」→「晶律」への改名はOK
"""

TEMPLATE = """---
type: character
tags:
  - 人物
created: <% tp.date.now("YYYY-MM-DD") %>
---
# <% tp.file.title %>

- 年齢:
- 出身:
- 役割:
"""

DAILY = """# 2024-05-01

- 第1章の冒頭を書き直した
- 世界観の地図を描いた（Pasted image として貼り付け）
"""

REFS = """参考文献

- 『鉱物の科学』第3版
- 『音響学入門』
- 『坑道の歴史と技術』
- 論文: 圧電効果と結晶構造
"""

FRAGMENTS = """・青い塔の話（別作品？）
・晶が歌う設定。六炎で使うかは未定
・タイトル候補:『沈黙の地図』
"""

NEW_CHARA = """---
type: character
tags:
  - 人物
---
# イェレナ

鐘守衆の若い見習い。静守会の命令に疑問を抱き始めている。
"""

MS_HEAD = "六炎 第1部\n\n"
MS_A = """第一章 沈黙の夜

北の山あいの町ノルデに、秋は音から訪れる。白樺の梢が乾いた風に鳴り、選鉱場の水車が氷の膜を割って軋む。
シューニャは第三坑の奥で、露頭に指を添えた。石は低く唸っていた。途切れない唸りだった。
親方のガランは何も訊かずに頷き、その日の採掘をやめさせた。
"""
MS_A_REVISED = """第一章 沈黙の夜

北の山あいの町ノルデに、秋は音から訪れる。白樺の梢が乾いた風に鳴り、選鉱場の水車が氷の膜を割って軋み、坑道の入り口の鈴が冷気に揺れる。
シューニャは第三坑の奥で、素手の指を露頭に添えた。石は低く、途切れずに唸っていた。
親方のガランは太い眉を寄せ、何も訊かずに頷いた。十六の少年の言葉ひとつで、その日の段取りが変わった。
"""
MS_B = """
第二章 水の街の地図屋

アクエラの街は、水の匂いより先に、音で分かった。荷揚げの掛け声、艀のぶつかる鈍い音、水門の軋み。
裏路地の戸板の店で、シューニャはカルタと名乗る地図屋に出会う。
"""
MS_C = """
第三章 古文書の律

教会の書庫で、モーラは古文書の一節を指でなぞった。「律術を修めし者、晶の声を畏れよ」。
その夜、書庫の目録が一冊だけ消えていた。
"""
SYNOPSIS = """六炎 第1部 あらすじ

鉱山町ノルデの少年シューニャは、晶の記憶を聴く力を持つ。
第一章で崩落の予兆を聴き分け、第二章で運河の街アクエラの地図屋カルタと出会う。
第三章では教会の書庫で古文書の一節が見つかり、目録が一冊消える。
"""
MINUTES_0412 = """定例会議 2024-04-12

出席: 編集部 田中、著者
- 第1部の構成を確認した
- 用語集の要否は次回までに検討
- 次回: 4月26日
"""
MINUTES_0308 = """定例会議 2024-03-08

出席: 編集部 田中、著者
- 企画の方向性を確認した
- 次回: 3月22日
"""
MINUTES_0322 = """定例会議 2024-03-22

出席: 編集部 田中、著者
- 主人公の年齢を17歳に変更
- 次回: 4月12日
"""


def build_creative(world_content=WORLD, world_modified="2026-07-10T11:20:00Z"):
    b = Builder("0AROOTcreativeFixture000000000000")
    t = "2026-05-02T10:00:00Z"
    for p in ["創作", "創作/Obsidian", "創作/Obsidian/.obsidian", "創作/Obsidian/人物", "創作/Obsidian/設定",
              "創作/Obsidian/章", "創作/Obsidian/メモ", "創作/Obsidian/添付", "創作/Obsidian/Templates",
              "創作/Obsidian/Daily", "創作/原稿", "創作/資料", "未整理", "議事録", "写真", "tool-app",
              "tool-app/src", "tool-app/node_modules"]:
        b.folder(p, t)

    ob = "創作/Obsidian"
    b.file(f"{ob}/.obsidian/app.json", JSON, t, "2026-07-01T09:00:00Z",
           '{"alwaysUpdateLinks": true, "newLinkFormat": "shortest", "attachmentFolderPath": "添付"}')
    b.file(f"{ob}/.obsidian/daily-notes.json", JSON, t, t, '{"folder": "Daily", "format": "YYYY-MM-DD"}')
    b.file(f"{ob}/.obsidian/templates.json", JSON, t, t, '{"folder": "Templates"}')
    b.file(f"{ob}/.obsidian/workspace.json", JSON, t, "2026-09-20T09:00:00Z", '{"main": {"id": "a1b2"}}' * 40)

    b.file(f"{ob}/人物/シューニャ.md", MD, "2026-05-03T09:00:00Z", "2026-07-02T13:00:00Z", SHUNYA)
    b.file(f"{ob}/人物/シューニャ設定.md", MD, "2026-05-04T09:00:00Z", "2026-06-11T08:00:00Z", SHUNYA_SETTING)
    b.file(f"{ob}/人物/キャラ_カルタ.md", MD, "2026-05-05T09:00:00Z", "2026-06-12T08:00:00Z", KARUTA)
    b.file(f"{ob}/人物/ペトロス.md", MD, "2026-05-06T09:00:00Z", "2026-06-13T08:00:00Z", PETROS)
    b.file(f"{ob}/人物/モーラ.md", MD, "2026-05-07T09:00:00Z", "2026-06-14T08:00:00Z", MORA)
    b.file(f"{ob}/設定/世界観.md", MD, "2026-05-08T09:00:00Z", world_modified, world_content)
    b.file(f"{ob}/設定/律術.md", MD, "2026-05-09T09:00:00Z", "2026-06-20T08:00:00Z", RITSUJUTSU)
    b.file(f"{ob}/設定/用語集.md", MD, "2026-05-10T09:00:00Z", "2026-06-21T08:00:00Z", GLOSSARY)
    b.file(f"{ob}/章/第01章.md", MD, "2026-05-11T09:00:00Z", "2026-06-25T08:00:00Z", CH1)
    b.file(f"{ob}/章/第02章.md", MD, "2026-05-12T09:00:00Z", "2026-06-28T08:00:00Z", CH2)
    b.file(f"{ob}/章/第03章.md", MD, "2026-05-13T09:00:00Z", "2026-07-01T08:00:00Z", CH3)
    b.file(f"{ob}/メモ/無題.md", MD, "2026-05-14T09:00:00Z", "2026-05-14T09:30:00Z", UNTITLED_MEMO)
    b.file(f"{ob}/メモ/2024-5-3 打ち合わせ.md", MD, "2026-05-15T09:00:00Z", "2026-05-15T09:00:00Z", MEETING_MEMO)
    b.file(f"{ob}/添付/シューニャ_立ち絵.png", PNG, "2026-05-03T09:10:00Z", "2026-05-03T09:10:00Z",
           binary=True, size=480_000, content_key="portrait")
    b.file(f"{ob}/添付/Pasted image 20240501123456.png", PNG, "2026-05-08T09:10:00Z", "2026-05-08T09:10:00Z",
           binary=True, size=210_000, content_key="map")
    b.file(f"{ob}/Templates/人物テンプレート.md", MD, "2026-05-02T11:00:00Z", "2026-05-02T11:00:00Z", TEMPLATE)
    b.file(f"{ob}/Daily/2024-05-01.md", MD, "2026-05-02T12:00:00Z", "2026-05-02T12:00:00Z", DAILY)

    ms = "創作/原稿"
    b.file(f"{ms}/六炎_第1部_最終版", GDOC, "2026-05-20T09:00:00Z", "2026-06-01T10:00:00Z", MS_HEAD + MS_A + MS_B)
    b.file(f"{ms}/六炎_第1部_最終版2", GDOC, "2026-06-02T09:00:00Z", "2026-06-20T10:00:00Z",
           MS_HEAD + MS_A + MS_B + MS_C)
    b.file(f"{ms}/六炎_第1部_最新版", GDOC, "2026-06-03T09:00:00Z", "2026-07-05T10:00:00Z",
           MS_HEAD + MS_A_REVISED + MS_B)
    b.file(f"{ms}/六炎_あらすじ", GDOC, "2026-06-21T09:00:00Z", "2026-06-21T12:00:00Z", SYNOPSIS)
    b.file(f"{ms}/六炎_第1部 へのショートカット", SHORTCUT, "2026-06-22T09:00:00Z", "2026-06-22T09:00:00Z", "")

    rs = "創作/資料"
    b.file(f"{rs}/参考文献メモ.md", MD, "2026-04-01T09:00:00Z", "2026-04-01T09:00:00Z", REFS)
    zukan_text = "鉱物図鑑（スキャン）\n石英、長石、雲母、方解石の結晶構造と産地。\n"
    b.file(f"{rs}/鉱物図鑑.pdf", PDF, "2026-03-11T09:00:00Z", "2026-03-10T10:00:00Z", binary=True,
           size=2_400_000, text=zukan_text, content_key="zukan")
    b.file(f"{rs}/鉱物図鑑 (1).pdf", PDF, "2026-04-18T09:00:00Z", "2026-03-10T10:00:00Z", binary=True,
           size=2_400_000, text=zukan_text, content_key="zukan")
    b.file(f"{rs}/鉱物図鑑_圧縮版.pdf", PDF, "2026-04-19T09:00:00Z", "2026-04-19T08:00:00Z", binary=True,
           size=800_000, text=zukan_text, content_key="zukan-small")

    un = "未整理"
    b.file(f"{un}/世界観.md", MD, "2026-08-01T09:00:00Z", "2026-07-10T11:20:00Z", WORLD)
    b.file(f"{un}/シューニャ.md", MD, "2026-08-01T09:01:00Z", "2026-04-02T08:00:00Z", SHUNYA_OLD)
    kikaku = "企画書\n\n作品名: 六炎\nジャンル: ファンタジー\n想定読者: 中高生〜大人\n概要: 晶の記憶を聴く少年の旅。\n"
    b.file(f"{un}/企画書.docx", DOCX, "2026-02-11T09:00:00Z", "2026-02-10T18:00:00Z", binary=True,
           size=52_000, text=kikaku, content_key="kikaku")
    b.file(f"{un}/企画書 のコピー.docx", DOCX, "2026-02-12T09:00:00Z", "2026-02-10T18:00:00Z", binary=True,
           size=52_000, text=kikaku, content_key="kikaku",
           permissions=[{"role": "reader", "type": "user", "emailAddress": "editor@publisher.example"}])
    b.file(f"{un}/議事録_0412", GDOC, "2024-04-12T10:00:00Z", "2024-04-12T12:00:00Z", MINUTES_0412)
    b.file(f"{un}/2024-04-12_定例会議", GDOC, "2024-04-13T10:00:00Z", "2024-04-13T10:05:00Z", MINUTES_0412)
    b.file(f"{un}/無題のドキュメント", GDOC, "2026-09-27T10:52:38Z", "2026-09-27T10:52:42Z", "")
    b.file(f"{un}/IMG_0001.jpg", JPG, "2026-08-02T09:00:00Z", "2026-08-01T15:00:00Z", binary=True,
           size=3_100_000, content_key="img0001")
    b.file(f"{un}/アイデア断片.md", MD, "2026-08-03T09:00:00Z", "2026-08-03T09:00:00Z", FRAGMENTS)

    b.file("議事録/2024-03-08_定例会議", GDOC, "2024-03-08T10:00:00Z", "2024-03-08T12:00:00Z", MINUTES_0308)
    b.file("議事録/2024-03-22_定例会議", GDOC, "2024-03-22T10:00:00Z", "2024-03-22T12:00:00Z", MINUTES_0322)

    for i in range(1, 6):
        b.file(f"写真/IMG_100{i}.jpg", JPG, f"2026-07-0{i}T09:00:00Z", f"2026-06-2{i}T15:00:00Z", binary=True,
               size=2_000_000 + i * 1111, content_key=f"img100{i}")
    b.file("写真/IMG_1003 (1).jpg", JPG, "2026-07-20T09:00:00Z", "2026-06-23T15:00:00Z", binary=True,
           size=2_000_000 + 3 * 1111, content_key="img1003")

    b.file("tool-app/package.json", JSON, t, t, '{"name": "tool-app", "version": "1.0.0"}')
    b.file("tool-app/README.md", MD, t, t, "# tool-app\n\n小さな変換ツール。\n")
    b.file("tool-app/src/index.js", JS, t, t, "import { run } from './util.js';\nrun();\n")
    b.file("tool-app/src/util.js", JS, t, t, "export function run() { return 1; }\n")
    for pkg in ["lodash", "semver", "chalk", "commander", "minimist"]:
        b.folder(f"tool-app/node_modules/{pkg}", t)
        b.file(f"tool-app/node_modules/{pkg}/README.md", MD, t, "2026-06-05T09:40:43Z", f"# {pkg}\n\nnpm package.\n")
        b.file(f"tool-app/node_modules/{pkg}/package.json", JSON, t, "2026-06-05T09:40:43Z", f'{{"name": "{pkg}"}}')
        b.file(f"tool-app/node_modules/{pkg}/index.js", JS, t, "2026-06-05T09:40:43Z", "module.exports = {};\n")
        b.file(f"tool-app/node_modules/{pkg}/LICENSE.md", MD, t, "2026-06-05T09:40:43Z", "MIT License\n")

    b.file("共有_課題.pdf", PDF, "2026-09-01T09:00:00Z", "2026-09-01T09:00:00Z", binary=True, size=300_000,
           text="課題プリント\n", content_key="kadai", owner="teacher@school.example")
    return b


def creative_keys(b):
    p = b.by_path
    return {
        "exact_groups": [
            [p["未整理/世界観.md"], p["創作/Obsidian/設定/世界観.md"]],
            [p["未整理/企画書.docx"], p["未整理/企画書 のコピー.docx"]],
            [p["未整理/議事録_0412"], p["未整理/2024-04-12_定例会議"]],
        ],
        "binary_meta_groups": [
            [p["創作/資料/鉱物図鑑.pdf"], p["創作/資料/鉱物図鑑 (1).pdf"]],
            [p["写真/IMG_1003.jpg"], p["写真/IMG_1003 (1).jpg"]],
        ],
        "version_set": [p["創作/原稿/六炎_第1部_最終版"], p["創作/原稿/六炎_第1部_最終版2"],
                        p["創作/原稿/六炎_第1部_最新版"]],
        "older_version_not_duplicate": p["未整理/シューニャ.md"],
        "shared_copy_must_not_be_trashed": p["未整理/企画書 のコピー.docx"],
        "linked_rename_candidates": [p["創作/Obsidian/人物/キャラ_カルタ.md"], p["創作/Obsidian/設定/律術.md"]],
        "do_not_rename": [p["創作/Obsidian/Daily/2024-05-01.md"], p["創作/Obsidian/Templates/人物テンプレート.md"],
                          p["創作/Obsidian/添付/Pasted image 20240501123456.png"]],
        "excluded_folders": [p["tool-app/node_modules"], p["創作/Obsidian/.obsidian"]]
        + [p[f"tool-app/node_modules/{k}"] for k in ["lodash", "semver", "chalk", "commander", "minimist"]],
        "not_owned": [p["共有_課題.pdf"]],
        "shortcut": p["創作/原稿/六炎_第1部 へのショートカット"],
        "outside_vault_md": p["創作/資料/参考文献メモ.md"],
        "role_differs": [p["創作/Obsidian/人物/シューニャ.md"], p["創作/Obsidian/人物/シューニャ設定.md"]],
        "all_ids": [f["id"] for f in b.files],
    }


# ======================================================================== scheduled

def build_scheduled():
    b = build_creative()
    b.folder("_drive-organizer-logs", "2026-09-01T09:00:00Z")
    p = b.by_path
    old_log = """# 作業ログ（2026-09-01 09:00）

```yaml
drive_organizer_state:
  version: 1
  last_scan: 2026-09-01T09:00:00Z
  last_full_scan: 2026-09-01T09:00:00Z
  scope:
    - {id: %s, path: マイドライブ/創作}
    - {id: %s, path: マイドライブ/未整理}
  open_items: []
  pending: []
  declined: []
```

- 初回の全体調査。詳細は 2026-09-15 のログに引き継ぎ。
""" % (p["創作"], p["未整理"])
    log = """# 作業ログ（2026-09-15 09:00）

```yaml
drive_organizer_state:
  version: 1
  last_scan: 2026-09-15T09:00:00Z
  last_full_scan: 2026-09-01T09:00:00Z
  scope:
    - {id: %(soku)s, path: マイドライブ/創作}
    - {id: %(mise)s, path: マイドライブ/未整理}
  excluded_folders:
    - {id: %(nm)s, path: マイドライブ/tool-app/node_modules, reason: コード依存フォルダ}
    - {id: %(obs)s, path: マイドライブ/創作/Obsidian/.obsidian, reason: アプリ設定}
  vaults:
    - {id: %(vault)s, path: マイドライブ/創作/Obsidian}
  conventions:
    人物: {filename: 人物名のみ, type: character, tags: [人物]}
    章: {filename: 第NN章, type: chapter, tags: [本文]}
    議事録: {filename: YYYY-MM-DD_定例会議, folder: マイドライブ/議事録}
  open_items:
    - {id: Q1, files: [%(v2)s, %(latest)s], issue: 最終版2 と 最新版 が互いにない内容を持つ（分岐）, since: 2026-09-15}
    - {id: Q2, files: [%(frag)s], issue: アイデア断片.md がどの作品のメモか不明, since: 2026-09-15}
  pending:
    - {id: D1, action: trash, file: %(mw)s, keep: %(vw)s, planned_modified: 2026-07-10T11:20:00Z}
  declined:
    - {action: move, file: %(refs)s, to: マイドライブ/創作/Obsidian, date: 2026-09-15}
```

## 整理案（承認待ち）
- D1: 未整理/世界観.md をゴミ箱へ（Obsidian/設定/世界観.md と完全一致。確度 高）

## 要確認
- Q1: 六炎_第1部_最終版2 と 六炎_第1部_最新版 が分岐している
- Q2: アイデア断片.md の所属

## 実行しなかった変更
- 資料/参考文献メモ.md の Vault への移動（ユーザーが却下）
""" % {"soku": p["創作"], "mise": p["未整理"], "nm": p["tool-app/node_modules"],
       "obs": p["創作/Obsidian/.obsidian"], "vault": p["創作/Obsidian"], "v2": p["創作/原稿/六炎_第1部_最終版2"],
       "latest": p["創作/原稿/六炎_第1部_最新版"], "frag": p["未整理/アイデア断片.md"], "mw": p["未整理/世界観.md"],
       "vw": p["創作/Obsidian/設定/世界観.md"], "refs": p["創作/資料/参考文献メモ.md"]}
    b.file("_drive-organizer-logs/2026-09-01_0900_drive-organizer.md", MD, "2026-09-01T09:05:00Z",
           "2026-09-01T09:05:00Z", old_log)
    b.file("_drive-organizer-logs/2026-09-15_0900_drive-organizer.md", MD, "2026-09-15T09:05:00Z",
           "2026-09-15T09:05:00Z", log)

    # 前回以降の変化
    b.file("未整理/第03章 (1).md", MD, "2026-09-20T08:00:00Z", "2026-07-01T08:00:00Z", CH3)
    b.file("創作/Obsidian/章/第04章.md", MD, "2026-09-22T08:00:00Z", "2026-09-22T08:30:00Z", CH4)
    b.file("創作/Obsidian/人物/イェレナ.md", MD, "2026-09-23T08:00:00Z", "2026-09-23T08:10:00Z", NEW_CHARA)
    for f in b.files:
        if f["id"] == p["創作/原稿/六炎_第1部_最新版"]:
            f["content"] = MS_HEAD + MS_A_REVISED + MS_B + MS_C
            f["modifiedTime"] = "2026-09-25T21:00:00Z"
    keys = creative_keys(b)
    keys.update({
        "log_folder": p["_drive-organizer-logs"],
        "latest_log": p["_drive-organizer-logs/2026-09-15_0900_drive-organizer.md"],
        "new_dup_copy": p["未整理/第03章 (1).md"],
        "new_dup_original": p["創作/Obsidian/章/第03章.md"],
        "declined_move_file": p["創作/資料/参考文献メモ.md"],
        "pending_trash_file": p["未整理/世界観.md"],
        "last_scan": "2026-09-15T09:00:00Z",
    })
    return b, keys


# ======================================================================== execution

def build_execution():
    b = build_creative(world_content=WORLD_UPDATED, world_modified="2026-09-28T12:00:00Z")
    p = b.by_path
    keys = creative_keys(b)
    keys.update({
        "D1_trash": p["未整理/世界観.md"],
        "D1_keep": p["創作/Obsidian/設定/世界観.md"],
        "M1_file": p["未整理/2024-04-12_定例会議"],
        "M1_dest": p["議事録"],
        "R1_file": p["創作/Obsidian/メモ/無題.md"],
        "R1_new_title": "第4章アイデア.md",
        "R2_file": p["創作/Obsidian/人物/キャラ_カルタ.md"],
        "F1_file": p["創作/Obsidian/人物/ペトロス.md"],
    })
    return b, keys


# ======================================================================== large

def build_large():
    rng = random.Random(20260929)
    b = Builder("0AROOTlargeFixture00000000000000")

    def ts(year=2025, month=None, day=None):
        m = month or rng.randint(1, 12)
        d = day or rng.randint(1, 28)
        return f"{year}-{m:02d}-{d:02d}T{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}Z"

    counter = {"n": 0}

    def uniq():
        counter["n"] += 1
        return f"u{counter['n']}"

    b.folder("仕事")
    projects = [f"案件{c}" for c in "ABCDEFGH"]
    for pj in projects:
        b.folder(f"仕事/{pj}")
        for i in range(1, 9):
            b.file(f"仕事/{pj}/資料{i:02d}.pdf", PDF, ts(), ts(), binary=True, size=rng.randint(80_000, 900_000),
                   text=f"{pj} 資料{i}\n", content_key=uniq())
        for i in range(1, 7):
            b.file(f"仕事/{pj}/メモ{i:02d}", GDOC, ts(), ts(), f"{pj} メモ {i}\n打ち合わせ内容の控え。項目{i}。\n")
        for i in range(1, 5):
            b.file(f"仕事/{pj}/集計{i:02d}.xlsx", XLSX, ts(), ts(), binary=True, size=rng.randint(10_000, 90_000),
                   text=f"{pj} 集計 {i}\n", content_key=uniq())
        for i in range(1, 5):
            b.file(f"仕事/{pj}/図{i:02d}.png", PNG, ts(), ts(), binary=True, size=rng.randint(20_000, 400_000),
                   content_key=uniq())

    b.folder("写真")
    for year in (2023, 2024, 2025):
        b.folder(f"写真/{year}")
        for i in range(150):
            n = 100 + i * 13 + year % 7
            b.file(f"写真/{year}/IMG_{n:04d}.jpg", JPG, ts(year), ts(year), binary=True,
                   size=rng.randint(1_500_000, 4_500_000), content_key=uniq())

    b.folder("学校")
    for c in range(1, 6):
        b.folder(f"学校/授業{c}")
        for i in range(1, 31):
            kind = i % 3
            if kind == 0:
                b.file(f"学校/授業{c}/プリント{i:02d}.pdf", PDF, ts(2024), ts(2024), binary=True,
                       size=rng.randint(50_000, 500_000), text=f"授業{c} プリント{i}\n", content_key=uniq())
            elif kind == 1:
                b.file(f"学校/授業{c}/ノート{i:02d}", GDOC, ts(2024), ts(2024), f"授業{c} ノート{i}\n板書の要点。\n")
            else:
                b.file(f"学校/授業{c}/課題{i:02d}.docx", DOCX, ts(2024), ts(2024), binary=True,
                       size=rng.randint(15_000, 60_000), text=f"授業{c} 課題{i}\n", content_key=uniq())

    vault = "創作/Obsidian"
    b.folder("創作")
    b.folder(vault)
    b.folder(f"{vault}/.obsidian")
    for name in ["app.json", "workspace.json", "core-plugins.json", "daily-notes.json"]:
        b.file(f"{vault}/.obsidian/{name}", JSON, ts(), ts(), '{"x": 1}')
    note_types = {"人物": "character", "設定": "setting", "章": "chapter", "資料": "research", "メモ": "note",
                  "会議": "meeting"}
    for folder, typ in note_types.items():
        b.folder(f"{vault}/{folder}")
        for i in range(1, 31):
            title = f"第{i:02d}章" if folder == "章" else f"{folder}{i:02d}"
            body = f"---\ntype: {typ}\ntags:\n  - {folder}\n---\n# {title}\n\n{folder}のノート {i}。\n"
            b.file(f"{vault}/{folder}/{title}.md", MD, ts(), ts(), body)
    b.folder(f"{vault}/添付")
    for i in range(1, 41):
        b.file(f"{vault}/添付/Pasted image 2025{i:04d}.png", PNG, ts(), ts(), binary=True,
               size=rng.randint(30_000, 300_000), content_key=uniq())

    b.folder("tool-app")
    b.file("tool-app/package.json", JSON, ts(), ts(), '{"name": "tool-app"}')
    b.file("tool-app/README.md", MD, ts(), ts(), "# tool-app\n\nツールの説明。\n")
    b.folder("tool-app/src")
    for i in range(1, 21):
        b.file(f"tool-app/src/mod{i:02d}.js", JS, ts(), ts(), f"export const m{i} = {i};\n")
    b.folder("tool-app/node_modules")
    for k in range(30):
        pkg = f"pkg-{k:02d}"
        b.folder(f"tool-app/node_modules/{pkg}")
        for name in ["README.md", "package.json", "index.js", "LICENSE", "CHANGELOG.md", "index.d.ts",
                     "lib-a.js", "lib-b.js", "lib-c.js", "util.js", "types.js", "helpers.js"]:
            mime = MD if name.endswith(".md") else JSON if name.endswith(".json") else JS
            b.file(f"tool-app/node_modules/{pkg}/{name}", mime, "2026-06-05T07:20:00Z", "2026-06-05T09:40:43Z",
                   f"{pkg} {name}\n")

    b.folder("未整理")
    for i in range(1, 51):
        b.file(f"未整理/scan_{i:03d}.pdf", PDF, ts(2026), ts(2026), binary=True, size=rng.randint(100_000, 2_000_000),
               text=f"スキャン {i}\n", content_key=uniq())
    for i in range(1, 11):
        b.file(f"未整理/ダウンロード{i:02d}.zip", "application/zip", ts(2026), ts(2026), binary=True,
               size=rng.randint(1_000_000, 9_000_000), content_key=uniq())
    for i in range(1, 16):
        b.file(f"root_file_{i:02d}.txt", "text/plain", ts(), ts(), f"メモ {i}\n")

    # ---- 埋め込む重複（正解）
    p = b.by_path
    planted = {}

    def twin(src_path, dst_path, created):
        src = next(f for f in b.files if f["id"] == p[src_path])
        f = copy.deepcopy(src)
        parent_path, _, name = dst_path.rpartition("/")
        f.update({"id": fid(dst_path), "title": name, "parentId": p[parent_path], "createdTime": created})
        b.files.append(f)
        p[dst_path] = f["id"]
        return [src["id"], f["id"]]

    photo = sorted(k for k in p if k.startswith("写真/2024/IMG_"))[5]
    planted["E1"] = twin(photo, "未整理/" + photo.rsplit("/", 1)[1], "2026-08-10T09:00:00Z")
    b.file("仕事/案件C/見積書_2025-03.pdf", PDF, "2025-03-04T09:00:00Z", "2025-03-03T17:00:00Z", binary=True,
           size=184_322, text="見積書 2025-03\n合計 1,200,000 円\n", content_key="mitsumori")
    planted["E2"] = twin("仕事/案件C/見積書_2025-03.pdf", "未整理/見積書_2025-03.pdf", "2026-08-11T09:00:00Z")
    planted["E3"] = twin(f"{vault}/人物/人物07.md", "未整理/人物07.md", "2026-08-12T09:00:00Z")
    b.file("仕事/案件A/売上集計.xlsx", XLSX, "2025-05-01T09:00:00Z", "2025-05-31T18:00:00Z", binary=True,
           size=64_512, text="売上集計 5月\n", content_key="uriage")
    planted["E4"] = twin("仕事/案件A/売上集計.xlsx", "仕事/案件A/売上集計 (1).xlsx", "2025-06-02T09:00:00Z")
    b.file("学校/授業3/レポート.docx", DOCX, "2024-11-01T09:00:00Z", "2024-11-20T21:00:00Z", binary=True,
           size=38_144, text="授業3 期末レポート\n", content_key="report")
    planted["E5"] = twin("学校/授業3/レポート.docx", "学校/授業3/Copy of レポート.docx", "2024-11-21T09:00:00Z")
    b.file("仕事/案件B/仕様書_v3.pdf", PDF, "2025-07-01T09:00:00Z", "2025-06-30T20:00:00Z", binary=True,
           size=733_901, text="仕様書 v3\n", content_key="spec")
    planted["E6"] = twin("仕事/案件B/仕様書_v3.pdf", "未整理/spec_final.pdf", "2026-08-13T09:00:00Z")
    minutes = "定例 2025-06-12\n出席: 佐藤、鈴木\n- 納期を7月末に変更\n- 次回 6/26\n"
    b.file("仕事/案件D/議事録_0612", GDOC, "2025-06-12T10:00:00Z", "2025-06-12T11:00:00Z", minutes)
    b.file("未整理/2025-06-12_定例", GDOC, "2025-06-13T10:00:00Z", "2025-06-13T10:02:00Z", minutes)
    planted["E7_bonus"] = [p["仕事/案件D/議事録_0612"], p["未整理/2025-06-12_定例"]]

    b.file("仕事/案件E/企画書_最終版.docx", DOCX, "2025-02-01T09:00:00Z", "2025-02-10T18:00:00Z", binary=True,
           size=40_960, text="企画書 最終版\n", content_key="kikaku1")
    b.file("仕事/案件E/企画書_最終版2.docx", DOCX, "2025-02-11T09:00:00Z", "2025-02-20T18:00:00Z", binary=True,
           size=43_008, text="企画書 最終版2\n追記あり\n", content_key="kikaku2")
    b.file("仕事/案件E/企画書_最新版.docx", DOCX, "2025-02-21T09:00:00Z", "2025-03-01T18:00:00Z", binary=True,
           size=41_472, text="企画書 最新版\n", content_key="kikaku3")
    planted["V1"] = [p["仕事/案件E/企画書_最終版.docx"], p["仕事/案件E/企画書_最終版2.docx"],
                     p["仕事/案件E/企画書_最新版.docx"]]
    b.file(f"{vault}/章/第05章_改訂版.md", MD, "2025-09-01T09:00:00Z", "2025-09-05T09:00:00Z",
           "---\ntype: chapter\ntags:\n  - 章\n---\n# 第05章\n\n章のノート 5。改訂で後半を追加。\n")
    planted["V2"] = [p[f"{vault}/章/第05章.md"], p[f"{vault}/章/第05章_改訂版.md"]]

    decoys = {}
    for pj, size in (("案件F", 22_528), ("案件G", 31_744), ("案件H", 27_136)):
        b.file(f"仕事/{pj}/議事録.docx", DOCX, ts(2025), ts(2025), binary=True, size=size,
               text=f"{pj} 議事録\n", content_key=uniq())
    decoys["same_name_diff_content"] = [p[f"仕事/{pj}/議事録.docx"] for pj in ("案件F", "案件G", "案件H")]
    b.file("写真/2023/IMG_0456.jpg", JPG, "2023-05-05T09:00:00Z", "2023-05-04T10:00:00Z", binary=True,
           size=2_811_004, content_key=uniq())
    b.file("写真/2025/IMG_0456.jpg", JPG, "2025-05-05T09:00:00Z", "2025-05-04T11:00:00Z", binary=True,
           size=3_402_118, content_key=uniq())
    decoys["same_name_photo"] = [p["写真/2023/IMG_0456.jpg"], p["写真/2025/IMG_0456.jpg"]]
    b.file("仕事/案件A/icon.png", PNG, "2025-01-10T09:00:00Z", "2025-01-10T09:00:00Z", binary=True, size=4_096,
           content_key=uniq())
    b.file("仕事/案件B/banner.png", PNG, "2025-04-10T09:00:00Z", "2025-04-10T09:00:00Z", binary=True, size=4_096,
           content_key=uniq())
    decoys["same_size_diff_file"] = [p["仕事/案件A/icon.png"], p["仕事/案件B/banner.png"]]
    for m in ("07", "08"):
        b.file(f"仕事/案件A/月報_2025-{m}.xlsx", XLSX, f"2025-{m}-28T09:00:00Z", f"2025-{m}-30T09:00:00Z",
               binary=True, size=18_000 + int(m) * 100, text=f"月報 2025-{m}\n", content_key=uniq())
    decoys["series"] = [p["仕事/案件A/月報_2025-07.xlsx"], p["仕事/案件A/月報_2025-08.xlsx"]]

    excluded = [p["tool-app/node_modules"], p[f"{vault}/.obsidian"]] + \
        [p[f"tool-app/node_modules/pkg-{k:02d}"] for k in range(30)]
    keys = {"planted": planted, "decoys": decoys, "excluded_folders": excluded,
            "total_files": sum(1 for f in b.files if f["mimeType"] != FOLDER),
            "all_ids": [f["id"] for f in b.files]}
    return b, keys


def main():
    OUT.mkdir(exist_ok=True)
    keys = {}
    b = build_creative()
    (OUT / "creative.json").write_text(json.dumps(b.fixture(), ensure_ascii=False, indent=1), encoding="utf-8")
    keys["creative"] = creative_keys(b)
    b, k = build_scheduled()
    (OUT / "scheduled.json").write_text(json.dumps(b.fixture(), ensure_ascii=False, indent=1), encoding="utf-8")
    keys["scheduled"] = k
    b, k = build_execution()
    (OUT / "execution.json").write_text(json.dumps(b.fixture(), ensure_ascii=False, indent=1), encoding="utf-8")
    keys["execution"] = k
    b, k = build_large()
    (OUT / "large.json").write_text(json.dumps(b.fixture(), ensure_ascii=False, indent=1), encoding="utf-8")
    keys["large"] = k
    (OUT / "answer_keys.json").write_text(json.dumps(keys, ensure_ascii=False, indent=1), encoding="utf-8")
    for name in ("creative", "scheduled", "execution", "large"):
        data = json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))
        n_files = sum(1 for f in data["files"] if f["mimeType"] != FOLDER)
        n_folders = sum(1 for f in data["files"] if f["mimeType"] == FOLDER)
        print(f"{name}: {n_files} files, {n_folders} folders")


if __name__ == "__main__":
    main()
