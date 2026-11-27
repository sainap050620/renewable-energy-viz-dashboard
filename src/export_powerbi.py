"""Export the hourly dataset as a star schema for the Power BI report.

Usage (from the repository root):
    python -m src.export_powerbi
"""
from pathlib import Path

import pandas as pd

from src.pipeline import generate_renewable_dataset

OUTPUT = Path("data/processed")


def build_star_schema(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split the flat hourly series into one fact table and two dimensions."""
    dates = pd.DataFrame({"full_date": df["timestamp"].dt.normalize().drop_duplicates()})
    dates = dates.sort_values("full_date").reset_index(drop=True)
    dates.insert(0, "date_id", dates.index + 1)
    dates["year"] = dates["full_date"].dt.year
    dates["month"] = dates["full_date"].dt.month
    dates["year_month"] = dates["full_date"].dt.strftime("%Y-%m")

    zones = df[["tso_zone"]].drop_duplicates().reset_index(drop=True)
    zones.insert(0, "zone_id", zones.index + 1)

    fact = df.assign(full_date=df["timestamp"].dt.normalize(), hour=df["timestamp"].dt.hour)
    fact = fact.merge(dates[["date_id", "full_date"]], on="full_date").merge(zones, on="tso_zone")
    fact = fact[[
        "date_id", "zone_id", "hour", "solar_mw", "wind_mw", "total_renewable_mw",
        "grid_demand_mw", "curtailment_mw", "residual_load_mw", "renewable_share_pct",
    ]].round(2)
    return {"dim_date": dates, "dim_zone": zones, "fact_generation": fact}


def export() -> None:
    tables = build_star_schema(generate_renewable_dataset())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(OUTPUT / f"{name}.csv", index=False, date_format="%Y-%m-%d", lineterminator="\n")
        print(f"{name}: {len(table)} rows -> {OUTPUT / name}.csv")


if __name__ == "__main__":
    export()
