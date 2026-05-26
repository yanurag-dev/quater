from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi import Request as FastAPIRequest
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware


class UserIn(BaseModel):
    name: str
    age: int
    tags: list[str] = Field(default_factory=list)


async def authenticate(request: FastAPIRequest) -> str:
    if request.headers.get("authorization") != "Bearer benchmark-token":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return "benchmark-user"


CurrentUser = Annotated[str, Depends(authenticate)]


app = FastAPI(title="quater-no-db-benchmark-fastapi")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost"],
)


def json_payload(size: int) -> dict[str, object]:
    bounded = max(1, min(size, 1000))
    return {
        "count": bounded,
        "items": [{"id": index, "value": index * 2} for index in range(bounded)],
    }


def compute_payload(iterations: int) -> dict[str, object]:
    bounded = max(1, min(iterations, 500_000))
    started = perf_counter()
    total = 0
    for index in range(bounded):
        total = (total + index * index) % 1_000_000_007
    return {
        "iterations": bounded,
        "total": total,
        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
    }


@app.get("/ping")
async def ping() -> dict[str, bool]:
    return {"ok": True}


@app.get("/health")
async def health() -> dict[str, object]:
    return {"ok": True, "service": "no-db-benchmark"}


@app.get("/json")
async def json_response(size: int = Query(default=10)) -> dict[str, object]:
    return json_payload(size)


@app.post("/echo")
async def echo(request: FastAPIRequest) -> dict[str, Any]:
    return {"body": await request.json()}


@app.post("/users")
async def create_user(user: UserIn, subject: CurrentUser) -> dict[str, object]:
    return {
        "subject": subject,
        "name": user.name,
        "age": user.age,
        "tags": user.tags,
    }


@app.get("/bytes")
async def bytes_response(size: int = Query(default=1024)) -> FastAPIResponse:
    bounded = max(1, min(size, 1024 * 1024))
    return FastAPIResponse(
        content=b"x" * bounded,
        media_type="application/octet-stream",
    )


@app.get("/compute")
async def compute(iterations: int = Query(default=10_000)) -> dict[str, object]:
    return compute_payload(iterations)


@app.get("/wait")
async def wait(delay_ms: int = Query(default=25)) -> dict[str, int]:
    bounded = max(0, min(delay_ms, 5000))
    await asyncio.sleep(bounded / 1000)
    return {"delay_ms": bounded}
