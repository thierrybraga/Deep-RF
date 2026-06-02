/**
 * IloveAntenas - Aplicação Principal
 * Gerenciamento de estado, API e interações
 */

class IloveAntenas {
    constructor() {
        this.state = {
            antennaType: 'dipole',
            frequency: 300e6,
            length: null,
            radius: 0.001,
            numDirectors: 3,
            substrateEr: 4.4,
            turns: 5,
            loopRadius: null,
            
            // Horn
            hornWidth: null,
            hornHeight: null,
            hornLength: null,
            
            // Dish
            dishDiameter: null,
            dishFocal: null,
            
            // LPDA
            lpdaTau: 0.86,
            lpdaSigma: 0.15,

            // Biquad
            biquadSide: null,
            biquadReflector: null,

            // Discone
            disconeDiscRadius: null,
            disconeConeRadius: null,
            disconeConeHeight: null,
            
            cellsPerWavelength: 20,
            numSteps: 200,
            sourceType: 'gaussian',
            courant: 0.99,
            pmlLayers: 8,
            useOptimized: true,
            
            isDarkMode: true,
            simulationId: null
        };
        
        this.data = {
            antenna: null,
            smith: null,
            radiation: null,
            parameters: null,
            simulation: null
        };
        
        this.renderer = null;
        this.fieldRenderer = null;
        this.chartManager = null;
        
        this.init();
    }
    
    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }
    
    setup() {
        console.log('🚀 IloveAntenas iniciando...');
        
        if (typeof AntennaRenderer === 'function') {
            this.renderer = new AntennaRenderer('canvas-3d');
        } else {
            console.error('AntennaRenderer não encontrado');
        }
        
        if (typeof FieldRenderer === 'function') {
            this.fieldRenderer = new FieldRenderer('canvas-field');
        } else {
            console.error('FieldRenderer não encontrado');
        }
        
        if (typeof ChartManager === 'function') {
            this.chartManager = new ChartManager();
            this.chartManager.init();
        } else {
            console.error('ChartManager não encontrado');
        }
        
        // Connect renderers for 3D field visualization
        if (this.fieldRenderer) {
            this.fieldRenderer.onFrameUpdate = (frame) => {
                if (this.renderer) this.renderer.updateField3D(frame);
            };
        }
        
        this.bindEvents();
        this.applyTheme();
        this.switchTab('design');
        this.createAntenna();
        this.fetchAnalysis();
        
        console.log('✅ IloveAntenas pronto!');

        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/service-worker.js').catch(err => {
                console.error('Service worker registration failed', err);
            });
        }
    }
    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.state.isDarkMode ? 'dark' : 'light');
        
        const icon = document.querySelector('#btn-theme i');
        if (icon) icon.className = this.state.isDarkMode ? 'fas fa-sun' : 'fas fa-moon';
        
        if (this.renderer) this.renderer.setTheme(this.state.isDarkMode);
    }

    switchTab(tab) {
        // Active State
        document.querySelectorAll('.nav-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        
        const show = (id) => document.getElementById(id)?.classList.remove('hidden');
        const hide = (id) => document.getElementById(id)?.classList.add('hidden');
        
        // Hide all toggleable panels
        ['panel-design-types', 'panel-design-params', 'panel-simulation', 
         'charts-panel', 'panel-results-text', 'panel-animation'].forEach(hide);
         
        const viewport = document.getElementById('viewport-3d');
        const resultsPanel = document.getElementById('results-panel');
        const sidebar = document.querySelector('.sidebar');
        
        // Reset visibility defaults
        if (viewport) viewport.style.display = '';
        if (resultsPanel) resultsPanel.classList.remove('hidden');
        if (sidebar) sidebar.classList.remove('hidden');

        switch(tab) {
            case 'design':
                show('panel-design-types');
                show('panel-design-params');
                if (resultsPanel) resultsPanel.classList.add('hidden');
                break;
                
            case 'simulation':
                show('panel-simulation');
                show('panel-animation');
                break;
                
            case 'analysis':
                show('charts-panel');
                show('panel-results-text');
                if (viewport) viewport.style.display = 'none';
                if (sidebar) sidebar.classList.add('hidden');
                break;
        }
        
        // Handle Resizing
        if (tab === 'analysis') {
            setTimeout(() => this.chartManager?.resize(), 50);
        } else {
            setTimeout(() => this.renderer?.onResize(), 50);
        }
    }
    
    bindSlider(inputId, valueId, onInput, onChange) {
        const input = document.getElementById(inputId);
        const value = document.getElementById(valueId);
        
        if (input) {
            input.addEventListener('input', (e) => {
                if (value) value.textContent = e.target.value;
                if (onInput) onInput(e.target.value);
            });
            
            if (onChange) {
                input.addEventListener('change', onChange);
            }
        }
    }

    setAntennaType(type) {
        this.state.antennaType = type;
        
        document.querySelectorAll('.antenna-type-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === type);
        });
        
        const groups = {
            length: ['dipole', 'v_dipole', 'folded_dipole', 'monopole'],
            radius: ['dipole', 'v_dipole', 'folded_dipole', 'monopole', 'yagi', 'helix', 'loop'],
            directors: ['yagi'],
            substrate: ['patch'],
            turns: ['helix'],
            horn: ['horn'],
            dish: ['dish'],
            lpda: ['lpda'],
            loop: ['loop'],
            biquad: ['biquad'],
            discone: ['discone']
        };
        
        Object.entries(groups).forEach(([group, types]) => {
            const el = document.getElementById(`group-${group}`);
            if (el) el.classList.toggle('hidden', !types.includes(type));
        });
        
        document.getElementById('info-type').textContent = this.getTypeName(type);
        this.createAntenna();
        this.fetchAnalysis();
    }
    
    getTypeName(type) {
        return {
            dipole: 'Dipolo',
            v_dipole: 'Dipolo em V',
            folded_dipole: 'Dipolo Dobrado',
            monopole: 'Monopolo',
            yagi: 'Yagi-Uda',
            patch: 'Patch',
            helix: 'Helicoidal',
            horn: 'Corneta',
            dish: 'Parabólica',
            lpda: 'Log-Periódica',
            loop: 'Loop',
            biquad: 'Biquad',
            discone: 'Discone'
        }[type] || type;
    }
    
    updateWavelength() {
        const wavelength = 299792458 / this.state.frequency;
        document.getElementById('calc-wavelength').textContent = `λ = ${(wavelength * 100).toFixed(2)} cm`;
        document.getElementById('info-freq').textContent = `${(this.state.frequency / 1e6).toFixed(0)} MHz`;
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const icons = {
            success: 'fa-check-circle',
            warning: 'fa-exclamation-triangle',
            error: 'fa-times-circle',
            info: 'fa-info-circle'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="toast-icon fas ${icons[type] || icons.info}"></i>
            <span class="toast-message">${message}</span>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    loadAntennaToSimulation(antenna) {
        if (!antenna || !antenna.config) return;
        
        const c = antenna.config;
        this.setAntennaType(c.type);
        
        // Map config back to state
        if (c.frequency) this.state.frequency = c.frequency;
        if (c.length) this.state.length = c.length;
        if (c.radius) this.state.radius = c.radius;
        if (c.num_directors) this.state.numDirectors = c.num_directors;
        if (c.substrate_er) this.state.substrateEr = c.substrate_er;
        if (c.turns) this.state.turns = c.turns;
        
        // Horn
        if (c.aperture_width) this.state.hornWidth = c.aperture_width;
        if (c.aperture_height) this.state.hornHeight = c.aperture_height;
        if (c.flare_length) this.state.hornLength = c.flare_length;
        
        // Dish
        if (c.dish_diameter) this.state.dishDiameter = c.dish_diameter;
        if (c.focal_length) this.state.dishFocal = c.focal_length;
        
        // LPDA
        if (c.tau) this.state.lpdaTau = c.tau;
        if (c.sigma) this.state.lpdaSigma = c.sigma;
        
        // Loop
        if (c.loop_radius) this.state.loopRadius = c.loop_radius;

        // Biquad
        if (c.side_length) this.state.biquadSide = c.side_length;
        if (c.reflector_distance) this.state.biquadReflector = c.reflector_distance;

        // Discone
        if (c.disc_radius) this.state.disconeDiscRadius = c.disc_radius;
        if (c.cone_radius) this.state.disconeConeRadius = c.cone_radius;
        if (c.cone_height) this.state.disconeConeHeight = c.cone_height;

        // Update UI inputs
        this.updateUIFromState();
        
        // Close library
        this.closeLibrary();
        
        // Trigger creation
        this.createAntenna();
        this.showToast(`Antena "${antenna.name}" carregada!`, 'success');
    }

    updateUIFromState() {
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.value = val;
        };
        
        setVal('input-frequency', this.state.frequency / 1e6);
        setVal('input-length', this.state.length || '');
        setVal('input-radius', this.state.radius * 1000); // mm
        setVal('input-directors', this.state.numDirectors);
        setVal('input-substrate', this.state.substrateEr);
        setVal('input-turns', this.state.turns);
        
        setVal('input-horn-width', this.state.hornWidth || '');
        setVal('input-horn-height', this.state.hornHeight || '');
        setVal('input-horn-length', this.state.hornLength || '');

        setVal('input-dish-diameter', this.state.dishDiameter || '');
        setVal('input-dish-focal', this.state.dishFocal || '');

        setVal('input-lpda-tau', this.state.lpdaTau || '');
        setVal('input-lpda-sigma', this.state.lpdaSigma || '');

        setVal('input-loop-radius', this.state.loopRadius || '');

        setVal('input-biquad-side', this.state.biquadSide || '');
        setVal('input-biquad-reflector', this.state.biquadReflector || '');

        setVal('input-discone-disc', this.state.disconeDiscRadius || '');
        setVal('input-discone-cone', this.state.disconeConeRadius || '');
        setVal('input-discone-height', this.state.disconeConeHeight || '');
    }
}

