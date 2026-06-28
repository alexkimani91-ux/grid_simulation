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


def render_ems_grid_animated(node, flows):
    pv = node["pv1_kw"] + node["pv2_kw"]
    load = node["load_kw"]
    soc = node["battery_soc"]

    pv_to_load = flows["pv_to_load"]
    pv_to_battery = flows["pv_to_battery"]
    pv_to_grid = flows["pv_to_grid"]
    battery_to_load = flows["battery_to_load"]
    grid_to_load = flows["grid_to_load"]

    batt_fill = int(60 * soc / 100)

    svg = f"""
    <svg width="900" height="320" xmlns="http://www.w3.org/2000/svg">

      <!-- Main bus -->
      <line x1="200" y1="160" x2="700" y2="160"
            stroke="#444" stroke-width="5"/>

      <!-- PV Array -->
      <rect x="60" y="80" width="100" height="60" fill="#f7e27c" stroke="#333" stroke-width="2"/>
      <line x1="60" y1="100" x2="160" y2="100" stroke="#333" stroke-width="1"/>
      <line x1="60" y1="120" x2="160" y2="120" stroke="#333" stroke-width="1"/>
      <text x="110" y="155" text-anchor="middle" font-size="13">PV Array</text>

      <!-- PV feeder to bus -->
      <line x1="160" y1="110" x2="200" y2="110"
            stroke="#2ecc71" stroke-width="4" stroke-dasharray="8 6">
        <animate attributeName="stroke-dashoffset"
                 from="16" to="0" dur="1s" repeatCount="indefinite"/>
      </line>
      <line x1="200" y1="110" x2="200" y2="160"
            stroke="#2ecc71" stroke-width="4" stroke-dasharray="8 6">
        <animate attributeName="stroke-dashoffset"
                 from="16" to="0" dur="1s" repeatCount="indefinite"/>
      </line>
      <text x="200" y="95" font-size="11" text-anchor="start">
        PV→Bus {pv:.1f} kW
      </text>

      <!-- Battery rack -->
      <rect x="60" y="200" width="120" height="70" fill="#fafafa" stroke="#333" stroke-width="2"/>
      <rect x="75" y="220" width="90" height="30" fill="#ddd" stroke="#333" stroke-width="1"/>
      <rect x="75" y="220" width="{batt_fill}" height="30" fill="#2ecc71"/>
      <text x="120" y="290" text-anchor="middle" font-size="13">Battery {soc:.1f}%</text>

      <!-- Battery feeder to bus -->
      <line x1="180" y1="235" x2="200" y2="235"
            stroke="#e67e22" stroke-width="4" stroke-dasharray="8 6">
        <animate attributeName="stroke-dashoffset"
                 from="16" to="0" dur="1s" repeatCount="indefinite"/>
      </line>
      <line x1="200" y1="235" x2="200" y2="160"
            stroke="#e67e22" stroke-width="4" stroke-dasharray="8 6">
        <animate attributeName="stroke-dashoffset"
                 from="16" to="0" dur="1s" repeatCount="indefinite"/>
      </line>
      <text x="210" y="230" font-size="11" text-anchor="start">
        Batt→Bus {battery_to_load:.1f} kW
      </text>

      <!-- Grid transformer -->
      <rect x="720" y="120" width="100" height="80" fill="#cce5ff" stroke="#333" stroke-width="2"/>
      <line x1="735" y1="135" x2="805" y2="185" stroke="#333" stroke-width="2"/>
      <line x1="735" y1="185" x2="805" y2="135" stroke="#333" stroke-width="2"/>
      <text x="770" y="215" text-anchor="middle" font-size="13">Grid</text>

      <!-- Grid feeder to bus -->
      <line x1="720" y1="160" x2="700" y2="160"
            stroke="#2980b9" stroke-width="4" stroke-dasharray="8 6">
        <animate attributeName="stroke-dashoffset"
                 from="16" to="0" dur="1s" repeatCount="indefinite"/>
      </line>
      <text x="650" y="145" font-size="11" text-anchor="end">
        Grid→Bus {grid_to_load:.1f} kW
      </text>

      <!-- House load -->
      <polygon points="350,80 390,80 370,60" fill="#e0e0e0" stroke="#333" stroke-width="2"/>
      <rect x="350" y="80" width="40" height="40" fill="#e0e0e0" stroke="#333" stroke-width="2"/>
      <text x="370" y="135" text-anchor="middle" font-size="13">House</text>

      <!-- Industry load -->
      <rect x="450" y="80" width="60" height="40" fill="#cfcfcf" stroke="#333" stroke-width="2"/>
      <text x="480" y="135" text-anchor="middle" font-size="13">Industry</text>

      <!-- Bus → House branch -->
      <line x1="350" y1="160" x2="350" y2="120"
            stroke="#444" stroke-width="3"/>
      <line x1="350" y1="120" x2="370" y2="120"
            stroke="#444" stroke-width="3"/>
      <polygon points="370,120 360,115 360,125" fill="#444"/>
      <text x="360" y="155" font-size="11" text-anchor="middle">
        Bus→House {pv_to_load:.1f} kW
      </text>

      <!-- Bus → Industry branch -->
      <line x1="450" y1="160" x2="450" y2="120"
            stroke="#444" stroke-width="3"/>
      <line x1="450" y1="120" x2="480" y2="120"
            stroke="#444" stroke-width="3"/>
      <polygon points="480,120 470,115 470,125" fill="#444"/>
      <text x="465" y="155" font-size="11" text-anchor="middle">
        Bus→Industry {load:.1f} kW
      </text>

    </svg>
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
    
flows = {
    "pv_to_load": pv_to_load,
    "pv_to_battery": pv_to_battery,
    "pv_to_grid": pv_to_grid,
    "battery_to_load": max(0, load_kw - pv_total - gi),
    "grid_to_load": gi,
}

st.markdown("## 🗺️ EMS Single‑Line Grid Model")
st.markdown(render_ems_grid_animated(node, flows), unsafe_allow_html=True)
