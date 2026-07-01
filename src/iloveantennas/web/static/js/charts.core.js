class ChartManager {
    constructor() {
        this.charts = {};
        this.smithCanvas = null;
        this.smithCtx = null;
        this.smithDims = null;
        this.currentData = { smith: null, radiation: null };
        
        const styles = getComputedStyle(document.documentElement);
        const token = (name, fallback) => styles.getPropertyValue(name).trim() || fallback;

        this.colors = {
            primary: token('--color-primary', '#2dd4bf'),
            secondary: token('--color-info', '#38bdf8'),
            success: token('--color-success', '#22c55e'),
            warning: token('--color-warning', '#f59e0b'),
            error: token('--color-danger', '#ef4444'),
            grid: 'rgba(170, 182, 197, 0.18)',
            text: token('--color-text-secondary', '#aab6c5'),
            background: token('--color-surface', '#1b222c'),
            primaryFill: 'rgba(45, 212, 191, 0.14)',
            secondaryFill: 'rgba(56, 189, 248, 0.14)',
            successFill: 'rgba(34, 197, 94, 0.14)',
            warningFill: 'rgba(245, 158, 11, 0.14)'
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

