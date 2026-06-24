odoo.define('cham_cong_tinh_luong.dashboard_chart_widget', function (require) {
    "use strict";

    const AbstractFieldOwl = require('web.AbstractFieldOwl');
    const field_registry = require('web.field_registry_owl');
    const { xml } = owl.tags;

    class DashboardChartWidget extends AbstractFieldOwl {
        constructor(...args) {
            super(...args);
            this.chart = null;
        }

        mounted() {
            super.mounted();
            this._renderChart();
        }

        patched() {
            super.patched();
            this._renderChart();
        }

        willUnmount() {
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
            super.willUnmount();
        }

        _renderChart() {
            const canvas = this.el.querySelector('canvas');
            if (!canvas) {
                return;
            }

            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }

            if (!this.value) {
                return;
            }

            let config = {};
            try {
                config = JSON.parse(this.value);
            } catch (e) {
                console.error("Invalid JSON data for chart widget:", e);
                return;
            }

            if (!config || !config.labels) {
                return;
            }

            if (typeof Chart === 'undefined') {
                console.warn("Chart.js is not loaded.");
                return;
            }

            // Thích ứng Reduced Motion
            const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
            const isReduced = mediaQuery && mediaQuery.matches;
            if (isReduced && config.options) {
                config.options.animation = false;
            }

            const ctx = canvas.getContext('2d');
            this.chart = new Chart(ctx, {
                type: config.type || "bar",
                data: {
                    labels: config.labels,
                    datasets: config.datasets,
                },
                options: config.options || {
                    responsive: true,
                    maintainAspectRatio: false,
                }
            });
        }
    }

    DashboardChartWidget.template = xml`
        <div style="position: relative; height: 320px; width: 100%;">
            <canvas></canvas>
        </div>
    `;
    
    field_registry.add('dashboard_chart_widget', DashboardChartWidget);

    return DashboardChartWidget;
});
