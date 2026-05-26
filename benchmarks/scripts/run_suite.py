from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urljoin
from urllib.request import Request, urlopen

Method = Literal["GET", "POST"]


@dataclass(frozen=True, slots=True)
class Service:
    app: str
    base_url: str


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    label: str
    method: Method
    path: str
    auth: bool = False
    body: str | None = None


NO_DB_SCENARIOS = (
    Scenario("health", "Health JSON", "GET", "/health"),
    Scenario("json-large", "Large JSON response", "GET", "/json?size=1000"),
    Scenario("echo", "JSON body echo", "POST", "/echo", body='{"hello":"world"}'),
    Scenario(
        "user-create",
        "Typed body + auth",
        "POST",
        "/users",
        auth=True,
        body='{"name":"Ada","age":37,"tags":["math","systems"]}',
    ),
    Scenario("bytes-large", "Large bytes response", "GET", "/bytes?size=1048576"),
)

DB_SCENARIOS = (
    Scenario("health", "DB health check", "GET", "/health"),
    Scenario("product-list", "Product list", "GET", "/products?limit=50", auth=True),
    Scenario(
        "product-detail", "Product detail", "GET", "/products/SKU-0001", auth=True
    ),
    Scenario("order-list", "Order list", "GET", "/orders?limit=25", auth=True),
    Scenario("summary-report", "Summary report", "GET", "/reports/summary", auth=True),
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run matching Quater and FastAPI benchmark scenarios with oha.",
    )
    parser.add_argument("suite", choices=("no-db", "db"))
    parser.add_argument("--quater-url", required=True)
    parser.add_argument("--fastapi-url", required=True)
    parser.add_argument("--duration", default=None)
    parser.add_argument("--concurrency", type=int, default=None)
    parser.add_argument("--token", default="benchmark-token")
    parser.add_argument("--warmup-requests", type=int, default=10)
    parser.add_argument(
        "--warmup-duration",
        default="10s",
        help="oha warmup duration per scenario (e.g. 10s). Set to 0 to skip.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    oha = shutil.which("oha")
    if oha is None:
        raise SystemExit("oha is required. Install it first, then rerun this script.")

    suite = _suite_name(args.suite)
    duration = args.duration or ("20s" if args.suite == "db" else "30s")
    concurrency = args.concurrency or (25 if args.suite == "db" else 100)
    scenarios = _scenarios(args.suite)
    services = (
        Service("Quater", args.quater_url),
        Service("FastAPI", args.fastapi_url),
    )
    warmup_duration = args.warmup_duration if args.warmup_duration != "0" else None

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "suite",
                "scenario",
                "scenario_label",
                "app",
                "concurrency",
                "requests_per_second",
                "p95_ms",
                "success_rate",
                "source",
            ]
        )
        for scenario in scenarios:
            for service in services:
                if args.warmup_requests > 0:
                    warmup(
                        service, scenario, token=args.token, count=args.warmup_requests
                    )
                if warmup_duration:
                    print(
                        f"  [warmup] {service.app} / {scenario.label} "
                        f"({warmup_duration})..."
                    )
                    run_oha_warmup(
                        oha,
                        service,
                        scenario,
                        duration=warmup_duration,
                        concurrency=concurrency,
                        token=args.token,
                    )
                result = run_oha(
                    oha,
                    service,
                    scenario,
                    duration=duration,
                    concurrency=concurrency,
                    token=args.token,
                )
                writer.writerow(
                    [
                        suite,
                        scenario.name,
                        scenario.label,
                        service.app,
                        concurrency,
                        f"{result.requests_per_second:.3f}",
                        f"{result.p95_ms:.3f}",
                        f"{result.success_rate:.5f}",
                        "local oha run",
                    ]
                )
                print(
                    f"{service.app} / {scenario.label}: "
                    f"{result.requests_per_second:.2f} rps, "
                    f"p95 {result.p95_ms:.2f} ms"
                )


@dataclass(frozen=True, slots=True)
class Result:
    requests_per_second: float
    p95_ms: float
    success_rate: float


def _suite_name(value: str) -> str:
    if value == "no-db":
        return "no_db"
    return "postgres"


def _scenarios(value: str) -> tuple[Scenario, ...]:
    if value == "no-db":
        return NO_DB_SCENARIOS
    return DB_SCENARIOS


def warmup(service: Service, scenario: Scenario, *, token: str, count: int) -> None:
    url = urljoin(service.base_url.rstrip("/") + "/", scenario.path.lstrip("/"))
    headers = {"accept": "application/json"}
    data: bytes | None = None
    if scenario.auth:
        headers["authorization"] = f"Bearer {token}"
    if scenario.body is not None:
        headers["content-type"] = "application/json"
        data = scenario.body.encode()
    for _ in range(count):
        with urlopen(
            Request(url, data=data, headers=headers, method=scenario.method),
            timeout=10,
        ):
            pass


def run_oha_warmup(
    oha: str,
    service: Service,
    scenario: Scenario,
    *,
    duration: str,
    concurrency: int,
    token: str,
) -> None:
    url = urljoin(service.base_url.rstrip("/") + "/", scenario.path.lstrip("/"))
    command = [
        oha,
        "--no-tui",
        "-z",
        duration,
        "-c",
        str(concurrency),
        "-m",
        scenario.method,
        "-H",
        "accept: application/json",
    ]
    if scenario.auth:
        command.extend(["-H", f"authorization: Bearer {token}"])
    if scenario.body is not None:
        command.extend(["-H", "content-type: application/json", "-d", scenario.body])
    command.append(url)
    subprocess.run(
        command,
        check=True,
        capture_output=True,
        timeout=duration_timeout(duration),
    )


def run_oha(
    oha: str,
    service: Service,
    scenario: Scenario,
    *,
    duration: str,
    concurrency: int,
    token: str,
) -> Result:
    url = urljoin(service.base_url.rstrip("/") + "/", scenario.path.lstrip("/"))
    command = [
        oha,
        "--no-tui",
        "--output-format",
        "json",
        "-z",
        duration,
        "-c",
        str(concurrency),
        "-m",
        scenario.method,
        "-H",
        "accept: application/json",
    ]
    if scenario.auth:
        command.extend(["-H", f"authorization: Bearer {token}"])
    if scenario.body is not None:
        command.extend(
            [
                "-H",
                "content-type: application/json",
                "-d",
                scenario.body,
            ]
        )
    command.append(url)

    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=duration_timeout(duration),
    )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("oha did not return a JSON object")
    return Result(
        requests_per_second=float_at(payload, ("summary", "requestsPerSec")),
        p95_ms=seconds_to_ms(percentile(payload, "95")),
        success_rate=float_at(payload, ("summary", "successRate")),
    )


def percentile(payload: dict[str, Any], key: str) -> float:
    value = at_path(payload, ("latencyPercentiles", key))
    if isinstance(value, int | float):
        return float(value)
    value = at_path(payload, ("latencyPercentiles", f"p{key}"))
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def float_at(payload: dict[str, Any], path: tuple[str, ...]) -> float:
    value = at_path(payload, path)
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def at_path(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = payload
    for part in path:
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def seconds_to_ms(value: float) -> float:
    return value * 1000.0


def duration_timeout(duration: str) -> float:
    value = duration.strip().lower()
    if value.endswith("ms"):
        return float(value[:-2]) / 1000.0 + 15
    if value.endswith("s"):
        return float(value[:-1]) + 15
    if value.endswith("m"):
        return float(value[:-1]) * 60 + 15
    return 60


if __name__ == "__main__":
    main()
