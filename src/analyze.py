"""Run the SQL files, save result tables, draw charts, and build a dashboard.

Usage:
    python src/generate_data.py
    python src/analyze.py
Outputs go to outputs/ (CSV tables, PNG charts, dashboard.html).
"""
import base64
import sqlite3
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import chi2_contingency

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "ecommerce.db"
SQL = ROOT / "sql"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

BLUE, ORANGE, GRAY = "#2b6cb0", "#dd6b20", "#a0aec0"


def run(con, filename, **fmt) -> pd.DataFrame:
    text = (SQL / filename).read_text()
    return pd.read_sql_query(text.format(**fmt) if fmt else text, con)


def fig_to_b64(fig) -> str:
    path = OUT / "_tmp.png"
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    data = base64.b64encode(path.read_bytes()).decode()
    path.unlink()
    return data


def main() -> None:
    con = sqlite3.connect(DB)

    overall = run(con, "01_funnel_overall.sql")
    by_source = run(con, "02_funnel_by_segment.sql", segment="source")
    by_device = run(con, "02_funnel_by_segment.sql", segment="device")
    revenue = run(con, "03_revenue_by_source.sql")
    weekly = run(con, "04_weekly_trend.sql")
    repeat = run(con, "05_repeat_customers.sql")

    for name, df in {
        "funnel_overall": overall,
        "funnel_by_source": by_source,
        "funnel_by_device": by_device,
        "revenue_by_source": revenue,
        "weekly_trend": weekly,
        "repeat_customers": repeat,
    }.items():
        df.to_csv(OUT / f"{name}.csv", index=False)

    # --- Significance test: mobile vs desktop checkout -> purchase ---
    d = by_device.set_index("segment")
    table = [
        [d.loc["mobile", "purchased"], d.loc["mobile", "checked_out"] - d.loc["mobile", "purchased"]],
        [d.loc["desktop", "purchased"], d.loc["desktop", "checked_out"] - d.loc["desktop", "purchased"]],
    ]
    chi2, p, _, _ = chi2_contingency(table)
    mob_rate = d.loc["mobile", "checkout_to_purchase_pct"]
    desk_rate = d.loc["desktop", "checkout_to_purchase_pct"]
    test_line = (
        f"Checkout-to-purchase: mobile {mob_rate:.1f}% vs desktop {desk_rate:.1f}% "
        f"(chi-square p = {p:.2g})"
    )

    # --- Charts ---
    fig, ax = plt.subplots(figsize=(7, 3.6))
    stages = overall[overall.stage != "sessions"]
    ax.barh(stages.stage[::-1], stages.sessions[::-1], color=BLUE)
    for i, (s, pct) in enumerate(zip(stages.sessions[::-1], stages.step_conversion_pct[::-1])):
        ax.text(s, i, f"  {s:,}  ({pct:.0f}% of prev. step)", va="center", fontsize=8)
    ax.set_xlim(0, stages.sessions.max() * 1.45)
    ax.set_title("Overall funnel (sessions reaching each stage)", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    funnel_b64 = fig_to_b64(fig)

    fig, ax = plt.subplots(figsize=(7, 3.6))
    colors = [ORANGE if s == "mobile" else BLUE for s in by_device.segment]
    ax.bar(by_device.segment, by_device.checkout_to_purchase_pct, color=colors)
    for x, v in zip(by_device.segment, by_device.checkout_to_purchase_pct):
        ax.text(x, v + 0.8, f"{v:.1f}%", ha="center", fontsize=9)
    ax.set_ylabel("Checkout -> purchase (%)")
    ax.set_title("Checkout completion by device", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    device_b64 = fig_to_b64(fig)

    fig, ax = plt.subplots(figsize=(7, 3.6))
    r = revenue.sort_values("revenue_per_session")
    ax.barh(r.source, r.revenue_per_session, color=BLUE)
    for i, v in enumerate(r.revenue_per_session):
        ax.text(v, i, f"  ${v:.2f}", va="center", fontsize=8)
    ax.set_xlim(0, r.revenue_per_session.max() * 1.2)
    ax.set_title("Revenue per session by source", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    rps_b64 = fig_to_b64(fig)

    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(weekly.week_start, weekly.conversion_pct, color=GRAY, label="Weekly")
    ax.plot(weekly.week_start, weekly.conv_4wk_avg_pct, color=BLUE, label="4-week avg")
    ax.set_ylabel("Session conversion (%)")
    ax.set_title("Weekly conversion trend", fontsize=10)
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.set_xticks(ax.get_xticks()[::4])
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    trend_b64 = fig_to_b64(fig)

    for name, b64 in [("funnel", funnel_b64), ("device", device_b64), ("rps", rps_b64), ("trend", trend_b64)]:
        (OUT / f"chart_{name}.png").write_bytes(base64.b64decode(b64))

    # --- Dashboard ---
    def table_html(df: pd.DataFrame) -> str:
        return df.to_html(index=False, border=0, classes="t", float_format=lambda x: f"{x:,.2f}")

    total_sessions = int(overall.loc[overall.stage == "sessions", "sessions"].iloc[0])
    purchases = int(overall.loc[overall.stage == "purchase", "sessions"].iloc[0])
    total_rev = float(revenue.revenue.sum())
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>E-commerce Funnel Dashboard</title>
<style>
body{{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;color:#1a202c}}
h1{{margin-bottom:4px}} .note{{background:#fffaf0;border-left:4px solid #dd6b20;padding:8px 12px;font-size:14px}}
.kpis{{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}}
.kpi{{flex:1;min-width:150px;border:1px solid #e2e8f0;border-radius:8px;padding:12px}}
.kpi b{{display:block;font-size:22px}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px}}
img{{max-width:100%}} table.t{{border-collapse:collapse;font-size:13px;width:100%}}
table.t th,table.t td{{padding:4px 8px;border-bottom:1px solid #e2e8f0;text-align:right}}
table.t th:first-child,table.t td:first-child{{text-align:left}}
</style></head><body>
<h1>E-commerce Funnel Dashboard</h1>
<div class="note">Simulated data. Sessions, events and orders were generated by <code>src/generate_data.py</code>; nothing here is real customer data.</div>
<div class="kpis">
<div class="kpi"><b>{total_sessions:,}</b>sessions</div>
<div class="kpi"><b>{purchases:,}</b>purchasing sessions</div>
<div class="kpi"><b>{100*purchases/total_sessions:.2f}%</b>session conversion</div>
<div class="kpi"><b>${total_rev:,.0f}</b>revenue</div>
</div>
<p><b>Key test:</b> {escape(test_line)}</p>
<div class="grid">
<div><img src="data:image/png;base64,{funnel_b64}" alt="Funnel"></div>
<div><img src="data:image/png;base64,{device_b64}" alt="Device"></div>
<div><img src="data:image/png;base64,{rps_b64}" alt="Revenue per session"></div>
<div><img src="data:image/png;base64,{trend_b64}" alt="Weekly trend"></div>
</div>
<h3>Funnel by traffic source</h3>{table_html(by_source)}
<h3>Funnel by device</h3>{table_html(by_device)}
<h3>Revenue by source</h3>{table_html(revenue)}
<h3>Repeat customers</h3>{table_html(repeat)}
</body></html>"""
    (OUT / "dashboard.html").write_text(html)

    # Print a summary for the README
    print(overall.to_string(index=False), "\n")
    print(by_source.to_string(index=False), "\n")
    print(by_device.to_string(index=False), "\n")
    print(revenue.to_string(index=False), "\n")
    print(repeat.to_string(index=False), "\n")
    print(test_line)


if __name__ == "__main__":
    main()
