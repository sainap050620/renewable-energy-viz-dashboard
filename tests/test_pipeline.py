from pathlib import Path

import pandas as pd
import pytest

from src.export_powerbi import build_star_schema
from src.pipeline import generate_renewable_dataset

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"


def load(name):
    return pd.read_csv(PROCESSED / f"{name}.csv")


def test_export_reproduces_committed_tables(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tables = build_star_schema(generate_renewable_dataset())
    tables["dim_date"]["full_date"] = tables["dim_date"]["full_date"].dt.strftime("%Y-%m-%d")
    for name, table in tables.items():
        pd.testing.assert_frame_equal(
            table.reset_index(drop=True), load(name), check_dtype=False
        )


def test_data_quality_rules_hold():
    """Same rules as the Data Quality page of the Power BI report."""
    fact, dates, zones = load("fact_generation"), load("dim_date"), load("dim_zone")
    assert len(fact) == len(dates) * len(zones) * 24
    assert not fact.duplicated(["date_id", "zone_id", "hour"]).any()
    assert (fact.filter(like="_mw") >= 0).all().all()
    assert (fact["curtailment_mw"] <= fact["total_renewable_mw"]).all()
    assert fact["renewable_share_pct"].between(0, 100).all()
    assert fact["date_id"].isin(dates["date_id"]).all()
    assert fact["zone_id"].isin(zones["zone_id"]).all()


def test_documented_figures():
    """These figures are quoted in the Power BI README."""
    fact = load("fact_generation")
    assert fact["total_renewable_mw"].sum() / 1000 == pytest.approx(278_660.98, abs=0.01)
    assert fact["curtailment_mw"].sum() / 1000 == pytest.approx(2_398.24, abs=0.01)
    assert fact["renewable_share_pct"].mean() == pytest.approx(37.95, abs=0.01)
    assert fact["residual_load_mw"].mean() == pytest.approx(11_361.83, abs=0.01)
    assert (fact["curtailment_mw"] > 0).sum() == 1_226
