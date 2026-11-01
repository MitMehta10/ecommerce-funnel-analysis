-- Repeat-purchase behavior: how many buyers come back, and how soon?
WITH ranked AS (
    SELECT
        user_id,
        order_id,
        order_ts,
        revenue,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_ts) AS order_n,
        LAG(order_ts) OVER (PARTITION BY user_id ORDER BY order_ts) AS prev_order_ts
    FROM orders
),
per_user AS (
    SELECT user_id, COUNT(*) AS orders, SUM(revenue) AS ltv
    FROM ranked
    GROUP BY user_id
)
SELECT
    COUNT(*)                                                       AS buyers,
    SUM(orders > 1)                                                AS repeat_buyers,
    ROUND(100.0 * SUM(orders > 1) / COUNT(*), 2)                   AS repeat_rate_pct,
    ROUND(AVG(ltv), 2)                                             AS avg_ltv,
    ROUND((SELECT AVG(julianday(order_ts) - julianday(prev_order_ts))
           FROM ranked WHERE order_n = 2), 1)                      AS avg_days_to_2nd_order
FROM per_user;
