import math

# ---------------------------------------------------------
# PV PERFORMANCE CONSTANTS
# ---------------------------------------------------------
PV_EFFICIENCY = 0.90
TEMP_COEFF = -0.004
NOCT = 45
AMBIENT_TEMP = 25

# Default grid pricing (€/kWh)
GRID_IMPORT_PRICE = 0.30
GRID_EXPORT_PRICE = 0.10


# ---------------------------------------------------------
# PV TEMPERATURE MODEL
# ---------------------------------------------------------
def pv_cell_temperature(irradiance):
    return AMBIENT_TEMP + (NOCT - 20) * irradiance


# ---------------------------------------------------------
# LOAD PROFILES
# ---------------------------------------------------------
def household_profile(hour: int) -> float:
    if 6 <= hour <= 9:
        return 2.5
    elif 18 <= hour <= 22:
        return 3.0
    elif 0 <= hour <= 5:
        return 0.8
    else:
        return 1.5


def industry_profile(hour: int) -> float:
    if 8 <= hour <= 18:
        return 5.0
    else:
        return 1.0


# ---------------------------------------------------------
# BATTERY CLASS
# ---------------------------------------------------------
class Battery:
    def __init__(self, capacity_kwh, soc_init=0.5, max_charge_kw=3.0, max_discharge_kw=3.0):
        self.capacity = capacity_kwh
        self.soc = soc_init * capacity_kwh
        self.min_soc = 0.20 * capacity_kwh
        self.max_soc = 0.80 * capacity_kwh

        self.max_charge_kw = max_charge_kw
        self.max_discharge_kw = max_discharge_kw

    def charge(self, amount_kwh):
        amount_kwh = min(amount_kwh, self.max_charge_kw)
        available_capacity = self.max_soc - self.soc
        actual_charge = min(amount_kwh, available_capacity)
        self.soc += actual_charge
        return actual_charge

    def discharge(self, amount_kwh):
        amount_kwh = min(amount_kwh, self.max_discharge_kw)
        available_energy = self.soc - self.min_soc
        actual_discharge = min(amount_kwh, available_energy)
        self.soc -= actual_discharge
        return actual_discharge


