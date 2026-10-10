/**
 * VERA Main Application Entrypoint
 * Orchestrates event listeners, API polling, input debounce, and data flows.
 */

class VeraApp {
    constructor() {
        this.debounceTimer = null;
        this.ws = null;
    }

    async init() {
        // 1. Initialize UI subsystem
        if (window.veraUI) window.veraUI.init();

        // 2. Bind interactive controls
        this.bindUserControls();
        this.bindHistoryControls();
        this.bindDatasetControls();
        this.bindRefreshButton();

        // 3. Immediately Initialize Real-Time WebSocket Telemetry
        this.initWebSocket();

        // 4. Initialize Upgrade Managers safely
        try { if (window.veraSimulator) window.veraSimulator.init(); } catch (e) { console.warn('Simulator init warning:', e); }
        try { if (window.veraRetraining) window.veraRetraining.load(); } catch (e) { console.warn('Retraining init warning:', e); }
        try { if (window.veraAlerts) window.veraAlerts.load(); } catch (e) { console.warn('Alerts init warning:', e); }
        try { if (window.semsFeatures) window.semsFeatures.init(); } catch (e) { console.warn('SEMS Features init warning:', e); }

        // 5. Initial Data Fetches in parallel (non-blocking)
        Promise.allSettled([
            this.refreshData(),
            this.loadHistory('today'),
            window.veraDataset ? window.veraDataset.loadDataset() : Promise.resolve()
        ]);

        // 6. Setup Periodic Auto-Refresh (Every 30 seconds fallback)
        setInterval(async () => {
            await this.refreshData(true);
            if (window.veraDataset) {
                await window.veraDataset.loadDataset();
            }
            if (window.veraAlerts) {
                await window.veraAlerts.load();
            }
        }, 30000);
    }

    initWebSocket() {
        try {
            this.ws = window.veraApi.createTelemetryWebSocket();

            this.ws.onopen = () => {
                const wsBadge = document.getElementById('ws-status-badge');
                if (wsBadge) {
                    wsBadge.classList.add('ws-connected');
                    wsBadge.querySelector('span:last-child').textContent = 'WS Stream Active';
                }
            };

            this.ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if ((msg.type === 'telemetry_stream' || msg.type === 'initial_state') && msg.data) {
                        window.veraDashboard.render(msg.data);
                        if (window.semsFeatures) {
                            window.semsFeatures.updateTelemetry(msg.data);
                        }
                    }
                } catch (e) {
                    // Ignore parsing error
                }
            };

