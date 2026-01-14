
// ========================================================================
// SIMULATION & COMPARISON
// ========================================================================

IloveAntenas.prototype.startComparison = async function() {
    console.log('Iniciando comparação FDTD vs FEM...');
    const modal = document.getElementById('comparison-overlay');
    const progressBar = document.getElementById('comp-progress-fill');
    const progressText = document.getElementById('comp-progress-text');
    
    if (!modal) return;
    
    modal.classList.remove('hidden');
    progressBar.style.width = '0%';
    progressText.textContent = '0%';
    
    document.getElementById('comp-error-mean').textContent = '--';
    document.getElementById('comp-error-max').textContent = '--';
    document.getElementById('comp-correlation').textContent = '--';
    
    const payload = this.getSimulationPayload();
    
    try {
        const response = await fetch('/api/simulation/compare', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (data.success) {
            this.pollComparison(data.comparison_id, data.fdtd_id, data.fem_id);
        } else {
            progressText.textContent = 'Erro: ' + data.error;
        }
    } catch (e) {
        console.error(e);
        progressText.textContent = 'Erro de conexão';
    }
};

IloveAntenas.prototype.pollComparison = async function(compId, fdtdId, femId) {
    const progressBar = document.getElementById('comp-progress-fill');
    const progressText = document.getElementById('comp-progress-text');
    
    const check = async () => {
        try {
            const [resFDTD, resFEM] = await Promise.all([
                fetch(`/api/simulation/${fdtdId}/status`).then(r => r.json()),
                fetch(`/api/simulation/${femId}/status`).then(r => r.json())
            ]);
            
            const fdtdData = resFDTD.data || resFDTD;
            const femData = resFEM.data || resFEM;
            
            const progFDTD = fdtdData.progress || 0;
            const progFEM = femData.progress || 0;
            const avgProgress = (progFDTD + progFEM) / 2;
            
            progressBar.style.width = `${avgProgress}%`;
            progressText.textContent = `${Math.floor(avgProgress)}%`;
            
            if (fdtdData.status === 'completed' && femData.status === 'completed') {
                progressText.textContent = '100% - Processando...';
                
                const [framesFDTD, framesFEM] = await Promise.all([
                     fetch(`/api/simulation/${fdtdId}/frames`).then(r => r.json()),
                     fetch(`/api/simulation/${femId}/frames`).then(r => r.json())
                ]);
                
                this.processComparisonResults(framesFDTD, framesFEM, fdtdData, femData);
            } else if (fdtdData.status === 'error' || femData.status === 'error') {
                progressText.textContent = `Erro: ${fdtdData.error || femData.error}`;
            } else {
                setTimeout(check, 1000);
            }
        } catch (e) {
            console.error(e);
            progressText.textContent = 'Erro de comunicação';
        }
    };
    
    check();
};

IloveAntenas.prototype.processComparisonResults = function(framesFDTD, framesFEM, statsFDTD, statsFEM) {
    if (!framesFDTD.success || !framesFEM.success) {
        console.error('Erro ao obter frames');
        return;
    }

    const fdtdList = framesFDTD.frames;
    const femList = framesFEM.frames;
    
    const findMaxFrame = (list) => {
        let maxVal = -1;
        let bestFrame = list[0];
        for(const f of list) {
            if(f.maxVal > maxVal) {
                maxVal = f.maxVal;
                bestFrame = f;
            }
        }
        return bestFrame;
    };
    
    const bestFdtd = findMaxFrame(fdtdList);
    const bestFem = findMaxFrame(femList);
    
    if (!bestFdtd || !bestFem) {
        console.error('Dados de frame incompletos');
        return;
    }
    
    this.renderComparisonCanvas('canvas-comp-fdtd', bestFdtd.fieldE);
    this.renderComparisonCanvas('canvas-comp-fem', bestFem.fieldE);
    
    document.getElementById('comp-fdtd-max').textContent = bestFdtd.maxVal.toExponential(2) + ' V/m';
    document.getElementById('comp-fem-max').textContent = bestFem.maxVal.toExponential(2) + ' V/m';
    
    const timeFDTD = statsFDTD.computation_time !== undefined ? statsFDTD.computation_time : (statsFDTD.stats?.computation_time || 0);
    const timeFEM = statsFEM.computation_time !== undefined ? statsFEM.computation_time : (statsFEM.stats?.computation_time || 0);

    document.getElementById('comp-fdtd-time').textContent = timeFDTD.toFixed(2) + 's';
    document.getElementById('comp-fem-time').textContent = timeFEM.toFixed(2) + 's';
    
    const metrics = this.calculateMetrics(bestFdtd.fieldE, bestFem.fieldE);
    
    document.getElementById('comp-error-mean').textContent = (metrics.mse * 100).toFixed(2) + '%';
    document.getElementById('comp-error-max').textContent = (metrics.maxError * 100).toFixed(2) + '%';
    document.getElementById('comp-correlation').textContent = metrics.correlation.toFixed(4);
};

IloveAntenas.prototype.getHeatmapColor = function(value) {
    const v = Math.max(0, Math.min(1, value));
    const r = Math.floor(255 * v);
    const g = 0;
    const b = Math.floor(255 * (1 - 0.7 * v));
    return [r, g, b];
};

IloveAntenas.prototype.renderComparisonCanvas = function(canvasId, data) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const displayWidth = canvas.clientWidth;
    const displayHeight = canvas.clientHeight;
    
    if (canvas.width !== displayWidth || canvas.height !== displayHeight) {
        canvas.width = displayWidth;
        canvas.height = displayHeight;
    }
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, width, height);
    
    if (!data || data.length === 0) return;
    
    const nx = data.length;
    const ny = data[0].length;
    
    const imgData = ctx.createImageData(width, height);
    const buf = new Uint32Array(imgData.data.buffer);
    
    let maxVal = 0;
    for (let i = 0; i < nx; i++) {
        for (let j = 0; j < ny; j++) {
            const v = Math.abs(data[i][j]);
            if (v > maxVal) maxVal = v;
        }
    }
    if (maxVal === 0) maxVal = 1;

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const gx = Math.floor(x / width * nx);
            const gy = Math.floor((height - 1 - y) / height * ny); 
            
            let val = 0;
            if (data[gx] && data[gx][gy] !== undefined) {
                val = data[gx][gy];
            }
            
            const intensity = Math.abs(val) / maxVal;
            
            let r, g, b;
            const t = Math.max(0, Math.min(1, intensity));
            
            if (t < 0.25) {
                const u = t / 0.25;
                r = 0; g = Math.floor(255 * u); b = 255;
            } else if (t < 0.5) {
                const u = (t - 0.25) / 0.25;
                r = 0; g = 255; b = Math.floor(255 * (1 - u));
            } else if (t < 0.75) {
                const u = (t - 0.5) / 0.25;
                r = Math.floor(255 * u); g = 255; b = 0;
            } else {
                const u = (t - 0.75) / 0.25;
                r = 255; g = Math.floor(255 * (1 - u)); b = 0;
            }
            
            buf[y * width + x] = (255 << 24) | (b << 16) | (g << 8) | r;
        }
    }
    
    ctx.putImageData(imgData, 0, 0);
};

