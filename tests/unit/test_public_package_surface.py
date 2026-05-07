from __future__ import annotations

import importlib.resources
import json
import os
import pathlib
import re
import subprocess
import sys

import quater
from quater import App, AuthContext, AuthRequest


def test_package_imports_from_outside_source_tree_without_optional_eager_imports(
    tmp_path: pathlib.Path,
) -> None:
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    src_path = repo_root / "src"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_path)

    script = """
import json
import os
import sys

os.chdir(sys.argv[1])
import quater

print(json.dumps({
    "file": quater.__file__,
    "has_app": hasattr(quater, "App"),
    "granian_eager": "granian" in sys.modules,
    "msgspec_eager": "msgspec" in sys.modules,
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        check=True,
        capture_output=True,
        env=env,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["has_app"] is True
    assert pathlib.Path(payload["file"]).is_relative_to(src_path)
    assert payload["granian_eager"] is False
    assert payload["msgspec_eager"] is False


def test_public_exports_are_intentionally_small() -> None:
    assert quater.__all__ == [
        "App",
        "AuthContext",
        "AuthRequest",
        "BytesResponse",
        "EmptyResponse",
        "HTTPError",
        "JSONResponse",
        "RedirectResponse",
        "Request",
        "Response",
        "StreamResponse",
        "TextResponse",
        "__version__",
    ]
    assert quater.App is App
    assert quater.AuthContext is AuthContext
    assert quater.AuthRequest is AuthRequest


def test_version_uses_pep440_compatible_shape() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[a-z]+\d*)?", quater.__version__)


def test_py_typed_marker_is_available_to_type_checkers() -> None:
    marker = importlib.resources.files("quater").joinpath("py.typed")
    assert marker.is_file()
