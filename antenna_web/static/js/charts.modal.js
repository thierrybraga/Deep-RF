ChartManager.prototype.showExpanded = function(type) {
    const modal = document.getElementById('modal-overlay');
    const modalCanvas = document.getElementById('modal-chart');
    const modalTitle = document.getElementById('modal-title');
    
    if (!modal || !modalCanvas) return;
    
    modal.classList.remove('hidden');
    
    if (this.charts.modal) {
        this.charts.modal.destroy();
        this.charts.modal = null;
    }
    
    const data = type === 'radiation' ? this.currentData.radiation : this.currentData.smith;
    if (!data) return;
    
    switch (type) {
        case 'smith':
            modalTitle.textContent = 'Carta de Smith';
            this.createExpandedSmith(modalCanvas, data);
            break;
        case 'gain_match':
            modalTitle.textContent = 'Ganho Efetivo (Casamento)';
            this.createExpandedS11(modalCanvas, {
                frequencies_mhz: data.frequencies_mhz,
                s11_db: data.gain_match_db || []
            });
            break;
        case 'radiation':
            modalTitle.textContent = 'Diagrama de Radiação';
            this.createExpandedRadiation(modalCanvas, data);
            break;
        case 's11':
            modalTitle.textContent = 'S11 (Return Loss)';
            this.createExpandedS11(modalCanvas, data);
            break;
        case 'vswr':
            modalTitle.textContent = 'VSWR';
            this.createExpandedVSWR(modalCanvas, data);
            break;
    }
};

ChartManager.prototype.closeModal = function() {
    const modal = document.getElementById('modal-overlay');
    if (modal) modal.classList.add('hidden');
    
    if (this.charts.modal) {
        this.charts.modal.destroy();
        this.charts.modal = null;
    }
};

