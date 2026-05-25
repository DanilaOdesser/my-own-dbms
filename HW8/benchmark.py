"""Run the analytical query against Postgres and Clickhouse, report timings.

Each DB is timed cold (first run after a fresh page/file cache) and warm
(subsequent runs hitting OS / DB caches). Result rows are compared to verify
the two engines compute the same answer.
"""

import statistics
import subprocess
import time
from pathlib import Path

import psycopg2
import requests

HERE = Path(__file__).parent
QUERY = (HERE / "query.sql").read_text().strip().rstrip(";")

PG_DSN = "dbname=taxi user=bench password=bench host=localhost port=5433"
CH_HOST = "localhost"
CH_PORT = 8124
CH_USER = "bench"
CH_PASSWORD = "bench"
CH_DB = "taxi"

WARM_RUNS = 5


def drop_pg_caches() -> None:
    # Cleanest approach: bounce the Postgres container — fresh shared_buffers.
    subprocess.run(
        ["docker", "exec", "hw8-postgres", "psql", "-U", "bench", "-d", "taxi", "-c", "CHECKPOINT"],
        check=True, capture_output=True,
    )
    subprocess.run(["docker", "restart", "hw8-postgres"], check=True, capture_output=True)
    # Wait for it to come back
    for _ in range(60):
        result = subprocess.run(
            ["docker", "exec", "hw8-postgres", "pg_isready", "-U", "bench", "-d", "taxi"],
            capture_output=True,
        )
        if result.returncode == 0:
            return
        time.sleep(0.5)
    raise RuntimeError("Postgres did not come back online")


def drop_ch_caches() -> None:
    # Clickhouse exposes SYSTEM DROP MARK CACHE / UNCOMPRESSED CACHE.
    # Then bounce the container so the OS page cache for the data files is dropped too.
    subprocess.run(["docker", "restart", "hw8-clickhouse"], check=True, capture_output=True)
    for _ in range(60):
        try:
            r = requests.get(f"http://{CH_HOST}:{CH_PORT}/ping", timeout=2)
            if r.ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise RuntimeError("Clickhouse did not come back online")


def run_pg() -> tuple[float, list]:
    t0 = time.time()
    with psycopg2.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute(QUERY)
        rows = cur.fetchall()
    return time.time() - t0, rows


def run_ch() -> tuple[float, list]:
    url = f"http://{CH_HOST}:{CH_PORT}/"
    params = {"query": QUERY + " FORMAT TSV", "database": CH_DB}
    t0 = time.time()
    r = requests.post(url, params=params, auth=(CH_USER, CH_PASSWORD), timeout=120)
    r.raise_for_status()
    dt = time.time() - t0
    rows = []
    for line in r.text.strip().split("\n"):
        parts = line.split("\t")
        # parts[0] may come back as "0" or "0.0" depending on CH version
        rows.append((int(float(parts[0])), int(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])))
    return dt, rows


def results_match(pg_rows, ch_rows, tol_rel=1e-3) -> bool:
    if len(pg_rows) != len(ch_rows):
        return False
    for r1, r2 in zip(pg_rows, ch_rows):
        if r1[0] != r2[0] or r1[1] != r2[1]:
            return False
        for a, b in zip(r1[2:], r2[2:]):
            a, b = float(a), float(b)
            if abs(a - b) > tol_rel * max(abs(a), abs(b), 1.0):
                return False
    return True


def main() -> None:
    print("=== Cold Postgres ===")
    drop_pg_caches()
    pg_cold, pg_rows = run_pg()
    print(f"  {pg_cold*1000:.0f} ms")

    print("=== Warm Postgres ===")
    pg_warm = []
    for i in range(WARM_RUNS):
        t, _ = run_pg()
        pg_warm.append(t)
        print(f"  run {i+1}: {t*1000:.0f} ms")

    print("=== Cold Clickhouse ===")
    drop_ch_caches()
    ch_cold, ch_rows = run_ch()
    print(f"  {ch_cold*1000:.0f} ms")

    print("=== Warm Clickhouse ===")
    ch_warm = []
    for i in range(WARM_RUNS):
        t, _ = run_ch()
        ch_warm.append(t)
        print(f"  run {i+1}: {t*1000:.0f} ms")

    print()
    print("=== Result comparison ===")
    print(f"Postgres   returned {len(pg_rows)} rows")
    print(f"Clickhouse returned {len(ch_rows)} rows")
    print(f"Rows match within 0.1% tolerance: {results_match(pg_rows, ch_rows)}")

    print()
    print("=== Summary (ms) ===")
    print(f"{'DB':<12} {'cold':>8} {'warm-min':>10} {'warm-med':>10} {'warm-avg':>10}")
    print(f"{'Postgres':<12} {pg_cold*1000:>8.0f} {min(pg_warm)*1000:>10.0f} {statistics.median(pg_warm)*1000:>10.0f} {sum(pg_warm)/len(pg_warm)*1000:>10.0f}")
    print(f"{'Clickhouse':<12} {ch_cold*1000:>8.0f} {min(ch_warm)*1000:>10.0f} {statistics.median(ch_warm)*1000:>10.0f} {sum(ch_warm)/len(ch_warm)*1000:>10.0f}")
    print()
    speedup_warm = statistics.median(pg_warm) / statistics.median(ch_warm)
    speedup_cold = pg_cold / ch_cold
    print(f"Clickhouse vs Postgres speedup: cold {speedup_cold:.1f}x, warm-median {speedup_warm:.1f}x")


if __name__ == "__main__":
    main()
