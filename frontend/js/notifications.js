/**
 * SEMS Real Browser/Device Notification Engine
 * Uses the Web Notifications API (Notification.requestPermission & new Notification())
 * Implements state-transition event detection, 5-minute anti-spam cooldown,
 * actionable click routing, and supplementary notification history logging.
 */

class BrowserNotificationService {
    constructor() {
        this.storageKey = 'sems_browser_notifications_pref';
        this.cooldownMs = 5 * 60 * 1000; // 5-minute cooldown per event type
        this.pollingIntervalMs = 15000;  // 15 seconds
        this.timer = null;
        this.isInitialized = false;

        this.previousState = null;
        this.lastNotifiedTimestamps = {};
        this.notificationHistory = [];
    }

    initializeNotifications() {
        if (this.isInitialized) return;
        this.isInitialized = true;
        console.log('Initializing SEMS Real Browser/Device Notification Service...');

        this.loadHistoryFromStorage();
        this.updatePermissionBanner();
        this.bindBannerControls();

        // Start periodic monitoring of energy-flow and server notifications
        this.startMonitoring();
    }

    isSupported() {
        return 'Notification' in window;
    }

    getPermission() {
        if (!this.isSupported()) return 'unsupported';
        return Notification.permission;
    }

    async requestNotificationPermission() {
        if (!this.isSupported()) {
            if (window.veraUI) {
                window.veraUI.showToast('Web Notifications are not supported in your browser.', 'warning');
            }
            return 'unsupported';
        }

        try {
            const permission = await Notification.requestPermission();
            localStorage.setItem(this.storageKey, permission);
            this.updatePermissionBanner();

            if (permission === 'granted') {
                if (window.veraUI) {
                    window.veraUI.showToast('✓ Real Browser/Device Notifications Enabled!', 'success');
                }
                // Send welcome test notification to verify OS display
                this.showBrowserNotification(
                    '🔔 SEMS Real-Time Alerts Enabled',
                    'You will now receive authentic device notifications for Solar, Battery, Grid, and 10-Hour Backup events.',
                    { tag: 'sems_welcome', severity: 'info', actionTarget: 'hero' }
                );
            } else if (permission === 'denied') {
                if (window.veraUI) {
                    window.veraUI.showToast('Browser notifications were blocked in browser settings.', 'warning');
                }
            }
            return permission;
        } catch (err) {
            console.error('Error requesting notification permission:', err);
            return 'default';
        }
    }

    updatePermissionBanner() {
        const banner = document.getElementById('notif-permission-banner');
        const deniedNotice = document.getElementById('notif-denied-message');
        const defaultPrompt = document.getElementById('notif-default-prompt');
        const grantedPill = document.getElementById('notif-granted-pill');

        if (!banner) return;

        const perm = this.getPermission();
        if (perm === 'granted') {
            banner.classList.add('banner-hidden');
            if (grantedPill) grantedPill.style.display = 'inline-flex';
        } else if (perm === 'denied') {
            banner.classList.remove('banner-hidden');
            if (deniedNotice) deniedNotice.style.display = 'flex';
            if (defaultPrompt) defaultPrompt.style.display = 'none';
            if (grantedPill) grantedPill.style.display = 'none';
        } else {
            // 'default'
            banner.classList.remove('banner-hidden');
            if (deniedNotice) deniedNotice.style.display = 'none';
            if (defaultPrompt) defaultPrompt.style.display = 'flex';
            if (grantedPill) grantedPill.style.display = 'none';
        }
    }

    bindBannerControls() {
        const btnEnable = document.getElementById('btn-enable-browser-notif');
        if (btnEnable) {
            btnEnable.addEventListener('click', async () => {
                await this.requestNotificationPermission();
            });
        }

        const btnDismiss = document.getElementById('btn-dismiss-perm-banner');
        if (btnDismiss) {
            btnDismiss.addEventListener('click', () => {
                const banner = document.getElementById('notif-permission-banner');
                if (banner) banner.classList.add('banner-hidden');
            });
        }
    }

