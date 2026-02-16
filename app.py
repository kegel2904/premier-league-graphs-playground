"""
FPL Price-Per-Point Dashboard
Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os
from etl_v1 import run as run_etl

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FPL Value Dashboard",
    page_icon="⚽",
    layout="wide",
)

# ── Load data (run ETL if CSV doesn't exist) ───────────────────────────────────
DATA_FILE = "data/fpl_price_per_point.csv"

@st.cache_data(show_spinner="Running ETL pipeline...")
def load_data():
    if not os.path.exists(DATA_FILE):
        run_etl()
    return pd.read_csv(DATA_FILE)

df = load_data()

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("⚽ FPL Value Dashboard — 2024/25")
st.caption("Source: vaastav/Fantasy-Premier-League · Metric: Total Season Points ÷ Price")

# ── Metric cards ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
best_gw1   = df.sort_values("pts_per_gw1_price", ascending=False).iloc[0]
best_gw38  = df.sort_values("pts_per_gw_last_price", ascending=False).iloc[0]
best_avg   = df.sort_values("pts_per_avg_price", ascending=False).iloc[0]

col1.metric("👑 Best Value (GW1 price)",  best_gw1["name"],  f"{best_gw1['pts_per_gw1_price']} pts/£m")
col2.metric("🏁 Best Value (GW38 price)", best_gw38["name"], f"{best_gw38['pts_per_gw_last_price']} pts/£m")
col3.metric("📊 Best Value (Avg price)",  best_avg["name"],  f"{best_avg['pts_per_avg_price']} pts/£m")
col4.metric("👥 Players Analysed", len(df), "≥5 GWs played")

st.divider()

# ── Sidebar filters ────────────────────────────────────────────────────────────
st.sidebar.header("🔧 Filters")

positions = st.sidebar.multiselect(
    "Position",
    options=["GK", "DEF", "MID", "FWD"],
    default=["DEF", "MID", "FWD"],
)

teams = st.sidebar.multiselect(
    "Team",
    options=sorted(df["team"].unique()),
    default=[],
    placeholder="All teams",
)

metric_choice = st.sidebar.selectbox(
    "Price Metric",
    options={
        "pts_per_gw1_price":     "Total Pts / GW1 Price",
        "pts_per_gw_last_price": "Total Pts / GW38 Price",
        "pts_per_avg_price":     "Total Pts / Avg Price",
    }.keys(),
    format_func=lambda k: {
        "pts_per_gw1_price":     "Total Pts / GW1 Price",
        "pts_per_gw_last_price": "Total Pts / GW38 Price",
        "pts_per_avg_price":     "Total Pts / Avg Price",
    }[k],
)

top_n = st.sidebar.slider("Show top N players", 10, 50, 20)

min_pts = st.sidebar.number_input("Min total points", 0, 300, 50)

# ── Apply filters ──────────────────────────────────────────────────────────────
filtered = df[df["position"].isin(positions)]
if teams:
    filtered = filtered[filtered["team"].isin(teams)]
filtered = filtered[filtered["total_pts"] >= min_pts]
filtered = filtered.sort_values(metric_choice, ascending=False).head(top_n)

# ── Tab layout ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Bar Chart", "🔵 Scatter: Points vs Price", "📋 Full Table"])

with tab1:
    metric_labels = {
        "pts_per_gw1_price":     "Pts per £m (GW1 Price)",
        "pts_per_gw_last_price": "Pts per £m (GW38 Price)",
        "pts_per_avg_price":     "Pts per £m (Avg Price)",
    }
    fig = px.bar(
        filtered,
        x="name",
        y=metric_choice,
        color="position",
        hover_data=["team", "total_pts", "gw1_price_m", "gw_last_price_m"],
        labels={"name": "Player", metric_choice: metric_labels[metric_choice]},
        title=f"Top {top_n} Players by {metric_labels[metric_choice]}",
        color_discrete_map={"GK": "#f59e0b", "DEF": "#3b82f6", "MID": "#10b981", "FWD": "#ef4444"},
    )
    fig.update_layout(xaxis_tickangle=-45, height=500)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    price_col = {
        "pts_per_gw1_price":     "gw1_price_m",
        "pts_per_gw_last_price": "gw_last_price_m",
        "pts_per_avg_price":     "avg_price_m",
    }[metric_choice]

    fig2 = px.scatter(
        filtered,
        x=price_col,
        y="total_pts",
        color="position",
        size="total_pts",
        hover_name="name",
        hover_data=["team", metric_choice],
        labels={
            price_col: "Price (£m)",
            "total_pts": "Total Season Points",
        },
        title="Points vs Price — bigger bubble = more points",
        color_discrete_map={"GK": "#f59e0b", "DEF": "#3b82f6", "MID": "#10b981", "FWD": "#ef4444"},
    )
    fig2.update_layout(height=500)
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    display_cols = {
        "name": "Player",
        "team": "Team",
        "position": "Pos",
        "total_pts": "Total Pts",
        "gw1_price_m": "GW1 Price (£m)",
        "gw_last_price_m": "GW38 Price (£m)",
        "price_change_m": "Price Δ (£m)",
        "pts_per_gw1_price": "Pts/£m (GW1)",
        "pts_per_gw_last_price": "Pts/£m (GW38)",
        "pts_per_avg_price": "Pts/£m (Avg)",
    }
    st.dataframe(
        filtered.rename(columns=display_cols)[display_cols.values()].reset_index(drop=True),
        use_container_width=True,
        height=500,
    )
    st.download_button(
        "⬇️ Download as CSV",
        filtered.to_csv(index=False),
        "fpl_value_players.csv",
        "text/csv",
    )