"""Generate a SYNTHETIC e-commerce clickstream dataset.

This data is simulated, not real customer data. Conversion rates by traffic
source and device are set by hand so the analysis has realistic patterns to
find (for example, mobile checkout friction). Findings in this repo describe
this simulated dataset only.

Usage:
    python src/generate_data.py            # writes data/ecommerce.db
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_SESSIONS = 60_000
START = pd.Timestamp("2025-01-01")
DAYS = 180

# Probability of moving from one funnel stage to the next, by source.
# Order: view_product -> add_to_cart -> begin_checkout -> purchase
SOURCE_PARAMS = {
    #            share, P(view), P(cart|view), P(checkout|cart), P(buy|checkout)
    "organic_search": (0.30, 0.85, 0.12, 0.60, 0.62),
    "paid_search":    (0.22, 0.88, 0.14, 0.58, 0.60),
    "social":         (0.20, 0.70, 0.07, 0.50, 0.52),
    "email":          (0.13, 0.92, 0.22, 0.68, 0.72),
    "direct":         (0.10, 0.90, 0.17, 0.64, 0.70),
    "referral":       (0.05, 0.82, 0.10, 0.56, 0.58),
}

# Device multipliers on stage transitions. Mobile has a planted
# checkout -> purchase penalty (friction in the payment step).
DEVICE_SHARE = {"mobile": 0.58, "desktop": 0.36, "tablet": 0.06}
DEVICE_MULT = {
    "mobile":  {"view": 1.00, "cart": 0.95, "checkout": 0.92, "buy": 0.68},
    "desktop": {"view": 1.00, "cart": 1.10, "checkout": 1.08, "buy": 1.15},
    "tablet":  {"view": 1.00, "cart": 1.00, "checkout": 1.00, "buy": 0.95},
}

STAGES = ["view_product", "add_to_cart", "begin_checkout", "purchase"]


def build(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    sources = list(SOURCE_PARAMS)
    src_p = np.array([SOURCE_PARAMS[s][0] for s in sources])
    src_p = src_p / src_p.sum()
    devices = list(DEVICE_SHARE)
    dev_p = np.array([DEVICE_SHARE[d] for d in devices])

    session_id = np.arange(1, N_SESSIONS + 1)
    user_id = rng.integers(1, int(N_SESSIONS * 0.6), N_SESSIONS)
    source = rng.choice(sources, N_SESSIONS, p=src_p)
    device = rng.choice(devices, N_SESSIONS, p=dev_p)
    day_offset = rng.integers(0, DAYS, N_SESSIONS)
    session_start = (
        START
        + pd.to_timedelta(day_offset, unit="D")
        + pd.to_timedelta(rng.integers(0, 86_400, N_SESSIONS), unit="s")
    )

    sessions = pd.DataFrame(
        {
            "session_id": session_id,
            "user_id": user_id,
            "source": source,
            "device": device,
            "session_start": session_start,
        }
    )

    events, orders = [], []
    order_id = 1
    for row in sessions.itertuples(index=False):
        _, p_view, p_cart, p_chk, p_buy = SOURCE_PARAMS[row.source]
        m = DEVICE_MULT[row.device]
        probs = [
            min(p_view * m["view"], 0.99),
            min(p_cart * m["cart"], 0.99),
            min(p_chk * m["checkout"], 0.99),
            min(p_buy * m["buy"], 0.99),
        ]
        t = row.session_start
        for stage, p in zip(STAGES, probs):
            if rng.random() > p:
                break
            t = t + pd.Timedelta(seconds=int(rng.integers(15, 240)))
            events.append((row.session_id, stage, t))
            if stage == "purchase":
                revenue = float(np.round(rng.lognormal(mean=4.2, sigma=0.55), 2))
                orders.append((order_id, row.session_id, row.user_id, t, revenue))
                order_id += 1

    events = pd.DataFrame(events, columns=["session_id", "event_type", "event_ts"])
    orders = pd.DataFrame(
        orders, columns=["order_id", "session_id", "user_id", "order_ts", "revenue"]
    )
    return sessions, events, orders


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "data" / "ecommerce.db"
    out.parent.mkdir(exist_ok=True)
    sessions, events, orders = build()
    if out.exists():
        out.unlink()
    with sqlite3.connect(out) as con:
        for name, df in [("sessions", sessions), ("events", events), ("orders", orders)]:
            df = df.copy()
            for col in df.columns:
                if str(df[col].dtype).startswith("datetime"):
                    df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            df.to_sql(name, con, index=False)
        con.execute("CREATE INDEX idx_events_session ON events(session_id)")
        con.execute("CREATE INDEX idx_sessions_source ON sessions(source)")
    print(
        f"Wrote {out} | sessions={len(sessions):,} events={len(events):,} "
        f"orders={len(orders):,}"
    )


if __name__ == "__main__":
    main()
