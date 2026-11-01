-- Funnel by traffic source and device. One row per segment, one column per stage.
-- Replace the segment column below ('source' or 'device') to switch the cut.
WITH per_session AS (
    SELECT
        s.session_id,
        s.source,
        s.device,
        MAX(e.event_type = 'view_product')   AS viewed,
        MAX(e.event_type = 'add_to_cart')    AS carted,
        MAX(e.event_type = 'begin_checkout') AS checked_out,
        MAX(e.event_type = 'purchase')       AS purchased
    FROM sessions s
    LEFT JOIN events e USING (session_id)
    GROUP BY s.session_id
)
SELECT
    {segment}                                             AS segment,
    COUNT(*)                                              AS sessions,
    SUM(viewed)                                           AS viewed,
    SUM(carted)                                           AS carted,
    SUM(checked_out)                                      AS checked_out,
    SUM(purchased)                                        AS purchased,
    ROUND(100.0 * SUM(carted)      / NULLIF(SUM(viewed), 0), 2)      AS view_to_cart_pct,
    ROUND(100.0 * SUM(checked_out) / NULLIF(SUM(carted), 0), 2)      AS cart_to_checkout_pct,
    ROUND(100.0 * SUM(purchased)   / NULLIF(SUM(checked_out), 0), 2) AS checkout_to_purchase_pct,
    ROUND(100.0 * SUM(purchased)   / COUNT(*), 2)                    AS session_conversion_pct
FROM per_session
GROUP BY {segment}
ORDER BY session_conversion_pct DESC;
