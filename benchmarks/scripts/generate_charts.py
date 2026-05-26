from __future__ import annotations

import argparse
import csv
import html
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Metric = Literal["requests_per_second", "p95_ms"]
SuiteSelection = Literal["all", "no-db", "db"]

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
ASSET_DIR = ROOT / "assets"

APP_COLORS = {
    "Quater": "#2563eb",
    "FastAPI": "#10b981",
}


@dataclass(frozen=True, slots=True)
class BenchmarkRow:
    suite: str
    scenario: str
    scenario_label: str
    app: str
    concurrency: int
    requests_per_second: float
    p95_ms: float
    success_rate: float
    source: str

    def metric(self, name: Metric) -> float:
        if name == "requests_per_second":
            return self.requests_per_second
        return self.p95_ms


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate benchmark SVG charts from local benchmark results.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS_DIR,
        help="Directory containing no_db.csv and/or postgres.csv.",
    )
    parser.add_argument(
        "--asset-dir",
        type=Path,
        default=ASSET_DIR,
        help="Directory where SVG charts are written.",
    )
    parser.add_argument(
        "--suite",
        choices=("all", "no-db", "db"),
        default="all",
        help="Generate charts for one suite or all available suites.",
    )
    args = parser.parse_args()

    rows = load_available_rows(args.results_dir, suite=args.suite)
    if not rows:
        raise SystemExit(
            "No benchmark CSV files found. Run the no-db or db suite first."
        )
    args.asset_dir.mkdir(parents=True, exist_ok=True)

    if any(row.suite == "no_db" for row in rows):
        write_chart(
            rows,
            suite="no_db",
            metric="requests_per_second",
            path=args.asset_dir / "no-db-throughput.svg",
            title="No database throughput",
            subtitle="Requests per second at concurrency 100. Higher is better.",
            unit="rps",
        )
        write_chart(
            rows,
            suite="no_db",
            metric="p95_ms",
            path=args.asset_dir / "no-db-p95.svg",
            title="No database p95 latency",
            subtitle="Milliseconds at concurrency 100. Lower is better.",
            unit="ms",
        )

    if any(row.suite == "postgres" for row in rows):
        write_chart(
            rows,
            suite="postgres",
            metric="requests_per_second",
            path=args.asset_dir / "postgres-throughput.svg",
            title="Postgres throughput",
            subtitle="Requests per second at concurrency 25. Higher is better.",
            unit="rps",
        )
        write_chart(
            rows,
            suite="postgres",
            metric="p95_ms",
            path=args.asset_dir / "postgres-p95.svg",
            title="Postgres p95 latency",
            subtitle="Milliseconds at concurrency 25. Lower is better.",
            unit="ms",
        )


def load_available_rows(
    results_dir: Path,
    *,
    suite: SuiteSelection,
) -> list[BenchmarkRow]:
    rows: list[BenchmarkRow] = []
    filenames = {
        "all": ("no_db.csv", "postgres.csv"),
        "no-db": ("no_db.csv",),
        "db": ("postgres.csv",),
    }[suite]
    for filename in filenames:
        path = results_dir / filename
        if path.exists():
            rows.extend(load_rows(path))
    return rows


def load_rows(path: Path) -> list[BenchmarkRow]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            BenchmarkRow(
                suite=row["suite"],
                scenario=row["scenario"],
                scenario_label=row["scenario_label"],
                app=row["app"],
                concurrency=int(row["concurrency"]),
                requests_per_second=float(row["requests_per_second"]),
                p95_ms=float(row["p95_ms"]),
                success_rate=float(row["success_rate"]),
                source=row["source"],
            )
            for row in csv.DictReader(handle)
        ]


def write_chart(
    rows: list[BenchmarkRow],
    *,
    suite: str,
    metric: Metric,
    path: Path,
    title: str,
    subtitle: str,
    unit: str,
) -> None:
    suite_rows = [row for row in rows if row.suite == suite]
    scenario_order = _scenario_order(suite_rows)
    max_value = max(row.metric(metric) for row in suite_rows)

    width = 1120
    row_height = 76
    top = 116
    left = 250
    right = 156
    plot_width = width - left - right
    height = top + len(scenario_order) * row_height + 54
    baseline = left
    chart_right = left + plot_width

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" role="img">'
        ),
        f"<title>{_escape(title)}</title>",
        '<rect width="100%" height="100%" rx="16" fill="#f8fafc"/>',
        f'<text x="32" y="46" fill="#0f172a" font-size="26" '
        f'font-family="Inter, ui-sans-serif, system-ui" font-weight="700">'
        f"{_escape(title)}</text>",
        f'<text x="32" y="76" fill="#475569" font-size="15" '
        f'font-family="Inter, ui-sans-serif, system-ui">{_escape(subtitle)}</text>',
        legend_item("Quater", 790, 44),
        legend_item("FastAPI", 900, 44),
        f'<line x1="{baseline}" y1="{top - 24}" x2="{chart_right}" '
        f'y2="{top - 24}" stroke="#cbd5e1"/>',
    ]

    for index, scenario in enumerate(scenario_order):
        y = top + index * row_height
        pair = [row for row in suite_rows if row.scenario == scenario]
        label = pair[0].scenario_label
        lines.append(
            f'<text x="32" y="{y + 34}" fill="#0f172a" font-size="16" '
            f'font-family="Inter, ui-sans-serif, system-ui" font-weight="600">'
            f"{_escape(label)}</text>"
        )
        for app_index, app in enumerate(("Quater", "FastAPI")):
            row = next(item for item in pair if item.app == app)
            bar_y = y + 10 + app_index * 28
            value = row.metric(metric)
            bar_width = 0 if max_value == 0 else (value / max_value) * plot_width
            color = APP_COLORS[app]
            lines.extend(
                [
                    f'<text x="{left - 68}" y="{bar_y + 17}" fill="#475569" '
                    f'font-size="13" font-family="Inter, ui-sans-serif, system-ui">'
                    f"{app}</text>",
                    f'<rect x="{baseline}" y="{bar_y}" width="{bar_width:.2f}" '
                    f'height="20" rx="5" fill="{color}"/>',
                    f'<text x="{min(chart_right + 10, baseline + bar_width + 10):.2f}" '
                    f'y="{bar_y + 16}" fill="#0f172a" font-size="13" '
                    f'font-family="Inter, ui-sans-serif, system-ui">'
                    f"{_format_value(value, unit)}</text>",
                ]
            )

    lines.extend(
        [
            f'<text x="32" y="{height - 22}" fill="#64748b" font-size="12" '
            f'font-family="Inter, ui-sans-serif, system-ui">'
            "Numbers are generated from your local benchmark run.</text>",
            "</svg>",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _scenario_order(rows: list[BenchmarkRow]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        if row.scenario not in seen:
            seen.append(row.scenario)
    return seen


def legend_item(app: str, x: int, y: int) -> str:
    color = APP_COLORS[app]
    return (
        f'<g><rect x="{x}" y="{y - 13}" width="14" height="14" rx="3" '
        f'fill="{color}"/><text x="{x + 20}" y="{y}" fill="#334155" '
        f'font-size="14" font-family="Inter, ui-sans-serif, system-ui">'
        f"{app}</text></g>"
    )


def _format_value(value: float, unit: str) -> str:
    if unit == "rps":
        return f"{value:,.0f} {unit}"
    return f"{value:,.1f} {unit}"


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


if __name__ == "__main__":
    main()
