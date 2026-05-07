from __future__ import annotations

from typing import assert_type

from quater import App, __version__

app = App()

assert_type(app, App)
assert_type(app.name, str | None)
assert_type(__version__, str)
