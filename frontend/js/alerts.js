/**
 * Multi-Channel Alerts & Notification Center Manager
 * Manages the floating header notification dropdown, active unread counter,
 * mark-as-read state, dismissals, and full-screen alerts ledger.
 */

class AlertCenterManager {
    constructor() {
        this.alerts = [];
        this.dropdownOpen = false;
        this.init();
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.bindControls());
        } else {
            this.bindControls();
        }
    }

    bindControls() {
        const alertBtn = document.getElementById('btn-header-alerts');
        const dropdown = document.getElementById('notification-dropdown');
        const markAllReadBtn = document.getElementById('btn-mark-all-read');
        const tabMarkAllReadBtn = document.getElementById('btn-tab-mark-read');
        const clearAllBtn = document.getElementById('btn-dropdown-clear-all');
        const tabClearAllBtn = document.getElementById('btn-tab-clear-all');
        const viewAllBtn = document.getElementById('btn-dropdown-view-all');

        // Toggle dropdown when bell icon is clicked
        if (alertBtn) {
            alertBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDropdown();
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (this.dropdownOpen) {
                const wrapper = document.getElementById('header-notif-wrapper');
                if (wrapper && !wrapper.contains(e.target)) {
                    this.closeDropdown();
                }
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.dropdownOpen) {
                this.closeDropdown();
            }
        });

        // Mark all as read handlers
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.markAllAsRead();
            });
        }
        if (tabMarkAllReadBtn) {
            tabMarkAllReadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.markAllAsRead();
            });
        }

        // Clear all handlers
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.clearAll();
            });
        }
        if (tabClearAllBtn) {
            tabClearAllBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.clearAll();
            });
        }

        // View all alerts page button
        if (viewAllBtn) {
            viewAllBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.closeDropdown();
                if (window.veraUI) {
                    window.veraUI.switchTab('tab-alerts');
                }
            });
        }
    }

    toggleDropdown() {
        const dropdown = document.getElementById('notification-dropdown');
        if (!dropdown) return;

        this.dropdownOpen = !this.dropdownOpen;
        dropdown.style.display = this.dropdownOpen ? 'block' : 'none';

        const alertBtn = document.getElementById('btn-header-alerts');
        if (alertBtn) {
            alertBtn.setAttribute('aria-expanded', String(this.dropdownOpen));
        }

        if (this.dropdownOpen) {
            this.load();
        }
    }

    closeDropdown() {
        const dropdown = document.getElementById('notification-dropdown');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
        this.dropdownOpen = false;
        const alertBtn = document.getElementById('btn-header-alerts');
        if (alertBtn) {
            alertBtn.setAttribute('aria-expanded', 'false');
        }
    }

    async load() {
        try {
            const res = await window.veraApi.getActiveAlerts();
            if (res && res.status === 'success') {
                this.alerts = res.alerts || [];
                this.renderAll();
            }
        } catch (error) {
            console.error('Failed to load alerts:', error);
        }
    }

    async fetchAlerts() {
        return await this.load();
    }

    renderAll() {
        const unreadCount = this.alerts.filter(a => !a.is_read).length;

        // 1. Update header bell badge
        const badgeCount = document.getElementById('header-alert-badge');
        if (badgeCount) {
            badgeCount.textContent = unreadCount;
            badgeCount.style.display = unreadCount > 0 ? 'inline-flex' : 'none';
        }

        // 2. Update dropdown pill
        const dropdownPill = document.getElementById('notif-badge-pill');
        if (dropdownPill) {
            dropdownPill.textContent = unreadCount > 0 ? `${unreadCount} Unread` : 'All Read';
            dropdownPill.style.background = unreadCount > 0 ? '#ef4444' : '#10b981';
            dropdownPill.style.color = '#ffffff';
        }

        // 3. Update full screen active counter
        const activeCountEl = document.getElementById('alerts-active-count');
        if (activeCountEl) {
            activeCountEl.textContent = `${unreadCount} Active`;
        }

        // 4. Render dropdown list
        this.renderDropdownList();

        // 5. Render full alerts page container
        this.renderTabList();
    }

    renderDropdownList() {
        const list = document.getElementById('notif-dropdown-list');
        if (!list) return;

        if (this.alerts.length === 0) {
            list.innerHTML = `
                <div class="notif-empty-state">
                    <span class="notif-empty-icon">✅</span>
                    <strong>No Active Notifications</strong>
                    <p>All microgrid systems and renewable dispatches are running normally.</p>
                </div>
            `;
            return;
        }

        list.innerHTML = this.alerts.map(alt => {
            const dt = new Date(alt.timestamp);
            const timeStr = !isNaN(dt.getTime()) ? dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Now';
            const isRead = alt.is_read;
            const icon = alt.severity === 'critical' ? '🚨' : (alt.severity === 'warning' ? '⚠️' : (alt.severity === 'success' ? '📊' : '⚡'));

            return `
                <div class="notif-item ${isRead ? 'notif-read' : 'notif-unread'} notif-sev-${alt.severity}" id="notif-dd-${alt.id}">
                    <div class="notif-item-left">
                        <span class="notif-item-icon">${icon}</span>
                    </div>
                    <div class="notif-item-body">
                        <div class="notif-item-head">
                            <span class="notif-item-title">${alt.title}</span>
                            <span class="notif-item-time">${timeStr}</span>
                        </div>
                        <p class="notif-item-msg">${alt.message}</p>
                        <div class="notif-item-actions">
                            ${alt.action_url ? `<button class="notif-action-btn" onclick="window.veraAlerts.navigateTo('${alt.action_url}')">View Details ➔</button>` : ''}
                            ${!isRead ? `<button class="notif-mark-btn" onclick="window.veraAlerts.markSingleRead('${alt.id}')" title="Mark as read">✓ Read</button>` : ''}
                            <button class="notif-dismiss-btn" onclick="window.veraAlerts.dismiss('${alt.id}')" title="Dismiss">✕</button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderTabList() {
        const container = document.getElementById('alerts-list-container');
        if (!container) return;

        if (this.alerts.length === 0) {
            container.innerHTML = `
                <div class="empty-alerts-box card">
                    <span class="empty-icon">✅</span>
                    <h3>All Systems Operating Normally</h3>
                    <p>No active anomalies, blackout islanding warnings, or high tariff alerts at this time.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.alerts.map(alt => {
            const dt = new Date(alt.timestamp);
            const timeStr = !isNaN(dt.getTime()) ? dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
            const isRead = alt.is_read;
            const icon = alt.severity === 'critical' ? '🚨' : (alt.severity === 'warning' ? '⚠️' : (alt.severity === 'success' ? '📊' : '⚡'));

            return `
                <div class="card alert-card severity-${alt.severity} ${isRead ? 'alert-read' : ''}" id="card-${alt.id}">
                    <div class="alert-icon-box">
                        ${icon}
                    </div>
                    <div class="alert-content">
                        <div class="alert-header-row">
                            <strong class="alert-title">${alt.title}</strong>
                            <div style="display:flex; align-items:center; gap:8px;">
                                ${isRead ? '<span style="font-size:0.75rem; color:#10b981; font-weight:700;">✓ Read</span>' : '<span style="font-size:0.75rem; color:#ef4444; font-weight:700;">● Unread</span>'}
                                <span class="alert-time">${timeStr}</span>
                            </div>
                        </div>
                        <p class="alert-msg">${alt.message}</p>
                    </div>
                    <div class="alert-actions" style="display:flex; align-items:center; gap:8px;">
                        ${alt.action_url ? `<button class="alert-link-btn" onclick="window.veraAlerts.navigateTo('${alt.action_url}')">View ➔</button>` : ''}
                        ${!isRead ? `<button class="icon-btn small-icon-btn" onclick="window.veraAlerts.markSingleRead('${alt.id}')" title="Mark as read" style="font-size:0.8rem; font-weight:bold; color:#10b981;">✓</button>` : ''}
                        <button class="icon-btn small-icon-btn" onclick="window.veraAlerts.dismiss('${alt.id}')" title="Dismiss Alert">✕</button>
                    </div>
                </div>
            `;
        }).join('');
    }

    async markSingleRead(alertId) {
        try {
            await window.veraApi.markAlertRead(alertId);
            const alt = this.alerts.find(a => a.id === alertId);
            if (alt) alt.is_read = true;
            this.renderAll();
            if (window.veraUI) window.veraUI.showToast('Notification marked as read', 'info');
        } catch (error) {
            console.error('Mark read failed:', error);
        }
    }

    async markAllAsRead() {
        try {
            await window.veraApi.markAllAlertsRead();
            this.alerts.forEach(a => { a.is_read = true; });
            this.renderAll();
            if (window.veraUI) {
                window.veraUI.showToast('✓ All notifications marked as read', 'success');
            }
        } catch (error) {
            console.error('Mark all read failed:', error);
            // Local fallback
            this.alerts.forEach(a => { a.is_read = true; });
            this.renderAll();
        }
    }

    async dismiss(alertId) {
        try {
            await window.veraApi.dismissAlert(alertId);
            this.alerts = this.alerts.filter(a => a.id !== alertId);
            this.renderAll();
        } catch (error) {
            console.error('Dismiss failed:', error);
        }
    }

    async clearAll() {
        try {
            await window.veraApi.clearAllAlerts();
            this.alerts = [];
            this.renderAll();
            if (window.veraUI) window.veraUI.showToast('All notifications cleared', 'info');
        } catch (error) {
            console.error('Clear all alerts failed:', error);
            this.alerts = [];
            this.renderAll();
        }
    }

    navigateTo(tabSelector) {
        this.closeDropdown();
        const tabId = tabSelector.replace('#', '');
        if (window.veraUI) {
            window.veraUI.switchTab(tabId);
        }
    }
}

window.veraAlerts = new AlertCenterManager();
