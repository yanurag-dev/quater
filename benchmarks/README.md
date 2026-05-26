# Quater Benchmarks

This folder contains small public benchmarks for comparing Quater and FastAPI.
The goal is not to prove a universal winner. It is to make the comparison easy
to rerun, easy to inspect, and honest about what is being measured.

There are two fixtures, with one file per framework:

- `apps/no_db_quater.py`
- `apps/no_db_fastapi.py`
- `apps/db_quater.py`
- `apps/db_fastapi.py`

The matching Quater and FastAPI files intentionally do the same work. If a
result looks strange, open the two files for that suite and compare them side by
side.

For the Postgres fixture, both apps create one database session per request.
FastAPI uses `Depends(get_session)`. Quater uses `Resource(get_session)` with
`inject={"session": db_session}`. That keeps the app structure close while still
using each framework's normal style.

## Results

These charts come from the CSV files in `benchmarks/results/`. They are local
numbers from one machine, not a universal claim. CPU, Python version, Postgres
settings, thermal state, and background work can all move the results.

### No Database

![No database throughput](assets/no-db-throughput.svg)

![No database p95 latency](assets/no-db-p95.svg)

### Postgres

![Postgres throughput](assets/postgres-throughput.svg)

![Postgres p95 latency](assets/postgres-p95.svg)

### Run Environment

The checked-in charts were generated on:

| Item | Value |
| --- | --- |
| Run date | 2026-05-26 |
| Machine | Apple M2 |
| CPU cores | 8 |
| Memory | 16 GiB |
| OS | macOS 26.3, arm64 |
| Python | 3.11.12 |
| Quater | 0.1.0a1 |
| Granian | 2.7.4 |
| FastAPI | 0.136.3 |
| Uvicorn | 0.48.0 |
| httptools | 0.8.0 |
| uvloop | 0.22.1 |
| SQLAlchemy | 2.0.50 |
| asyncpg | 0.31.0 |
| msgspec | 0.21.1 |
| oha | 1.14.0 |
| Postgres | `postgres:16-alpine` through Docker Compose v2.31.0 |

## What The Benchmarks Measure

The no-database suite focuses on framework overhead:

- small JSON response
- large JSON serialization
- JSON request body parsing
- typed body binding with auth
- large bytes response

The Postgres suite focuses on real backend shape without becoming a full demo
product:

- DB health check
- product list
- product detail
- order list
- summary report

Quater runs through `quater run`, which uses Granian's RSGI path. FastAPI runs
through Uvicorn with `uvloop` and `httptools`. Both examples use one worker by
default so the request path is easier to compare.

Quater keeps its default request safety work enabled in these fixtures:
Host validation, request ids, response security headers, and body limits. Those
defaults can make tiny no-database endpoints look slower than a bare framework
path, because the handler itself does almost no work. The Postgres fixture is
closer to a real service, so database work usually dominates that fixed
framework cost.

The fixture apps are intentionally small:

- one no-database file for Quater
- one no-database file for FastAPI
- one Postgres file for Quater
- one Postgres file for FastAPI

There is no shared application code between the frameworks. That makes the files
easy to read in public, and it avoids hiding framework differences behind helper
modules.

## Install Dependencies

From the repository root:

```bash
python -m venv .bench-venv
source .bench-venv/bin/activate

python -m pip install -U pip wheel maturin
python -m pip install -e . --no-build-isolation
python -m pip install "fastapi[standard]" asyncpg "sqlalchemy[asyncio]"
```

Install `oha` separately. On macOS:

```bash
brew install oha
```

Or with Cargo:

```bash
cargo install oha
```

## Run The No-Database Benchmark

Start Quater in one terminal:

```bash
source .bench-venv/bin/activate
PYTHONPATH=benchmarks/apps quater run no_db_quater:app \
  --host 127.0.0.1 \
  --port 8002 \
  --workers 1 \
  --no-reload \
  --no-access-log
```

Start FastAPI in another terminal:

```bash
source .bench-venv/bin/activate
PYTHONPATH=benchmarks/apps uvicorn no_db_fastapi:app \
  --host 127.0.0.1 \
  --port 8001 \
  --workers 1 \
  --loop uvloop \
  --http httptools \
  --no-access-log
```

Run the suite:

```bash
source .bench-venv/bin/activate
python benchmarks/scripts/run_suite.py no-db \
  --quater-url http://127.0.0.1:8002 \
  --fastapi-url http://127.0.0.1:8001 \
  --output benchmarks/results/no_db.csv
```

That writes fresh numbers to:

```text
benchmarks/results/no_db.csv
```

The default no-database run uses concurrency `100` for `30s` per scenario. You
can change that:

```bash
python benchmarks/scripts/run_suite.py no-db \
  --quater-url http://127.0.0.1:8002 \
  --fastapi-url http://127.0.0.1:8001 \
  --concurrency 50 \
  --duration 15s \
  --output benchmarks/results/no_db.csv
```

## Run The Postgres Benchmark

Start Postgres:

```bash
docker compose -f benchmarks/docker-compose.yml up -d postgres
```

The DB app creates its schema and seed rows on startup if the tables are empty.
If you want a clean database:

```bash
docker compose -f benchmarks/docker-compose.yml down -v
docker compose -f benchmarks/docker-compose.yml up -d postgres
```

Start Quater in one terminal:

```bash
source .bench-venv/bin/activate
PYTHONPATH=benchmarks/apps quater run db_quater:app \
  --host 127.0.0.1 \
  --port 8010 \
  --workers 1 \
  --no-reload \
  --no-access-log
```

Start FastAPI in another terminal:

```bash
source .bench-venv/bin/activate
PYTHONPATH=benchmarks/apps uvicorn db_fastapi:app \
  --host 127.0.0.1 \
  --port 8011 \
  --workers 1 \
  --loop uvloop \
  --http httptools \
  --no-access-log
```

Run the suite:

```bash
source .bench-venv/bin/activate
python benchmarks/scripts/run_suite.py db \
  --quater-url http://127.0.0.1:8010 \
  --fastapi-url http://127.0.0.1:8011 \
  --output benchmarks/results/postgres.csv
```

That writes fresh numbers to:

```text
benchmarks/results/postgres.csv
```

The default Postgres run uses concurrency `25` for `20s` per scenario. That
keeps the benchmark below the default DB pool limit. If you raise concurrency a
lot, you may end up measuring connection waiting more than framework overhead.

## Generate Charts

```bash
python benchmarks/scripts/generate_charts.py
```

If you have only run the no-database suite:

```bash
python benchmarks/scripts/generate_charts.py --suite no-db
```

The script reads whichever result files exist:

```text
benchmarks/results/no_db.csv
benchmarks/results/postgres.csv
```

If you have only `benchmarks/results/no_db.csv`, it generates only the no-DB
charts. You can run the Postgres suite later and rerun the same command.

It writes:

```text
benchmarks/assets/no-db-throughput.svg
benchmarks/assets/no-db-p95.svg
benchmarks/assets/postgres-throughput.svg
benchmarks/assets/postgres-p95.svg
```

If you want to publish graphs, commit the CSV files and SVG files from the same
run together so the chart and the raw numbers always match.
