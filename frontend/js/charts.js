/**
 * VERA Chart Manager
 * Integrates Chart.js visualizations for Energy Contribution, Diurnal Curves, DQN Policy, and History.
 */

class VeraChartsManager {
    constructor() {
        this.charts = {};
    }

    getThemeColors() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        return {
            textColor: isDark ? '#E2E8F0' : '#0F172A',
            gridColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
            solar: '#F59E0B',
            battery: '#10B981',
            grid: '#38BDF8',
            load: '#818CF8',
            cost: '#F472B6'
        };
    }

    updateTheme() {
        const colors = this.getThemeColors();
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.options) {
                if (chart.options.scales) {
                    if (chart.options.scales.x) {
                        chart.options.scales.x.ticks.color = colors.textColor;
                        chart.options.scales.x.grid.color = colors.gridColor;
                    }
                    if (chart.options.scales.y) {
                        chart.options.scales.y.ticks.color = colors.textColor;
                        chart.options.scales.y.grid.color = colors.gridColor;
                    }
                }
                chart.update();
            }
        });
    }

    /**
     * Render / Update Source Contribution Doughnut Chart
     */
    updateSourceContributionChart(solarKw, batteryKw, gridKw) {
        const ctx = document.getElementById('chart-source-contribution')?.getContext('2d');
        if (!ctx) return;

        const total = Math.max(0.001, solarKw + batteryKw + gridKw);
        const dataVals = [
            Number(((solarKw / total) * 100).toFixed(1)),
            Number(((batteryKw / total) * 100).toFixed(1)),
            Number(((gridKw / total) * 100).toFixed(1))
        ];

        if (this.charts.sourceContribution) {
            this.charts.sourceContribution.data.datasets[0].data = dataVals;
            this.charts.sourceContribution.update();
            return;
        }

        const colors = this.getThemeColors();
        this.charts.sourceContribution = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Solar ☀️', 'Battery 🔋', 'Grid ⚡'],
                datasets: [{
                    data: dataVals,
                    backgroundColor: [colors.solar, colors.battery, colors.grid],
                    borderWidth: 2,
                    borderColor: 'transparent'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.raw}%`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Render / Update Diurnal Solar & Load Prediction Chart
     */
    updatePredictionsChart(solarCurrent, loadCurrent) {
        const ctx = document.getElementById('chart-predictions-diurnal')?.getContext('2d');
        if (!ctx) return;

        const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
        const solarCurve = hours.map((_, h) => {
            if (h >= 6 && h <= 18) {
                return Number((3.5 * Math.sin((h - 6) * Math.PI / 12)).toFixed(2));
            }
            return 0.0;
        });

        const loadCurve = hours.map((_, h) => {
            if (h >= 6 && h <= 9) return 2.4;
            if (h >= 10 && h <= 16) return 1.6;
            if (h >= 17 && h <= 22) return 2.8;
            return 0.8;
        });

        const colors = this.getThemeColors();

        if (this.charts.predictions) {
            this.charts.predictions.data.datasets[0].data = solarCurve;
            this.charts.predictions.data.datasets[1].data = loadCurve;
            this.charts.predictions.update();
            return;
        }

        this.charts.predictions = new Chart(ctx, {
            type: 'line',
            data: {
                labels: hours,
                datasets: [
                    {
                        label: 'Solar Potential (kW)',
                        data: solarCurve,
                        borderColor: colors.solar,
                        backgroundColor: 'rgba(217, 119, 6, 0.12)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointRadius: 2
                    },
                    {
                        label: 'Household Demand Forecast (kW)',
                        data: loadCurve,
                        borderColor: colors.load,
                        borderDash: [5, 5],
                        tension: 0.3,
                        borderWidth: 2.5,
                        pointRadius: 3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: {
                        ticks: { color: colors.textColor },
                        grid: { color: colors.gridColor }
                    },
                    y: {
                        ticks: { color: colors.textColor },
                        grid: { color: colors.gridColor },
                        title: { display: true, text: 'Power (kW)', color: colors.textColor }
                    }
                }
            }
        });
    }

    /**
     * Render / Update DQN Q-Values Bar Chart
     */
    updateDqnChart(qValues = [0, 0, 0, 0], selectedActionId = 0) {
        const ctx = document.getElementById('chart-dqn-bar')?.getContext('2d');
        if (!ctx) return;

        const labels = [
            '⚡ Action 0: PRIORITY_HYBRID',
            '🔋 Action 1: BATTERY_CONSERVATION',
            '📈 Action 2: PEAK_SHAVING',
            '🌐 Action 3: GRID_MINIMIZE'
        ];

        const colors = this.getThemeColors();
        const barColors = [0, 1, 2, 3].map(i => i === selectedActionId ? colors.grid : 'rgba(100, 116, 139, 0.4)');

        if (this.charts.dqn) {
            this.charts.dqn.data.datasets[0].data = qValues;
            this.charts.dqn.data.datasets[0].backgroundColor = barColors;
            this.charts.dqn.update();
            return;
        }

        this.charts.dqn = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Expected Return Q(s, a)',
                    data: qValues,
                    backgroundColor: barColors,
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        ticks: { color: colors.textColor },
                        grid: { color: colors.gridColor },
                        title: { display: true, text: 'Expected Cumulative Return Q(s, a)', color: colors.textColor }
                    },
                    y: {
                        ticks: { color: colors.textColor },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    /**
     * Render Historical Time Series
     */
    updateHistoryChart(records = []) {
        if (!records || !records.length) return;

        const labels = records.map(r => r.timestamp);
        const solarData = records.map(r => r.solar_generation_kw);
        const loadData = records.map(r => r.load_demand_kw);
        const gridData = records.map(r => r.grid_power_kw);
        const batteryData = records.map(r => r.battery_power_kw);
        const colors = this.getThemeColors();

        const targets = [
            { id: 'chart-history-series', key: 'history' },
            { id: 'chart-history-series-tab', key: 'historyTab' }
        ];

        targets.forEach(t => {
            const canvas = document.getElementById(t.id);
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            if (!ctx) return;

            if (this.charts[t.key]) {
                this.charts[t.key].data.labels = labels;
                this.charts[t.key].data.datasets[0].data = solarData;
                this.charts[t.key].data.datasets[1].data = loadData;
                this.charts[t.key].data.datasets[2].data = batteryData;
                this.charts[t.key].data.datasets[3].data = gridData;
                this.charts[t.key].update();
            } else {
                this.charts[t.key] = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: 'Solar Gen (kW)',
                                data: solarData,
                                borderColor: colors.solar,
                                backgroundColor: 'rgba(217, 119, 6, 0.1)',
                                fill: true,
                                tension: 0.3
                            },
                            {
                                label: 'Household Demand (kW)',
                                data: loadData,
                                borderColor: colors.load,
                                tension: 0.3
                            },
                            {
                                label: 'Battery Dispatch (kW)',
                                data: batteryData,
                                borderColor: colors.battery,
                                tension: 0.3
                            },
                            {
                                label: 'Grid Backup (kW)',
                                data: gridData,
                                borderColor: colors.grid,
                                tension: 0.3
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                ticks: { color: colors.textColor, maxTicksLimit: 12 },
                                grid: { color: colors.gridColor }
                            },
                            y: {
                                ticks: { color: colors.textColor },
                                grid: { color: colors.gridColor },
                                title: { display: true, text: 'Power (kW)', color: colors.textColor }
                            }
                        }
                    }
                });
            }
        });
    }

    /**
     * Render / Update Live Dataset Stream Trend Line Chart
     */
    updateDatasetStreamChart(records = []) {
        const ctx = document.getElementById('chart-dataset-stream')?.getContext('2d');
        if (!ctx) return;

        // Filter valid records and sort strictly in chronological ASCENDING order (oldest to newest)
        const validRecords = (records || []).filter(r => r && r.timestamp);
        validRecords.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

        // Deduplicate records that have identical minute timestamps to avoid duplicate x-axis labels
        const sorted = [];
        const seenKeys = new Set();
        for (const r of validRecords) {
            const dt = new Date(r.timestamp);
            if (isNaN(dt.getTime())) continue;
            const minKey = `${dt.getFullYear()}-${dt.getMonth()}-${dt.getDate()}-${dt.getHours()}-${dt.getMinutes()}`;
            if (!seenKeys.has(minKey)) {
                seenKeys.add(minKey);
                sorted.push(r);
            }
        }

        if (sorted.length === 0) return;

        // Check if dataset spans multiple calendar days
        const distinctDays = new Set(sorted.map(r => new Date(r.timestamp).toDateString()));
        const isMultiDay = distinctDays.size > 1;

        const labels = sorted.map(r => {
            const dt = new Date(r.timestamp);
            if (isNaN(dt.getTime())) return r.timestamp || '';
            if (isMultiDay) {
                return `${dt.toLocaleDateString([], { month: 'short', day: 'numeric' })}, ${dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
            }
            return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        });

        const solarData = sorted.map(r => Number(r.solar_kw ?? r.solar_power_kw ?? 0));
        const loadData = sorted.map(r => Number(r.energy_usage_kw ?? 0));
        const batData = sorted.map(r => Number(r.battery_power_kw ?? 0));
        const gridData = sorted.map(r => Number(r.grid_power_kw ?? 0));
        const socData = sorted.map(r => Number(r.battery_soc ?? 0));

        if (this.charts.datasetStream) {
            this.charts.datasetStream.data.labels = labels;
            this.charts.datasetStream.data.datasets[0].data = solarData;
            this.charts.datasetStream.data.datasets[1].data = loadData;
            this.charts.datasetStream.data.datasets[2].data = batData;
            this.charts.datasetStream.data.datasets[3].data = gridData;
            this.charts.datasetStream.data.datasets[4].data = socData;
            this.charts.datasetStream.update();
            return;
        }

        const colors = this.getThemeColors();
        this.charts.datasetStream = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Solar Gen (kW)',
                        data: solarData,
                        borderColor: colors.solar,
                        backgroundColor: 'rgba(217, 119, 6, 0.12)',
                        fill: true,
                        tension: 0.25,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Household Demand (kW)',
                        data: loadData,
                        borderColor: colors.load,
                        tension: 0.25,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Battery Dispatch (kW)',
                        data: batData,
                        borderColor: colors.battery,
                        tension: 0.25,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Grid Backup (kW)',
                        data: gridData,
                        borderColor: colors.grid,
                        tension: 0.25,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Battery SOC (%)',
                        data: socData,
                        borderColor: '#10B981',
                        borderDash: [5, 5],
                        pointRadius: 2,
                        tension: 0.2,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const val = context.parsed.y;
                                if (label.includes('SOC')) {
                                    return `${label}: ${Number(val).toFixed(1)}%`;
                                }
                                return `${label}: ${Number(val).toFixed(2)} kW`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: colors.textColor,
                            maxRotation: 45,
                            minRotation: 0,
                            autoSkip: true,
                            maxTicksLimit: 14
                        },
                        grid: { color: colors.gridColor }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        ticks: { color: colors.textColor },
                        grid: { color: colors.gridColor },
                        title: { display: true, text: 'Power (kW)', color: colors.textColor }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 0,
                        max: 100,
                        ticks: { color: '#10B981' },
                        grid: { drawOnChartArea: false },
                        title: { display: true, text: 'SOC (%)', color: '#10B981' }
                    }
                }
            }
        });
    }

    renderPendingCharts(tabId) {
        Object.values(this.charts).forEach(c => {
            if (c && typeof c.resize === 'function') {
                try { c.resize(); } catch(e) {}
            }
        });
    }
}

window.veraCharts = new VeraChartsManager();
