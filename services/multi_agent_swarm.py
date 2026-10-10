"""
Multi-Agent Microgrid Swarm P2P Consensus & Double-Auction Energy Trading Engine.
Simulates autonomous localized microgrid nodes negotiating energy bids, clearing midpoint rates,
and maintaining a cryptographic Proof-of-Green Ledger.
"""

import time
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("SEMS.SwarmTrading")

class SwarmNode:
    def __init__(self, node_id: str, name: str, node_type: str, solar_capacity_kw: float, battery_kwh: float):
        self.node_id = node_id
        self.name = name
        self.node_type = node_type # "PROSUMER", "CONSUMER", "STORAGE_HUB"
        self.solar_capacity_kw = solar_capacity_kw
        self.battery_kwh = battery_kwh
        self.current_solar_kw = 0.0
        self.current_load_kw = 0.0
        self.current_soc_pct = 70.0
        self.wallet_balance_inr = 500.0

class MultiAgentSwarmEngine:
    """
    Decentralized multi-agent coordination simulating dynamic neighborhood microgrid exchange.
    """
    def __init__(self):
        self.nodes: Dict[str, SwarmNode] = {
            "node_home_local": SwarmNode("node_home_local", "Home (Local SEMS)", "PROSUMER", 5.0, 20.0),
            "node_peer_alpha": SwarmNode("node_peer_alpha", "Neighbor Alpha (Villa 102)", "PROSUMER", 8.0, 15.0),
            "node_peer_beta": SwarmNode("node_peer_beta", "Neighbor Beta (Villa 104)", "CONSUMER", 0.0, 5.0),
            "node_peer_gamma": SwarmNode("node_peer_gamma", "Community EV Hub", "STORAGE_HUB", 12.0, 60.0),
        }
        self.ledger: List[Dict[str, Any]] = []
        self._seed_initial_ledger()

    def _seed_initial_ledger(self):
        sample_hashes = [
            ("node_peer_alpha", "node_peer_beta", 2.4, 3.85, "000a8f9b2c3d4e5f"),
            ("node_peer_gamma", "node_home_local", 1.8, 3.90, "000b9e8d7c6b5a4f"),
            ("node_home_local", "node_peer_beta", 3.1, 3.80, "000c7d6e5f4a3b2c")
        ]
        now = time.time()
        for i, (seller, buyer, kwh, rate, h) in enumerate(sample_hashes):
            self.ledger.append({
                "block_index": i + 1,
                "timestamp": datetime.fromtimestamp(now - (3600 * (3 - i)), tz=timezone.utc).isoformat(),
                "seller": seller,
                "buyer": buyer,
                "energy_kwh": kwh,
                "rate_inr_kwh": rate,
                "total_inr": round(kwh * rate, 2),
                "block_hash": h,
                "green_provenance_verified": True
            })

    def run_swarm_market_clearing(
        self,
        local_solar_kw: float,
        local_load_kw: float,
        local_soc: float,
        grid_import_tariff: float = 4.80,
        grid_export_feedin: float = 2.50
    ) -> Dict[str, Any]:
        """
        Executes multi-agent double-auction market clearing between swarm nodes.
        """
        # Update local node telemetry
        self.nodes["node_home_local"].current_solar_kw = local_solar_kw
        self.nodes["node_home_local"].current_load_kw = local_load_kw
        self.nodes["node_home_local"].current_soc_pct = local_soc

        # Simulate dynamic prosumer agents
        self.nodes["node_peer_alpha"].current_solar_kw = max(0.0, local_solar_kw * 1.3)
        self.nodes["node_peer_alpha"].current_load_kw = 2.8
        self.nodes["node_peer_beta"].current_solar_kw = 0.0
        self.nodes["node_peer_beta"].current_load_kw = 3.5
        self.nodes["node_peer_gamma"].current_solar_kw = max(0.0, local_solar_kw * 1.8)
        self.nodes["node_peer_gamma"].current_load_kw = 5.2

        bids = [] # Buyers: [node_id, max_price, demand_kw]
        asks = [] # Sellers: [node_id, min_price, surplus_kw]

        for nid, node in self.nodes.items():
            net_power = node.current_solar_kw - node.current_load_kw
            if net_power > 0.1:
                # Seller ask price between feed-in tariff and grid tariff
                ask_price = round(grid_export_feedin + (grid_import_tariff - grid_export_feedin) * 0.35, 2)
                asks.append({"node_id": nid, "name": node.name, "surplus_kw": round(net_power, 2), "ask_inr": ask_price})
            elif net_power < -0.1:
                # Buyer bid price offering discount compared to grid import
                bid_price = round(grid_import_tariff - (grid_import_tariff - grid_export_feedin) * 0.35, 2)
                bids.append({"node_id": nid, "name": node.name, "deficit_kw": round(abs(net_power), 2), "bid_inr": bid_price})

        # Market equilibrium clearing price: midpoint of average bid and ask
        total_matched_kw = 0.0
        clearing_price_inr = round((grid_import_tariff + grid_export_feedin) / 2.0, 2)
        trades_executed = []

        for ask in asks:
            for bid in bids:
                if ask["surplus_kw"] > 0 and bid["deficit_kw"] > 0:
                    trade_vol = min(ask["surplus_kw"], bid["deficit_kw"])
                    if trade_vol > 0.05:
                        total_matched_kw += trade_vol
                        ask["surplus_kw"] -= trade_vol
                        bid["deficit_kw"] -= trade_vol
                        
                        # Generate cryptographic block hash
                        block_str = f"{ask['node_id']}{bid['node_id']}{trade_vol}{clearing_price_inr}{time.time()}"
                        block_hash = hashlib.sha256(block_str.encode()).hexdigest()[:16]

                        trade_record = {
                            "block_index": len(self.ledger) + 1,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "seller": ask["node_id"],
                            "seller_name": ask["name"],
                            "buyer": bid["node_id"],
                            "buyer_name": bid["name"],
                            "energy_kwh": round(trade_vol, 2),
                            "rate_inr_kwh": clearing_price_inr,
                            "total_inr": round(trade_vol * clearing_price_inr, 2),
                            "block_hash": f"000{block_hash}",
                            "green_provenance_verified": True
                        }
                        trades_executed.append(trade_record)
                        self.ledger.insert(0, trade_record)
                        if len(self.ledger) > 30:
                            self.ledger.pop()

        return {
            "status": "success",
            "market_clearing_inr": clearing_price_inr,
            "grid_import_benchmark_inr": grid_import_tariff,
            "grid_feedin_benchmark_inr": grid_export_feedin,
            "prosumer_savings_pct": round(((grid_import_tariff - clearing_price_inr) / grid_import_tariff) * 100, 1),
            "total_p2p_power_traded_kw": round(total_matched_kw, 2),
            "active_swarm_nodes": [
                {
                    "node_id": n.node_id,
                    "name": n.name,
                    "type": n.node_type,
                    "solar_kw": round(n.current_solar_kw, 2),
                    "load_kw": round(n.current_load_kw, 2),
                    "soc_pct": round(n.current_soc_pct, 1)
                }
                for n in self.nodes.values()
            ],
            "recent_trades": trades_executed,
            "proof_of_green_ledger": self.ledger[:10]
        }
