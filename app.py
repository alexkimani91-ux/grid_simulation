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
st.set_page_config(page_title="Grid Simulation Dashboard", layout="wide")
st.title("⚡ Alex's Multi‑Node Grid Simulation Dashboard")

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
def render_battery_svg(soc_pct: float) -> str:
    soc = max(0, min(100, soc_pct))

    outer_width = 80
    outer_height = 20
    inner_padding = 3

    inner_width = outer_width - 2 * inner_padding
    inner_height = outer_height - 2 * inner_padding

    fill_width = int(inner_width * soc / 100)

    # MATCH YOUR STREAMLIT COLOR LOGIC
    if soc <= 25:
        color = "#e74c3c"   # red
    elif soc >= 75:
        color = "#2ecc71"   # green
    else:
        color = "#f1c40f"   # yellow

    svg = f"""
    <svg width="140" height="50" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="10" width="{outer_width}" height="{outer_height}"
            rx="4" ry="4" fill="none" stroke="#333" stroke-width="2"/>
      <rect x="{10 + outer_width}" y="15" width="8" height="10"
            rx="2" ry="2" fill="#333"/>
      <rect x="{10 + inner_padding}" y="{10 + inner_padding}"
            width="{inner_width}" height="{inner_height}"
            rx="2" ry="2" fill="#eee"/>
      <rect x="{10 + inner_padding}" y="{10 + inner_padding}"
            width="{fill_width}" height="{inner_height}"
            rx="2" ry="2" fill="{color}"/>
      <text x="50" y="45" font-size="12" text-anchor="middle" fill="#333">
        {soc:.1f}%
      </text>
    </svg>
    """
    return svg

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

