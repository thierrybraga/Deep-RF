/**
 * Módulo de Interface do Usuário do IloveAntenas
 * Responsável por atualizar painéis de informação e resultados
 */

IloveAntenas.prototype.updateInfoPanel = function() {
    if (!this.data.antenna) return;
    
    const bb = this.data.antenna.bounding_box;
    const maxDim = Math.max(bb.size[0], bb.size[1], bb.size[2]);
    document.getElementById('info-length').textContent = `${(maxDim * 100).toFixed(1)} cm`;
    
    this.updateWavelength();
    this.updateParametersPanel();
};

IloveAntenas.prototype.updateResultsFromSmith = function() {
    if (!this.data.smith) return;
    
    const { resonance, bandwidth } = this.data.smith;
    
    document.getElementById('result-z').textContent = resonance.impedance + ' Ω';
    document.getElementById('result-s11').textContent = resonance.s11_db.toFixed(1) + ' dB';
    document.getElementById('result-vswr').textContent = resonance.vswr.toFixed(2) + ':1';
    
    const gamma = (resonance.vswr - 1) / (resonance.vswr + 1);
    document.getElementById('result-gamma').textContent = gamma.toFixed(3);
    
    document.getElementById('info-impedance').textContent = resonance.impedance.split('+')[0].trim() + ' Ω';
    
    document.getElementById('result-fc').textContent = resonance.frequency_mhz.toFixed(1) + ' MHz';
    document.getElementById('result-bw').textContent = bandwidth.width_mhz.toFixed(1) + ' MHz';
    document.getElementById('result-bw-pct').textContent = bandwidth.percent.toFixed(1) + '%';
    document.getElementById('result-range').textContent = `${bandwidth.min_mhz.toFixed(0)} - ${bandwidth.max_mhz.toFixed(0)} MHz`;

    if (this.renderer) {
        const gainDb = this.data.parameters && typeof this.data.parameters.gain_db === 'number'
            ? this.data.parameters.gain_db
            : null;
        const directivityDb = this.data.parameters && typeof this.data.parameters.directivity_db === 'number'
            ? this.data.parameters.directivity_db
            : (this.data.radiation && typeof this.data.radiation.directivity_db === 'number'
                ? this.data.radiation.directivity_db
                : null);
        this.renderer.setPerformanceMetrics({
            vswr: resonance.vswr,
            s11_db: resonance.s11_db,
            gain_db: gainDb,
            directivity_db: directivityDb
        });
    }
};

IloveAntenas.prototype.updateResultsFromRadiation = function() {
    if (!this.data.radiation) return;
    
    document.getElementById('result-directivity').textContent = this.data.radiation.directivity_db.toFixed(2) + ' dBi';
    if (this.data.parameters && typeof this.data.parameters.gain_db === 'number') {
        document.getElementById('result-gain').textContent = this.data.parameters.gain_db.toFixed(2) + ' dBi';
    } else {
        document.getElementById('result-gain').textContent = (this.data.radiation.directivity_db - 0.5).toFixed(1) + ' dBi';
    }
    document.getElementById('result-beamwidth').textContent = this.data.radiation['3db_beamwidth'].toFixed(0) + '°';
    document.getElementById('result-polarization').textContent = this.state.antennaType === 'helix' ? 'Circular' : 'Linear';
    
    // Passa dados 3D para o renderer
    if (this.data.radiation.pattern_3d && this.renderer) {
        this.renderer.setRadiationData(this.data.radiation.pattern_3d);
    }

    if (this.renderer) {
        const gainDb = this.data.parameters && typeof this.data.parameters.gain_db === 'number'
            ? this.data.parameters.gain_db
            : null;
        const directivityDb = typeof this.data.radiation.directivity_db === 'number'
            ? this.data.radiation.directivity_db
            : null;
        const vswr = this.data.smith && this.data.smith.resonance
            ? this.data.smith.resonance.vswr
            : null;
        const s11Db = this.data.smith && this.data.smith.resonance
            ? this.data.smith.resonance.s11_db
            : null;
        this.renderer.setPerformanceMetrics({
            vswr: vswr,
            s11_db: s11Db,
            gain_db: gainDb,
            directivity_db: directivityDb
        });
    }
};

