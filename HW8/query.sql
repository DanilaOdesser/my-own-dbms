-- Analytical query: per hour-of-day across all of January 2024,
-- compute trip count, average distance, average fare, average tip percentage.
-- Filters out free rides and missing data. Aggregation over ~3M rows,
-- touches only 4 columns out of 19. This is the classic shape where
-- columnar storage wins.
--
-- This file is the Postgres dialect. EXTRACT(HOUR FROM ts) is standard SQL
-- and works as-is in Clickhouse too, but Clickhouse also accepts toHour(ts).
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
