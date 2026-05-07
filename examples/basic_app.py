from __future__ import annotations

from quater import App, Request

app = App()


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/hello")
async def hello(name: str = "world") -> dict[str, str]:
    return {"message": f"hello {name}"}


@app.post("/echo")
async def echo(request: Request) -> dict[str, object]:
    return {"received": await request.json()}
