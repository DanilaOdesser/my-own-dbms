DROP TABLE IF EXISTS trips;

CREATE TABLE trips (
    vendor_id              Nullable(Int16),
    pickup_datetime        DateTime64(6),
    dropoff_datetime       DateTime64(6),
    passenger_count        Nullable(Float32),
    trip_distance          Nullable(Float32),
    ratecode_id            Nullable(Float32),
    store_and_fwd_flag     Nullable(FixedString(1)),
    pu_location_id         Nullable(Int32),
    do_location_id         Nullable(Int32),
    payment_type           Nullable(Int16),
    fare_amount            Nullable(Float32),
    extra                  Nullable(Float32),
    mta_tax                Nullable(Float32),
    tip_amount             Nullable(Float32),
    tolls_amount           Nullable(Float32),
    improvement_surcharge  Nullable(Float32),
    total_amount           Nullable(Float32),
    congestion_surcharge   Nullable(Float32),
    airport_fee            Nullable(Float32)
)
ENGINE = MergeTree
ORDER BY pickup_datetime;