IloveAntenas.prototype.calculateMetrics = function(data1, data2) {
    const nx1 = data1.length;
    const ny1 = data1[0].length;
    const nx2 = data2.length;
    const ny2 = data2[0].length;
    
    const sample2 = (u, v) => {
        const x = Math.min(nx2 - 1, Math.max(0, Math.floor(u * nx2)));
        const y = Math.min(ny2 - 1, Math.max(0, Math.floor(v * ny2)));
        return data2[x][y];
    };
    
    let sumSqErr = 0;
    let maxErr = 0;
    let sumProd = 0;
    let sumSq1 = 0;
    let sumSq2 = 0;
    let count = 0;
    
    for (let i = 0; i < nx1; i++) {
        for (let j = 0; j < ny1; j++) {
            const u = i / nx1;
            const v = j / ny1;
            
            const v1 = Math.abs(data1[i][j]);
            const v2 = Math.abs(sample2(u, v));
            
            const err = Math.abs(v1 - v2);
            sumSqErr += err * err;
            maxErr = Math.max(maxErr, err);
            
            sumProd += v1 * v2;
            sumSq1 += v1 * v1;
            sumSq2 += v2 * v2;
            
            count++;
        }
    }
    
    const mse = sumSqErr / count;
    const correlation = sumProd / (Math.sqrt(sumSq1) * Math.sqrt(sumSq2));
    
    return {
        mse: mse,
        maxError: maxErr,
        correlation: correlation || 0
    };
};

