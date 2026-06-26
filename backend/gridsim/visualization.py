import plotly.graph_objects as go
import streamlit as st

# -----------------------------
# GRID‑LEVEL PLOTS
# -----------------------------
def plot_grid_load(history):
    hours = [h["hour"] for h in history]
    load = [h["grid_load_kw"] for h in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=load,
        mode="lines",
        line=dict(width=4, color="#4F8DF5"),
        fill="tozeroy",
        fillcolor="rgba(79,141,245,0.25)",
        hovertemplate="Hour %{x}<br>Load %{y:.2f} kW"
    ))

    fig.update_layout(
        title="Grid Load (kW)",
        xaxis_title="Hour",
        yaxis_title="kW",
        template="plotly_white",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_battery_soc(history):
    hours = [h["hour"] for h in history]
    soc = [h["nodes"][0]["battery_soc"] for h in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=soc,
        mode="lines+markers",
        line=dict(width=4, color="#00C49A"),
        marker=dict(size=6),
        hovertemplate="Hour %{x}<br>SOC %{y:.1f}%"
    ))

    fig.update_layout(
        title="Battery State of Charge (%)",
        xaxis_title="Hour",
        yaxis_title="SOC (%)",
        template="plotly_white",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_grid_contribution(history):
    hours = [h["hour"] for h in history]
    contrib = [h["grid_contribution_kw"] for h in history]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=hours, y=contrib,
        marker_color=["#FF6B6B" if c > 0 else "#4ECDC4" for c in contrib],
        hovertemplate="Hour %{x}<br>Contribution %{y:.2f} kW"
    ))

    fig.update_layout(
        title="Grid Contribution (kW)",
        xaxis_title="Hour",
        yaxis_title="kW",
        template="plotly_white",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# NODE‑LEVEL PLOTS
# -----------------------------
def plot_node_load(history, node_index):
    hours = [h["hour"] for h in history]
    load = [
        h["nodes"][node_index]["grid_import_kw"]
        - h["nodes"][node_index]["grid_export_kw"]
        for h in history
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=load,
        mode="lines",
        line=dict(width=4, color="#3A86FF"),
        fill="tozeroy",
        fillcolor="rgba(58,134,255,0.25)",
        hovertemplate="Hour %{x}<br>Net Flow %{y:.2f} kW"
    ))

    fig.update_layout(
        title=f"Node {node_index+1} Net Grid Flow (kW)",
        xaxis_title="Hour",
        yaxis_title="kW",
        template="plotly_white",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_node_pv1(history, node_index):
    hours = [h["hour"] for h in history]
    pv1 = [h["nodes"][node_index]["pv1_kw"] for h in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=pv1,
        mode="lines",
        line=dict(width=4, color="#FDB813"),
        fill="tozeroy",
        fillcolor="rgba(253,184,19,0.25)",
        hovertemplate="Hour %{x}<br>PV1 %{y:.2f} kW"
    ))

    fig.update_layout(
        title=f"Node {node_index+1} PV1 Output (kW)",
        template="plotly_white",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_node_pv2(history, node_index):
    hours = [h["hour"] for h in history]
    pv2 = [h["nodes"][node_index]["pv2_kw"] for h in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=pv2,
        mode="lines",
        line=dict(width=4, color="#FF9F1C"),
        fill="tozeroy",
        fillcolor="rgba(255,159,28,0.25)",
        hovertemplate="Hour %{x}<br>PV2 %{y:.2f} kW"
    ))

    fig.update_layout(
        title=f"Node {node_index+1} PV2 Output (kW)",
        template="plotly_white",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_node_soc(history, node_index):
    hours = [h["hour"] for h in history]
    soc = [h["nodes"][node_index]["battery_soc"] for h in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=soc,
        mode="lines+markers",
        line=dict(width=4, color="#2EC4B6"),
        marker=dict(size=6),
        hovertemplate="Hour %{x}<br>SOC %{y:.1f}%"
    ))

    fig.update_layout(
        title=f"Node {node_index+1} Battery SOC (%)",
        template="plotly_white",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)