def render_ems_grid_topology(history, latest_index, num_nodes):
    latest = history[latest_index]

    svg = """
<div style="display:block;">
<svg viewBox="0 0 1600 900" xmlns="http://www.w3.org/2000/svg">

  <defs>
    <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
      <polygon points="0,0 12,6 0,12" fill="currentColor"/>
    </marker>
  </defs>

  <!-- GRID TRANSFORMER (SOURCE) -->
  <rect x="100" y="400" width="160" height="100" fill="#cce5ff" stroke="#333" stroke-width="4"/>
  <circle cx="130" cy="450" r="20" fill="none" stroke="#333" stroke-width="4"/>
  <circle cx="180" cy="450" r="20" fill="none" stroke="#333" stroke-width="4"/>
  <text x="180" y="530" text-anchor="middle" font-size="18">Grid</text>
"""

    # Lay out nodes horizontally
    x_start = 350
    x_step = 250
    y_bus = 450

    for i in range(num_nodes):
        node_data = latest["nodes"][i]
        x = x_start + i * x_step

        pv = node_data["pv1_kw"] + node_data["pv2_kw"]
        load = node_data["load_kw"]
        soc = node_data["battery_soc"]

        # Line from grid to node
        svg += f"""
  <!-- Line Grid → Node {i+1} -->
  <line x1="{100 + 160}" y1="{450}" x2="{x}" y2="{y_bus}"
        stroke="#444" stroke-width="6" marker-end="url(#arrow)"/>
"""

        # Node bus
        svg += f"""
  <!-- Node {i+1} bus -->
  <circle cx="{x}" cy="{y_bus}" r="14" fill="#444"/>
  <text x="{x}" y="{y_bus - 30}" text-anchor="middle" font-size="16">Node {i+1}</text>
"""

        # Household + PV
        svg += f"""
  <!-- Household + PV at Node {i+1} -->
  <polygon points="{x-40},{y_bus-140} {x+40},{y_bus-140} {x},{y_bus-180}"
           fill="#e0e0e0" stroke="#333" stroke-width="3"/>
  <rect x="{x-40}" y="{y_bus-140}" width="80" height="50"
        fill="#e0e0e0" stroke="#333" stroke-width="3"/>
  <rect x="{x-30}" y="{y_bus-125}" width="20" height="20"
        fill="#fff" stroke="#333"/>
  <rect x="{x-35}" y="{y_bus-160}" width="70" height="15"
        fill="#f7e27c" stroke="#333" stroke-width="2"/>
  <text x="{x}" y="{y_bus-200}" text-anchor="middle" font-size="12">House + PV</text>

  <line x1="{x}" y1="{y_bus-140}" x2="{x}" y2="{y_bus}"
        stroke="#2ecc71" stroke-width="4" stroke-dasharray="10 8"
        marker-end="url(#arrow)">
    <animate attributeName="stroke-dashoffset" from="20" to="0" dur="1s" repeatCount="indefinite"/>
  </line>
"""

        # Industry
        svg += f"""
  <!-- Industry at Node {i+1} -->
  <rect x="{x-45}" y="{y_bus+40}" width="90" height="60"
        fill="#cfcfcf" stroke="#333" stroke-width="3"/>
  <rect x="{x-35}" y="{y_bus+20}" width="12" height="20"
        fill="#cfcfcf" stroke="#333"/>
  <rect x="{x-15}" y="{y_bus+10}" width="12" height="30"
        fill="#cfcfcf" stroke="#333"/>
  <rect x="{x+5}" y="{y_bus}" width="12" height="40"
        fill="#cfcfcf" stroke="#333"/>
  <text x="{x}" y="{y_bus+120}" text-anchor="middle" font-size="12">Industry</text>

  <line x1="{x}" y1="{y_bus}" x2="{x}" y2="{y_bus+40}"
        stroke="#444" stroke-width="4" marker-end="url(#arrow)"/>
"""

        # Battery
        batt_fill = int(60 * soc / 100)
        svg += f"""
  <!-- Battery at Node {i+1} -->
  <rect x="{x-60}" y="{y_bus+150}" width="120" height="60"
        fill="#fafafa" stroke="#333" stroke-width="3"/>
  <rect x="{x-45}" y="{y_bus+165}" width="90" height="30"
        fill="#ddd" stroke="#333"/>
  <rect x="{x-45}" y="{y_bus+165}" width="{batt_fill}" height="30"
        fill="#2ecc71"/>
  <text x="{x}" y="{y_bus+210}" text-anchor="middle" font-size="12">Batt {soc:.1f}%</text>

  <line x1="{x}" y1="{y_bus}" x2="{x}" y2="{y_bus+150}"
        stroke="#e67e22" stroke-width="4" stroke-dasharray="10 8"
        marker-end="url(#arrow)">
    <animate attributeName="stroke-dashoffset" from="20" to="0" dur="1s" repeatCount="indefinite"/>
  </line>
"""

    svg += """
</svg>
</div>
"""
    return svg

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
latest_index = st.sidebar.slider("Hour for meter readings", 0, 23, 12)
latest = history[latest_index]
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
    soc_pct = node["battery_soc"]
    st.markdown(render_battery_svg(soc_pct), unsafe_allow_html=True)
    st.caption("Battery SOC")



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
pv_to_load = latest["pv_to_load_kw"]
pv_to_battery = latest["pv_to_battery_kw"]
pv_to_grid = latest["pv_to_grid_kw"]

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
    st.markdown(f"PV → Load: ➡️ **{pv_to_load:.2f} kW**")
    st.markdown(f"PV → Battery: ➡️ **{pv_to_battery:.2f} kW**")
    st.markdown(f"PV → Grid: ➡️ **{pv_to_grid:.2f} kW**")


with colB:
    st.markdown("### 🔋 & 🔌 Other Flows")
    st.markdown(f"Battery → Load: {arrow_batt_load}  **{max(0, load_kw - pv_total - gi):.2f} kW**")
    st.markdown(f"Grid → Load: {arrow_grid_load}  **{gi:.2f} kW**")
    
# Build flows dict (you already do this)
st.markdown("## 🗺️ Grid Topology View")
st.markdown(
    render_ems_grid_topology(history, latest_index, num_nodes),
    unsafe_allow_html=True
)
