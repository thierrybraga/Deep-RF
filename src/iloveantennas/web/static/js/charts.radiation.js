ChartManager.prototype.initRadiationChart = function(canvasId = 'chart-radiation') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`❌ ChartManager: Canvas "${canvasId}" não encontrado!`);
        return;
    }

    const isPlaneE = canvasId.toLowerCase().includes('rad-e');
    const isPlaneH = canvasId.toLowerCase().includes('rad-h');
    const isCombined = !isPlaneE && !isPlaneH;
    const datasets = [];

    if (isPlaneE) {
        datasets.push({
            label: 'Plano E',
            data: new Array(37).fill(0),
            borderColor: this.colors.primary,
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            pointRadius: 0,
            borderWidth: 2
        });
    } else if (isPlaneH) {
        datasets.push({
            label: 'Plano H',
            data: new Array(37).fill(0),
            borderColor: this.colors.secondary,
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            pointRadius: 0,
            borderWidth: 2
        });
    } else {
        datasets.push(
            {
                label: 'Plano E',
                data: new Array(37).fill(0),
                borderColor: this.colors.primary,
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                pointRadius: 0,
                borderWidth: 2
            },
            {
                label: 'Plano H',
                data: new Array(37).fill(0),
                borderColor: this.colors.secondary,
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                pointRadius: 0,
                borderWidth: 2
            },
            {
                label: 'E left',
                data: new Array(37).fill(0),
                borderColor: this.colors.success,
                backgroundColor: 'rgba(34, 197, 94, 0.08)',
                pointRadius: 0,
                borderWidth: 1.5,
                borderDash: [4, 2]
            },
            {
                label: 'E right',
                data: new Array(37).fill(0),
                borderColor: this.colors.warning,
                backgroundColor: 'rgba(234, 179, 8, 0.08)',
                pointRadius: 0,
                borderWidth: 1.5,
                borderDash: [4, 2]
            }
        );
    }

    this.charts[canvasId] = new Chart(canvas, {
        type: 'radar',
        data: {
            labels: this.generatePolarLabels(),
            datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, padding: 6, font: { size: 9 } }
                }
            },
            scales: {
                r: {
                    min: 0,
                    max: 1,
                    ticks: { stepSize: 0.25, font: { size: 8 }, backdropColor: 'transparent' },
                    grid: { color: this.colors.grid },
                    angleLines: { color: this.colors.grid },
                    pointLabels: { font: { size: 7 }, color: this.colors.text }
                }
            }
        }
    });
};

ChartManager.prototype.generatePolarLabels = function() {
    const labels = [];
    for (let i = 0; i <= 360; i += 10) labels.push(i + '°');
    return labels;
};

ChartManager.prototype.updateRadiationChart = function(data) {
    if (!data) return;

    this.currentData.radiation = data;
    const resample = arr => {
        const result = [];
        for (let i = 0; i <= 360; i += 10) {
            const idx = Math.round((i / 360) * (arr.length - 1));
            result.push(arr[idx]);
        }
        return result;
    };

    Object.entries(this.charts).forEach(([key, chart]) => {
        if (!chart || !chart.config || chart.config.type !== 'radar') return;
        const canvasId = chart.canvas.id.toLowerCase();

        if (canvasId.includes('rad-e')) {
            chart.data.datasets[0].data = resample(data.pattern_e);
            chart.update();
            return;
        }

        if (canvasId.includes('rad-h')) {
            chart.data.datasets[0].data = resample(data.pattern_h);
            chart.update();
            return;
        }

        if (canvasId.includes('chart-radiation') || canvasId.includes('radiation')) {
            if (chart.data.datasets.length >= 2) {
                chart.data.datasets[0].data = resample(data.pattern_e);
                chart.data.datasets[1].data = resample(data.pattern_h);
            }
            if (data.pattern_left && data.pattern_right && chart.data.datasets.length >= 4) {
                chart.data.datasets[2].data = resample(data.pattern_left);
                chart.data.datasets[3].data = resample(data.pattern_right);
            }
            chart.update();
        }
    });
};

ChartManager.prototype.createExpandedRadiation = function(canvas, data) {
    const resample = arr => {
        const result = [];
        for (let i = 0; i <= 360; i += 10) {
            const idx = Math.round((i / 360) * (arr.length - 1));
            result.push(arr[idx]);
        }
        return result;
    };
    
    this.charts.modal = new Chart(canvas, {
        type: 'radar',
        data: {
            labels: this.generatePolarLabels(),
            datasets: [
                {
                    label: 'Plano E',
                    data: resample(data.pattern_e),
                    borderColor: this.colors.primary,
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    pointRadius: 1,
                    borderWidth: 2
                },
                {
                    label: 'Plano H',
                    data: resample(data.pattern_h),
                    borderColor: this.colors.secondary,
                    backgroundColor: 'rgba(139, 92, 246, 0.2)',
                    pointRadius: 1,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } },
            scales: { r: { min: 0, max: 1, ticks: { stepSize: 0.2 } } }
        }
    });
};

