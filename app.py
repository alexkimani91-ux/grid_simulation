import sys, os
import math
import random
import streamlit as st

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from backend.gridsim.ui_simulator import run_simulation
from backend.gridsim.visualization import (
    plot_grid_load,
    plot_battery_soc,
    plot_grid_contribution,
    plot_node_load,
    plot_node_pv1,
    plot_node_pv2,
    plot_node_soc
)

# -----------------------------
# IRRADIANCE MODES
# -----------------------------
def irradiance_clear(hour):
    return max(0, math.sin((hour - 6) * math.pi / 12))

def irradiance_cloudy(hour):
    return irradiance_clear(hour) * 0.4

def irradiance_random(hour):
    return max(0, min(1, irradiance_clear(hour) + random.uniform(-0.3, 0.3)))

def get_irradiance_curve(mode):
    if mode == "Clear Sky":
        return irradiance_clear
    if mode == "Cloudy":
        return irradiance_cloudy
    if mode == "Random":
        return irradiance_random
    return irradiance_clear


# -----------------------------
# STREAMLIT UI
# -----------------------------
st.set_page_config(page_title="Alex's Grid Simulation Dashboard", layout="wide")
st.title("⚡ Multi‑Node Grid Simulation Dashboard")

# -----------------------------
# CONTROL DASHBOARD (SIDEBAR)
# -----------------------------
st.sidebar.markdown("## ⚙️ Control Dashboard")

# PV Controls
st.sidebar.markdown("### ☀️ PV Controls")
pv1_enabled = st.sidebar.checkbox("Enable PV1", value=True)
pv2_enabled = st.sidebar.checkbox("Enable PV2", value=True)
inverter_limit_ui = st.sidebar.slider(
    "Inverter AC Limit (kW)",
    min_value=0.0,
    max_value=50.0,
    value=10.0,
    step=0.5
)

# Battery Controls
st.sidebar.markdown("### 🔋 Battery Controls")
battery_enabled = st.sidebar.checkbox("Enable Battery", value=True)
max_charge_ui = st.sidebar.slider(
    "Max Charge Rate (kW)",
    min_value=0.0,
    max_value=10.0,
    value=3.0,
    step=0.5
)
max_discharge_ui = st.sidebar.slider(
    "Max Discharge Rate (kW)",
    min_value=0.0,
    max_value=10.0,
    value=3.0,
    step=0.5
)
soc_min_ui = st.sidebar.slider(
    "Min SOC (%)",
    min_value=0,
    max_value=50,
    value=20,
    step=1
)
soc_max_ui = st.sidebar.slider(
    "Max SOC (%)",
    min_value=50,
    max_value=100,
    value=80,
    step=1
)

# Load Controls
st.sidebar.markdown("### 🏠 Load Controls")
household_multiplier = st.sidebar.slider(
    "Household Load Multiplier",
    min_value=0.5,
    max_value=2.0,
    value=1.0,
    step=0.1
)
industry_multiplier = st.sidebar.slider(
    "Industry Load Multiplier",
    min_value=0.5,
    max_value=2.0,
    value=1.0,
    step=0.1
)

# Grid Controls
st.sidebar.markdown("### 🔌 Grid Controls")
grid_enabled = st.sidebar.checkbox("Enable Grid Connection", value=True)
grid_import_price_ui = st.sidebar.number_input(
    "Grid Import Price (€/kWh)",
    min_value=0.0,
    max_value=1.0,
    value=0.30,
    step=0.01
)
grid_export_price_ui = st.sidebar.number_input(
    "Grid Export Price (€/kWh)",
    min_value=0.0,
    max_value=1.0,
    value=0.10,
    step=0.01
)

# Scenario Mode
st.sidebar.markdown("### 🎛️ Scenario Mode")
scenario = st.sidebar.selectbox(
    "Select Control Strategy",
    [
        "Self-Consumption Mode",
        "Battery-First Mode",
        "Grid-First Mode",
        "Export-Maximization Mode"
    ]
)

# -----------------------------
# SIMULATION CONTROLS
# -----------------------------
st.sidebar.header("Simulation Controls")

num_nodes = st.sidebar.slider("Nodes", 1, 5, 1)
households = st.sidebar.slider("Households per Node", 0, 50, 5)
industries = st.sidebar.slider("Industries per Node", 0, 10, 1)
pv_kw = st.sidebar.slider("PV kW per Node", 0, 50, 10)
battery_kwh = st.sidebar.slider("Battery kWh per Node", 0, 100, 20)

irradiance_mode = st.sidebar.selectbox(
    "Sun Mode",
    ["Clear Sky", "Cloudy", "Random"]
)

node_index = st.sidebar.selectbox(
    "Select Node",
    list(range(num_nodes)),
    format_func=lambda i: f"Node {i+1}"
)

irradiance_curve = get_irradiance_curve(irradiance_mode)

# Apply control dashboard effects to inputs (where possible)
effective_households = int(households * household_multiplier)
effective_industries = int(industries * industry_multiplier)

# Simple PV enable logic: if both disabled, PV = 0
effective_pv_kw = pv_kw
if not pv1_enabled and not pv2_enabled:
    effective_pv_kw = 0

controls = {
    "pv1_enabled": pv1_enabled,
    "pv2_enabled": pv2_enabled,
    "inverter_limit_kw": inverter_limit_ui,
    "battery_enabled": battery_enabled,
    "max_charge_kw": max_charge_ui,
    "max_discharge_kw": max_discharge_ui,
    "soc_min_pct": soc_min_ui,
    "soc_max_pct": soc_max_ui,
    "grid_enabled": grid_enabled,
    "grid_import_price": grid_import_price_ui,
    "grid_export_price": grid_export_price_ui,
    "scenario": scenario,  # reserved for future logic
}

