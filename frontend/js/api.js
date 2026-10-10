/**
 * VERA API Client Service
 * Centralizes all asynchronous fetch() requests to the FastAPI backend.
 */

const API_BASE_URL = window.location.origin;

class VeraApiClient {
    constructor(baseUrl = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    async _request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };

        const config = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                let errorDetails = `HTTP Error ${response.status}: ${response.statusText}`;
                try {
                    const errJson = await response.json();
                    if (errJson.detail) {
                        errorDetails = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
                    }
                } catch (e) {
                    // Ignore JSON parsing failure for raw HTTP error
                }
                throw new Error(errorDetails);
            }
            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    /**
     * Get unified dashboard snapshot (Live + Predictions + DQN Recommendation + XAI)
     */
    async getDashboardData() {
        return await this._request('/api/dashboard');
    }

    /**
     * Get live telemetry (OpenWeather, Smart Meter, Battery)
     */
    async getLiveData() {
        return await this._request('/api/live-data');
    }

    /**
     * Get ML predictions from neural models
     */
    async getPredictions() {
        return await this._request('/api/predictions');
    }

    /**
     * Post updated user inputs to generate custom DQN recommendation + XAI explanation
     */
    async postRecommendation(payload = {}) {
        return await this._request('/api/recommendation', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    /**
     * Update user spending budget preference
     */
    async updateBudget(budgetVal) {
        return await this._request('/api/budget', {
            method: 'POST',
            body: JSON.stringify({ budget: Number(budgetVal) })
        });
    }

    /**
     * Get historical energy & dispatch records (period: today | 7days | 30days)
     */
    async getHistory(period = 'today') {
        return await this._request(`/api/history?period=${encodeURIComponent(period)}`);
    }

    /**
     * Fetch paginated live telemetry dataset records
     */
    async getLiveDataset(limit = 25, offset = 0, interval = 'all', search = '') {
        let url = `/api/dataset/live?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`;
        if (interval && interval !== 'all') {
            url += `&interval=${encodeURIComponent(interval)}`;
        }
        if (search && search.trim()) {
            url += `&search=${encodeURIComponent(search.trim())}`;
        }
        return await this._request(url);
    }

    /**
     * Fetch dataset summary metrics and scheduler status
     */
    async getDatasetStats() {
        return await this._request('/api/dataset/stats');
    }

    /**
     * Fetch chronologically ordered stream trend points for chart
     */
    async getDatasetStreamTrend(limit = 48) {
        return await this._request(`/api/dataset/stream-trend?limit=${encodeURIComponent(limit)}`);
    }

    /**
     * Manually trigger live telemetry collection snapshot
     */
    async collectDatasetSnapshot(intervalType = 'manual', source = 'DashboardManual') {
        return await this._request('/api/dataset/collect', {
            method: 'POST',
            body: JSON.stringify({
                interval_type: intervalType,
                source: source
            })
        });
    }

    /**
     * Get periodic collector scheduler status
     */
    async getDatasetSchedulerStatus() {
        return await this._request('/api/dataset/scheduler');
    }

    /**
     * Generate CSV export download URL
     */
    getDatasetExportUrl(interval = 'all') {
        const query = interval && interval !== 'all' ? `?interval=${encodeURIComponent(interval)}` : '';
        return `${this.baseUrl}/api/dataset/export${query}`;
    }

    /**
     * Clear all telemetry dataset records
     */
    async clearLiveDataset() {
        return await this._request('/api/dataset/clear', {
            method: 'DELETE'
        });
    }

    /**
     * Seed baseline telemetry data
     */
    async seedDatasetBaseline() {
        return await this._request('/api/dataset/seed', {
            method: 'POST'
        });
    }

    /**
     * AI Retraining Endpoints
     */
    async getModelStatus() {
        return await this._request('/api/models/status');
    }

    async triggerModelRetraining() {
        return await this._request('/api/models/retrain', {
            method: 'POST'
        });
    }

    /**
     * IoT & Smart Relays
     */
    async getIoTDevices() {
        return await this._request('/api/iot/devices');
    }

    async toggleIoTRelay(deviceId, state = null) {
        return await this._request('/api/iot/relay/toggle', {
            method: 'POST',
            body: JSON.stringify({ device_id: deviceId, state: state })
        });
    }



    /**
     * EV Smart Charging & V2H Bidirectional Dispatch
     */
    async getEVDispatch() {
        return await this._request('/api/ev/dispatch');
    }

    /**
     * 'What-If' Solar & Battery ROI Simulator
     */
    async evaluateSimulation(payload) {
        return await this._request('/api/simulator/evaluate', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    /**
     * Alerts & Notification Center
     */
    async getActiveAlerts() {
        return await this._request('/api/alerts/active');
    }

    async dismissAlert(alertId) {
        return await this._request(`/api/alerts/dismiss/${encodeURIComponent(alertId)}`, {
            method: 'POST'
        });
    }

    async markAlertRead(alertId) {
        return await this._request(`/api/alerts/mark-read/${encodeURIComponent(alertId)}`, {
            method: 'POST'
        });
    }

    async markAllAlertsRead() {
        return await this._request('/api/alerts/read-all', {
            method: 'POST'
        });
    }

    async clearAllAlerts() {
        return await this._request('/api/alerts/clear', {
            method: 'DELETE'
        });
    }

    /**
     * Enterprise v3.0: Islanding, Swarm P2P, OpenADR & PINN
     */
    async getIslandingStatus() {
        return await this._request('/api/islanding/status');
    }

    async triggerIslanding(reason = 'MANUAL_OPERATOR_DISCONNECT') {
        return await this._request('/api/islanding/trigger', {
            method: 'POST',
            body: JSON.stringify({ reason })
        });
    }

    async restoreGrid() {
        return await this._request('/api/islanding/restore', {
            method: 'POST'
        });
    }

    async getSwarmMarket() {
        return await this._request('/api/swarm/market');
    }

    async getDemandResponseStatus() {
        return await this._request('/api/demand-response/status');
    }

    async getFastFrequencyResponse(freq = 49.95) {
        return await this._request(`/api/demand-response/ffr?freq=${encodeURIComponent(freq)}`);
    }

    async setDemandResponseOpt(optState) {
        return await this._request('/api/demand-response/opt', {
            method: 'POST',
            body: JSON.stringify({ opt_state: optState })
        });
    }

    async getPINNBatteryPhysics() {
        return await this._request('/api/pinn/battery/evaluate');
    }

    /**
     * WebSocket Telemetry Stream Factory
     */
    createTelemetryWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
        return new WebSocket(wsUrl);
    }

    /**
     * Real-time Energy Flow & Dynamic Battery Management
     */
    async getEnergyFlow(solarKw = null, loadKw = null, batterySoc = null) {
        let query = '';
        const params = [];
        if (solarKw !== null && solarKw !== undefined) params.push(`solar_kw=${encodeURIComponent(solarKw)}`);
        if (loadKw !== null && loadKw !== undefined) params.push(`load_kw=${encodeURIComponent(loadKw)}`);
        if (batterySoc !== null && batterySoc !== undefined) params.push(`battery_soc=${encodeURIComponent(batterySoc)}`);
        if (params.length > 0) query = '?' + params.join('&');
        return await this._request(`/api/energy-flow${query}`);
    }

    /**
     * Real Battery API Endpoints
     */
    async getBattery() {
        return await this._request('/api/battery');
    }

    async getBatteryStatus() {
        return await this._request('/api/battery/status');
    }

    async getBatteryBackup(loadKw = null, desiredHours = 10.0) {
        let query = '';
        const params = [];
        if (loadKw !== null && loadKw !== undefined) params.push(`load_kw=${encodeURIComponent(loadKw)}`);
        if (desiredHours !== null && desiredHours !== undefined) params.push(`desired_hours=${encodeURIComponent(desiredHours)}`);
        if (params.length > 0) query = '?' + params.join('&');
        return await this._request(`/api/battery/backup${query}`);
    }

    async updateBackupConfig(desiredHours, avgLoadKw = null) {
        return await this._request('/api/energy/backup-config', {
            method: 'POST',
            body: JSON.stringify({
                desired_backup_hours: desiredHours,
                average_household_load_kw: avgLoadKw
            })
        });
    }

    async getDailySummary(budget = 25.0) {
        return await this._request(`/api/summary/daily?budget=${encodeURIComponent(budget)}`);
    }

    async sendDailySummaryNotification(budget = 25.0) {
        return await this._request('/api/summary/daily/notify', {
            method: 'POST',
            body: JSON.stringify({ user_budget: budget })
        });
    }

    async sendHourlyNotification() {
        return await this._request('/api/notifications/hourly-trigger', {
            method: 'POST'
        });
    }

    async getHourlyIntelligence() {
        return await this._request('/api/hourly/intelligence');
    }

    async getSystemNotifications(limit = 20) {
        return await this._request(`/api/notifications?limit=${encodeURIComponent(limit)}`);
    }

    /**
     * Check backend API health
     */

    async getHealth() {
        return await this._request('/api/health');
    }
}


// Global singleton instance
window.veraApi = new VeraApiClient();
