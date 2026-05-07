from __future__ import annotations

from typing import assert_type

from quater import App
from quater.adapters.asgi import ASGIAdapter
from quater.adapters.rsgi import RSGIAdapter
from quater.adapters.wsgi import WSGIAdapter

app = App()

assert_type(app.asgi, ASGIAdapter)
assert_type(app.rsgi, RSGIAdapter)
assert_type(app.wsgi, WSGIAdapter)
assert_type(app.__rsgi__, RSGIAdapter)
