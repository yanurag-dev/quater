from __future__ import annotations

import sys
import textwrap
from pathlib import Path


def write_app(tmp_path: Path, source: str) -> None:
    sys.modules.pop("sample", None)
    tmp_path.joinpath("sample.py").write_text(textwrap.dedent(source), encoding="utf-8")


def file_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777