IloveAntenas.prototype.updateParametersPanel = function() {
    if (!this.data.parameters) return;
    
    const dirEl = document.getElementById('info-directivity');
    const gainEl = document.getElementById('info-gain');
    
    if (dirEl && typeof this.data.parameters.directivity_db === 'number') {
        dirEl.textContent = `${this.data.parameters.directivity_db.toFixed(2)} dBi`;
    }
    
    if (gainEl && typeof this.data.parameters.gain_db === 'number') {
        gainEl.textContent = `${this.data.parameters.gain_db.toFixed(2)} dBi`;
    }
};

// --- Library Management ---

IloveAntenas.prototype.openLibrary = function() {
    const overlay = document.getElementById('library-overlay');
    if (overlay) {
        overlay.classList.remove('hidden');
        this.loadLibrary();
    }
};

IloveAntenas.prototype.closeLibrary = function() {
    document.getElementById('library-overlay')?.classList.add('hidden');
};

IloveAntenas.prototype.loadLibrary = async function() {
    try {
        const tbody = document.querySelector('#antenna-table tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '<tr class="table-loading"><td colspan="7">Carregando...</td></tr>';
        
        const response = await fetch('/api/antennas');
        if (!response.ok) throw new Error('Falha ao carregar biblioteca');
        
        const antennas = await response.json();
        this.renderLibraryTable(antennas);
    } catch (error) {
        console.error('Library load error:', error);
        this.showToast('Erro ao carregar biblioteca de antenas', 'error');
    }
};

IloveAntenas.prototype.renderLibraryTable = function(antennas) {
    const tbody = document.querySelector('#antenna-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (antennas.length === 0) {
        tbody.innerHTML = '<tr class="table-empty"><td colspan="7">Nenhuma antena encontrada</td></tr>';
        return;
    }
    
    antennas.forEach(antenna => {
        const tr = document.createElement('tr');
        
        // Formata valores
        const freq = (antenna.config.frequency / 1e6).toFixed(1);
        const gain = antenna.gain_db ? `${antenna.gain_db.toFixed(1)} dBi` : '--';
        const typeName = this.getTypeName(antenna.config.type);
        
        tr.innerHTML = `
            <td>${antenna.name}</td>
            <td>${antenna.brand || '-'}</td>
            <td>${antenna.technology || '-'}</td>
            <td>${typeName}</td>
            <td>${freq}</td>
            <td>${gain}</td>
            <td>
                <div class="table-actions">
                    <button class="btn-icon small load-antenna" title="Carregar" data-id="${antenna.id}">
                        <i class="fas fa-upload"></i>
                    </button>
                    <button class="btn-icon small edit-antenna" title="Editar" data-id="${antenna.id}">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon small delete-antenna danger-icon" title="Excluir" data-id="${antenna.id}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        
        // Bind actions
        tr.querySelector('.load-antenna').addEventListener('click', () => this.loadAntennaFromLibrary(antenna));
        tr.querySelector('.edit-antenna').addEventListener('click', () => this.openEditor(antenna));
        tr.querySelector('.delete-antenna').addEventListener('click', () => this.deleteAntenna(antenna.id));
        
        tbody.appendChild(tr);
    });
};

IloveAntenas.prototype.filterLibrary = function(query) {
    const term = query.toLowerCase();
    const rows = document.querySelectorAll('#antenna-table tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(term) ? '' : 'none';
    });
};

IloveAntenas.prototype.loadAntennaFromLibrary = function(antenna) {
    // Carrega configuração
    this.state.antennaType = antenna.config.type;
    this.state.frequency = antenna.config.frequency;
    
    // Atualiza UI
    const typeBtn = document.querySelector(`.antenna-type-btn[data-type="${antenna.config.type}"]`);
    if (typeBtn) typeBtn.click();
    
    const freqInput = document.getElementById('input-frequency');
    if (freqInput) {
        freqInput.value = (antenna.config.frequency / 1e6).toFixed(1);
        freqInput.dispatchEvent(new Event('change'));
    }
    
    // Aplica parâmetros específicos
    // TODO: Mapear parâmetros específicos de cada tipo
    
    this.closeLibrary();
    this.showToast(`Antena "${antenna.name}" carregada`, 'success');
    
    // Recalcula
    setTimeout(() => this.createAntenna(), 100);
};

IloveAntenas.prototype.deleteAntenna = async function(id) {
    if (!confirm('Tem certeza que deseja excluir esta antena?')) return;
    
    try {
        const response = await fetch(`/api/antennas/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Erro ao excluir');
        
        this.showToast('Antena excluída com sucesso', 'success');
        this.loadLibrary(); // Recarrega lista
    } catch (error) {
        console.error(error);
        this.showToast('Erro ao excluir antena', 'error');
    }
};

// --- Editor Management ---

IloveAntenas.prototype.openEditor = function(antenna = null) {
    const overlay = document.getElementById('editor-overlay');
    if (!overlay) return;
    
    const isNew = !antenna;
    document.getElementById('editor-title').textContent = isNew ? 'Nova Antena' : 'Editar Antena';
    document.getElementById('edit-antenna-id').value = isNew ? '' : antenna.id;
    
    // Preenche campos básicos
    document.getElementById('edit-name').value = isNew ? '' : antenna.name;
    document.getElementById('edit-brand').value = isNew ? '' : (antenna.brand || '');
    document.getElementById('edit-technology').value = isNew ? '' : (antenna.technology || '');
    document.getElementById('edit-gain').value = isNew ? '' : (antenna.gain_db || '');
    
    // Configura tipo e frequência
    const typeSelect = document.getElementById('edit-type');
    
    // Popula select se vazio
    if (typeSelect.options.length === 0) {
        const types = [
            {id: 'dipole', name: 'Dipolo'},
            {id: 'monopole', name: 'Monopolo'},
            {id: 'yagi', name: 'Yagi-Uda'},
            {id: 'patch', name: 'Patch'},
            {id: 'horn', name: 'Corneta'},
            {id: 'dish', name: 'Parabólica'},
            {id: 'helix', name: 'Helicoidal'},
            {id: 'lpda', name: 'Log-Periódica'},
            {id: 'loop', name: 'Loop'},
            {id: 'biquad', name: 'Biquad'},
            {id: 'v_dipole', name: 'Dipolo em V'},
            {id: 'folded_dipole', name: 'Dipolo Dobrado'},
            {id: 'discone', name: 'Discone'}
        ];
        types.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t.id;
            opt.textContent = t.name;
            typeSelect.appendChild(opt);
        });
    }
    
    typeSelect.value = isNew ? this.state.antennaType : antenna.config.type;
    document.getElementById('edit-frequency').value = isNew ? (this.state.frequency / 1e6).toFixed(1) : (antenna.config.frequency / 1e6).toFixed(1);
    
    // TODO: Renderizar campos específicos baseado no tipo
    
    overlay.classList.remove('hidden');
    
    // Bind save
    const form = document.getElementById('antenna-form');
    form.onsubmit = (e) => {
        e.preventDefault();
        this.saveAntenna();
    };
    
    // Bind close
    document.getElementById('btn-close-editor').onclick = () => {
        overlay.classList.add('hidden');
    };
};

IloveAntenas.prototype.saveAntenna = async function() {
    const id = document.getElementById('edit-antenna-id').value;
    const isNew = !id;
    
    const data = {
        name: document.getElementById('edit-name').value,
        brand: document.getElementById('edit-brand').value,
        technology: document.getElementById('edit-technology').value,
        gain_db: parseFloat(document.getElementById('edit-gain').value) || null,
        config: {
            type: document.getElementById('edit-type').value,
            frequency: parseFloat(document.getElementById('edit-frequency').value) * 1e6
            // TODO: Adicionar outros parâmetros específicos
        }
    };
    
    if (!isNew) data.id = id;
    
    try {
        const url = isNew ? '/api/antennas' : `/api/antennas/${id}`;
        const method = isNew ? 'POST' : 'PUT';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) throw new Error('Erro ao salvar');
        
        this.showToast('Antena salva com sucesso', 'success');
        document.getElementById('editor-overlay').classList.add('hidden');
        
        // Se a biblioteca estiver aberta, recarrega
        if (!document.getElementById('library-overlay').classList.contains('hidden')) {
            this.loadLibrary();
        }
    } catch (error) {
        console.error(error);
        this.showToast('Erro ao salvar antena', 'error');
    }
};