            this.ws.onclose = () => {
                const wsBadge = document.getElementById('ws-status-badge');
                if (wsBadge) {
                    wsBadge.classList.remove('ws-connected');
                    wsBadge.querySelector('span:last-child').textContent = 'WS Reconnecting';
                }
                setTimeout(() => this.initWebSocket(), 5000);
            };
        } catch (err) {
            console.warn('WebSocket init skipped:', err);
        }
    }

    async refreshData(isBackground = false) {
        let data = null;
        try {
            if (!isBackground) {
                window.veraUI.setSystemStatus(true, 'Fetching Smart Home Telemetry...');
            }

            data = await window.veraApi.getDashboardData();
            window.veraUI.setSystemStatus(true, 'FastAPI Online • SEMS Active');
        } catch (netErr) {
            console.error('Failed to fetch telemetry from backend:', netErr);
            window.veraUI.setSystemStatus(false, 'Backend Offline');
            window.veraUI.showToast('Unable to retrieve latest recommendations. Check backend server.', 'error');
            return;
        }

        try {
            if (data && window.veraDashboard) {
                window.veraDashboard.render(data);
            }
            if (data && window.semsFeatures) {
                window.semsFeatures.updateTelemetry(data);
            }

            if (!isBackground) {
                window.veraUI.showToast('Energy recommendation updated successfully', 'success');
            }
        } catch (renderErr) {
            console.error('Error rendering dashboard components:', renderErr);
        }
    }

    async loadHistory(period = 'today') {
        try {
            const res = await window.veraApi.getHistory(period);
            if (res && res.records) {
                window.veraCharts.updateHistoryChart(res.records);
            }
        } catch (error) {
            console.error('Failed to load history data:', error);
        }
    }

    bindRefreshButton() {
        const btn = document.getElementById('btn-refresh-data');
        if (btn) {
            btn.addEventListener('click', async () => {
                btn.disabled = true;
                btn.classList.add('loading');
                await this.refreshData();
                if (window.veraDataset) {
                    await window.veraDataset.loadDataset();
                }
                btn.disabled = false;
                btn.classList.remove('loading');
            });
        }
    }

    bindUserControls() {
        const budgetSlider = document.getElementById('input-user-budget');
        const budgetNum = document.getElementById('num-user-budget');
        const btnDailySummary = document.getElementById('btn-daily-summary-notify');
        const btnHourlyNotify = document.getElementById('btn-hourly-notify-now');

        // Synchronize Budget Inputs
        if (budgetSlider && budgetNum) {
            budgetSlider.addEventListener('input', (e) => {
                budgetNum.value = e.target.value;
                const label = document.getElementById('label-user-budget');
                if (label) label.textContent = `₹ ${Number(e.target.value).toFixed(2)} / hr`;
                this.debouncedTriggerRecommendation();
            });

            budgetNum.addEventListener('change', (e) => {
                budgetSlider.value = e.target.value;
                const label = document.getElementById('label-user-budget');
                if (label) label.textContent = `₹ ${Number(e.target.value).toFixed(2)} / hr`;
                this.debouncedTriggerRecommendation();
            });
        }

        // Daily Summary Notification Trigger
        if (btnDailySummary) {
            btnDailySummary.addEventListener('click', async () => {
                btnDailySummary.disabled = true;
                let dispatched = false;
                try {
                    const budgetVal = Number(document.getElementById('input-user-budget')?.value || 25.0);
                    const res = await window.veraApi.sendDailySummaryNotification(budgetVal);
                    if (res && res.status === 'success') {
                        dispatched = true;
                        window.veraUI.showToast('📊 Daily Summary Reminder sent to notification center!', 'success');
                    }
                } catch (err) {
                    console.error('Failed to trigger daily summary:', err);
                    window.veraUI.showToast('Could not dispatch daily summary alert', 'error');
                } finally {
                    btnDailySummary.disabled = false;
                }

                if (dispatched && window.veraAlerts) {
                    try {
                        await window.veraAlerts.load();
                    } catch (e) {
                        console.warn('Alerts list refresh skipped:', e);
                    }
                }
            });
        }

        // Hourly Power Usage Notification Trigger
        if (btnHourlyNotify) {
            btnHourlyNotify.addEventListener('click', async () => {
                btnHourlyNotify.disabled = true;
                let dispatched = false;
                try {
                    const res = await window.veraApi.sendHourlyNotification();
                    if (res && res.status === 'success') {
                        dispatched = true;
                        window.veraUI.showToast('⚡ Hourly usage breakdown notification dispatched!', 'info');
                    }
                } catch (err) {
                    console.error('Failed to trigger hourly notice:', err);
                    window.veraUI.showToast('Could not dispatch hourly notification', 'error');
                } finally {
                    btnHourlyNotify.disabled = false;
                }

                if (dispatched && window.veraAlerts) {
                    try {
                        await window.veraAlerts.load();
                    } catch (e) {
                        console.warn('Alerts list refresh skipped:', e);
                    }
                }
            });
        }
    }


    debouncedTriggerRecommendation() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(async () => {
            const budgetVal = Number(document.getElementById('input-user-budget')?.value || 25);
            const demandElem = document.getElementById('input-user-demand');
            const socElem = document.getElementById('input-battery-soc');
            const outageElem = document.getElementById('toggle-grid-outage');

            try {
                const payload = {
                    user_budget: budgetVal
                };
                if (demandElem) payload.user_demand = Number(demandElem.value);
                if (socElem) payload.battery_soc = Number(socElem.value);
                if (outageElem) payload.grid_outage = outageElem.checked;

                const updatedData = await window.veraApi.postRecommendation(payload);
                window.veraDashboard.render(updatedData);
            } catch (error) {
                console.error('Error sending recommendation update:', error);
            }
        }, 300);
    }


    bindHistoryControls() {
        const btns = document.querySelectorAll('.period-btn');
        btns.forEach(btn => {
            btn.addEventListener('click', async () => {
                btns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const period = btn.getAttribute('data-period');
                await this.loadHistory(period);
            });
        });
    }

    bindDatasetControls() {
        const ds = window.veraDataset;
        if (!ds) return;

        // 1. Snapshot capture buttons
        const btnManual = document.getElementById('btn-collect-manual');
        const btnQuick = document.getElementById('btn-quick-collect');
        const btn15m = document.getElementById('btn-collect-15m');
        const btn1h = document.getElementById('btn-collect-1h');

        if (btnManual) btnManual.addEventListener('click', () => ds.triggerCollect('manual'));
        if (btnQuick) btnQuick.addEventListener('click', () => ds.triggerCollect('manual'));
        if (btn15m) btn15m.addEventListener('click', () => ds.triggerCollect('15min'));
        if (btn1h) btn1h.addEventListener('click', () => ds.triggerCollect('1hour'));

        // 2. Export, Refresh, Seed, Clear
        const btnExport = document.getElementById('btn-export-csv');
        const btnRefreshDs = document.getElementById('btn-refresh-dataset');
        const btnSeed = document.getElementById('btn-seed-dataset');
        const btnClear = document.getElementById('btn-clear-dataset');

        if (btnExport) btnExport.addEventListener('click', () => ds.exportCsv());
        if (btnRefreshDs) btnRefreshDs.addEventListener('click', () => ds.loadDataset(true));
        if (btnSeed) btnSeed.addEventListener('click', () => ds.seedBaseline());
        if (btnClear) btnClear.addEventListener('click', () => ds.clearData());

        // 3. Interval Filter & Page Size
        const filterSelect = document.getElementById('dataset-interval-filter');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                ds.currentInterval = e.target.value;
                ds.currentPage = 1;
                ds.loadDataset();
            });
        }

        const pageSizeSelect = document.getElementById('dataset-page-size');
        if (pageSizeSelect) {
            pageSizeSelect.addEventListener('change', (e) => {
                ds.pageSize = Number(e.target.value) || 25;
                ds.currentPage = 1;
                ds.loadDataset();
            });
        }

        // 4. Search Filter with Debounce
        const searchInput = document.getElementById('dataset-search-input');
        if (searchInput) {
            let searchTimer = null;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(() => {
                    ds.searchQuery = e.target.value;
                    ds.currentPage = 1;
                    ds.loadDataset();
                }, 350);
            });
        }

        // 5. Pagination Buttons
        const btnFirst = document.getElementById('btn-dataset-first');
        const btnPrev = document.getElementById('btn-dataset-prev');
        const btnNext = document.getElementById('btn-dataset-next');
        const btnLast = document.getElementById('btn-dataset-last');

        if (btnFirst) {
            btnFirst.addEventListener('click', () => {
                if (ds.currentPage > 1) {
                    ds.currentPage = 1;
                    ds.loadDataset();
                }
            });
        }

        if (btnPrev) {
            btnPrev.addEventListener('click', () => {
                if (ds.currentPage > 1) {
                    ds.currentPage -= 1;
                    ds.loadDataset();
                }
            });
        }

        if (btnNext) {
            btnNext.addEventListener('click', () => {
                const totalPages = Math.ceil(ds.totalRecords / ds.pageSize);
                if (ds.currentPage < totalPages) {
                    ds.currentPage += 1;
                    ds.loadDataset();
                }
            });
        }

        if (btnLast) {
            btnLast.addEventListener('click', () => {
                const totalPages = Math.ceil(ds.totalRecords / ds.pageSize);
                if (ds.currentPage < totalPages) {
                    ds.currentPage = totalPages;
                    ds.loadDataset();
                }
            });
        }

        // 6. Quick Dashboard button to jump to Live Dataset Tab
        const btnQuickView = document.getElementById('btn-quick-view-dataset');
        if (btnQuickView) {
            btnQuickView.addEventListener('click', () => {
                const navDataset = document.getElementById('nav-dataset');
                if (navDataset) {
                    navDataset.click();
                }
            });
        }
    }
}

// Bootstrap on DOM ready (handles both loading and already-loaded DOM)
function bootstrapVeraApp() {
    if (!window.veraApp) {
        window.veraApp = new VeraApp();
        window.veraApp.init();
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrapVeraApp);
} else {
    bootstrapVeraApp();
}
