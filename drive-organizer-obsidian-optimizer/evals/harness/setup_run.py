#!/usr/bin/env python3
"""評価 1 回分の実行ディレクトリを用意する: state/（fixture のコピーと呼び出しログ）、drive（呼び出し用ラッパー）、outputs/。

使い方: python3 setup_run.py FIXTURE_NAME RUN_DIR
"""
import shutil
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    fixture, run_dir = sys.argv[1], Path(sys.argv[2]).resolve()
    (run_dir / "state").mkdir(parents=True, exist_ok=True)
    (run_dir / "outputs").mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "fixtures" / f"{fixture}.json", run_dir / "state" / "fixture.json")
    (run_dir / "state" / "calls.jsonl").write_text("", encoding="utf-8")
    wrapper = run_dir / "drive"
    wrapper.write_text(f'#!/bin/sh\nexec python3 "{HERE / "mockdrive.py"}" --state "{run_dir / "state"}" "$@"\n',
                       encoding="utf-8")
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(run_dir)


if __name__ == "__main__":
    main()