# ---------------------------------------------------------
# MULTI‑NODE SIMULATION ENGINE (CONTROL‑ENABLED + SCENARIOS)
# ---------------------------------------------------------
def run_simulation(
    hours,
    irradiance_curve,
    num_nodes,
    households_per_node,
    industries_per_node,
    pv_kw_per_node,
    battery_kwh_per_node,
    controls=None,
):

    # -----------------------------
    # APPLY CONTROL DEFAULTS
    # -----------------------------
    if controls is None:
        controls = {}

    pv1_enabled = controls.get("pv1_enabled", True)
    pv2_enabled = controls.get("pv2_enabled", True)
    inverter_limit_ctrl = controls.get("inverter_limit_kw", pv_kw_per_node)

    battery_enabled = controls.get("battery_enabled", True)
    max_charge_ctrl = controls.get("max_charge_kw", 3.0)
    max_discharge_ctrl = controls.get("max_discharge_kw", 3.0)
    soc_min_pct = controls.get("soc_min_pct", 20)
    soc_max_pct = controls.get("soc_max_pct", 80)

    grid_enabled = controls.get("grid_enabled", True)
    grid_import_price = controls.get("grid_import_price", GRID_IMPORT_PRICE)
    grid_export_price = controls.get("grid_export_price", GRID_EXPORT_PRICE)

    scenario = controls.get("scenario", "Self-Consumption Mode")

    # -----------------------------
    # INITIALIZE NODES
    # -----------------------------
    nodes = []
    for _ in range(num_nodes):

        pv1_kw = pv_kw_per_node if pv1_enabled else 0.0
        pv2_kw = pv_kw_per_node if pv2_enabled else 0.0

        battery = Battery(
            capacity_kwh=battery_kwh_per_node,
            max_charge_kw=max_charge_ctrl,
            max_discharge_kw=max_discharge_ctrl,
        )

        # Apply SOC limits
        battery.min_soc = (soc_min_pct / 100) * battery.capacity
        battery.max_soc = (soc_max_pct / 100) * battery.capacity

        # Disable battery if needed
        if not battery_enabled:
            battery.capacity = 0.0
            battery.soc = 0.0
            battery.min_soc = 0.0
            battery.max_soc = 0.0
            battery.max_charge_kw = 0.0
            battery.max_discharge_kw = 0.0

        # ---------------------------------------------------------
        # APPLY SCENARIO CONTROL STRATEGIES (PER NODE)
        # ---------------------------------------------------------
        if scenario == "Self-Consumption Mode":
            # Default behaviour: PV → Load → Battery → Grid
            pass

        elif scenario == "Battery-First Mode":
            # Battery discharges aggressively, no charging
            battery.max_discharge_kw = max_discharge_ctrl
            battery.max_charge_kw = 0.0

        elif scenario == "Grid-First Mode":
            # Grid supplies load first, battery only charges
            battery.max_discharge_kw = 0.0
            battery.max_charge_kw = max_charge_ctrl

        elif scenario == "Export-Maximization Mode":
            # PV goes to grid, battery mostly idle
            battery.max_charge_kw = 0.0
            if grid_enabled:
                battery.max_discharge_kw = 0.0

        nodes.append({
            "pv1_kw": pv1_kw,
            "pv2_kw": pv2_kw,
            "inverter_limit_kw": inverter_limit_ctrl,
            "battery": battery,
            "households": households_per_node,
            "industries": industries_per_node,
        })

    history = []

    # -----------------------------
    # SIMULATION LOOP
    # -----------------------------
    for hour in range(hours):

        irradiance = irradiance_curve(hour)

        node_values = []
        total_grid_import = 0.0
        total_grid_export = 0.0
        total_grid_load = 0.0

        for node in nodes:

            # PV production
            pv1_dc_raw = node["pv1_kw"] * irradiance
            pv2_dc_raw = node["pv2_kw"] * irradiance
            pv_total_dc_raw = pv1_dc_raw + pv2_dc_raw

            cell_temp = pv_cell_temperature(irradiance)
            temp_loss_factor = 1 + TEMP_COEFF * (cell_temp - 25)

            pv1_dc = pv1_dc_raw * PV_EFFICIENCY * temp_loss_factor
            pv2_dc = pv2_dc_raw * PV_EFFICIENCY * temp_loss_factor
            pv_total_dc = pv1_dc + pv2_dc

            inv_limit = node["inverter_limit_kw"]
            pv_total_ac = min(pv_total_dc, inv_limit)

            if pv_total_dc > 0:
                pv1_output = pv_total_ac * (pv1_dc / pv_total_dc)
                pv2_output = pv_total_ac * (pv2_dc / pv_total_dc)
            else:
                pv1_output = 0.0
                pv2_output = 0.0

            # Load
            household_load = node["households"] * household_profile(hour)
            industry_load = node["industries"] * industry_profile(hour)
            total_load = household_load + industry_load

            battery = node["battery"]

            # -----------------------------
            # PV → Load → Battery → Grid
            # -----------------------------
            if pv_total_ac >= total_load:
                load_supplied_by_pv = total_load
                pv_surplus = pv_total_ac - total_load
                load_deficit = 0.0
            else:
                load_supplied_by_pv = pv_total_ac
                pv_surplus = 0.0
                load_deficit = total_load - pv_total_ac

            # PV surplus → battery
            if pv_surplus > 0:
                charged = battery.charge(pv_surplus)
                pv_surplus_after_battery = pv_surplus - charged
            else:
                charged = 0.0
                pv_surplus_after_battery = 0.0

            # PV surplus → grid
            grid_export = pv_surplus_after_battery if grid_enabled else 0.0

            # Battery discharge
            if load_deficit > 0:
                discharged = battery.discharge(load_deficit)
                remaining_deficit = load_deficit - discharged
            else:
                discharged = 0.0
                remaining_deficit = 0.0

            # Remaining deficit → grid
            grid_import = remaining_deficit if grid_enabled else 0.0

            total_grid_import += grid_import
            total_grid_export += grid_export
            total_grid_load += total_load

            node_values.append((
                pv1_output,
                pv2_output,
                battery,
                total_load,
                grid_import,
                grid_export
            ))

        # Save history
        history.append({
    "hour": hour,
    "irradiance": irradiance,
    "grid_load_kw": total_grid_load,
    "grid_contribution_kw": total_grid_import - total_grid_export,

    "pv_to_load_kw": load_supplied_by_pv,
    "pv_to_battery_kw": charged,
    "pv_to_grid_kw": grid_export,

    "grid_import_kwh": total_grid_import,
    "grid_export_kwh": total_grid_export,
    "cost_eur": total_grid_import * grid_import_price,
    "revenue_eur": total_grid_export * grid_export_price,
    "net_cost_eur": (total_grid_import * grid_import_price)
                    - (total_grid_export * grid_export_price),

    "nodes": [
    {
        "pv1_kw": pv1_kw,
        "pv2_kw": pv2_kw,
        "battery_soc": 100.0 * (battery.soc / battery.capacity) if battery.capacity > 0 else 0.0,
        "load_kw": total_load,
        "grid_import_kw": grid_import,
        "grid_export_kw": grid_export,
    }
    for (pv1_kw, pv2_kw, battery, total_load, grid_import, grid_export) in node_values
]

})

    return history