IloveAntenas.prototype.optimizeLength = async function() {
    const btn = document.getElementById('btn-optimize');
    const status = document.getElementById('optimization-status');
    const msg = document.getElementById('opt-message');
    const progress = document.getElementById('opt-progress');
    const progressFill = document.getElementById('opt-progress-fill');
    
    btn.disabled = true;
    status.classList.remove('hidden');
    msg.textContent = 'Iniciando otimização...';
    progress.textContent = '0%';
    progressFill.style.width = '0%';
    
    try {
        const response = await fetch('/api/optimize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                antenna_type: this.state.antennaType,
                target_freq: this.state.frequency,
                start_length: this.state.length,
                radius: this.state.radius
            })
        });
        
        const data = await response.json();
        if (!data.id) throw new Error('ID de otimização não retornado');
        
        const optId = data.id;
        
        let completed = false;
        while (!completed) {
            await this.sleep(1000);
            
            const statusRes = await fetch(`/api/optimize/${optId}/status`);
            const state = await statusRes.json();
            
            msg.textContent = state.message;
            const pct = Math.round(state.progress);
            progress.textContent = `${pct}%`;
            progressFill.style.width = `${pct}%`;
            
            if (state.status === 'completed') {
                completed = true;
                if (state.result && state.result.optimized_length) {
                    this.state.length = state.result.optimized_length;
                    
                    const inputLen = document.getElementById('input-length');
                    const autoLen = document.getElementById('auto-length');
                    
                    if (inputLen) {
                        inputLen.value = this.state.length.toFixed(4);
                        inputLen.disabled = false;
                    }
                    if (autoLen) {
                        autoLen.checked = false;
                    }
                    
                    this.createAntenna();
                    this.showToast(`Otimizado! Novo comprimento: ${this.state.length.toFixed(4)}m (VSWR: ${state.result.final_vswr.toFixed(2)})`, 'success');
                }
            } else if (state.status === 'error') {
                throw new Error(state.message);
            }
        }
    } catch (error) {
        console.error('Erro na otimização:', error);
        this.showToast('Erro na otimização: ' + error.message, 'error');
        msg.textContent = 'Erro: ' + error.message;
    } finally {
        btn.disabled = false;
        if (!msg.textContent.includes('Erro')) {
            setTimeout(() => status.classList.add('hidden'), 5000);
        }
    }
};

