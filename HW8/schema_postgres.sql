DROP TABLE IF EXISTS trips;

CREATE TABLE trips (
    vendor_id              SMALLINT,
    pickup_datetime        TIMESTAMP NOT NULL,
    dropoff_datetime       TIMESTAMP NOT NULL,
    passenger_count        REAL,
    trip_distance          REAL,
    ratecode_id            REAL,
    store_and_fwd_flag     CHAR(1),
    pu_location_id         INTEGER,
    do_location_id         INTEGER,
    payment_type           SMALLINT,
    fare_amount            REAL,
    extra                  REAL,
    mta_tax                REAL,
    tip_amount             REAL,
    tolls_amount           REAL,
    improvement_surcharge  REAL,
    total_amount           REAL,
    congestion_surcharge   REAL,
    airport_fee            REAL
);

CREATE INDEX idx_trips_pickup ON trips (pickup_datetime);
