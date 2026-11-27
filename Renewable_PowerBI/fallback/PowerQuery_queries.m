// ===== GetCsv (function; needs parameter DataBaseUrl) =====
(fileName as text) as table =>
let
    // DataBaseUrl is a parameter: an https:// folder URL (default: the GitHub repo)
    // or a local folder path such as C:\Data\processed
    Source =
        if Text.StartsWith(DataBaseUrl, "http") then
            Csv.Document(
                Web.Contents(DataBaseUrl, [RelativePath = fileName]),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
            )
        else
            Csv.Document(
                File.Contents(DataBaseUrl & "\" & fileName),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
            ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
in
    Promoted

// ===== fact_generation =====
let
    Source = GetCsv("fact_generation.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"date_id", Int64.Type},
            {"zone_id", Int64.Type},
            {"hour", Int64.Type},
            {"solar_mw", type number},
            {"wind_mw", type number},
            {"total_renewable_mw", type number},
            {"grid_demand_mw", type number},
            {"curtailment_mw", type number},
            {"residual_load_mw", type number},
            {"renewable_share_pct", type number}
        },
        "en-US"
    )
in
    Typed

// ===== dim_date =====
let
    Source = GetCsv("dim_date.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"date_id", Int64.Type},
            {"full_date", type date},
            {"year", Int64.Type},
            {"month", Int64.Type},
            {"year_month", type text}
        },
        "en-US"
    )
in
    Typed

// ===== dim_zone =====
let
    Source = GetCsv("dim_zone.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"zone_id", Int64.Type},
            {"tso_zone", type text}
        },
        "en-US"
    )
in
    Typed

// ===== dq_checks =====
let
    // Violations are reported instead of stopping the refresh, so the report can show them.
    Checks = #table(
        type table [Check = text, Rule = text, Violations = Int64.Type],
        {
            {"Hourly series is complete", "One row per day, zone and hour",
                Number.Abs(Table.RowCount(fact_generation) - Table.RowCount(dim_date) * Table.RowCount(dim_zone) * 24)},
            {"No duplicate readings", "date_id, zone_id and hour are unique",
                Table.RowCount(fact_generation) - Table.RowCount(Table.Distinct(fact_generation, {"date_id", "zone_id", "hour"}))},
            {"Power is not negative", "All MW columns >= 0",
                Table.RowCount(Table.SelectRows(fact_generation, each [solar_mw] < 0 or [wind_mw] < 0 or [total_renewable_mw] < 0 or [grid_demand_mw] < 0 or [curtailment_mw] < 0 or [residual_load_mw] < 0))},
            {"Curtailment is plausible", "curtailment_mw <= total_renewable_mw",
                Table.RowCount(Table.SelectRows(fact_generation, each [curtailment_mw] > [total_renewable_mw]))},
            {"Renewable share in range", "0 to 100 percent",
                Table.RowCount(Table.SelectRows(fact_generation, each [renewable_share_pct] < 0 or [renewable_share_pct] > 100))},
            {"Date keys resolve", "fact.date_id exists in dim_date",
                List.Count(List.Difference(List.Distinct(fact_generation[date_id]), dim_date[date_id]))},
            {"Zone keys resolve", "fact.zone_id exists in dim_zone",
                List.Count(List.Difference(List.Distinct(fact_generation[zone_id]), dim_zone[zone_id]))}
        }
    ),
    WithStatus = Table.AddColumn(
        Checks, "Status", each if [Violations] = 0 then "PASS" else "FAIL", type text
    )
in
    WithStatus