# -----------------------------
# RUN SIMULATION
# -----------------------------
history = run_simulation(
    hours=24,
    irradiance_curve=irradiance_curve,
    num_nodes=num_nodes,
    households_per_node=effective_households,
    industries_per_node=effective_industries,
    pv_kw_per_node=effective_pv_kw,
    battery_kwh_per_node=battery_kwh,
)

# -----------------------------
# DIGITAL METER READINGS
# -----------------------------
latest = history[-1]
node = latest["nodes"][node_index]

st.markdown("## 🔌 Digital Meter Readings")

colA, colB, colC = st.columns(3)
colD, colE, colF = st.columns(3)

with colA:
    st.metric("Load (kW)", f"{latest['grid_load_kw']:.2f}")

with colB:
    st.metric("PV1 (kW)", f"{node['pv1_kw']:.2f}")

with colC:
    st.metric("PV2 (kW)", f"{node['pv2_kw']:.2f}")

with colD:
    usable_max = 0.8 * battery_kwh
    soc_pct = 0.0
    if usable_max > 0:
        soc_pct = node["battery_soc"]

    if soc_pct <= 25:
        st.error(f"{soc_pct:.1f}%")
    elif soc_pct >= 75:
        st.warning(f"{soc_pct:.1f}%")
    else:
        st.success(f"{soc_pct:.1f}%")

    st.caption("Battery SOC (%)")

with colE:
    st.metric("Grid Contribution (kW)", f"{latest['grid_contribution_kw']:.2f}")

with colF:
    net_flow = node["grid_import_kw"] - node["grid_export_kw"]
    st.metric("Net Flow (kW)", f"{net_flow:.2f}")

# -----------------------------
# GRID-LEVEL OVERVIEW
# -----------------------------
st.markdown("## 🌍 Grid‑Level Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### Grid Load")
    plot_grid_load(history)

with col2:
    st.markdown("#### Battery SOC")
    plot_battery_soc(history)

with col3:
    st.markdown("#### Grid Contribution")
    plot_grid_contribution(history)

# -----------------------------
# NODE-LEVEL OVERVIEW
# -----------------------------
st.markdown(f"## 🏘️ Node {node_index+1} Overview")

col4, col5, col6 = st.columns(3)

with col4:
    st.markdown("#### Household PV1")
    plot_node_pv1(history, node_index)

with col5:
    st.markdown("#### Household PV2")
    plot_node_pv2(history, node_index)

with col6:
    st.markdown("#### Node SOC")
    plot_node_soc(history, node_index)

# -----------------------------
# EMS CONTROL ROOM
# -----------------------------
st.markdown("## 🧭 EMS Control Room")

col_status, col_flows = st.columns(2)

with col_status:
    st.markdown("#### System Status")
    st.markdown(f"**Scenario:** {scenario}")
    st.markdown(f"**Grid:** {'Connected' if grid_enabled else 'Disconnected'}")
    st.markdown(f"**Battery:** {'Enabled' if battery_enabled else 'Disabled'}")
    st.markdown(f"**PV1:** {'On' if pv1_enabled else 'Off'}")
    st.markdown(f"**PV2:** {'On' if pv2_enabled else 'Off'}")

with col_flows:
    st.markdown("#### Energy Flows (Latest Hour)")
    pv_total = node["pv1_kw"] + node["pv2_kw"]
    load_kw = node["load_kw"]
    gi = node["grid_import_kw"]
    ge = node["grid_export_kw"]
    soc_pct = node["battery_soc"]

    st.markdown(f"☀️ PV: {pv_total:.2f} kW")
    st.markdown(f"🏠 Load: {load_kw:.2f} kW")
    st.markdown(f"🔋 Battery SOC: {soc_pct:.1f}%")
    st.markdown(f"🔌 Grid import: {gi:.2f} kW")
    st.markdown(f"🔌 Grid export: {ge:.2f} kW")

# -----------------------------
# ENERGY FLOW ANIMATION PANEL
# -----------------------------
st.markdown("## 🔄 Energy Flow Animation")

# Extract latest values
pv1 = node["pv1_kw"]
pv2 = node["pv2_kw"]
pv_total = pv1 + pv2
load_kw = node["load_kw"]
gi = node["grid_import_kw"]
ge = node["grid_export_kw"]
soc_pct = node["battery_soc"]

# Determine flow directions
arrow_pv_load = "➡️" if pv_total > 0 else "⛔"
arrow_pv_batt = "➡️" if pv_total > load_kw else "⛔"
arrow_pv_grid = "➡️" if ge > 0 else "⛔"

arrow_batt_load = "➡️" if (load_kw > pv_total and soc_pct > 20) else "⛔"
arrow_grid_load = "➡️" if gi > 0 else "⛔"

# Layout
colA, colB = st.columns(2)

with colA:
    st.markdown("### ☀️ PV Flows")
    st.markdown(f"PV → Load: {arrow_pv_load}  **{min(pv_total, load_kw):.2f} kW**")
    st.markdown(f"PV → Battery: {arrow_pv_batt}  **{max(0, pv_total - load_kw):.2f} kW**")
    st.markdown(f"PV → Grid: {arrow_pv_grid}  **{ge:.2f} kW**")

with colB:
    st.markdown("### 🔋 & 🔌 Other Flows")
    st.markdown(f"Battery → Load: {arrow_batt_load}  **{max(0, load_kw - pv_total - gi):.2f} kW**")
    st.markdown(f"Grid → Load: {arrow_grid_load}  **{gi:.2f} kW**")
