# E-commerce Funnel Analysis (SQL + Python)

A funnel and revenue-quality analysis written the way a business analyst would approach a "why is conversion low?" request: define the funnel, cut it by segment, test the biggest gap, and turn the result into a recommendation.

> **About the data:** this repo uses a **simulated** clickstream (60,000 sessions) created by `src/generate_data.py`. Conversion rates by source and device were set by hand, including a deliberate mobile checkout problem, so the analysis has something realistic to find. Nothing here is real customer data, and the findings describe the simulated dataset only. The point of the project is the method and the SQL.

## Business question

Where do shoppers drop out of the purchase funnel, which traffic sources are actually worth the most, and what should the team fix first?

## What's inside

| Path | Purpose |
|---|---|
| `src/generate_data.py` | Builds a seeded SQLite database (`sessions`, `events`, `orders`) |
| `sql/01_funnel_overall.sql` | Stage counts, step conversion and drop-off (CTE + `LAG`, `FIRST_VALUE`) |
| `sql/02_funnel_by_segment.sql` | Funnel by source or device (conditional aggregation) |
| `sql/03_revenue_by_source.sql` | Orders, AOV, revenue per session, share of revenue vs share of traffic |
| `sql/04_weekly_trend.sql` | Weekly conversion with WoW change and 4-week rolling average |
| `sql/05_repeat_customers.sql` | Repeat-purchase rate, LTV, days to second order |
| `src/analyze.py` | Runs the SQL, runs a chi-square test, writes CSVs, charts and `outputs/dashboard.html` |
| `outputs/` | Result tables, charts, and a self-contained HTML dashboard |
| `tests/test_pipeline.py` | Sanity checks: reproducible data, monotonic funnel, segment totals reconcile |
| `.github/workflows/ci.yml` | GitHub Actions: runs tests on Python 3.11 and 3.12, rebuilds the dashboard weekly, and uploads it as a build artifact |

## Run it

```bash
pip install -r requirements.txt
python src/generate_data.py
python src/analyze.py
# open outputs/dashboard.html in a browser
```

## Findings (simulated data)

1. **Biggest leak is add-to-cart.** Only 13.7% of product viewers add to cart, so 86% drop out at that step. Cart-to-checkout (60.1%) and checkout-to-purchase (59.4%) are comparatively healthy.
2. **Mobile checkout is the clearest fixable problem.** Mobile is 58% of sessions but only 45.5% of mobile checkouts finish, versus 75.3% on desktop (chi-square p < 0.001). Overall session conversion is 2.72% on mobile versus 6.27% on desktop.
3. **Source quality varies by 7x.** Email earns $7.07 per session and social earns $0.99. Social is 20.3% of traffic but only 6.2% of revenue. Paid search and organic search sit in the middle.
4. **Repeat purchasing is weak.** Only 3.6% of buyers purchased more than once in the 6-month window, with about 62 days to the second order.

## Recommendations

- **Run a mobile checkout audit first** (payment step, form fields, wallet payments). Closing even half of the mobile-to-desktop gap in checkout completion is the largest single lever in this dataset.
- **Shift spend toward email and direct-style lifecycle channels** and re-evaluate social spend against revenue per session, not sessions.
- **Test a post-purchase reorder nudge** around day 45-60 to improve the repeat rate.
- **Validate the add-to-cart drop** with product-page testing (pricing, shipping cost visibility) before investing in checkout changes alone.

## Limitations

- Simulated data, so effect sizes are illustrative, not benchmarks.
- The first and last weeks in the weekly trend are partial weeks.
- Sessions are treated as the unit of conversion; no multi-session attribution is modeled.
- Mobile vs desktop differences are observational. A real project would confirm them with an A/B test on the fixed checkout.

## Skills shown

SQL (CTEs, window functions, conditional aggregation), funnel and cohort-style analysis, KPI definition, hypothesis testing (chi-square), Python (pandas, SciPy, matplotlib), dashboarding, and turning analysis into recommendations.
