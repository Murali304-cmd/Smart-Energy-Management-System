/**
 * SEMS 3D Digital Twin Interactive House Visualizer
 * Hardware-accelerated canvas engine rendering isometric microgrid layout with dynamic particle power streams.
 */

class DigitalTwin3D {
    constructor(canvasId = 'digital-twin-canvas') {
        this.canvasId = canvasId;
        this.canvas = document.getElementById(canvasId);
        this.isPaused = false;
        this.animationId = null;
        this.particles = [];

        if (this.canvas) {
            this.initCanvas();
        } else {
            document.addEventListener('DOMContentLoaded', () => this.initCanvas());
        }
    }

    initCanvas() {
        this.canvas = document.getElementById(this.canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.resize();

        this.nodes = {
            solar: { x: this.width * 0.22, y: this.height * 0.22, label: '☀️ Solar Rooftop', power: 4.00, color: '#f59e0b' },
            inverter: { x: this.width * 0.50, y: this.height * 0.48, label: '⚡ Smart Inverter', power: 3.80, color: '#38bdf8' },
            battery: { x: this.width * 0.22, y: this.height * 0.76, label: '🔋 LiFePO4 ESS', power: 1.50, color: '#10b981' },
            home: { x: this.width * 0.78, y: this.height * 0.48, label: '🏠 Smart Home', power: 2.10, color: '#a855f7' },
            grid: { x: this.width * 0.78, y: this.height * 0.76, label: '🏢 Utility Grid', power: 0.50, color: '#0284c7' }
        };

        this.initParticles();
        this.bindEvents();
        this.animate = this.animate.bind(this);
        this.start();
    }

    resize() {
        if (!this.canvas || !this.canvas.parentElement) return;
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.width = this.canvas.width = rect.width || 800;
        this.height = this.canvas.height = 400;

        if (this.nodes) {
            this.nodes.solar.x = this.width * 0.22;
            this.nodes.solar.y = this.height * 0.22;
            this.nodes.inverter.x = this.width * 0.50;
            this.nodes.inverter.y = this.height * 0.48;
            this.nodes.battery.x = this.width * 0.22;
            this.nodes.battery.y = this.height * 0.76;
            this.nodes.home.x = this.width * 0.78;
            this.nodes.home.y = this.height * 0.48;
            this.nodes.grid.x = this.width * 0.78;
            this.nodes.grid.y = this.height * 0.76;
        }
    }

    initParticles() {
        this.particles = [];
        // Solar -> Inverter stream
        for (let i = 0; i < 25; i++) {
            this.particles.push({
                source: 'solar',
                target: 'inverter',
                progress: Math.random(),
                speed: 0.008 + Math.random() * 0.006,
                size: 2.8 + Math.random() * 1.8,
                color: '#f59e0b'
            });
        }
        // Inverter -> Home stream
        for (let i = 0; i < 25; i++) {
            this.particles.push({
                source: 'inverter',
                target: 'home',
                progress: Math.random(),
                speed: 0.008 + Math.random() * 0.005,
                size: 3.0 + Math.random() * 1.5,
                color: '#38bdf8'
            });
        }
        // Battery <-> Inverter stream
        for (let i = 0; i < 18; i++) {
            this.particles.push({
                source: 'battery',
                target: 'inverter',
                progress: Math.random(),
                speed: 0.007 + Math.random() * 0.005,
                size: 2.6 + Math.random() * 1.5,
                color: '#10b981'
            });
        }
    }

    bindEvents() {
        window.addEventListener('resize', () => this.resize());

        const toggleBtn = document.getElementById('btn-toggle-particles');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                this.isPaused = !this.isPaused;
                toggleBtn.textContent = this.isPaused ? '▶️ Resume Stream' : '⏸️ Pause Stream';
                const pill = document.getElementById('digital-twin-live-pill');
                if (pill) {
                    pill.textContent = this.isPaused ? '⏸️ Stream Paused' : '⚡ Particle Physics Stream Active';
                    pill.style.background = this.isPaused ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)';
                    pill.style.color = this.isPaused ? '#ef4444' : '#10b981';
                }
            });
        }
    }

    updatePowerFlows(solarKw = 4.00, loadKw = 2.10, batteryKw = 1.50, gridKw = 0.50) {
        if (!this.nodes) return;
        this.nodes.solar.power = Number(solarKw || 0);
        this.nodes.home.power = Number(loadKw || 0);
        this.nodes.battery.power = Number(batteryKw || 0);
        this.nodes.grid.power = Number(gridKw || 0);
        this.nodes.inverter.power = Math.max(0.1, this.nodes.solar.power + this.nodes.battery.power);

        // Update footer node badges
        const sEl = document.getElementById('twin-val-solar');
        const bEl = document.getElementById('twin-val-battery');
        const hEl = document.getElementById('twin-val-home');
        const gEl = document.getElementById('twin-val-grid');

        if (sEl) sEl.textContent = `${this.nodes.solar.power.toFixed(2)} kW`;
        if (bEl) bEl.textContent = `${this.nodes.battery.power.toFixed(2)} kW`;
        if (hEl) hEl.textContent = `${this.nodes.home.power.toFixed(2)} kW`;
        if (gEl) gEl.textContent = `${this.nodes.grid.power.toFixed(2)} kW`;
    }

    drawConnections() {
        const links = [
            { from: this.nodes.solar, to: this.nodes.inverter, color: '#f59e0b', active: this.nodes.solar.power > 0.05 },
            { from: this.nodes.battery, to: this.nodes.inverter, color: '#10b981', active: this.nodes.battery.power > 0.05 },
            { from: this.nodes.inverter, to: this.nodes.home, color: '#38bdf8', active: this.nodes.home.power > 0.05 },
            { from: this.nodes.grid, to: this.nodes.home, color: '#0284c7', active: this.nodes.grid.power > 0.05 }
        ];

        links.forEach(l => {
            this.ctx.beginPath();
            this.ctx.moveTo(l.from.x, l.from.y);
            this.ctx.lineTo(l.to.x, l.to.y);
            this.ctx.strokeStyle = l.active ? 'rgba(56, 189, 248, 0.4)' : 'rgba(100, 116, 139, 0.2)';
            this.ctx.lineWidth = l.active ? 3 : 1.5;
            this.ctx.setLineDash(l.active ? [6, 4] : []);
            this.ctx.stroke();
            this.ctx.setLineDash([]);
        });
    }

    drawNodes() {
        Object.values(this.nodes).forEach(n => {
            // Radiant Outer Glow
            const glow = this.ctx.createRadialGradient(n.x, n.y, 10, n.x, n.y, 36);
            glow.addColorStop(0, n.color + '44');
            glow.addColorStop(1, 'transparent');
            this.ctx.fillStyle = glow;
            this.ctx.beginPath();
            this.ctx.arc(n.x, n.y, 36, 0, Math.PI * 2);
            this.ctx.fill();

            // Core Node Circle
            this.ctx.beginPath();
            this.ctx.arc(n.x, n.y, 24, 0, Math.PI * 2);
            this.ctx.fillStyle = '#0f172a';
            this.ctx.fill();
            this.ctx.strokeStyle = n.color;
            this.ctx.lineWidth = 2.5;
            this.ctx.stroke();

            // Node Label
            this.ctx.fillStyle = '#f8fafc';
            this.ctx.font = 'bold 11px Plus Jakarta Sans, sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.fillText(n.label, n.x, n.y - 32);

            // Power Value Display
            this.ctx.fillStyle = n.color;
            this.ctx.font = 'bold 12px JetBrains Mono, monospace';
            this.ctx.fillText(`${n.power.toFixed(2)} kW`, n.x, n.y + 4);
        });
    }

    drawParticles() {
        this.particles.forEach(p => {
            if (!this.isPaused) {
                p.progress += p.speed;
                if (p.progress >= 1.0) p.progress = 0.0;
            }

            const fromNode = this.nodes[p.source];
            const toNode = this.nodes[p.target];
            if (!fromNode || !toNode) return;

            const px = fromNode.x + (toNode.x - fromNode.x) * p.progress;
            const py = fromNode.y + (toNode.y - fromNode.y) * p.progress;

            this.ctx.beginPath();
            this.ctx.arc(px, py, p.size, 0, Math.PI * 2);
            this.ctx.fillStyle = p.color;
            this.ctx.shadowColor = p.color;
            this.ctx.shadowBlur = 10;
            this.ctx.fill();
            this.ctx.shadowBlur = 0;
        });
    }

    animate() {
        if (this.ctx) {
            this.ctx.clearRect(0, 0, this.width, this.height);
            this.drawConnections();
            this.drawParticles();
            this.drawNodes();
        }
        this.animationId = requestAnimationFrame(this.animate);
    }

    start() {
        if (!this.animationId) {
            this.animate();
        }
    }

    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }
}

// Global Singleton
window.digitalTwin = new DigitalTwin3D();
