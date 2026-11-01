-- Weekly sessions, orders, conversion, and week-over-week change (window functions).
WITH weekly AS (
    SELECT
        DATE(s.session_start, 'weekday 0', '-6 days')        AS week_start,
        COUNT(DISTINCT s.session_id)                         AS sessions,
        COUNT(DISTINCT o.order_id)                           AS orders,
        COALESCE(SUM(o.revenue), 0)                          AS revenue
    FROM sessions s
    LEFT JOIN orders o USING (session_id)
    GROUP BY week_start
)
SELECT
    week_start,
    sessions,
    orders,
    ROUND(revenue, 0)                                       AS revenue,
    ROUND(100.0 * orders / sessions, 2)                     AS conversion_pct,
    ROUND(100.0 * (orders * 1.0 / sessions
        - LAG(orders * 1.0 / sessions) OVER (ORDER BY week_start))
        / NULLIF(LAG(orders * 1.0 / sessions) OVER (ORDER BY week_start), 0), 1) AS conv_wow_pct,
    ROUND(AVG(100.0 * orders / sessions)
        OVER (ORDER BY week_start ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 2)  AS conv_4wk_avg_pct
FROM weekly
ORDER BY week_start;
