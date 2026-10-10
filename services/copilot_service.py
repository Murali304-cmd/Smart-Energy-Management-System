"""
SEMS AI Energy Copilot & Natural Language Advisory Service.

Provides bilingual (English & Tamil தமிழ்) intelligent energy explanations,
TNEB tariff slab guidance, appliance scheduling optimization, and AI decision rationale.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("SEMS.Copilot")

TNEB_DOMESTIC_SLABS = [
    {"limit": 100, "rate": 0.00, "name": "Free Tier (Govt Subsidy)"},
    {"limit": 400, "rate": 4.70, "name": "Tier 1 (Normal Usage)"},
    {"limit": 500, "rate": 6.30, "name": "Tier 2 (Moderate Usage)"},
    {"limit": 600, "rate": 8.40, "name": "Tier 3 (High Usage)"},
    {"limit": 800, "rate": 9.45, "name": "Tier 4 (Heavy Usage)"},
    {"limit": 1000, "rate": 10.50, "name": "Tier 5 (Commercial-like Domestic)"},
    {"limit": float("inf"), "rate": 11.55, "name": "Tier 6 (Maximum Slab)"}
]


def calculate_tneb_bill(units: float) -> Dict[str, Any]:
    """Calculates official TNEB / TANGEDCO LT-IA domestic bill and active slab."""
    if units <= 0:
        return {"units": 0.0, "total_bill_inr": 0.0, "active_rate": 0.0, "slab_name": "Free Tier"}

    total_bill = 0.0
    active_rate = 0.0
    active_slab = TNEB_DOMESTIC_SLABS[0]["name"]

    # Official slab math
    if units <= 100:
        total_bill = 0.0
        active_rate = 0.0
        active_slab = "Free 100 Units (Govt Subsidy)"
    elif units <= 400:
        # 100 units free, remaining at 4.70
        total_bill = (units - 100) * 4.70
        active_rate = 4.70
        active_slab = "Tier 1 (101 - 400 Units @ ₹4.70)"
    elif units <= 500:
        total_bill = (300 * 4.70) + ((units - 400) * 6.30)
        active_rate = 6.30
        active_slab = "Tier 2 (401 - 500 Units @ ₹6.30)"
    elif units <= 600:
        total_bill = (300 * 4.70) + (100 * 6.30) + ((units - 500) * 8.40)
        active_rate = 8.40
        active_slab = "Tier 3 (501 - 600 Units @ ₹8.40)"
    elif units <= 800:
        total_bill = (300 * 4.70) + (100 * 6.30) + (100 * 8.40) + ((units - 600) * 9.45)
        active_rate = 9.45
        active_slab = "Tier 4 (601 - 800 Units @ ₹9.45)"
    elif units <= 1000:
        total_bill = (300 * 4.70) + (100 * 6.30) + (100 * 8.40) + (200 * 9.45) + ((units - 800) * 10.50)
        active_rate = 10.50
        active_slab = "Tier 5 (801 - 1000 Units @ ₹10.50)"
    else:
        total_bill = (300 * 4.70) + (100 * 6.30) + (100 * 8.40) + (200 * 9.45) + (200 * 10.50) + ((units - 1000) * 11.55)
        active_rate = 11.55
        active_slab = "Tier 6 (1000+ Units @ ₹11.55)"

    return {
        "units": round(units, 2),
        "total_bill_inr": round(total_bill, 2),
        "active_rate": active_rate,
        "slab_name": active_slab
    }


class EnergyCopilotService:
    """
    Bilingual AI Advisor reasoning over real-time home energy states,
    RL dispatch decisions, TNEB tariffs, and solar nowcasts.
    """

    def __init__(self):
        logger.info("Initializing SEMS AI Energy Copilot Service...")

    def generate_quick_insights(self, telemetry: Dict[str, Any], lang: str = "en") -> List[str]:
        """Generates 3 fast, actionable bullet-point insights for dashboard banners."""
        solar = float(telemetry.get("solar_power_kw", 0.0) or 0.0)
        load = float(telemetry.get("load_power_kw", 0.0) or 0.0)
        soc = float(telemetry.get("battery_soc", 50.0) or 50.0)
        units_today = float(telemetry.get("units_used_today", 12.5) or 12.5)
        is_tamil = (lang.lower() == "ta")

        insights = []

        # 1. Solar vs Load Insight
        if solar >= load and solar > 0.5:
            if is_tamil:
                insights.append(f"☀️ சூரிய சக்தி உற்பத்தி ({solar:.1f} kW) உங்கள் வீட்டு சுமையை ({load:.1f} kW) விட அதிகமாக உள்ளது. வீடு 100% இலவச சூரிய ஒளியில் இயங்குகிறது!")
            else:
                insights.append(f"☀️ Solar generation ({solar:.1f} kW) exceeds house demand ({load:.1f} kW). Your home is 100% self-powered!")
        elif solar > 0:
            deficit = max(0.0, load - solar)
            if is_tamil:
                insights.append(f"⚡ சூரிய ஒளி {solar:.1f} kW அளிக்கிறது; மீதமுள்ள {deficit:.1f} kW பேட்டரி மற்றும் EB மூலம் ஈடுசெய்யப்படுகிறது.")
            else:
                insights.append(f"⚡ Solar covers {solar:.1f} kW; the remaining {deficit:.1f} kW is smoothly supplied by battery & grid.")
        else:
            if is_tamil:
                insights.append("🌙 இரவு நேரம்: சூரிய சக்தி இல்லை. வீடு பேட்டரி சேமிப்பு மற்றும் குறைந்த கட்டண EB மூலம் இயங்குகிறது.")
            else:
                insights.append("🌙 Night hours: Solar idle. Home is powered via stored battery energy and off-peak grid.")

        # 2. Battery SoC & Backup Insight
        backup_hours = round(max(0.5, (soc - 20.0) * 0.20 / max(0.5, load)), 1)
        if soc >= 70:
            if is_tamil:
                insights.append(f"🔋 பேட்டரி ஆரோக்கியமாக உள்ளது ({soc:.0f}%). மின் தடை ஏற்பட்டால் ~{backup_hours} மணி நேரம் தாங்கும்.")
            else:
                insights.append(f"🔋 Battery reserve is excellent ({soc:.0f}%). Provides approximately {backup_hours} hours of resilient backup.")
        elif soc >= 30:
            if is_tamil:
                insights.append(f"🔋 பேட்டரி அளவு {soc:.0f}%. மின்சார பயன்பாட்டிற்கு ஏற்ப சேமிப்பு நிர்வகிக்கப்படுகிறது (~{backup_hours} மணி நேரம்).")
            else:
                insights.append(f"🔋 Battery at {soc:.0f}%, offering ~{backup_hours} hours of backup under current load.")
        else:
            if is_tamil:
                insights.append("⚠️ பேட்டரி 20% குறைந்தபட்ச அளவிற்கு அருகில் உள்ளது. சூரிய ஒளி வரும் வரை கூடுதல் சாதனங்களை தவிருங்கள்.")
            else:
                insights.append("⚠️ Battery near depth-of-discharge reserve (20%). Conserve heavy appliances until solar peaks.")

        # 3. TNEB Slab & Savings Insight
        tneb = calculate_tneb_bill(units_today)
        saved_inr = round(units_today * 0.65 * 4.70, 2)
        if is_tamil:
            insights.append(f"💰 இன்று பயன்படுத்தியது: {units_today:.1f} யூனிட்டுகள். சூரிய சக்தியால் இன்று தோராயமாக ₹{saved_inr} மிச்சப்படுத்தப்பட்டுள்ளது!")
        else:
            insights.append(f"💰 Today's consumption: {units_today:.1f} Units ({tneb['slab_name']}). Saved approx ₹{saved_inr} via solar!")

        return insights

    def answer_query(self, query: str, telemetry: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
        """
        Parses user questions in natural language and produces context-rich,
        accurate energy explanations in English or Tamil.
        """
        q = (query or "").lower().strip()
        is_tamil = (lang.lower() == "ta") or any("\u0b80" <= c <= "\u0bff" for c in query)

        solar = float(telemetry.get("solar_power_kw", 0.0) or 0.0)
        load = float(telemetry.get("load_power_kw", 0.0) or 0.0)
        soc = float(telemetry.get("battery_soc", 50.0) or 50.0)
        grid = float(telemetry.get("grid_power_kw", 0.0) or 0.0)
        units_today = float(telemetry.get("units_used_today", 12.5) or 12.5)
        tneb = calculate_tneb_bill(units_today)
        backup_hours = round(max(0.5, (soc - 20.0) * 0.20 / max(0.5, load)), 1)
        action_name = telemetry.get("recommended_action", "SOLAR + BATTERY")

        # Category 1: Bill, Cost, Slab, Savings (பில், கட்டணம், சேமிப்பு)
        if any(w in q for w in ["bill", "cost", "save", "saving", "slab", "rate", "tneb", "amount", "money", "rupee", "ரூபாய்", "பில்", "கட்டணம்", "சேமிப்பு"]):
            saved_today = round(units_today * 0.65 * 4.70, 2)
            month_proj_units = round(units_today * 30, 1)
            month_proj_bill = calculate_tneb_bill(month_proj_units)["total_bill_inr"]

            if is_tamil:
                response = (
                    f"📊 **இன்றைய மின்சார கட்டண விவரம்:**\n"
                    f"- இன்று பயன்படுத்திய மின்சாரம்: **{units_today:.1f} யூனிட்டுகள்**\n"
                    f"- இன்றைய TNEB கட்டண மதிப்பீடு: **₹{tneb['total_bill_inr']}** ({tneb['slab_name']})\n"
                    f"- சூரிய ஒளி & பேட்டரி மூலம் சேமிப்பு: **₹{saved_today}**\n\n"
                    f"💡 **மாதாந்திர கணிப்பு:** இந்த வேகத்தில் சென்றால் மாதத்திற்கு ~{month_proj_units:.0f} யூனிட்டுகள் (கட்டணம் ~₹{month_proj_bill}). "
                    f"முதல் 100 யூனிட்டுகள் தமிழக அரசு இலவசம் என்பதால், மதிய வேளையில் சூரிய ஒளியை அதிகம் பயன்படுத்தினால் கட்டணம் மிகக் குறைவாக இருக்கும்."
                )
            else:
                response = (
                    f"📊 **Today's Electricity & Tariff Analysis:**\n"
                    f"- Total units consumed today: **{units_today:.1f} kWh / Units**\n"
                    f"- Estimated daily TNEB bill: **₹{tneb['total_bill_inr']}** ({tneb['slab_name']})\n"
                    f"- Saved today via Solar + Storage: **₹{saved_today}**\n\n"
                    f"💡 **Month-End Projection:** At this consumption rate, 30-day usage will be ~{month_proj_units:.0f} Units (~₹{month_proj_bill}). "
                    f"To stay in the lowest tariff bracket (or under the 100-unit free subsidy), shift energy-intensive appliances to peak solar hours (11 AM - 3 PM)."
                )

            return {
                "category": "billing_and_tariffs",
                "language": "ta" if is_tamil else "en",
                "answer": response,
                "metrics": {
                    "units_today": units_today,
                    "bill_today_inr": tneb["total_bill_inr"],
                    "saved_inr": saved_today,
                    "slab": tneb["slab_name"]
                }
            }

        # Category 2: Battery & Backup (பேட்டரி, இருப்பு, மின் தடை)
        elif any(w in q for w in ["battery", "soc", "backup", "charge", "discharge", "power cut", "outage", "பேட்டரி", "மின் தடை", "சேமிப்பு"]):
            if is_tamil:
                response = (
                    f"🔋 **பேட்டரி இருப்பு & நிலைமை:**\n"
                    f"- தற்போதைய பேட்டரி அளவு: **{soc:.1f}%**\n"
                    f"- தற்போதைய மின் நுகர்வில் ({load:.2f} kW) இயங்கக்கூடிய நேரம்: **~{backup_hours} மணி நேரம்**\n"
                    f"- AI கட்டுப்பாட்டு செயல்: **{action_name}**\n\n"
                    f"💡 **AI விளக்கம்:** உங்கள் பேட்டரி குறைந்தபட்சம் 20% இருப்பை எப்போதும் மின் தடை அவசர காலத்திற்காக பாதுகாக்கிறது. "
                    f"சூரிய ஒளி உச்சத்தில் இருக்கும் போது பேட்டரி தானாகவே சார்ஜ் ஆகும்."
                )
            else:
                response = (
                    f"🔋 **Battery Energy Storage Status:**\n"
                    f"- State of Charge (SoC): **{soc:.1f}%** (Usable reserve: {max(0.0, soc - 20.0):.1f}%)\n"
                    f"- Estimated backup run-time: **~{backup_hours} hours** at current {load:.2f} kW load\n"
                    f"- Active AI Strategy: **{action_name}**\n\n"
                    f"💡 **AI Decision Rationale:** SEMS maintains a 20% DoD reserve so your home remains resilient during unexpected grid outages. "
                    f"During peak sun, excess solar will replenish the battery to 100% at zero grid cost."
                )

            return {
                "category": "battery_and_resilience",
                "language": "ta" if is_tamil else "en",
                "answer": response,
                "metrics": {
                    "soc_pct": soc,
                    "backup_hours": backup_hours,
                    "action": action_name
                }
            }

        # Category 3: Appliances & Scheduling (சாதனங்கள், வாஷிங் மெஷின், ஏசி, ஹீட்டர்)
        elif any(w in q for w in ["appliance", "washing", "ac", "air conditioner", "geyser", "heater", "fridge", "turn on", "run", "schedule", "சாதனம்", "வாஷிங்", "ஏசி", "ஹீட்டர்"]):
            can_run_heavy = (solar >= 2.0) or (soc >= 75.0)
            if is_tamil:
                advice = (
                    "✅ **ஆம், இப்போது இயக்கலாம்!** சூரிய ஒளி மற்றும் பேட்டரி போதுமான அளவு உள்ளது. கூடுதல் கட்டணம் இன்றி இலவச சூரிய ஒளியில் இயங்கும்."
                    if can_run_heavy else
                    "⏳ **சிறிது நேரம் காத்திருப்பது நல்லது.** இப்போது இயக்கினால் EB மின்சாரம் இறக்குமதி செய்யப்படும். காலை 11:00 மணி முதல் மதியம் 3:00 மணிக்குள் சூரிய ஒளி உச்சத்தில் இருக்கும் போது இயக்கினால் பணம் மிச்சமாகும்."
                )
                response = (
                    f"🔌 **சாதன பயன்பாட்டு ஆலோசனை:**\n"
                    f"- தற்போதைய சூரிய மின்சாரம்: **{solar:.2f} kW** | வீட்டு சுமை: **{load:.2f} kW**\n"
                    f"- ஆலோசனை: {advice}\n\n"
                    f"📌 **பரிந்துரைக்கப்படும் நேரம்:**\n"
                    f"- 🧺 வாஷிங் மெஷின் & மோட்டார்: **11:00 AM - 02:30 PM** (சூரிய ஒளி உச்சம்)\n"
                    f"- 🚿 வாட்டர் ஹீட்டர்: **07:00 AM - 08:30 AM** (பேட்டரி சேமிப்பு)\n"
                    f"- ❄️ ஏர் கண்டிஷனர் (AC): பகலில் 24°C-ல் இயக்குவது உகந்தது."
                )
            else:
                advice = (
                    "✅ **Yes, great time to run!** Solar production and battery reserves are sufficient to power heavy loads without grid surcharge."
                    if can_run_heavy else
                    "⏳ **Wait for solar window if possible.** Running now will import electricity from the grid. Scheduling heavy appliances between 11:00 AM and 2:30 PM maximizes free solar self-consumption."
                )
                response = (
                    f"🔌 **Appliance Scheduling & Optimization:**\n"
                    f"- Current Solar Generation: **{solar:.2f} kW** | Active Demand: **{load:.2f} kW**\n"
                    f"- Recommendation: {advice}\n\n"
                    f"📌 **Optimal Operating Windows:**\n"
                    f"- 🧺 Washing Machine & Water Pumps: **11:00 AM – 02:30 PM** (Peak Solar)\n"
                    f"- 🚿 Water Heater / Geyser: **07:00 AM – 08:30 AM** (Solar pre-heat or off-peak)\n"
                    f"- ❄️ Air Conditioner (1.5 Ton): Recommended setpoint 24°C–25°C for 22% energy savings."
                )

            return {
                "category": "appliance_scheduling",
                "language": "ta" if is_tamil else "en",
                "answer": response,
                "metrics": {
                    "can_run_heavy": can_run_heavy,
                    "solar_kw": solar,
                    "load_kw": load
                }
            }

        # Category 4: General / AI Decision Explanation (பொதுவான / AI விளக்கம்)
        else:
            if is_tamil:
                response = (
                    f"🤖 **SEMS AI மின்சார உதவியாளர்:**\n"
                    f"தற்போது உங்கள் வீடு **{action_name}** முறையில் இயங்குகிறது.\n\n"
                    f"• ☀️ சூரிய சக்தி: **{solar:.2f} kW**\n"
                    f"• 🔋 பேட்டரி: **{soc:.1f}%** ({backup_hours} மணி நேர பேக்கப்)\n"
                    f"• ⚡ வீட்டு பயன்பாடு: **{load:.2f} kW**\n"
                    f"• 🔌 EB மின்சாரம்: **{grid:.2f} kW**\n"
                    f"• 💰 இன்றைய TNEB கணக்கு: **{units_today:.1f} யூனிட்டுகள்** ({tneb['slab_name']})\n\n"
                    f"என்னிடம் கட்டணம், பேட்டரி நிலை, சாதனங்கள் இயக்கும் நேரம் அல்லது மின்சார சேமிப்பு குறித்து கேட்கலாம்!"
                )
            else:
                response = (
                    f"🤖 **SEMS Intelligent Energy Copilot:**\n"
                    f"Your microgrid is currently operating under the **{action_name}** policy.\n\n"
                    f"• ☀️ Solar Generation: **{solar:.2f} kW**\n"
                    f"• 🔋 Battery SoC: **{soc:.1f}%** (~{backup_hours} hrs backup)\n"
                    f"• ⚡ Household Load: **{load:.2f} kW**\n"
                    f"• 🔌 Grid Import/Export: **{grid:.2f} kW**\n"
                    f"• 💰 Units Today: **{units_today:.1f} kWh** ({tneb['slab_name']})\n\n"
                    f"You can ask me about: *Electricity bill & savings*, *Battery backup duration*, *When to run washing machine/AC*, or *How to stay in the free 100-unit slab*!"
                )

            return {
                "category": "general_overview",
                "language": "ta" if is_tamil else "en",
                "answer": response,
                "metrics": {
                    "solar_kw": solar,
                    "load_kw": load,
                    "soc_pct": soc,
                    "action": action_name
                }
            }


# Singleton instance
copilot_service = EnergyCopilotService()
