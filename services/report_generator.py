import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger("SEMS.ReportGenerator")

class ReportGenerator:
    """
    Automated Energy Audit & TNEB Billing Analytics Report Generator.
    Generates professional monthly energy efficiency audits and financial ROI statements.
    """

    def generate_monthly_audit_html(
        self,
        month_name: str,
        total_solar_kwh: float,
        total_load_kwh: float,
        total_grid_imported_kwh: float,
        total_grid_exported_kwh: float,
        total_bill_saved_inr: float,
        co2_offset_kg: float
    ) -> str:
        """Generates a styled, printable HTML Energy Audit Statement."""
        self_sufficiency_pct = round((total_solar_kwh / total_load_kwh * 100.0), 1) if total_load_kwh > 0 else 100.0
        grid_independence_pct = round(((total_load_kwh - total_grid_imported_kwh) / total_load_kwh * 100.0), 1) if total_load_kwh > 0 else 100.0

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SEMS Monthly Energy Audit Report - {month_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #1e293b; background: #f8fafc; }}
        .header {{ border-bottom: 3px solid #0284c7; padding-bottom: 20px; display: flex; justify-content: space-between; }}
        .title {{ font-size: 24px; font-weight: bold; color: #0f172a; }}
        .subtitle {{ font-size: 14px; color: #64748b; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 30px 0; }}
        .kpi-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid #0284c7; }}
        .kpi-title {{ font-size: 12px; text-transform: uppercase; color: #64748b; font-weight: 600; }}
        .kpi-val {{ font-size: 22px; font-weight: bold; color: #0f172a; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: white; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1fr solid #e2e8f0; }}
        th {{ background: #f1f5f9; font-weight: 600; color: #475569; }}
        .grade-badge {{ display: inline-block; padding: 4px 12px; background: #dcfce7; color: #166534; font-weight: bold; border-radius: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="title">⚡ Smart Home Energy Management System</div>
            <div class="subtitle">Official Monthly Energy Efficiency & Carbon Audit Statement</div>
        </div>
        <div style="text-align: right;">
            <div style="font-weight: bold;">Month: {month_name}</div>
            <div class="subtitle">Generated: {datetime.now().strftime('%d %b %Y')}</div>
        </div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title">Solar Generation</div>
            <div class="kpi-val">{total_solar_kwh:.1f} kWh</div>
        </div>
        <div class="kpi-card" style="border-left-color: #10b981;">
            <div class="kpi-title">Clean Self-Sufficiency</div>
            <div class="kpi-val">{self_sufficiency_pct}%</div>
        </div>
        <div class="kpi-card" style="border-left-color: #f59e0b;">
            <div class="kpi-title">Net Financial Savings</div>
            <div class="kpi-val">₹{total_bill_saved_inr:.2f}</div>
        </div>
        <div class="kpi-card" style="border-left-color: #8b5cf6;">
            <div class="kpi-title">CO₂ Avoided</div>
            <div class="kpi-val">{co2_offset_kg:.1f} kg</div>
        </div>
    </div>

    <h3>📊 Consumption & Grid Interaction Breakdown</h3>
    <table>
        <thead>
            <tr>
                <th>Category</th>
                <th>Energy Metric</th>
                <th>Grid Rate</th>
                <th>Cost / Valuation</th>
                <th>Performance Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Rooftop Solar PV Output</td>
                <td>{total_solar_kwh:.1f} kWh</td>
                <td>--</td>
                <td>Valued at ₹{round(total_solar_kwh * 6.5, 2)}</td>
                <td><span class="grade-badge">A+ Optimal</span></td>
            </tr>
            <tr>
                <td>Total Household Demand</td>
                <td>{total_load_kwh:.1f} kWh</td>
                <td>₹5.20 avg</td>
                <td>₹{round(total_load_kwh * 5.2, 2)}</td>
                <td>Baseline Normalized</td>
            </tr>
            <tr>
                <td>Grid Electricity Imported</td>
                <td>{total_grid_imported_kwh:.1f} kWh</td>
                <td>₹6.80 peak</td>
                <td>₹{round(total_grid_imported_kwh * 6.8, 2)}</td>
                <td>Reduced by {grid_independence_pct}%</td>
            </tr>
            <tr>
                <td>Surplus Solar Exported to Grid</td>
                <td>{total_grid_exported_kwh:.1f} kWh</td>
                <td>₹3.50 feed-in</td>
                <td>+₹{round(total_grid_exported_kwh * 3.5, 2)} Net Credit</td>
                <td>Export Optimized</td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""
        return html
