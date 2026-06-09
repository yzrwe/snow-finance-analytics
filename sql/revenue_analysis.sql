-- Quarterly revenue analysis: growth, bridges, and trend flags.
-- Snowflake SQL. Source: FINANCE.REPORTING.QUARTERLY_METRICS
-- (one row per fiscal quarter; see data/snow_quarterly_metrics.csv for shape).

WITH base AS (
    SELECT
        fiscal_quarter,
        fiscal_year,
        quarter_end,
        product_revenue_m,
        nrr_pct,
        rpo_b,
        customers_1m_plus,
        -- Dedupe defensively in case of restated rows: keep latest load
        ROW_NUMBER() OVER (
            PARTITION BY fiscal_quarter
            ORDER BY quarter_end DESC
        ) AS rn
    FROM finance.reporting.quarterly_metrics
),

deduped AS (
    SELECT * FROM base WHERE rn = 1
),

growth AS (
    SELECT
        d.*,
        LAG(product_revenue_m, 1) OVER w AS prior_q_rev,
        LAG(product_revenue_m, 4) OVER w AS prior_yr_rev,
        product_revenue_m
            - LAG(product_revenue_m, 1) OVER w           AS seq_dollar_add_m,
        ROUND(product_revenue_m
            / NULLIF(LAG(product_revenue_m, 1) OVER w, 0) - 1, 4) AS qoq_growth,
        ROUND(product_revenue_m
            / NULLIF(LAG(product_revenue_m, 4) OVER w, 0) - 1, 4) AS yoy_growth
    FROM deduped d
    WINDOW w AS (ORDER BY quarter_end)
),

trend AS (
    SELECT
        g.*,
        AVG(yoy_growth) OVER (
            ORDER BY quarter_end
            ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING
        ) AS trailing_4q_avg_yoy,
        AVG(nrr_pct) OVER (
            ORDER BY quarter_end
            ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING
        ) AS trailing_4q_avg_nrr
    FROM growth g
)

SELECT
    fiscal_quarter,
    product_revenue_m,
    seq_dollar_add_m,
    qoq_growth,
    yoy_growth,
    trailing_4q_avg_yoy,
    nrr_pct,
    rpo_b,
    customers_1m_plus,
    -- Flag re-acceleration / deceleration > 2pts vs. trailing trend
    CASE
        WHEN yoy_growth - trailing_4q_avg_yoy >  0.02 THEN 'RE-ACCELERATING'
        WHEN yoy_growth - trailing_4q_avg_yoy < -0.02 THEN 'DECELERATING'
        ELSE 'IN-TREND'
    END AS growth_flag,
    CASE
        WHEN nrr_pct - trailing_4q_avg_nrr < -2 THEN 'NRR EROSION'
        ELSE 'OK'
    END AS retention_flag
FROM trend
ORDER BY quarter_end;
