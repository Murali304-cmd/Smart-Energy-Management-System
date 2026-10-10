import numpy as np
from typing import Dict, Any, List

class ScenarioSimulatorService:
    """
    'What-If' Solar PV, Battery Capacity & Tariff ROI Scenario Evaluator.
    Computes annual generation forecasts, electricity bill savings, payback period (ROI in years),
    and lifetime CO2 emission reductions for custom solar & storage configurations.
    """

    # Benchmarks (Tamil Nadu / South India residential solar & LiFePO4 battery benchmarks)
    SOLAR_COST_PER_KW_INR = 48000.0       # ₹ 48,000 / kW (including panels, inverter, mounting, BOS)
    BATTERY_COST_PER_KWH_INR = 22000.0    # ₹ 22,000 / kWh (LiFePO4 high-cycle energy storage)
    ANNUAL_SOLAR_KWH_PER_KW = 1450.0      # ~1450 kWh generated per kW capacity annually
    GRID_BASELINE_TARIFF_INR = 4.70       # Standard tariff rate ₹ 4.70 / kWh
    PEAK_TARIFF_INR = 6.50                # Peak tariff rate ₹ 6.50 / kWh
    CO2_EMISSION_FACTOR_KG_PER_KWH = 0.82 # ~0.82 kg CO2 per kWh grid electricity displaced

    def evaluate_scenario(
        self,
        solar_capacity_kw: float = 3.0,
        battery_capacity_kwh: float = 7.0,
        daily_average_load_kwh: float = 12.0,
        grid_tariff_inr: float = 4.70,
        system_lifespan_years: int = 15
    ) -> Dict[str, Any]:
        """
        Evaluates financial savings, ROI payback period, and green energy self-sufficiency.
        """
        solar_kw = max(0.5, float(solar_capacity_kw))
        bat_kwh = max(1.0, float(battery_capacity_kwh))
        daily_load = max(2.0, float(daily_average_load_kwh))
        tariff = max(1.0, float(grid_tariff_inr))

        # 1. Capital Expenditure (CapEx)
        solar_capex = round(solar_kw * self.SOLAR_COST_PER_KW_INR, 2)
        battery_capex = round(bat_kwh * self.BATTERY_COST_PER_KWH_INR, 2)
        total_investment_inr = round(solar_capex + battery_capex, 2)

        # 2. Generation & Self-Sufficiency
        annual_solar_gen_kwh = round(solar_kw * self.ANNUAL_SOLAR_KWH_PER_KW, 1)
        annual_load_demand_kwh = round(daily_load * 365.0, 1)

        # Usable battery capacity (80% Depth of Discharge)
        usable_battery_storage_kwh = round(bat_kwh * 0.80, 2)

        # Simulated daily dispatch fraction
        solar_self_consumed_pct = min(92.0, 50.0 + (bat_kwh / solar_kw) * 12.0)
        annual_self_consumed_kwh = round(min(annual_solar_gen_kwh * (solar_self_consumed_pct / 100.0), annual_load_demand_kwh * 0.95), 1)
        annual_grid_import_kwh = max(0.0, round(annual_load_demand_kwh - annual_self_consumed_kwh, 1))

        # 3. Financial Savings Calculation
        annual_baseline_grid_cost = round(annual_load_demand_kwh * tariff, 2)
        annual_post_solar_grid_cost = round(annual_grid_import_kwh * tariff, 2)
        annual_savings_inr = round(annual_baseline_grid_cost - annual_post_solar_grid_cost, 2)
        monthly_savings_inr = round(annual_savings_inr / 12.0, 2)

        # 4. Payback Period (ROI in Years)
        if annual_savings_inr > 0:
            payback_years = round(total_investment_inr / annual_savings_inr, 1)
        else:
            payback_years = 99.0

        # Lifetime 15-year net return
        lifetime_savings_inr = round(annual_savings_inr * system_lifespan_years - total_investment_inr, 2)
        roi_percentage = round((lifetime_savings_inr / total_investment_inr) * 100.0, 1) if total_investment_inr > 0 else 0.0

        # 5. Environmental Sustainability Impact
        annual_co2_avoided_kg = round(annual_self_consumed_kwh * self.CO2_EMISSION_FACTOR_KG_PER_KWH, 1)
        annual_trees_equivalent = round(annual_co2_avoided_kg / 21.0, 1) # ~21 kg CO2 absorbed per tree/year
        renewable_fraction_pct = round((annual_self_consumed_kwh / annual_load_demand_kwh) * 100.0, 1)

        # 6. Monthly 12-Month Projection Array
        monthly_breakdown = []
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        solar_monthly_weights = [1.0, 1.1, 1.25, 1.3, 1.15, 0.85, 0.80, 0.90, 1.0, 0.95, 0.85, 0.90]

        for m_idx, m_name in enumerate(months):
            weight = solar_monthly_weights[m_idx]
            m_solar = round((annual_solar_gen_kwh / 12.0) * weight, 1)
            m_load = round(annual_load_demand_kwh / 12.0, 1)
            m_saved = round((annual_savings_inr / 12.0) * weight, 2)
            monthly_breakdown.append({
                "month": m_name,
                "solar_generation_kwh": m_solar,
                "household_load_kwh": m_load,
                "bill_savings_inr": m_saved
            })

        return {
            "inputs": {
                "solar_capacity_kw": solar_kw,
                "battery_capacity_kwh": bat_kwh,
                "daily_average_load_kwh": daily_load,
                "grid_tariff_inr": tariff
            },
            "financials": {
                "solar_capex_inr": solar_capex,
                "battery_capex_inr": battery_capex,
                "total_investment_inr": total_investment_inr,
                "monthly_savings_inr": monthly_savings_inr,
                "annual_savings_inr": annual_savings_inr,
                "payback_years": payback_years,
                "lifetime_net_savings_inr": lifetime_savings_inr,
                "roi_percentage": roi_percentage
            },
            "energy_balance": {
                "annual_solar_gen_kwh": annual_solar_gen_kwh,
                "annual_load_demand_kwh": annual_load_demand_kwh,
                "annual_self_consumed_kwh": annual_self_consumed_kwh,
                "annual_grid_import_kwh": annual_grid_import_kwh,
                "renewable_fraction_pct": renewable_fraction_pct,
                "usable_battery_storage_kwh": usable_battery_storage_kwh
            },
            "environmental_impact": {
                "annual_co2_avoided_kg": annual_co2_avoided_kg,
                "lifetime_co2_avoided_tonnes": round((annual_co2_avoided_kg * system_lifespan_years) / 1000.0, 2),
                "trees_planted_equivalent": annual_trees_equivalent
            },
            "monthly_breakdown": monthly_breakdown
        }
