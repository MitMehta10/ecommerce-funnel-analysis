"""Sanity checks for the funnel pipeline (run with: pytest)."""
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import generate_data  # noqa: E402


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    sessions, events, orders = generate_data.build()
    db = tmp_path_factory.mktemp("db") / "t.db"
    c = sqlite3.connect(db)
    for name, df in [("sessions", sessions), ("events", events), ("orders", orders)]:
        df = df.copy()
        for col in df.columns:
            if str(df[col].dtype).startswith("datetime"):
                df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        df.to_sql(name, c, index=False)
    yield c
    c.close()


def sql(name: str, **fmt) -> str:
    text = (ROOT / "sql" / name).read_text()
    return text.format(**fmt) if fmt else text


def test_data_is_reproducible():
    a = generate_data.build()[2]
    b = generate_data.build()[2]
    assert a.equals(b)


def test_funnel_is_monotonic(con):
    rows = con.execute(sql("01_funnel_overall.sql")).fetchall()
    counts = [r[1] for r in rows]
    assert counts == sorted(counts, reverse=True)


def test_every_order_has_a_purchase_event(con):
    orders = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    purchases = con.execute(
        "SELECT COUNT(*) FROM events WHERE event_type='purchase'"
    ).fetchone()[0]
    assert orders == purchases


@pytest.mark.parametrize("segment", ["source", "device"])
def test_segment_sessions_sum_to_total(con, segment):
    rows = con.execute(sql("02_funnel_by_segment.sql", segment=segment)).fetchall()
    total = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    assert sum(r[1] for r in rows) == total


def test_revenue_shares_sum_to_100(con):
    rows = con.execute(sql("03_revenue_by_source.sql")).fetchall()
    assert abs(sum(r[6] for r in rows) - 100) < 0.5
    assert abs(sum(r[7] for r in rows) - 100) < 0.5


def test_remaining_queries_run(con):
    assert con.execute(sql("04_weekly_trend.sql")).fetchall()
    assert con.execute(sql("05_repeat_customers.sql")).fetchall()
