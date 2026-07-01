ChartManager.prototype.initS11Chart = function(canvasId = 'chart-s11') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`❌ ChartManager: Canvas "${canvasId}" não encontrado!`);
        return;
    }
    
    this.charts.s11 = new Chart(canvas, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'S11',
                data: [],
                borderColor: this.colors.primary,
                backgroundColor: this.colors.primaryFill,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    title: { display: true, text: 'Freq (MHz)', font: { size: 9 } },
                    ticks: { font: { size: 8 }, maxTicksLimit: 6 },
                    grid: { color: this.colors.grid }
                },
                y: {
                    title: { display: true, text: 'S11 (dB)', font: { size: 9 } },
                    min: -40,
                    max: 0,
                    ticks: { font: { size: 8 } },
                    grid: { color: this.colors.grid }
                }
            }
        }
    });
};

ChartManager.prototype.updateS11Chart = function(data) {
    if (!this.charts.s11 || !data) return;
    
    const step = Math.max(1, Math.floor(data.frequencies_mhz.length / 40));
    const labels = [];
    const values = [];
    
    for (let i = 0; i < data.frequencies_mhz.length; i += step) {
        labels.push(data.frequencies_mhz[i].toFixed(0));
        values.push(data.s11_db[i]);
    }
    
    this.charts.s11.data.labels = labels;
    this.charts.s11.data.datasets[0].data = values;
    this.charts.s11.update();
};

ChartManager.prototype.initVSWRChart = function(canvasId = 'chart-vswr') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`❌ ChartManager: Canvas "${canvasId}" não encontrado!`);
        return;
    }
    
    this.charts.vswr = new Chart(canvas, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'VSWR',
                data: [],
                borderColor: this.colors.secondary,
                backgroundColor: this.colors.secondaryFill,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    title: { display: true, text: 'Freq (MHz)', font: { size: 9 } },
                    ticks: { font: { size: 8 }, maxTicksLimit: 6 },
                    grid: { color: this.colors.grid }
                },
                y: {
                    title: { display: true, text: 'VSWR', font: { size: 9 } },
                    min: 1,
                    max: 10,
                    ticks: { font: { size: 8 } },
                    grid: { color: this.colors.grid }
                }
            }
        }
    });
};

ChartManager.prototype.updateVSWRChart = function(data) {
    if (!this.charts.vswr || !data) return;
    
    const step = Math.max(1, Math.floor(data.frequencies_mhz.length / 40));
    const labels = [];
    const values = [];
    
    for (let i = 0; i < data.frequencies_mhz.length; i += step) {
        labels.push(data.frequencies_mhz[i].toFixed(0));
        values.push(Math.min(data.vswr[i], 10));
    }
    
    this.charts.vswr.data.labels = labels;
    this.charts.vswr.data.datasets[0].data = values;
    this.charts.vswr.update();
};

ChartManager.prototype.initMatchGainChart = function(canvasId = 'chart-gain-match') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`❌ ChartManager: Canvas "${canvasId}" não encontrado!`);
        return;
    }
    
    this.charts.gainMatch = new Chart(canvas, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Ganho Efetivo (casamento)',
                data: [],
                borderColor: this.colors.success,
                backgroundColor: this.colors.successFill,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    title: { display: true, text: 'Freq (MHz)', font: { size: 9 } },
                    ticks: { font: { size: 8 }, maxTicksLimit: 6 },
                    grid: { color: this.colors.grid }
                },
                y: {
                    title: { display: true, text: 'Ganho Relativo (dB)', font: { size: 9 } },
                    min: -10,
                    max: 0,
                    ticks: { font: { size: 8 } },
                    grid: { color: this.colors.grid }
                }
            }
        }
    });
};

ChartManager.prototype.updateMatchGainChart = function(data) {
    if (!data || !data.gain_match_db) return;
    
    if (!this.charts.gainMatch) {
        this.initMatchGainChart();
        if (!this.charts.gainMatch) return;
    }
    
    const step = Math.max(1, Math.floor(data.frequencies_mhz.length / 40));
    const labels = [];
    const values = [];
    
    for (let i = 0; i < data.frequencies_mhz.length; i += step) {
        labels.push(data.frequencies_mhz[i].toFixed(0));
        values.push(-Math.abs(data.gain_match_db[i]));
    }
    
    this.charts.gainMatch.data.labels = labels;
    this.charts.gainMatch.data.datasets[0].data = values;
    this.charts.gainMatch.update();
};

ChartManager.prototype.createExpandedS11 = function(canvas, data) {
    this.charts.modal = new Chart(canvas, {
        type: 'line',
        data: {
            labels: data.frequencies_mhz.map(f => f.toFixed(0)),
            datasets: [{
                label: 'S11 (dB)',
                data: data.s11_db,
                borderColor: this.colors.primary,
                backgroundColor: this.colors.primaryFill,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Frequência (MHz)' } },
                y: { title: { display: true, text: 'S11 (dB)' }, min: -40, max: 0 }
            }
        }
    });
};

ChartManager.prototype.createExpandedVSWR = function(canvas, data) {
    this.charts.modal = new Chart(canvas, {
        type: 'line',
        data: {
            labels: data.frequencies_mhz.map(f => f.toFixed(0)),
            datasets: [{
                label: 'VSWR',
                data: data.vswr.map(v => Math.min(v, 10)),
                borderColor: this.colors.secondary,
                backgroundColor: this.colors.secondaryFill,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Frequência (MHz)' } },
                y: { title: { display: true, text: 'VSWR' }, min: 1, max: 10 }
            }
        }
    });
};

