/**
 * VERA UI Manager
 * Handles theming, navigation tabs, toast notifications, and DOM helpers.
 */

class UIManager {
    constructor() {
        this.theme = localStorage.getItem('vera_theme') || 'light';
        this.activeTab = 'tab-dashboard';
    }

    init() {
        this.applyTheme(this.theme);
        this.setupNavigation();
        this.setupThemeToggle();
        this.setupCollapsibles();
    }

    applyTheme(theme) {
        this.theme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('vera_theme', theme);

        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) {
            themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }

        // Notify charts to update theme colors if active
        if (window.veraCharts) {
            window.veraCharts.updateTheme(theme);
        }
    }

    setupThemeToggle() {
        const btn = document.getElementById('theme-toggle-btn');
        if (btn) {
            btn.addEventListener('click', () => {
                const nextTheme = this.theme === 'dark' ? 'light' : 'dark';
                this.applyTheme(nextTheme);
                this.showToast(`Theme switched to ${nextTheme} mode`, 'info');
            });
        }
    }

    setupNavigation() {
        const navElements = document.querySelectorAll('.nav-link');
        navElements.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetTab = link.getAttribute('data-tab');
                if (targetTab) {
                    this.switchTab(targetTab);
                }
            });
        });

        if (window.location.hash) {
            const hashTab = window.location.hash.replace('#', '');
            if (document.getElementById(hashTab)) {
                setTimeout(() => this.switchTab(hashTab), 100);
            }
        }
    }

    switchTab(tabId) {
        if (!tabId) return;

        // Update nav links
        document.querySelectorAll('.nav-link').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
        });

        // Show strictly the active screen pane; hide all other screens
        document.querySelectorAll('.tab-pane').forEach(pane => {
            const isMatch = pane.id === tabId;
            pane.classList.toggle('active', isMatch);
        });

        this.activeTab = tabId;

        // Reset scroll position to top of window so there is no residual downward scroll
        window.scrollTo(0, 0);

        // Trigger chart resizes when tab becomes visible
        if (window.veraCharts) {
            window.veraCharts.renderPendingCharts(tabId);
        }

        // Trigger dataset reload when switching to dataset tab
        if (tabId === 'tab-dataset' && window.veraDataset) {
            window.veraDataset.loadDataset();
        }

        // Trigger history chart and monthly billing reload when switching to usage tab
        if (tabId === 'tab-usage') {
            if (window.veraApp) {
                window.veraApp.loadHistory(window.veraApp.currentHistoryPeriod || 'today');
            }
            if (window.semsFeatures) {
                window.semsFeatures.updateTnebCalculations();
            }
            if (window.monthlyBillingManager) {
                window.monthlyBillingManager.loadMonthlyData();
            }
        }

        // Trigger history & monthly billing reload when switching to history tab
        if (tabId === 'tab-history') {
            if (window.veraApp) {
                window.veraApp.loadHistory(window.veraApp.currentHistoryPeriod || 'today');
            }
            if (window.monthlyBillingManager) {
                window.monthlyBillingManager.loadMonthlyData();
            }
        }

        // Trigger alerts reload when switching to alerts tab
        if (tabId === 'tab-alerts' && window.veraAlerts) {
            window.veraAlerts.load();
        }
    }

    setupCollapsibles() {
        const toggleBtn = document.getElementById('btn-toggle-tech');
        const content = document.getElementById('tech-content-pane');
        if (toggleBtn && content) {
            toggleBtn.addEventListener('click', () => {
                content.classList.toggle('open');
                const isOpened = content.classList.contains('open');
                const icon = toggleBtn.querySelector('.toggle-icon');
                if (icon) {
                    icon.textContent = isOpened ? '▲' : '▼';
                }
            });
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let icon = 'ℹ️';
        if (type === 'success') icon = '✓';
        if (type === 'error') icon = '⚠️';
        if (type === 'warning') icon = '🚨';

        toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    setSystemStatus(online = true, text = null) {
        const indicator = document.getElementById('system-status-indicator');
        const dot = indicator?.querySelector('.status-dot');
        const label = document.getElementById('system-status-text');

        if (dot && label) {
            dot.className = `status-dot ${online ? 'online' : 'offline'}`;
            label.textContent = text || (online ? 'FastAPI Online' : 'Offline / Error');
        }
    }
}

window.veraUI = new UIManager();
