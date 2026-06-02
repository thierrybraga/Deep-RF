ChartManager.prototype.initSmithChart = function(canvasId = 'chart-smith') {
    this.smithCanvas = document.getElementById(canvasId);
    if (!this.smithCanvas) {
        console.error(`❌ ChartManager: Canvas "${canvasId}" não encontrado!`);
        return;
    }
    
    this.smithCtx = this.smithCanvas.getContext('2d');
    if (!this.smithCtx) {
        console.error(`❌ ChartManager: Contexto 2D para "${canvasId}" falhou!`);
        return;
    }
    this.drawSmithGrid();
};

ChartManager.prototype.drawSmithGrid = function() {
    const canvas = this.smithCanvas;
    const ctx = this.smithCtx;
    
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) / 2 - 22;
    
    ctx.fillStyle = this.colors.background;
    ctx.fillRect(0, 0, w, h);
    
    ctx.strokeStyle = 'rgba(100, 116, 139, 0.25)';
    ctx.lineWidth = 0.6;
    
    [0, 0.2, 0.5, 1, 2, 5].forEach(r => {
        const cr = Math.max(1, radius / (1 + r));
        const ccx = cx + (r / (1 + r)) * radius;
        if (cr > 0 && !isNaN(cr)) {
            ctx.beginPath();
            ctx.arc(ccx, cy, cr, 0, Math.PI * 2);
            ctx.stroke();
        }
    });
    
    [0.2, 0.5, 1, 2, 5].forEach(x => {
        const ar = radius / x;
        ctx.beginPath();
        const startPos = Math.PI + Math.asin(Math.min(1, 1 / x));
        ctx.arc(cx + radius, cy - ar, ar, startPos, Math.PI * 1.5);
        ctx.stroke();
        ctx.beginPath();
        const endNeg = Math.PI - Math.asin(Math.min(1, 1 / x));
        ctx.arc(cx + radius, cy + ar, ar, Math.PI * 0.5, endNeg);
        ctx.stroke();
    });
    
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.6)';
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.stroke();
    
    ctx.beginPath();
    ctx.moveTo(cx - radius, cy);
    ctx.lineTo(cx + radius, cy);
    ctx.stroke();

    ctx.fillStyle = this.colors.text;
    ctx.font = '11px Inter';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('Z=0', cx, cy - radius - 12);
    ctx.fillText('Z=∞', cx + radius + 20, cy);
    ctx.fillText('Re=0', cx - radius - 20, cy);
    ctx.fillText('Im=j0', cx, cy + radius + 16);
    
    ctx.fillStyle = this.colors.success;
    ctx.beginPath();
    ctx.arc(cx, cy, 4, 0, Math.PI * 2);
    ctx.fill();
    
    this.smithDims = { cx, cy, radius };
};

