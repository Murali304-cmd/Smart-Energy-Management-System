import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("SEMS.P2PTradingService")

class P2PTradingService:
    """
    Peer-to-Peer (P2P) Microgrid Energy Trading Market & Virtual Power Plant (VPP) Engine.
    Clears local neighborhood energy transactions via continuous double-auction (CDA) mechanics.
    """

    def __init__(self):
        self.market_orders: List[Dict[str, Any]] = [
            {"id": "ORD-101", "neighbor": "Villa 12 (Solar Prosumer)", "type": "ASK (Selling Solar)", "energy_kwh": 4.5, "price_inr": 4.20, "status": "MATCHED"},
            {"id": "ORD-102", "neighbor": "Apartment 4B (Consumer)", "type": "BID (Buying Load)", "energy_kwh": 3.0, "price_inr": 4.30, "status": "MATCHED"},
            {"id": "ORD-103", "neighbor": "Villa 08 (EV Fleet)", "type": "BID (Buying Load)", "energy_kwh": 6.0, "price_inr": 4.10, "status": "OPEN"},
            {"id": "ORD-104", "neighbor": "Block C (Rooftop PV)", "type": "ASK (Selling Solar)", "energy_kwh": 5.2, "price_inr": 4.05, "status": "OPEN"}
        ]
        self.completed_trades: List[Dict[str, Any]] = [
            {"trade_id": "TRD-091", "seller": "Villa 12", "buyer": "Apartment 4B", "energy_kwh": 3.0, "price_inr": 4.25, "timestamp": "2026-09-15T11:45:00Z"}
        ]
        self.vpp_aggregated_capacity_kw = 45.0
        self.vpp_response_mode = "GRID_RESERVE_STANDBY"

    def submit_order(self, neighbor: str, order_type: str, energy_kwh: float, price_inr: float) -> Dict[str, Any]:
        """Submits a new BID (buy) or ASK (sell) order to the decentralized microgrid order book."""
        new_id = f"ORD-{100 + len(self.market_orders) + 1}"
        order = {
            "id": new_id,
            "neighbor": neighbor,
            "type": "ASK (Selling Solar)" if "ask" in order_type.lower() or "sell" in order_type.lower() else "BID (Buying Load)",
            "energy_kwh": round(float(energy_kwh), 2),
            "price_inr": round(float(price_inr), 2),
            "status": "OPEN",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.market_orders.append(order)
        self._clear_cda_auction()
        return order

    def _clear_cda_auction(self):
        """Executes Continuous Double Auction matching between highest bid and lowest ask."""
        bids = [o for o in self.market_orders if "BID" in o["type"] and o["status"] == "OPEN"]
        asks = [o for o in self.market_orders if "ASK" in o["type"] and o["status"] == "OPEN"]
        
        # Sort bids descending (highest willingness to pay), asks ascending (cheapest available)
        bids.sort(key=lambda x: x["price_inr"], reverse=True)
        asks.sort(key=lambda x: x["price_inr"])

        for bid in bids:
            for ask in asks:
                if ask["status"] == "OPEN" and bid["status"] == "OPEN" and bid["price_inr"] >= ask["price_inr"]:
                    clearing_price = round((bid["price_inr"] + ask["price_inr"]) / 2.0, 2)
                    matched_kwh = min(bid["energy_kwh"], ask["energy_kwh"])
                    
                    bid["energy_kwh"] -= matched_kwh
                    ask["energy_kwh"] -= matched_kwh
                    if bid["energy_kwh"] <= 0.01:
                        bid["status"] = "MATCHED"
                    if ask["energy_kwh"] <= 0.01:
                        ask["status"] = "MATCHED"

                    trade_rec = {
                        "trade_id": f"TRD-{len(self.completed_trades) + 101}",
                        "seller": ask["neighbor"],
                        "buyer": bid["neighbor"],
                        "energy_kwh": matched_kwh,
                        "price_inr": clearing_price,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    self.completed_trades.append(trade_rec)
                    logger.info(f"P2P Trade Cleared: {matched_kwh} kWh @ ₹{clearing_price}/kWh between {ask['neighbor']} and {bid['neighbor']}")

    def match_local_market(
        self,
        home_solar_surplus_kw: float,
        home_deficit_kw: float,
        grid_buy_rate: float = 6.50,
        grid_feed_in_rate: float = 3.50
    ) -> Dict[str, Any]:
        """Clears local trade between home and microgrid neighbors at win-win midpoint rates."""
        self._clear_cda_auction()
        p2p_clearing_price = round((grid_buy_rate + grid_feed_in_rate) / 2.0, 2)  # e.g. ₹5.00/kWh

        trade_action = "IDLE"
        energy_traded_kwh = 0.0
        financial_gain_inr = 0.0

        if home_solar_surplus_kw > 0.5:
            trade_action = "P2P_EXPORT_SALE"
            energy_traded_kwh = home_solar_surplus_kw
            financial_gain_inr = round(energy_traded_kwh * (p2p_clearing_price - grid_feed_in_rate), 2)
            desc = f"Selling {energy_traded_kwh:.2f} kW surplus solar to neighbor @ ₹{p2p_clearing_price:.2f}/kWh (vs utility ₹{grid_feed_in_rate:.2f})."
        elif home_deficit_kw > 0.5:
            trade_action = "P2P_IMPORT_BUY"
            energy_traded_kwh = home_deficit_kw
            financial_gain_inr = round(energy_traded_kwh * (grid_buy_rate - p2p_clearing_price), 2)
            desc = f"Buying {energy_traded_kwh:.2f} kW clean community solar @ ₹{p2p_clearing_price:.2f}/kWh (saving vs utility ₹{grid_buy_rate:.2f})."
        else:
            desc = "Home energy in self-consumption balance."

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "p2p_clearing_price_inr": p2p_clearing_price,
            "trade_action": trade_action,
            "energy_traded_kwh": energy_traded_kwh,
            "financial_gain_inr": financial_gain_inr,
            "description": desc,
            "vpp_cluster": {
                "community_name": "Green Meadows Eco Microgrid",
                "participating_homes": 18,
                "total_vpp_available_kw": self.vpp_aggregated_capacity_kw,
                "grid_ancillary_reward_inr_month": 4250.0
            },
            "recent_orders": self.market_orders,
            "completed_trades": self.completed_trades[-5:]
        }