    showBrowserNotification(title, message, options = {}) {
        const now = Date.now();
        const eventType = options.tag || 'general';

        // 1. Dispatch Real Browser/Device Notification
        if (this.isSupported() && Notification.permission === 'granted') {
            try {
                const nativeNotif = new Notification(title, {
                    body: message,
                    icon: options.icon || '/static/assets/favicon.ico',
                    tag: eventType, // Prevents OS notification duplicates
                    badge: '/static/assets/favicon.ico',
                    data: {
                        actionTarget: options.actionTarget,
                        url: options.url || window.location.href,
                        timestamp: now
                    }
                });

                nativeNotif.onclick = (event) => {
                    event.preventDefault();
                    window.focus();
                    if (options.actionTarget) {
                        this.navigateToTarget(options.actionTarget);
                    }
                    nativeNotif.close();
                };
            } catch (err) {
                console.warn('Native notification dispatch error:', err);
            }
        }

        // 2. Add to supplementary Notification History log
        this.addNotificationToHistory({
            id: `evt_${now}_${Math.random().toString(36).substr(2, 5)}`,
            title: title,
            message: message,
            severity: options.severity || 'info',
            actionTarget: options.actionTarget,
            timestamp: new Date().toISOString(),
            timeStr: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
    }

    addNotificationToHistory(item) {
        this.notificationHistory.unshift(item);
        if (this.notificationHistory.length > 40) {
            this.notificationHistory.pop();
        }
        this.saveHistoryToStorage();
        this.renderNotificationHistory();
    }

    saveHistoryToStorage() {
        try {
            localStorage.setItem('sems_notif_history', JSON.stringify(this.notificationHistory.slice(0, 25)));
        } catch (e) {
            // Ignore quota errors
        }
    }

    loadHistoryFromStorage() {
        try {
            const raw = localStorage.getItem('sems_notif_history');
            if (raw) {
                this.notificationHistory = JSON.parse(raw);
            }
        } catch (e) {
            this.notificationHistory = [];
        }
    }

    renderNotificationHistory() {
        const container = document.getElementById('supplementary-notif-list');
        const countBadge = document.getElementById('notif-history-count');
        if (countBadge) {
            countBadge.textContent = this.notificationHistory.length;
        }

        if (!container) return;

        if (this.notificationHistory.length === 0) {
            container.innerHTML = `
                <div class="empty-notif-history">
                    <span>🔔</span>
                    <p>No browser notifications triggered yet. State change alerts will appear here.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.notificationHistory.map(item => `
            <div class="notif-history-item notif-severity-${item.severity || 'info'}" onclick="window.browserNotifications.navigateToTarget('${item.actionTarget || 'dashboard'}')">
                <div class="notif-item-header">
                    <strong class="notif-item-title">${item.title}</strong>
                    <span class="notif-item-time">${item.timeStr || ''}</span>
                </div>
                <div class="notif-item-msg">${item.message}</div>
            </div>
        `).join('');
    }

    startMonitoring() {
        if (this.timer) clearInterval(this.timer);
        this.checkEnergyAndBackendEvents();
        this.timer = setInterval(() => this.checkEnergyAndBackendEvents(), this.pollingIntervalMs);
    }

    async checkEnergyAndBackendEvents() {
        try {
            if (!window.veraApi) return;
            const flowData = await window.veraApi.getEnergyFlow();
            if (flowData) {
                this.checkEnergyEvents(flowData);
            }
        } catch (err) {
            // Polling silent catch
        }
    }

    checkEnergyEvents(current) {
        if (!current) return;

        const solarKw = parseFloat(current.solar_power_kw || 0.0);
        const loadKw = parseFloat(current.household_load_kw || 0.0);
        const battKw = parseFloat(current.battery_power_kw || 0.0);
        const battMode = current.battery_mode || 'idle';
        const battSoc = parseFloat(current.battery_soc || 75.0);
        const gridKw = parseFloat(current.grid_power_kw || 0.0);
        const estBackup = parseFloat(current.estimated_backup_hours || 4.8);
        const reqBackup = parseFloat(current.required_backup_hours || 10.0);
        const maxSoc = 100.0;

        const now = Date.now();

        // Check if cooldown has elapsed for an event key
        const canFire = (eventType) => {
            const lastTime = this.lastNotifiedTimestamps[eventType] || 0;
            return (now - lastTime) >= this.cooldownMs;
        };

        const markFired = (eventType) => {
            this.lastNotifiedTimestamps[eventType] = now;
        };

        const cost = parseFloat(current.estimated_cost || 0.0);
        const budget = parseFloat(current.user_budget || 25.0);
        const isBudgetExceeded = cost > budget || (current.budget_status && current.budget_status.toLowerCase().includes('exceeded'));

        // If this is the initial run, seed previousState and evaluate initial notable conditions
        if (!this.previousState) {
            this.previousState = {
                solar_power_kw: solarKw,
                household_load_kw: loadKw,
                battery_mode: battMode,
                battery_soc: battSoc,
                grid_power_kw: gridKw,
                estimated_backup_hours: estBackup,
                is_solar_surplus: solarKw > loadKw,
                is_budget_exceeded: isBudgetExceeded
            };
            return;
        }

        const isConnected = current.connected !== false && current.status !== 'unavailable';
        const isApiUnavailable = current.status === 'unavailable' || current.error;

        // ==========================================
        // A. 🔋 BATTERY CONNECTION & API STATUS
        // ==========================================
        if (prev.is_connected === false && isConnected === true) {
            if (canFire('battery_connected')) {
                markFired('battery_connected');
                this.showBrowserNotification(
                    '🔋 Battery Connected',
                    `Battery ESS is now online and communicating in ${String(current.mode || 'real').toUpperCase()} mode.`,
                    { tag: 'battery_connected', severity: 'info', actionTarget: 'battery' }
                );
            }
        } else if (prev.is_connected === true && isConnected === false) {
            if (canFire('battery_disconnected')) {
                markFired('battery_disconnected');
                this.showBrowserNotification(
                    '⚠️ Battery Disconnected',
                    'Battery ESS has lost connection or is unreachable. Reverting to utility grid safeguards.',
                    { tag: 'battery_disconnected', severity: 'warning', actionTarget: 'battery' }
                );
            }
        }

        if (isApiUnavailable && !prev.is_api_unavailable) {
            if (canFire('battery_api_unavailable')) {
                markFired('battery_api_unavailable');
                this.showBrowserNotification(
                    '⚠️ Battery API Unavailable',
                    'Unable to retrieve real-time battery telemetry. Check API connection and credentials.',
                    { tag: 'battery_api_unavailable', severity: 'warning', actionTarget: 'battery' }
                );
            }
        }

        // ==========================================
        // 1. ☀️ SOLAR SURPLUS DETECTED (solar > load)
        // ==========================================
        const currentSurplus = solarKw > loadKw;
        if (currentSurplus && !prev.is_solar_surplus) {
            if (canFire('solar_surplus')) {
                markFired('solar_surplus');
                this.showBrowserNotification(
                    '☀️ Solar Surplus Detected',
                    'Solar generation is higher than household demand. Available excess solar is charging the battery.',
                    { tag: 'solar_surplus', severity: 'info', actionTarget: 'solar' }
                );
            }
        }

        // ==========================================
        // 2. 🔋 BATTERY CHARGING
        // ==========================================
        if (battMode === 'charging' && prev.battery_mode !== 'charging') {
            if (canFire('battery_charging')) {
                markFired('battery_charging');
                this.showBrowserNotification(
                    '🔋 Battery Charging',
                    `Excess solar energy is currently charging the battery storage (SOC: ${battSoc.toFixed(0)}%).`,
                    { tag: 'battery_charging', severity: 'info', actionTarget: 'battery' }
                );
            }
        }

        // ==========================================
        // 2B. 🔋 BATTERY DISCHARGING
        // ==========================================
        if (battMode === 'discharging' && prev.battery_mode !== 'discharging') {
            if (canFire('battery_discharging')) {
                markFired('battery_discharging');
                this.showBrowserNotification(
                    '🔋 Battery Discharging',
                    `Battery is supplying household demand to offset grid consumption (SOC: ${battSoc.toFixed(0)}%).`,
                    { tag: 'battery_discharging', severity: 'info', actionTarget: 'battery' }
                );
            }
        }

        // ==========================================
        // 3. 🔋 BATTERY FULL
        // ==========================================
        if (battSoc >= (maxSoc - 0.5) && prev.battery_soc < (maxSoc - 0.5)) {
            if (canFire('battery_full')) {
                markFired('battery_full');
                this.showBrowserNotification(
                    '🔋 Battery Full',
                    'Battery storage has reached its maximum SOC. Remaining excess solar is exported to the grid.',
                    { tag: 'battery_full', severity: 'info', actionTarget: 'battery' }
                );
            }
        }

        // ==========================================
        // 4. ⚠️ BATTERY LOW (<= 25%)
        // ==========================================
        if (battSoc <= 25.0 && prev.battery_soc > 25.0) {
            if (canFire('battery_low')) {
                markFired('battery_low');
                this.showBrowserNotification(
                    '⚠️ Battery Low',
                    'Battery SOC is low. Grid backup will activate if solar cannot meet demand.',
                    { tag: 'battery_low', severity: 'warning', actionTarget: 'battery' }
                );
            }
        }

        // ==========================================
        // 5. ⚡ GRID ACTIVATED (transition 0 -> >0)
        // ==========================================
        if (gridKw > 0.05 && prev.grid_power_kw <= 0.05) {
            if (canFire('grid_activated')) {
                markFired('grid_activated');
                this.showBrowserNotification(
                    '⚡ Grid Activated',
                    'Solar and battery power are insufficient to meet household demand. Grid backup is active.',
                    { tag: 'grid_activated', severity: 'important', actionTarget: 'grid' }
                );
            }
        }

        // ==========================================
        // 6. ⚡ GRID USAGE STOPPED (transition >0 -> 0)
        // ==========================================
        if (gridKw <= 0.05 && prev.grid_power_kw > 0.05) {
            if (canFire('grid_stopped')) {
                markFired('grid_stopped');
                this.showBrowserNotification(
                    '⚡ Grid Usage Stopped',
                    'Household demand is now fully satisfied without utility grid power.',
                    { tag: 'grid_stopped', severity: 'info', actionTarget: 'grid' }
                );
            }
        }

        // ==========================================
        // 7. 💰 BUDGET EXCEEDED
        // ==========================================
        if (isBudgetExceeded && !prev.is_budget_exceeded) {
            if (canFire('budget_exceeded')) {
                markFired('budget_exceeded');
                this.showBrowserNotification(
                    '💰 Budget Exceeded',
                    `Estimated electricity cost (₹${cost.toFixed(2)}) has exceeded the configured budget of ₹${budget.toFixed(2)}.`,
                    { tag: 'budget_exceeded', severity: 'warning', actionTarget: 'budget' }
                );
            }
        }

        // ==========================================
        // 8 & 9. 🔋 10-HOUR BACKUP STATUS
        // ==========================================
        const isBackupSatisfied = estBackup >= reqBackup;
        const prevBackupSatisfied = prev.estimated_backup_hours >= reqBackup;

        if (isBackupSatisfied && !prevBackupSatisfied) {
            if (canFire('backup_available')) {
                markFired('backup_available');
                this.showBrowserNotification(
                    '🔋 10-Hour Backup Available',
                    `Battery currently has sufficient stored energy for ${estBackup.toFixed(1)} hours of backup (>= 10 hours target).`,
                    { tag: 'backup_available', severity: 'info', actionTarget: 'backup' }
                );
            }
        } else if (!isBackupSatisfied && prevBackupSatisfied) {
            if (canFire('backup_not_available')) {
                markFired('backup_not_available');
                this.showBrowserNotification(
                    '⚠️ 10-Hour Backup Not Available',
                    `Current battery backup is ${estBackup.toFixed(1)} hours, which is below the required 10-hour duration.`,
                    { tag: 'backup_not_available', severity: 'warning', actionTarget: 'backup' }
                );
            }
        }

        // Update previousState
        this.previousState = {
            solar_power_kw: solarKw,
            household_load_kw: loadKw,
            battery_mode: battMode,
            battery_soc: battSoc,
            grid_power_kw: gridKw,
            estimated_backup_hours: estBackup,
            is_solar_surplus: currentSurplus,
            is_budget_exceeded: isBudgetExceeded,
            is_connected: isConnected,
            is_api_unavailable: isApiUnavailable
        };
    }

    navigateToTarget(target) {
        let el = null;
        if (target === 'solar') {
            el = document.getElementById('flow-node-solar') || document.getElementById('kpi-solar-num');
        } else if (target === 'battery') {
            el = document.getElementById('flow-node-battery') || document.getElementById('kpi-battery-num');
        } else if (target === 'grid') {
            el = document.getElementById('flow-node-grid') || document.getElementById('kpi-price-num');
        } else if (target === 'backup') {
            el = document.querySelector('.backup-monitor-footer') || document.getElementById('flow-node-battery');
        } else {
            el = document.getElementById('hero-recommendation-card');
        }

        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.classList.add('highlight-pulse');
            setTimeout(() => el.classList.remove('highlight-pulse'), 3000);
        }
    }
}

// Global Singleton Instance
window.browserNotifications = new BrowserNotificationService();

// Auto-initialize when document is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.browserNotifications.initializeNotifications());
} else {
    window.browserNotifications.initializeNotifications();
}
