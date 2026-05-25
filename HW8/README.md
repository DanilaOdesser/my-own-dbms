# HW8 — Row-Oriented vs Column-Oriented Database Comparison

## Setup

I ran two database instances locally via Docker Compose: **PostgreSQL 16** as the row-oriented database, and **ClickHouse 24.8** as the column-oriented one. The same NYC TLC Yellow Taxi dataset (January 2024, ~3 million trips) was loaded into both. I converted the source Parquet file to CSV and used that single CSV as the input for both engines so the load was fair and reproducible.

The schemas use matching column names and equivalent types in both DBs. PostgreSQL has a B-tree index on `pickup_datetime`; ClickHouse uses `MergeTree ORDER BY pickup_datetime`, which is the column-store equivalent — both engines have a sort key on the same column for fairness.

## The query

The same analytical query was run in both engines (portable SQL):

```sql
SELECT
    EXTRACT(HOUR FROM pickup_datetime)       AS hour,
    COUNT(*)                                 AS trips,
    AVG(trip_distance)                       AS avg_distance,
    AVG(fare_amount)                         AS avg_fare,
    AVG(tip_amount / NULLIF(fare_amount, 0)) AS avg_tip_pct
FROM trips
WHERE fare_amount > 0
GROUP BY hour
ORDER BY hour
```

It computes, for each hour of the day, the number of trips, average trip distance, average fare, and average tip percentage. This is a typical analytical workload: it aggregates over millions of rows but only needs 4 of the 19 columns.

## Results

Both engines returned 24 rows (one per hour) with matching numerical results (within 0.1% floating-point tolerance), so the query is logically equivalent on both sides.

Execution times, measured by running the query several times against each DB:

| Database   | Cold (first run) | Warm (median of 5 runs) |
|------------|------------------|--------------------------|
| PostgreSQL | 926 ms           | 844 ms                   |
| ClickHouse | 42 ms            | 37 ms                    |

**ClickHouse executed the query roughly 22× faster than PostgreSQL.**

## Observations

ClickHouse wins by ~22× because the query only needs 4 of the 19 columns and aggregates over all 3M rows — exactly the shape column stores are built for. PostgreSQL has to read entire rows from disk just to access a few columns; ClickHouse reads only those columns and skips the rest.

The B-tree index on `pickup_datetime` didn't help PostgreSQL because the query has no time filter, so every row has to be scanned regardless.

PostgreSQL would win on the opposite workload: single-row lookups by indexed key, or transactional updates. The two engines target different problems (OLTP vs OLAP); this benchmark is firmly OLAP territory.

## Files

- `docker-compose.yml` — Postgres + ClickHouse containers
- `schema_postgres.sql`, `schema_clickhouse.sql` — matching table definitions
- `query.sql` — the analytical query (same SQL for both engines)
- `load.py` — downloads the parquet file, converts to CSV, loads both DBs
- `benchmark.py` — runs the query in both engines, reports cold/warm timings, verifies result equality

## How to reproduce

```bash
docker compose up -d
python load.py
python benchmark.py
```
