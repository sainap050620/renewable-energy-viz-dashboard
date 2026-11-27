# German Renewable Feed-In: Power BI version

A Power BI rebuild of the Streamlit dashboard in this repo, on a star schema
(`fact_generation` + `dim_date`, `dim_zone`) exported by `python -m src.export_powerbi`.
The data is **synthetic** (hourly values for 2025).

| Layer | What it contains |
|---|---|
| **Power Query (M)** | One reusable `GetCsv` function, a `DataBaseUrl` parameter, typed columns and a `dq_checks` query |
| **Data model** | Two one-to-many relationships and a marked date table (`dim_date[full_date]`) |
| **DAX** | 17 measures: generation and curtailment, average power, month-over-month, zone share and ranking |
| **Report** | Grid Overview, Curtailment, Zones and Growth, Data Quality |

## Open it

1. In Power BI Desktop, make sure the preview features **Power BI Project (.pbip) save option**,
   **Store semantic model using TMDL format** and **Store reports using enhanced metadata format (PBIR)**
   are on (File, Options and settings, Options, Preview features), then restart Desktop.
   Newer versions may already have them on.
2. Open `Renewable_Energy.pbip`.
3. A PBIP stores no data, so click **Refresh**. When asked how to connect to
   `raw.githubusercontent.com`, choose **Anonymous**. The default address reads the files on the `main` branch.
4. To load local files instead: Home, Transform data, Manage parameters, set `DataBaseUrl`
   to the full path of `data\\processed` in your clone.
5. Save as `.pbix` (File, Save as) if you want a single file to share or publish.

If the project will not open, use `fallback/`: create a blank report, paste each query from
`PowerQuery_queries.m` (create `DataBaseUrl` as a text parameter first), set the relationships and
mark `dim_date` as a date table,
then paste the measures from `DAX_measures.dax`.

## Expected figures (no filters)

Renewable generation **278,661 GWh**, curtailed **2,398 GWh** (loss **0.86%**), average renewable share
**38.0%**, average residual load **11,362 MW**, zone-hours with curtailment **1,226**.

| TSO zone | Generation GWh | Share of generation | Curtailed GWh | Loss % | Avg renewable share |
|---|---|---|---|---|---|
| TenneT | 114,178 | 41.0% | 2,339 | 2.05% | 60.5% |
| Amprion | 62,446 | 22.4% | 38 | 0.06% | 32.8% |
| 50Hertz | 62,309 | 22.4% | 21 | 0.03% | 36.5% |
| TransnetBW | 39,727 | 14.3% | 0 | 0.00% | 22.0% |

Curtailment peaks at hour **11** (average **232 MW** per zone-hour). Month-over-month growth is blank for
January 2025 and **-6.6%** for February. All seven data-quality checks should show PASS.

## Verification status

- The semantic model loads in Microsoft's TMDL parser (`Microsoft.AnalysisServices`) with no validation errors.
- The report JSON files that declare a `$schema` validate against Microsoft's published schemas.
- The Power Query code passes Microsoft's Power Query parser (syntax only).
- `tests/test_powerbi.py` checks that visuals only use fields that exist in the model and that the
  fallback files match the model.
- The project has **not yet been opened and refreshed in Power BI Desktop**, so the Power Query and DAX
  code has not been executed. Use the expected figures above to confirm it on first refresh.
