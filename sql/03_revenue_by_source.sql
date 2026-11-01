-- Revenue quality by source: orders, AOV, and revenue per session (RPS).
-- RPS puts low-converting but high-volume channels on the same footing as the rest.
WITH src AS (
    SELECT source, COUNT(*) AS sessions FROM sessions GROUP BY source
),
rev AS (
    SELECT s.source,
           COUNT(o.order_id)  AS orders,
           SUM(o.revenue)     AS revenue
    FROM orders o
    JOIN sessions s USING (session_id)
    GROUP BY s.source
)
SELECT
    src.source,
    src.sessions,
    rev.orders,
    ROUND(rev.revenue, 0)                          AS revenue,
    ROUND(rev.revenue / rev.orders, 2)             AS aov,
    ROUND(rev.revenue / src.sessions, 3)           AS revenue_per_session,
    ROUND(100.0 * rev.revenue / SUM(rev.revenue) OVER (), 1) AS pct_of_revenue,
    ROUND(100.0 * src.sessions / SUM(src.sessions) OVER (), 1) AS pct_of_sessions
FROM src
JOIN rev USING (source)
ORDER BY revenue_per_session DESC;
