"""Download Yellow Taxi Jan 2024 Parquet, load into Postgres and Clickhouse.

Postgres: COPY FROM CSV (the standard fast path).
Clickhouse: INSERT FROM Parquet directly (its standard fast path).

We measure load time for each so the README can compare ingestion as well.
"""

import io
import os
import sys
import time
from pathlib import Path

import clickhouse_connect
import psycopg2
import pyarrow.parquet as pq
import pyarrow.csv as pv_csv
import requests

HERE = Path(__file__).parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)

PARQUET_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet"
PARQUET_PATH = DATA / "yellow_tripdata_2024-01.parquet"
CSV_PATH = DATA / "yellow_tripdata_2024-01.csv"

PG_DSN = "dbname=taxi user=bench password=bench host=localhost port=5433"
CH_HOST = "localhost"
CH_PORT = 8124
CH_USER = "bench"
CH_PASSWORD = "bench"
CH_DB = "taxi"

COLUMN_RENAME = {
    "VendorID": "vendor_id",
    "tpep_pickup_datetime": "pickup_datetime",
    "tpep_dropoff_datetime": "dropoff_datetime",
    "passenger_count": "passenger_count",
    "trip_distance": "trip_distance",
    "RatecodeID": "ratecode_id",
    "store_and_fwd_flag": "store_and_fwd_flag",
    "PULocationID": "pu_location_id",
    "DOLocationID": "do_location_id",
    "payment_type": "payment_type",
    "fare_amount": "fare_amount",
    "extra": "extra",
    "mta_tax": "mta_tax",
    "tip_amount": "tip_amount",
    "tolls_amount": "tolls_amount",
    "improvement_surcharge": "improvement_surcharge",
    "total_amount": "total_amount",
    "congestion_surcharge": "congestion_surcharge",
    "Airport_fee": "airport_fee",
}
ORDERED_COLUMNS = list(COLUMN_RENAME.values())


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def download_parquet() -> None:
    if PARQUET_PATH.exists():
        log(f"Parquet already at {PARQUET_PATH} ({PARQUET_PATH.stat().st_size / 1e6:.1f} MB)")
        return
    log(f"Downloading {PARQUET_URL}")
    t0 = time.time()
    with requests.get(PARQUET_URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(PARQUET_PATH, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
    log(f"Downloaded {PARQUET_PATH.stat().st_size / 1e6:.1f} MB in {time.time() - t0:.1f}s")


def parquet_to_csv() -> None:
    if CSV_PATH.exists():
        log(f"CSV already at {CSV_PATH} ({CSV_PATH.stat().st_size / 1e6:.1f} MB)")
        return
    log("Converting parquet -> csv with renamed columns")
    t0 = time.time()
    table = pq.read_table(str(PARQUET_PATH))
    new_names = [COLUMN_RENAME[c] for c in table.column_names]
    table = table.rename_columns(new_names)
    # Pyarrow's CSV writer handles datetimes/floats/nulls cleanly.
    pv_csv.write_csv(table, str(CSV_PATH))
    log(f"CSV written in {time.time() - t0:.1f}s ({CSV_PATH.stat().st_size / 1e6:.1f} MB)")


def apply_schema_postgres() -> None:
    sql = (HERE / "schema_postgres.sql").read_text()
    with psycopg2.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()
    log("Postgres schema applied")


def apply_schema_clickhouse() -> None:
    sql = (HERE / "schema_clickhouse.sql").read_text()
    client = clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD, database=CH_DB
    )
    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
        client.command(stmt)
    log("Clickhouse schema applied")


def load_postgres() -> float:
    log("Postgres: COPY trips FROM csv")
    t0 = time.time()
    with psycopg2.connect(PG_DSN) as conn, conn.cursor() as cur:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            cur.copy_expert(
                f"COPY trips ({', '.join(ORDERED_COLUMNS)}) "
                "FROM STDIN WITH (FORMAT CSV, HEADER TRUE)",
                f,
            )
        conn.commit()
        cur.execute("ANALYZE trips")
    dt = time.time() - t0
    log(f"Postgres load: {dt:.1f}s")
    return dt


def load_clickhouse() -> float:
    log("Clickhouse: INSERT trips FORMAT CSVWithNames via HTTP")
    t0 = time.time()
    # The HTTP interface is the simplest route for a streaming CSV insert.
    url = f"http://{CH_HOST}:{CH_PORT}/"
    params = {
        "query": "INSERT INTO trips FORMAT CSVWithNames",
        "database": CH_DB,
        "input_format_null_as_default": 1,
    }
    with open(CSV_PATH, "rb") as f:
        r = requests.post(url, params=params, data=f, auth=(CH_USER, CH_PASSWORD), timeout=300)
    r.raise_for_status()
    dt = time.time() - t0
    log(f"Clickhouse load: {dt:.1f}s")
    return dt


def verify_counts() -> None:
    with psycopg2.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM trips")
        pg_count = cur.fetchone()[0]
    client = clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD, database=CH_DB
    )
    ch_count = client.command("SELECT count() FROM trips")
    log(f"Postgres rows: {pg_count:,}")
    log(f"Clickhouse rows: {ch_count:,}")
    if pg_count != ch_count:
        log("WARNING: row counts differ!")
        sys.exit(1)
    log("Row counts match.")


def main() -> None:
    download_parquet()
    parquet_to_csv()
    apply_schema_postgres()
    apply_schema_clickhouse()
    pg_dt = load_postgres()
    ch_dt = load_clickhouse()
    verify_counts()
    log(f"Summary: PG load {pg_dt:.1f}s, CH load {ch_dt:.1f}s")


if __name__ == "__main__":
    main()