IloveAntenas.prototype.fetchAnalysis = async function() {
    if (!this.chartManager) {
        console.error('ChartManager não inicializado');
        return;
    }
    
    const payload = {
        type: this.state.antennaType,
        frequency: this.state.frequency,
        length: this.state.length,
        radius: this.state.radius,
        num_directors: this.state.numDirectors,
        substrate_er: this.state.substrateEr,
        substrate_h: 1.6e-3,
        turns: this.state.turns,
        aperture_width: this.state.hornWidth,
        aperture_height: this.state.hornHeight,
        flare_length: this.state.hornLength,
        dish_diameter: this.state.dishDiameter,
        focal_length: this.state.dishFocal,
        tau: this.state.lpdaTau,
        sigma: this.state.lpdaSigma,
        loop_radius: this.state.loopRadius,
        side_length: this.state.biquadSide,
        reflector_distance: this.state.biquadReflector,
        disc_radius: this.state.disconeDiscRadius,
        cone_radius: this.state.disconeConeRadius,
        cone_height: this.state.disconeConeHeight
    };
    
    try {
        const [smithRes, radRes] = await Promise.all([
            fetch('/api/smith-chart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            }),
            fetch('/api/radiation-pattern', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
        ]);
        
        const smithJson = await smithRes.json();
        const radJson = await radRes.json();
        
        if (!smithJson.success) {
            console.error('Erro Smith:', smithJson.error);
            this.showToast('Erro ao calcular Carta de Smith', 'error');
            return;
        }
        if (!radJson.success) {
            console.error('Erro Radiação:', radJson.error);
            this.showToast('Erro ao calcular diagrama de radiação', 'error');
            return;
        }
        
        this.data.smith = smithJson.data;
        this.data.radiation = radJson.data;
        
        this.chartManager.updateAll(this.data.smith, this.data.radiation);
        this.updateResultsFromSmith();
        this.updateResultsFromRadiation();
    } catch (err) {
        console.error('Erro em fetchAnalysis:', err);
        this.showToast('Falha na análise da antena', 'error');
    }
};

IloveAntenas.prototype.createAntenna = async function() {
        if (!this.renderer) {
            console.error('AntennaRenderer não inicializado');
            return;
        }
        
        const payload = {
            type: this.state.antennaType,
            frequency: this.state.frequency,
            length: this.state.length,
            radius: this.state.radius,
            num_directors: this.state.numDirectors,
            substrate_er: this.state.substrateEr,
            substrate_h: this.state.substrateEr ? 1.6e-3 : 1.6e-3,
            turns: this.state.turns,
            aperture_width: this.state.hornWidth,
            aperture_height: this.state.hornHeight,
            flare_length: this.state.hornLength,
            dish_diameter: this.state.dishDiameter,
            focal_length: this.state.dishFocal,
            tau: this.state.lpdaTau,
            sigma: this.state.lpdaSigma,
            loop_radius: this.state.loopRadius,
            side_length: this.state.biquadSide,
            reflector_distance: this.state.biquadReflector,
            disc_radius: this.state.disconeDiscRadius,
            cone_radius: this.state.disconeConeRadius,
            cone_height: this.state.disconeConeHeight
        };
        
        try {
            const res = await fetch('/api/antenna/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const json = await res.json();
            if (!json.success) {
                console.error('Erro ao criar antena:', json.error);
                this.showToast('Erro ao criar antena: ' + json.error, 'error');
                return;
            }
            
            const data = json.data;
            this.data.antenna = data;
            this.renderer.renderAntenna(data);
            this.updateInfoPanel();
        } catch (err) {
            console.error('Erro na requisição /api/antenna/create:', err);
            this.showToast('Falha na comunicação com o backend', 'error');
        }
    };