ChartManager.prototype.updateSmithChart = function(data) {
    if (!this.smithCtx || !data) return;
    
    this.currentData.smith = data;
    this.drawSmithGrid();
    
    const ctx = this.smithCtx;
    const { cx, cy, radius } = this.smithDims;
    
    if (!Array.isArray(data.gamma_real) || !Array.isArray(data.gamma_imag)) {
        return;
    }

    ctx.strokeStyle = this.colors.primary;
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    let first = true;
    for (let i = 0; i < data.gamma_real.length; i++) {
        const x = cx + data.gamma_real[i] * radius;
        const y = cy - data.gamma_imag[i] * radius;
        if (first) {
            ctx.moveTo(x, y);
            first = false;
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.stroke();

    const stylePoint = (x, y, color, radiusPx, label) => {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, radiusPx, 0, Math.PI * 2);
        ctx.fill();
        if (label) {
            ctx.fillStyle = this.colors.text;
            ctx.font = '10px Inter';
            ctx.textAlign = 'left';
            ctx.textBaseline = 'top';
            ctx.fillText(label, x + 6, y + 6);
        }
    };

    if (data.gamma_real.length > 0) {
        stylePoint(
            cx + data.gamma_real[0] * radius,
            cy - data.gamma_imag[0] * radius,
            this.colors.success,
            5,
            'Start'
        );

        const last = data.gamma_real.length - 1;
        stylePoint(
            cx + data.gamma_real[last] * radius,
            cy - data.gamma_imag[last] * radius,
            this.colors.error,
            5,
            'End'
        );
    }

    const annotateFreqPoint = (freq, color, text) => {
        if (!freq || !data.frequencies_mhz) return;
        const idx = data.frequencies_mhz.findIndex(f => Math.abs(f - freq) < 2);
        if (idx < 0) return;
        const x = cx + data.gamma_real[idx] * radius;
        const y = cy - data.gamma_imag[idx] * radius;
        stylePoint(x, y, color, 6, text + ` ${freq.toFixed(0)} MHz`);
    };

    if (data.resonance) {
        annotateFreqPoint(data.resonance.frequency_mhz, this.colors.warning, 'Resonance');
    }
    if (data.best_match) {
        annotateFreqPoint(data.best_match.frequency_mhz, this.colors.secondary, 'Best Match');
    }

    if (data.bandwidth && data.frequencies_mhz) {
        const bwMin = data.bandwidth.min_mhz;
        const bwMax = data.bandwidth.max_mhz;
        [
            { freq: bwMin, label: '-10 dB' },
            { freq: bwMax, label: '-10 dB' }
        ].forEach(point => {
            const idx = data.frequencies_mhz.findIndex(f => Math.abs(f - point.freq) < 2);
            if (idx >= 0) {
                const x = cx + data.gamma_real[idx] * radius;
                const y = cy - data.gamma_imag[idx] * radius;
                stylePoint(x, y, '#e5e7eb', 4, point.label);
            }
        });
    }

    const vswrs = [1.5, 2, 3];
    ctx.setLineDash([4, 4]);
    vswrs.forEach((s, idx) => {
        const rGamma = ((s - 1) / (s + 1)) * radius;
        ctx.strokeStyle = idx === 1 ? this.colors.success : 'rgba(148, 163, 184, 0.5)';
        ctx.lineWidth = idx === 1 ? 1.3 : 0.9;
        ctx.beginPath();
        ctx.arc(cx, cy, rGamma, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = '#e5e7eb';
        ctx.font = '9px Inter';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(`VSWR=${s.toFixed(1)}`, cx + rGamma + 6, cy - 6 - idx * 14);
        ctx.setLineDash([4, 4]);
    });
    ctx.setLineDash([]);
};

ChartManager.prototype.createExpandedSmith = function(canvas, data) {
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) / 2 - 40;
    
    ctx.fillStyle = this.colors.background;
    ctx.fillRect(0, 0, w, h);
    
    ctx.strokeStyle = 'rgba(100, 116, 139, 0.3)';
    ctx.lineWidth = 1;
    
    [0, 0.2, 0.5, 1, 2, 5].forEach(r => {
        const cr = radius / (1 + r);
        const ccx = cx + (r / (1 + r)) * radius;
        ctx.beginPath();
        ctx.arc(ccx, cy, cr, 0, Math.PI * 2);
        ctx.stroke();
        
        ctx.fillStyle = '#64748b';
        ctx.font = '11px Inter';
        ctx.fillText(r.toString(), ccx + cr + 4, cy + 4);
    });
    
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.6)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.stroke();
    
    ctx.beginPath();
    ctx.moveTo(cx - radius, cy);
    ctx.lineTo(cx + radius, cy);
    ctx.stroke();
    
    if (data.gamma_real) {
        ctx.strokeStyle = this.colors.primary;
        ctx.lineWidth = 3;
        ctx.beginPath();
        
        let first = true;
        for (let i = 0; i < data.gamma_real.length; i++) {
            const x = cx + data.gamma_real[i] * radius;
            const y = cy - data.gamma_imag[i] * radius;
            first ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            first = false;
        }
        ctx.stroke();
        
        const firstX = cx + data.gamma_real[0] * radius;
        const firstY = cy - data.gamma_imag[0] * radius;
        ctx.fillStyle = this.colors.success;
        ctx.beginPath();
        ctx.arc(firstX, firstY, 5, 0, Math.PI * 2);
        ctx.fill();
        
        const last = data.gamma_real.length - 1;
        const lastX = cx + data.gamma_real[last] * radius;
        const lastY = cy - data.gamma_imag[last] * radius;
        ctx.fillStyle = this.colors.error;
        ctx.beginPath();
        ctx.arc(lastX, lastY, 5, 0, Math.PI * 2);
        ctx.fill();
        
        if (data.resonance) {
            const resFreq = data.resonance.frequency_mhz;
            const idx = data.frequencies_mhz.findIndex(f => Math.abs(f - resFreq) < 2);
            if (idx >= 0) {
                const x = cx + data.gamma_real[idx] * radius;
                const y = cy - data.gamma_imag[idx] * radius;
                ctx.fillStyle = this.colors.warning;
                ctx.beginPath();
                ctx.arc(x, y, 7, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }
    
    ctx.fillStyle = this.colors.success;
    ctx.beginPath();
    ctx.arc(cx, cy, 6, 0, Math.PI * 2);
    ctx.fill();
    
    const vswrs = [1.5, 2, 3];
    ctx.setLineDash([4, 4]);
    vswrs.forEach((s, idx) => {
        const rGamma = ((s - 1) / (s + 1)) * radius;
        ctx.strokeStyle = idx === 1 ? this.colors.success : 'rgba(148, 163, 184, 0.5)';
        ctx.lineWidth = idx === 1 ? 1.2 : 0.8;
        ctx.beginPath();
        ctx.arc(cx, cy, rGamma, 0, Math.PI * 2);
        ctx.stroke();
    });
    ctx.setLineDash([]);
    
    ctx.fillStyle = '#e5e7eb';
    ctx.font = '11px Inter';
    let ty = 24;
    if (data.z0) {
        ctx.fillText(`Z0 = ${data.z0.toFixed ? data.z0.toFixed(1) : data.z0} Ω`, 16, ty);
        ty += 14;
    }
    if (data.resonance) {
        ctx.fillText(`fc ≈ ${data.resonance.frequency_mhz.toFixed(1)} MHz`, 16, ty);
        ty += 14;
        ctx.fillText(`Zin(fc) = ${data.resonance.impedance} Ω`, 16, ty);
        ty += 14;
        ctx.fillText(`S11(fc) = ${data.resonance.s11_db.toFixed(1)} dB`, 16, ty);
        ty += 14;
        ctx.fillText(`VSWR(fc) = ${data.resonance.vswr.toFixed(2)}`, 16, ty);
        ty += 14;
    }
    if (data.bandwidth) {
        ctx.fillText(`BW(-10 dB) = ${data.bandwidth.width_mhz.toFixed(1)} MHz`, 16, ty);
        ty += 14;
        ctx.fillText(`Faixa: ${data.bandwidth.min_mhz.toFixed(0)}–${data.bandwidth.max_mhz.toFixed(0)} MHz`, 16, ty);
    }
};

