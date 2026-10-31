import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.pipeline import generate_renewable_dataset

st.set_page_config(
    page_title="German Energiewende Grid Monitor",
    page_icon="⚡",
    layout="wide"
)

DATA_PATH = "data/renewable_energy_timeseries.parquet"

@st.cache_data
def load_data():
    if not os.path.exists(DATA_PATH):
        generate_renewable_dataset()
    df = pd.read_parquet(DATA_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["month"] = df["timestamp"].dt.to_period("M").astype(str)
    return df

df = load_data()

# Header
st.title("⚡ German Energiewende Grid & Renewable Feed-In Monitor")
st.markdown(
    "Near real-time dispatch transparency dashboard modeling transmission grid integration, "
    "renewable feed-in spikes (Solar/Wind), curtailment events, and residual load across German TSO zones."
)

# Sidebar
st.sidebar.header("Transmission Grid Filters")
selected_tso = st.sidebar.multiselect(
    "Control Area (TSO Zone):",
    options=df["tso_zone"].unique(),
    default=["TenneT", "50Hertz", "Amprion", "TransnetBW"]
)

# Filter data
filtered = df[df["tso_zone"].isin(selected_tso)]

# Executive KPIs
col1, col2, col3, col4 = st.columns(4)
total_gen_gwh = (filtered["total_renewable_mw"].sum() / 1000).round(1)
total_curtailed_gwh = (filtered["curtailment_mw"].sum() / 1000).round(1)
avg_ren_share = filtered["renewable_share_pct"].mean().round(1)
avg_res_load_mw = filtered["residual_load_mw"].mean().round(1)

col1.metric("Renewable Generation", f"{total_gen_gwh:,.0f} GWh")
col2.metric("Curtailed Volume (Redispatch)", f"{total_curtailed_gwh:,.0f} GWh", delta=f"{(total_curtailed_gwh/total_gen_gwh*100):.2f}% loss", delta_color="inverse")
col3.metric("Avg Renewable Share", f"{avg_ren_share:.1f}%")
col4.metric("Avg Residual Load", f"{avg_res_load_mw:,.0f} MW")

st.markdown("---")

# Visualizations Row 1: Generation Mix & TSO Distribution
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Monthly Generation by Tech (Solar vs Wind)")
    monthly = filtered.groupby("month")[["wind_mw", "solar_mw", "grid_demand_mw"]].mean().reset_index()
    fig_mix = go.Figure()
    fig_mix.add_trace(go.Bar(x=monthly["month"], y=monthly["wind_mw"], name="Wind (On/Offshore)", marker_color="#0083B8"))
    fig_mix.add_trace(go.Bar(x=monthly["month"], y=monthly["solar_mw"], name="Solar PV", marker_color="#FFAA00"))
    fig_mix.add_trace(go.Scatter(x=monthly["month"], y=monthly["grid_demand_mw"], name="Avg Demand", line=dict(color="#FF4B4B", width=2)))
    fig_mix.update_layout(barmode="stack", yaxis_title="Average Power (MW)", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_mix, use_container_width=True)

with col_right:
    st.subheader("Renewable Share by Transmission Control Zone")
    tso_comp = filtered.groupby("tso_zone")[["renewable_share_pct", "curtailment_mw"]].mean().reset_index()
    fig_tso = px.bar(
        tso_comp,
        x="tso_zone",
        y="renewable_share_pct",
        color="tso_zone",
        labels={"renewable_share_pct": "Renewable Share (%)", "tso_zone": "TSO Zone"},
        title="Mean Renewable Penetration per Control Area"
    )
    st.plotly_chart(fig_tso, use_container_width=True)

# Visualizations Row 2: Grid Stress & Curtailment Analysis
st.subheader("Grid Congestion & Redispatch Pressure")
st.markdown("Evaluates peak curtailment hours where renewable feed-in exceeds transmission corridor capacity.")
curtail_hourly = filtered.groupby(filtered["timestamp"].dt.hour)["curtailment_mw"].mean().reset_index()
curtail_hourly.columns = ["Hour_of_Day", "Avg_Curtailed_MW"]

fig_curtail = px.area(
    curtail_hourly,
    x="Hour_of_Day",
    y="Avg_Curtailed_MW",
    labels={"Hour_of_Day": "Hour of Day (UTC)", "Avg_Curtailed_MW": "Curtailed Feed-in (MW)"},
    title="Hourly Curtailment Distribution Profile"
)
st.plotly_chart(fig_curtail, use_container_width=True)
