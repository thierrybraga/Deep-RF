class ChartManager {
    constructor() {
        this.charts = {};
        this.smithCanvas = null;
        this.smithCtx = null;
        this.smithDims = null;
        this.currentData = { smith: null, radiation: null };
        
        this.colors = {
            primary: '#3b82f6',
            secondary: '#8b5cf6',
            success: '#10b981',
            warning: '#f59e0b',
            error: '#ef4444',
            grid: 'rgba(148, 163, 184, 0.15)',
            text: '#94a3b8',
            background: '#1e293b'
        };
    }
}

ChartManager.prototype.init = function() {
    console.log('📊 ChartManager.init: Starting initialization...');
    Chart.defaults.color = this.colors.text;
    Chart.defaults.borderColor = this.colors.grid;
    Chart.defaults.font.family = "'Inter', sans-serif";
    
    this.initSmithChart();
    this.initRadiationChart();
    this.initS11Chart();
    this.initVSWRChart();
    this.initMatchGainChart();
    
    console.log('📊 ChartManager inicializado com sucesso');
};

ChartManager.prototype.updateAll = function(smithData, radiationData) {
    console.log('📊 ChartManager.updateAll chamado', { smithDataKeys: smithData ? Object.keys(smithData) : null, radiationDataKeys: radiationData ? Object.keys(radiationData) : null });
    
    if (smithData) {
        try {
            this.updateSmithChart(smithData);
        } catch (e) { console.error('Erro ao atualizar Smith Chart:', e); }
        
        try {
            this.updateS11Chart(smithData);
        } catch (e) { console.error('Erro ao atualizar S11 Chart:', e); }
        
        try {
            this.updateVSWRChart(smithData);
        } catch (e) { console.error('Erro ao atualizar VSWR Chart:', e); }
        
        try {
            this.updateMatchGainChart(smithData);
        } catch (e) { console.error('Erro ao atualizar Match Gain Chart:', e); }
    } else {
        console.warn('📊 ChartManager.updateAll: smithData é null/undefined');
    }
    
    if (radiationData) {
        try {
            this.updateRadiationChart(radiationData);
        } catch (e) { console.error('Erro ao atualizar Radiation Chart:', e); }
    } else {
        console.warn('📊 ChartManager.updateAll: radiationData é null/undefined');
    }
};

ChartManager.prototype.resize = function() {
    Object.values(this.charts).forEach(chart => {
        if (chart && chart.resize) chart.resize();
    });
    
    if (this.currentData.smith) {
        this.updateSmithChart(this.currentData.smith);
    } else if (this.smithCanvas) {
        this.drawSmithGrid();
    }
};

window.ChartManager = ChartManager;

