"""Revenue Analytics — Streamlit app for quarterly revenue review.

Runs locally against the bundled CSV; swap `load_metrics` for a
Snowpark/connector query (`FINANCE.REPORTING.QUARTERLY_METRICS`) to deploy
as a Streamlit-in-Snowflake app unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = Path(__file__).parent / "data" / "snow_quarterly_metrics.csv"

st.set_page_config(page_title="Revenue Analytics", page_icon="📊", layout="wide")


@st.cache_data(ttl=3600)
def load_metrics() -> pd.DataFrame:
    """Load quarterly metrics and compute derived growth fields."""
    df = pd.read_csv(DATA_PATH, parse_dates=["quarter_end"]).sort_values("quarter_end")
    df["yoy_growth"] = df["product_revenue_m"] / df["product_revenue_m"].shift(4) - 1
    df["qoq_growth"] = df["product_revenue_m"] / df["product_revenue_m"].shift(1) - 1
    df["seq_add_m"] = df["product_revenue_m"].diff()
    df["trailing_4q_yoy"] = df["yoy_growth"].rolling(4).mean().shift(1)
    return df


def headline(df: pd.DataFrame) -> str:
    """One-sentence stakeholder summary of the selected quarter."""
    q = df.iloc[-1]
    direction = "re-accelerating" if q["yoy_growth"] > q["trailing_4q_yoy"] else "moderating"
    return (
        f"**{q['fiscal_quarter']}** product revenue was **${q['product_revenue_m']:,.0f}M**, "
        f"up **{q['yoy_growth']:.1%} YoY** (+${q['seq_add_m']:,.0f}M sequentially) — "
        f"growth is {direction} vs. the trailing-4Q average of {q['trailing_4q_yoy']:.1%}."
    )


df = load_metrics()

st.title("📊 Quarterly Revenue Analytics")
st.caption(
    "Demo built on Snowflake's publicly reported metrics (8-K filings, FY25–Q1 FY27). "
    "Structured the way a Strategic Finance revenue review actually runs."
)

# ---- Sidebar controls -------------------------------------------------------
quarters = df["fiscal_quarter"].tolist()
selected = st.sidebar.select_slider(
    "Analyze through quarter", options=quarters, value=quarters[-1]
)
view = df[df["fiscal_quarter"].apply(quarters.index) <= quarters.index(selected)]

# ---- Headline + KPI cards ---------------------------------------------------
st.info(headline(view))

latest, prior = view.iloc[-1], view.iloc[-2]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Product revenue", f"${latest['product_revenue_m']:,.0f}M",
          f"{latest['yoy_growth']:+.1%} YoY")
c2.metric("Sequential add", f"${latest['seq_add_m']:,.0f}M",
          f"{latest['qoq_growth']:+.1%} QoQ")
c3.metric("NRR", f"{latest['nrr_pct']:.0f}%",
          f"{latest['nrr_pct'] - prior['nrr_pct']:+.0f} pts QoQ")
c4.metric("RPO", f"${latest['rpo_b']:.2f}B",
          f"{(latest['rpo_b'] / prior['rpo_b'] - 1):+.1%} QoQ")

# ---- Charts -----------------------------------------------------------------
left, right = st.columns(2)

with left:
    fig = go.Figure()
    fig.add_bar(x=view["fiscal_quarter"], y=view["product_revenue_m"],
                name="Product revenue ($M)", marker_color="#29B5E8")
    fig.add_scatter(x=view["fiscal_quarter"], y=view["yoy_growth"] * 100,
                    name="YoY growth (%)", yaxis="y2", mode="lines+markers",
                    line=dict(color="#0B5394", width=3))
    fig.update_layout(
        title="Product revenue & YoY growth",
        yaxis=dict(title="$M"),
        yaxis2=dict(title="YoY %", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.12),
        height=420,
    )
    st.plotly_chart(fig, width="stretch")

with right:
    fig2 = px.line(view, x="fiscal_quarter", y="nrr_pct", markers=True,
                   title="Net revenue retention (%)")
    fig2.update_traces(line_color="#29B5E8", line_width=3)
    fig2.update_layout(height=420, yaxis_title="NRR %")
    st.plotly_chart(fig2, width="stretch")

# ---- Detail table -----------------------------------------------------------
st.subheader("Quarter detail")
table = view[["fiscal_quarter", "product_revenue_m", "seq_add_m", "yoy_growth",
              "qoq_growth", "nrr_pct", "rpo_b", "customers_1m_plus"]].copy()
st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    column_config={
        "fiscal_quarter": st.column_config.TextColumn("Quarter"),
        "product_revenue_m": st.column_config.NumberColumn("Product rev ($M)", format="%.1f"),
        "seq_add_m": st.column_config.NumberColumn("Seq add ($M)", format="%.1f"),
        "yoy_growth": st.column_config.NumberColumn("YoY", format="percent"),
        "qoq_growth": st.column_config.NumberColumn("QoQ", format="percent"),
        "nrr_pct": st.column_config.NumberColumn("NRR (%)", format="%.0f"),
        "rpo_b": st.column_config.NumberColumn("RPO ($B)", format="%.2f"),
        "customers_1m_plus": st.column_config.NumberColumn("$1M+ customers"),
    },
)

st.caption(
    "Sources: Snowflake 8-K earnings releases (sec.gov). Demo dataset — a few "
    "non-headline fields are estimates where not separately disclosed."
)
