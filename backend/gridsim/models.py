class Grid:
    def __init__(self, name: str):
        self.name = name
        self.nodes = []

    def add_node(self, node):
        self.nodes.append(node)


class Node:
    def __init__(self, node_id: str, capacity_kw: float):
        self.node_id = node_id
        self.capacity_kw = capacity_kw
        self.households = []
        self.industries = []
        self.pv_systems = []
        self.batteries = []

    def add_household(self, household):
        self.households.append(household)

    def add_industry(self, industry):
        self.industries.append(industry)

    def add_pv(self, pv):
        self.pv_systems.append(pv)

    def add_battery(self, battery):
        self.batteries.append(battery)


class Household:
    def __init__(self, household_id: str, base_demand_kw: float):
        self.household_id = household_id
        self.base_demand_kw = base_demand_kw

    def get_demand(self, hour: int) -> float:
        return self.base_demand_kw


class SolarPV:
    def __init__(self, pv_id: str, peak_kw: float):
        self.pv_id = pv_id
        self.peak_kw = peak_kw

    def get_output(self, irradiance: float) -> float:
        irradiance = max(0, min(irradiance, 1))
        return self.peak_kw * irradiance


class Battery:
    def __init__(self, capacity_kwh, soc_init=0.5):
        self.capacity = capacity_kwh
        self.soc = soc_init * capacity_kwh
        self.min_soc = 0.20 * capacity_kwh
        self.max_soc = 0.80 * capacity_kwh

    def charge(self, amount_kwh):
        """Charge battery but never exceed 80%."""
        available_capacity = self.max_soc - self.soc
        actual_charge = min(amount_kwh, available_capacity)
        self.soc += actual_charge
        return actual_charge

    def discharge(self, amount_kwh):
        """Discharge battery but never go below 20%."""
        available_energy = self.soc - self.min_soc
        actual_discharge = min(amount_kwh, available_energy)
        self.soc -= actual_discharge
        return actual_discharge



class Industry:
    def __init__(self, industry_id: str, base_demand_kw: float):
        self.industry_id = industry_id
        self.base_demand_kw = base_demand_kw

    def get_demand(self, hour: int) -> float:
        return self.base_demand_kw


class SimulationEngine:
    def __init__(self, grid):
        self.grid = grid
        self.history = []

    def step(self, hour: int, irradiance: float):
        grid_load = 0.0
        node_records = []

        for node in self.grid.nodes:
            demand = sum(h.get_demand(hour) for h in node.households)
            demand += sum(i.get_demand(hour) for i in node.industries)

            pv_output = sum(p.get_output(irradiance) for p in node.pv_systems)

            net_load = demand - pv_output

            total_battery_soc = []
            for b in node.batteries:
                if net_load > 0:
                    discharged = b.discharge(net_load)
                    net_load -= discharged
                else:
                    surplus = -net_load
                    charged = b.charge(surplus)
                    net_load += charged
                total_battery_soc.append(b.state_of_charge)

            grid_load += max(net_load, 0)

            node_records.append({
                "node_id": node.node_id,
                "demand_kw": demand,
                "pv_kw": pv_output,
                "battery_soc": total_battery_soc,
                "net_load_kw": max(net_load, 0)
            })

        self.history.append({
            "hour": hour,
            "irradiance": irradiance,
            "grid_load_kw": grid_load,
            "nodes": node_records
        })
