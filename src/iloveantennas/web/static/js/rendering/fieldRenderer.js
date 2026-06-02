(function() {
if (window.FieldRenderer) return;
class FieldRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        
        this.ctx = this.canvas.getContext('2d');
        this.frames = [];
        this.currentFrame = 0;
        this.isPlaying = false;
        this.animationId = null;
        this.fieldShape = [0, 0];
        this.playbackSpeed = 1;
        this.scaleMode = 'linear';
        this.intensityScale = 1.0;
        this.dbRange = 40;
        
        this.colormap = this.generateColormap();
    }
    
    generateColormap() {
        const colors = [];
        for (let i = 0; i < 256; i++) {
            const t = i / 255;
            const c1 = { r: 0.02, g: 0.02, b: 0.25 };
            const c2 = { r: 0.0, g: 0.7, b: 1.0 };
            const c3 = { r: 0.0, g: 1.0, b: 0.2 };
            const c4 = { r: 1.0, g: 1.0, b: 0.0 };
            const c5 = { r: 1.0, g: 0.0, b: 0.0 };
            let r, g, b;
            if (t < 0.25) {
                const u = t / 0.25;
                r = c1.r + (c2.r - c1.r) * u;
                g = c1.g + (c2.g - c1.g) * u;
                b = c1.b + (c2.b - c1.b) * u;
            } else if (t < 0.5) {
                const u = (t - 0.25) / 0.25;
                r = c2.r + (c3.r - c2.r) * u;
                g = c2.g + (c3.g - c2.g) * u;
                b = c2.b + (c3.b - c2.b) * u;
            } else if (t < 0.75) {
                const u = (t - 0.5) / 0.25;
                r = c3.r + (c4.r - c3.r) * u;
                g = c3.g + (c4.g - c3.g) * u;
                b = c3.b + (c4.b - c3.b) * u;
            } else {
                const u = (t - 0.75) / 0.25;
                r = c4.r + (c5.r - c4.r) * u;
                g = c4.g + (c5.g - c4.g) * u;
                b = c4.b + (c5.b - c4.b) * u;
            }
            r = Math.round(255 * r);
            g = Math.round(255 * g);
            b = Math.round(255 * b);
            colors.push([r, g, b]);
        }
        return colors;
    }
    
    setFrames(frames, fieldShape) {
        this.frames = frames || [];
        this.fieldShape = fieldShape || [0, 0];
        this.currentFrame = 0;
        if (this.frames.length > 0) this.renderFrame(0);
    }
    
    renderFrame(idx) {
        if (idx < 0 || idx >= this.frames.length) return;
        
        const frame = this.frames[idx];
        
        if (this.onFrameUpdate) {
            this.onFrameUpdate(frame);
        }
        
        const field = frame.field;
        const [nx, nz] = this.fieldShape;
        
        const width = this.canvas.width;
        const height = this.canvas.height;
        const imageData = this.ctx.createImageData(width, height);
        const data = imageData.data;
        
        const cellW = width / nx;
        const cellH = height / nz;
        
        for (let py = 0; py < height; py++) {
            for (let px = 0; px < width; px++) {
                const gx = (px + 0.5) / cellW - 0.5;
                const gz = (height - 1 - py + 0.5) / cellH - 0.5;
                const i0 = Math.floor(gx);
                const j0 = Math.floor(gz);
                const tx = gx - i0;
                const tz = gz - j0;
                
                if (i0 >= 0 && i0 < nx - 1 && j0 >= 0 && j0 < nz - 1) {
                    const s00 = field[i0] ? (field[i0][j0] || 0) : 0;
                    const s10 = field[i0 + 1] ? (field[i0 + 1][j0] || 0) : 0;
                    const s01 = field[i0] ? (field[i0][j0 + 1] || 0) : 0;
                    const s11 = field[i0 + 1] ? (field[i0 + 1][j0 + 1] || 0) : 0;
                    const raw = 
                        s00 * (1 - tx) * (1 - tz) +
                        s10 * tx * (1 - tz) +
                        s01 * (1 - tx) * tz +
                        s11 * tx * tz;
                    const mag = Math.abs(raw);
                    let norm;
                    if (this.scaleMode === 'db') {
                        const m = Math.max(mag, 1e-6);
                        const db = 20 * Math.log10(m);
                        norm = 1 + db / this.dbRange;
                    } else {
                        norm = mag * this.intensityScale;
                    }
                    const t = Math.max(0, Math.min(1, norm));
                    const colorIdx = Math.floor(t * 255);
                    const [r, g, b] = this.colormap[colorIdx];
                    const idx = (py * width + px) * 4;
                    data[idx] = r;
                    data[idx + 1] = g;
                    data[idx + 2] = b;
                    data[idx + 3] = 255;
                }
            }
        }
        
        this.ctx.putImageData(imageData, 0, 0);
        
        const timeEl = document.getElementById('animation-time');
        if (timeEl) timeEl.textContent = `${frame.time_ns.toFixed(2)} ns`;
        
        const slider = document.getElementById('animation-slider');
        if (slider && this.frames.length > 1) {
            slider.value = (idx / (this.frames.length - 1)) * 100;
        }
    }
    
    setScaleMode(mode) {
        this.scaleMode = mode === 'db' ? 'db' : 'linear';
        if (this.frames.length) this.renderFrame(this.currentFrame);
    }
    
    setIntensityScale(scale) {
        this.intensityScale = Math.max(0.1, Math.min(5, scale || 1));
        if (this.frames.length) this.renderFrame(this.currentFrame);
    }
    
    play() {
        if (!this.frames.length) return;
        this.isPlaying = true;
        this.animate();
        this.updateButton(true);
    }
    
    pause() {
        this.isPlaying = false;
        if (this.animationId) {
            clearTimeout(this.animationId);
            this.animationId = null;
        }
        this.updateButton(false);
    }
    
    toggle() {
        this.isPlaying ? this.pause() : this.play();
    }
    
    animate() {
        if (!this.isPlaying) return;
        this.renderFrame(this.currentFrame);
        this.currentFrame = (this.currentFrame + 1) % this.frames.length;
        this.animationId = setTimeout(() => this.animate(), 50 / this.playbackSpeed);
    }
    
    seekTo(pct) {
        this.currentFrame = Math.floor((pct / 100) * (this.frames.length - 1));
        this.renderFrame(this.currentFrame);
    }
    
    setSpeed(speed) {
        this.playbackSpeed = Math.max(0.25, Math.min(4, speed));
    }
    
    reset() {
        this.pause();
        this.currentFrame = 0;
        if (this.frames.length) this.renderFrame(0);
    }
    
    updateButton(playing) {
        const btn = document.getElementById('btn-play-pause');
        if (btn) btn.innerHTML = playing ? '<i class="fas fa-pause"></i>' : '<i class="fas fa-play"></i>';
    }
}

window.FieldRenderer = FieldRenderer;
})(); 
