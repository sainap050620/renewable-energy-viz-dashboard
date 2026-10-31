import pandas as pd
import numpy as np

def generate_renewable_dataset():
    """Generates realistic German TSO-level renewable generation & grid feed-in data."""
    dates = pd.date_range(start="2025-01-01", end="2025-12-31 23:00:00", freq="h")
    np.random.seed(42)
    n = len(dates)

    tso_zones = ["TenneT", "50Hertz", "Amprion", "TransnetBW"]
    records = []

    for tso in tso_zones:
        # Seasonality factors
        day_of_year = dates.dayofyear.values
        hour = dates.hour.values

        # Solar peaks in summer midday
        solar_base = np.maximum(0, np.sin((hour - 6) * np.pi / 12)) * (1 + 0.5 * np.sin(day_of_year * 2 * np.pi / 365))
        solar_mw = (solar_base * (18000 if tso in ["TenneT", "Amprion"] else 9000) * np.random.uniform(0.7, 1.1, n)).round(1)

        # Wind peaks in winter and autumn (higher in northern TSOs: TenneT, 50Hertz)
        wind_seasonal = 1 + 0.6 * np.cos(day_of_year * 2 * np.pi / 365)
        wind_factor = 28000 if tso == "TenneT" else (16000 if tso == "50Hertz" else 7000)
        wind_mw = (wind_seasonal * wind_factor * np.random.beta(2, 5, n)).round(1)

        # Grid Load / Demand
        demand_mw = (15000 + 7000 * np.sin((hour - 8) * np.pi / 12) + 4000 * np.random.uniform(0.9, 1.1, n)).round(1)

        # Total generation & curtailment (redispatch when renewables overshoot local capacity)
        total_renewables = solar_mw + wind_mw
        curtailment_mw = np.where(total_renewables > demand_mw * 1.15, (total_renewables - demand_mw * 1.15) * 0.4, 0).round(1)
        residual_load = np.maximum(0, demand_mw - (total_renewables - curtailment_mw)).round(1)

        df_tso = pd.DataFrame({
            "timestamp": dates,
            "tso_zone": tso,
            "solar_mw": solar_mw,
            "wind_mw": wind_mw,
            "total_renewable_mw": total_renewables,
            "grid_demand_mw": demand_mw,
            "curtailment_mw": curtailment_mw,
            "residual_load_mw": residual_load,
            "renewable_share_pct": np.minimum(100.0, (total_renewables / demand_mw * 100)).round(2)
        })
        records.append(df_tso)

    full_df = pd.concat(records, ignore_index=True)
    full_df.to_parquet("data/renewable_energy_timeseries.parquet", index=False)
    print("Dataset generated successfully: data/renewable_energy_timeseries.parquet")
    return full_df

if __name__ == "__main__":
    generate_renewable_dataset()
