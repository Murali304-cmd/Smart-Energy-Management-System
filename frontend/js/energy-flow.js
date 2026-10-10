/**
 * VERA Real-Time Energy Flow & Dynamic Battery Backup Controller
 * Implements realistic Solar -> House -> Battery -> Grid visualization,
 * dynamic particle flow animations, and 10-hour backup duration monitoring.
 */

class EnergyFlowVisualizer {
    constructor() {
        this.pollIntervalMs = 15000;
        this.timer = null;
        this.lastData = null;
        this.isPolling = false;
    }

    init() {
        console.log("SEMS Real-Time Energy Flow Visualizer synchronized with dashboard manager.");
    }

    startPolling() {
        // Polling is managed centrally by VeraApp and WebSocket telemetry
    }

    stopPolling() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
        this.isPolling = false;
    }

    async fetchAndUpdate() {
        try {
            if (!window.veraApi) return;
            const data = await window.veraApi.getDashboardData();
            if (data) {
                this.lastData = data;
                if (window.veraDashboard) {
                    window.veraDashboard.render(data);
                } else {
                    this.render(data);
                }
            }
        } catch (err) {
            console.warn("Energy flow polling update skipped:", err);
        }
    }

    render(data) {
        if (!data) return;
        const rec = data.recommendation || {};
        const preds = data.predictions || {};
        const live = data.live || {};
        const em = data.energy_management || {};

        const solarKw = parseFloat(rec.solar_power || preds.solar || data.solar_power_kw || em.solar_power_kw || 0.0);
        const loadKw = parseFloat(rec.total_power || preds.load || data.household_load_kw || em.household_load_kw || 0.0);
        const battKw = parseFloat(rec.battery_power || data.battery_power_kw || em.battery_power_kw || 0.0);
        const battMode = rec.battery_mode || data.battery_mode || em.battery_mode || 'idle';
        const battSoc = parseFloat(rec.battery_soc_after || live.battery_soc || data.battery_soc || 75.0);
        const availEnergy = parseFloat(rec.available_battery_energy_kwh || data.available_battery_energy_kwh || em.available_battery_energy_kwh || 0.0);
        const gridKw = parseFloat(rec.grid_power || data.grid_power_kw || em.grid_power_kw || 0.0);
        const exportKw = parseFloat(rec.grid_export || data.grid_export_kw || em.grid_export_kw || 0.0);
        const estBackup = parseFloat(rec.estimated_backup_hours || data.estimated_backup_hours || em.estimated_backup_hours || 0.0);
        const reqBackup = parseFloat(rec.required_backup_hours || data.required_backup_hours || em.required_backup_hours || 10.0);
        const isSatisfied = (data.backup_target_satisfied !== undefined) ? data.backup_target_satisfied : (estBackup >= reqBackup);
        const statusLabel = data.backup_status_label || (isSatisfied ? '10-Hour Backup Available' : '10-Hour Backup Incomplete');

        // 1. Update KPI Values across DOM
        this._setText('live-solar-gen', `${solarKw.toFixed(2)} kW`);
        this._setText('live-house-demand', `${loadKw.toFixed(2)} kW`);
        this._setText('live-battery-soc', `${battSoc.toFixed(1)}%`);

        const fluidEl = document.getElementById('live-battery-fluid-fill');
        const boltEl = document.getElementById('battery-charging-bolt');
        if (fluidEl) {
            fluidEl.style.width = `${Math.min(100, Math.max(5, battSoc))}%`;
            fluidEl.classList.toggle('charging', battMode === 'charging');
            fluidEl.classList.toggle('low-soc', battSoc <= 25);
        }
        if (boltEl) {
            boltEl.classList.toggle('active', battMode === 'charging');
        }

        this._setText('live-battery-power', `${battKw.toFixed(2)} kW`);
        this._setText('live-battery-mode', battMode.toUpperCase());
        this._setText('live-battery-energy', `${availEnergy.toFixed(2)} kWh`);
        this._setText('live-battery-est-backup', `${estBackup.toFixed(1)} hrs`);
        this._setText('live-battery-req-backup', `${reqBackup.toFixed(0)} hrs`);
        this._setText('live-battery-capacity', `${(data.battery_capacity_kwh || 20.0).toFixed(1)} kWh`);
        const tenHourEl = document.getElementById('live-battery-10h-backup');
        if (tenHourEl) {
            tenHourEl.textContent = isSatisfied ? 'Available' : 'Not Available';
            tenHourEl.className = `detail-val ${isSatisfied ? 'backup-met' : 'backup-not-met'}`;
        }
        this._setText('live-grid-usage', `${gridKw.toFixed(2)} kW`);

        // Also update standard flow card nodes
        this._setText('flow-val-solar', `${solarKw.toFixed(1)} kW`);
        this._setText('flow-val-demand', `${loadKw.toFixed(1)} kW`);
        this._setText('flow-val-grid', gridKw > 0.05 ? `${gridKw.toFixed(1)} kW` : (exportKw > 0.05 ? `-${exportKw.toFixed(1)} kW` : '0.0 kW'));

        const battNodeVal = document.getElementById('flow-val-battery');
        if (battNodeVal) {
            battNodeVal.textContent = battMode === 'discharging' && battKw > 0.05 
                ? `-${battKw.toFixed(1)} kW` 
                : (battMode === 'charging' && battKw > 0.05 ? `+${battKw.toFixed(1)} kW` : `${battKw.toFixed(1)} kW`);
        }

        const hubBatFill = document.getElementById('hub-battery-fill');
        if (hubBatFill) {
            const calculatedSoc = Math.min(100, Math.max(8, Number(data.battery_soc || 82)));
            hubBatFill.style.width = `${calculatedSoc}%`;
        }

        // Breakdown of Solar Generation:
        const solarToLoad = Math.min(solarKw, loadKw);
        const remainingForLoad = Math.max(0.0, loadKw - solarToLoad);
        const battToLoad = battMode === 'discharging' ? Math.min(battKw, remainingForLoad) : 0.0;
        const gridToLoad = Math.max(0.0, loadKw - solarToLoad - battToLoad);
        const solarToBatKw = battMode === 'charging' ? battKw : 0.0;
        const inverterThroughput = solarToLoad + battToLoad + gridToLoad + solarToBatKw + exportKw;

        // Percentage shares of household load:
        const homeSolarPct = ((solarToLoad / Math.max(0.01, loadKw)) * 100).toFixed(1);
        const homeBattPct = ((battToLoad / Math.max(0.01, loadKw)) * 100).toFixed(1);
        const homeGridPct = Math.max(0, 100.0 - parseFloat(homeSolarPct) - parseFloat(homeBattPct)).toFixed(1);

        // Update Central Inverter Node
        this._setText('flow-val-inverter', `${inverterThroughput.toFixed(2)} kW`);
        const nodeInverter = document.getElementById('flow-node-inverter');
        if (nodeInverter) {
            nodeInverter.classList.toggle('active', inverterThroughput > 0.05);
            nodeInverter.classList.toggle('inactive', inverterThroughput <= 0.05);
        }
        const invBadge = document.getElementById('inverter-feed-badge');
        if (invBadge) {
            invBadge.textContent = inverterThroughput > 0.05 ? `⚡ Inverting ${loadKw.toFixed(2)} kW AC` : 'Standby Mode';
        }

        // Display exact distribution under Solar PV
        this._setText('flow-pct-solar', solarKw > 0.01 ? `${((solarToLoad / solarKw) * 100).toFixed(0)}% to Inverter` : 'Standby (0 kW)');
        this._setText('flow-pct-battery', battMode === 'charging' ? `⚡ Charging (${((data.battery_soc || 82))}%)` : (battKw > 0.01 ? `${battKw.toFixed(1)} kW Discharging` : 'Standby / 0 kW'));
        this._setText('flow-pct-grid', gridKw > 0.01 ? `${gridKw.toFixed(1)} kW to Inverter` : (exportKw > 0.01 ? `Net Export: ${exportKw.toFixed(1)} kW` : 'Zero Grid Draw ✓'));

        // Update WHAT IS GOING TO HOME LOAD Breakdown Box:
        this._setText('feed-val-solar', `${solarToLoad.toFixed(2)} kW`);
        this._setText('feed-pct-solar', `${homeSolarPct}% of Home Demand`);
        const barSolar = document.getElementById('feed-bar-solar');
        if (barSolar) barSolar.style.width = `${homeSolarPct}%`;

        this._setText('feed-val-battery', `${battToLoad.toFixed(2)} kW`);
        this._setText('feed-pct-battery', `${homeBattPct}% of Home Demand`);
        const barBattery = document.getElementById('feed-bar-battery');
        if (barBattery) barBattery.style.width = `${homeBattPct}%`;

        this._setText('feed-val-grid', `${gridToLoad.toFixed(2)} kW`);
        this._setText('feed-pct-grid', `${homeGridPct}% of Home Demand`);
        const barGrid = document.getElementById('feed-bar-grid');
        if (barGrid) barGrid.style.width = `${homeGridPct}%`;

        this._setText('badge-total-feed', `Total Load: ${loadKw.toFixed(2)} kW (100% Met)`);

        const auxText = document.getElementById('aux-flow-text');
        if (auxText) {
            if (solarToBatKw > 0.05) {
                auxText.textContent = `⚡ Surplus Solar (+${solarToBatKw.toFixed(2)} kW) is actively charging the Sungrow 1,000 kWh Battery.`;
            } else if (exportKw > 0.05) {
                auxText.textContent = `☀️ Net-metering surplus (+${exportKw.toFixed(2)} kW) exported to TNEB utility grid for bill credits.`;
            } else if (gridToLoad <= 0.01) {
                auxText.textContent = `🌱 100% Clean Green Energy: Zero electricity imported from utility grid.`;
            } else {
                auxText.textContent = `⚡ Residual demand (${gridToLoad.toFixed(2)} kW) drawn from utility grid under LT-IA tariff.`;
            }
        }

        // 2. Dynamic Flow Pipe Animations (Solar, Battery, Grid to Inverter to House)
        this._updatePipes(solarKw, loadKw, battKw, battMode, gridKw, exportKw);

        // 3. 10-Hour Backup Status Indicator Card
        this._updateBackupCard(estBackup, reqBackup, isSatisfied, statusLabel, availEnergy, data.required_battery_capacity_kwh);
    }

    _updatePipes(solarKw, loadKw, battKw, battMode, gridKw, exportKw) {
        const pipeSolar = document.getElementById('pipe-solar');
        const pipeBattery = document.getElementById('pipe-battery');
        const pipeGrid = document.getElementById('pipe-grid');

        const nodeSolar = document.getElementById('flow-node-solar');
        const nodeBattery = document.getElementById('flow-node-battery');
        const nodeGrid = document.getElementById('flow-node-grid');

        // 1. Solar supplies house
        if (solarKw > 0.05) {
            if (pipeSolar) pipeSolar.setAttribute('class', 'pipe active-pipe-solar');
            if (nodeSolar) {
                nodeSolar.classList.add('active');
                nodeSolar.classList.remove('inactive');
            }
        } else {
            if (pipeSolar) pipeSolar.setAttribute('class', 'pipe inactive-pipe');
            if (nodeSolar) {
                nodeSolar.classList.remove('active');
                nodeSolar.classList.add('inactive');
            }
        }

        // 2. Battery Flow (Charging from excess solar vs Discharging to house)
        if (battMode === 'charging' && battKw > 0.05) {
            // Reverse animated current into battery
            if (pipeBattery) pipeBattery.setAttribute('class', 'pipe active-pipe-battery-charging');
            if (nodeBattery) {
                nodeBattery.classList.add('active', 'active-charging');
                nodeBattery.classList.remove('inactive', 'active-discharging');
            }
        } else if (battMode === 'discharging' && battKw > 0.05) {
            // Forward animated current into house
            if (pipeBattery) pipeBattery.setAttribute('class', 'pipe active-pipe-battery-discharging');
            if (nodeBattery) {
                nodeBattery.classList.add('active', 'active-discharging');
                nodeBattery.classList.remove('inactive', 'active-charging');
            }
        } else {
            // Standby / Idle
            if (pipeBattery) pipeBattery.setAttribute('class', 'pipe inactive-pipe');
            if (nodeBattery) {
                nodeBattery.classList.remove('active', 'active-charging', 'active-discharging');
                nodeBattery.classList.add('inactive');
            }
        }

        // 3. Grid Flow (Importing into house vs Exporting surplus solar)
        if (gridKw > 0.05) {
            // Importing into house
            if (pipeGrid) pipeGrid.setAttribute('class', 'pipe active-pipe-grid-import');
            if (nodeGrid) {
                nodeGrid.classList.add('active', 'active-import');
                nodeGrid.classList.remove('inactive', 'active-export');
            }
        } else if (exportKw > 0.05) {
            // Exporting to grid
            if (pipeGrid) pipeGrid.setAttribute('class', 'pipe active-pipe-grid-export');
            if (nodeGrid) {
                nodeGrid.classList.add('active', 'active-export');
                nodeGrid.classList.remove('inactive', 'active-import');
            }
        } else {
            // Grid Standby
            if (pipeGrid) pipeGrid.setAttribute('class', 'pipe inactive-pipe');
            if (nodeGrid) {
                nodeGrid.classList.remove('active', 'active-import', 'active-export');
                nodeGrid.classList.add('inactive');
            }
        }

        // 4. Inverter -> Household Load Pipe
        const pipeInverterLoad = document.getElementById('pipe-inverter-load');
        if (pipeInverterLoad) {
            if (loadKw > 0.05) {
                pipeInverterLoad.setAttribute('class', 'pipe active-pipe-inverter-load');
            } else {
                pipeInverterLoad.setAttribute('class', 'pipe inactive-pipe');
            }
        }

        // 5. Dynamic Glowing Energy Particle Orbs
        const pSolar = document.getElementById('particle-solar');
        if (pSolar) pSolar.style.opacity = solarKw > 0.05 ? '1' : '0';

        const pBat = document.getElementById('particle-battery');
        if (pBat) pBat.style.opacity = battKw > 0.05 ? '1' : '0';

        const pGrid = document.getElementById('particle-grid');
        if (pGrid) pGrid.style.opacity = (gridKw > 0.05 || exportKw > 0.05) ? '1' : '0';

        const pLoad = document.getElementById('particle-inverter-load');
        if (pLoad) pLoad.style.opacity = loadKw > 0.05 ? '1' : '0';

        // 6. Inverter Center Rotating Core
        const invIcon = document.getElementById('inverter-center-icon');
        if (invIcon) {
            const isFlowing = (solarKw + battKw + gridKw) > 0.05;
            invIcon.textContent = isFlowing ? '🔄' : '⚡';
            invIcon.style.animation = isFlowing ? 'spinSlow 4s linear infinite' : 'none';
        }

        // Status badge
        const destStatus = document.getElementById('flow-dest-status');
        if (destStatus) {
            if (solarKw >= loadKw) {
                destStatus.textContent = exportKw > 0 
                    ? `☀️ 100% Green Solar Surplus (${exportKw.toFixed(1)} kW export)`
                    : `☀️ 100% Green Solar Powered`;
                destStatus.className = 'dest-status status-clean';
            } else if (gridKw <= 0.01) {
                destStatus.textContent = `🌱 100% Solar + Battery Clean Energy`;
                destStatus.className = 'dest-status status-clean';
            } else {
                destStatus.textContent = `⚡ Grid Supported (${gridKw.toFixed(2)} kW imported)`;
                destStatus.className = 'dest-status status-grid';
            }
        }
    }

    _updateBackupCard(estBackup, reqBackup, isSatisfied, statusLabel, availEnergy, reqCapacity) {
        const badgeElem = document.getElementById('backup-status-badge');
        const estElem = document.getElementById('backup-hours-display');
        const reqElem = document.getElementById('backup-hours-target');
        const barElem = document.getElementById('backup-progress-bar');
        const subtextElem = document.getElementById('backup-subtext');

        if (estElem) estElem.textContent = `${estBackup.toFixed(1)} hrs`;
        if (reqElem) reqElem.textContent = `/ ${reqBackup.toFixed(0)} hrs Target`;

        const ratio = Math.min(100, Math.max(5, (estBackup / reqBackup) * 100));
        if (barElem) {
            barElem.style.width = `${ratio}%`;
            barElem.className = isSatisfied ? 'progress-fill fill-success' : (ratio >= 50 ? 'progress-fill fill-warning' : 'progress-fill fill-danger');
        }

        if (badgeElem) {
            if (isSatisfied) {
                badgeElem.textContent = '✓ 10h Target Met';
                badgeElem.className = 'backup-badge badge-success';
            } else {
                badgeElem.textContent = `⚠ ${estBackup.toFixed(1)}h Available (< 10h)`;
                badgeElem.className = 'backup-badge badge-warning';
            }
        }

        if (subtextElem) {
            subtextElem.textContent = `Usable Energy: ${availEnergy.toFixed(1)} kWh | Required Battery: ${(reqCapacity || 25.0).toFixed(1)} kWh for 10h full backup`;
        }
    }

    _setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }
}

// Global Animation Play/Pause Toggle
window.toggleFlowAnimation = function() {
    const container = document.getElementById('hub-diagram-container');
    const icon = document.getElementById('flow-playback-icon');
    const svg = document.getElementById('hub-flow-svg-elem');
    if (!container) return;
    
    const isPaused = container.classList.toggle('flow-paused');
    if (icon) icon.textContent = isPaused ? '▶' : '❚❚';
    
    if (svg) {
        try {
            if (isPaused && svg.pauseAnimations) {
                svg.pauseAnimations();
            } else if (!isPaused && svg.unpauseAnimations) {
                svg.unpauseAnimations();
            }
        } catch (e) {
            console.warn('SVG animation control:', e);
        }
    }
};

// Global Singleton
window.energyFlowVisualizer = new EnergyFlowVisualizer();

// Initialize when DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.energyFlowVisualizer.init());
} else {
    window.energyFlowVisualizer.init();
}
