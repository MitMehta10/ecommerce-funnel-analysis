-- Overall funnel: how many sessions reach each stage, and where do they drop?
WITH stage_counts AS (
    SELECT 'sessions'       AS stage, 0 AS stage_order, COUNT(*) AS sessions FROM sessions
    UNION ALL
    SELECT event_type,
           CASE event_type
                WHEN 'view_product'   THEN 1
                WHEN 'add_to_cart'    THEN 2
                WHEN 'begin_checkout' THEN 3
                WHEN 'purchase'       THEN 4
           END,
           COUNT(DISTINCT session_id)
    FROM events
    GROUP BY event_type
)
SELECT
    stage,
    sessions,
    ROUND(100.0 * sessions / FIRST_VALUE(sessions) OVER (ORDER BY stage_order), 2) AS pct_of_all_sessions,
    ROUND(100.0 * sessions / LAG(sessions) OVER (ORDER BY stage_order), 2)         AS step_conversion_pct,
    ROUND(100.0 - 100.0 * sessions / LAG(sessions) OVER (ORDER BY stage_order), 2) AS step_dropoff_pct
FROM stage_counts
ORDER BY stage_order;