IloveAntenas.prototype.calculateMatching = async function() {
    if (!this.data.smith) {
        this.showToast('Sem dados de impedância', 'error');
        return;
    }

    const smith = this.data.smith;
    const centerIdx = Math.floor(smith.resistance.length / 2);
    const R = smith.resistance[centerIdx];
    const X = smith.reactance[centerIdx];
    const f = this.state.frequency;
    const Z0 = 50;

    const modal = document.getElementById('matching-overlay');
    modal.classList.remove('hidden');

    document.getElementById('match-z-load').textContent = `${R.toFixed(1)} ${X >= 0 ? '+' : ''}${X.toFixed(1)}j Ω`;
    document.getElementById('match-freq').textContent = `${(f/1e6).toFixed(1)} MHz`;

    const networkSelect = document.getElementById('match-network-type');
    const qInput = document.getElementById('match-q');
    const networkType = networkSelect ? networkSelect.value : 'L';
    const qValue = qInput && qInput.value !== '' ? parseFloat(qInput.value) : null;

    try {
        const response = await fetch('/api/matching', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                z_load_re: R,
                z_load_im: X,
                z0: Z0,
                frequency: f,
                network_type: networkType,
                q: qValue
            })
        });
        const result = await response.json();
        if (!result.success) {
            this.showToast('Erro no cálculo de casamento: ' + result.error, 'error');
            return;
        }

        const data = result.data;
        const components = data.components || [];
        const stub = data.stub || null;
        const qUsed = data.q_used;
        const notes = data.notes;

        const qRow = document.getElementById('row-match-q');
        const qVal = document.getElementById('match-q-val');
        const notesEl = document.getElementById('match-notes');

        if (qUsed !== null && qUsed !== undefined) {
            if (qRow) {
                qRow.classList.remove('hidden');
                qVal.textContent = qUsed.toFixed(2);
            }
        } else {
            if (qRow) qRow.classList.add('hidden');
        }

        if (notes && notes.length > 0) {
            if (notesEl) {
                notesEl.textContent = notes.join('; ');
                notesEl.classList.remove('hidden');
            }
        } else {
            if (notesEl) notesEl.classList.add('hidden');
        }

        const formatVal = (v, u) => {
            if (u === 'H') {
                if (v < 1e-6) return (v * 1e9).toFixed(1) + ' nH';
                return (v * 1e6).toFixed(1) + ' uH';
            } else {
                if (v < 1e-9) return (v * 1e12).toFixed(1) + ' pF';
                return (v * 1e9).toFixed(1) + ' nF';
            }
        };

        let series = components.find(c => c.role === 'series' || c.role === 'series_center' || c.role === 'series_source');
        let shunt = components.find(c => c.role === 'shunt_source' || c.role === 'shunt_load' || c.role === 'shunt_center');

        const seriesLabel = document.getElementById('comp-series');
        const shuntLabel = document.getElementById('comp-shunt');

        if (series) {
            const seriesType = series.kind === 'L' ? 'Indutor (Série)' : 'Capacitor (Série)';
            seriesLabel.textContent = seriesType;
            document.getElementById('match-val-series').textContent = formatVal(Math.abs(series.value), series.unit);
        } else {
            seriesLabel.textContent = '--';
            document.getElementById('match-val-series').textContent = '--';
        }

        if (shunt) {
            let label = 'Componente Paralelo';
            if (shunt.role === 'shunt_source') label = 'Paralelo @ Fonte';
            if (shunt.role === 'shunt_load') label = 'Paralelo @ Carga';
            if (shunt.role === 'shunt_center') label = 'Paralelo Central';
            shuntLabel.textContent = label;
            document.getElementById('match-val-shunt').textContent = formatVal(Math.abs(shunt.value), shunt.unit);
        } else {
            shuntLabel.textContent = '--';
            document.getElementById('match-val-shunt').textContent = '--';
        }

        const stubShortEl = document.getElementById('match-stub-short');
        const stubOpenEl = document.getElementById('match-stub-open');
        if (stub && typeof stub.short_lambda === 'number') {
            stubShortEl.textContent = stub.short_lambda.toFixed(3);
        } else {
            stubShortEl.textContent = '--';
        }
        if (stub && typeof stub.open_lambda === 'number') {
            stubOpenEl.textContent = stub.open_lambda.toFixed(3);
        } else {
            stubOpenEl.textContent = '--';
        }
    } catch (e) {
        console.error(e);
        this.showToast('Erro de conexão no cálculo de casamento', 'error');
        document.getElementById('match-val-series').textContent = "Erro";
        document.getElementById('match-val-shunt').textContent = "Erro";
    }
};
