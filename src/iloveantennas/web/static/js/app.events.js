/**
 * IloveAntenas - Eventos e interação de UI
 */

IloveAntenas.prototype.bindEvents = function() {
    document.getElementById('btn-open-library')?.addEventListener('click', () => this.openLibrary());
    document.getElementById('btn-close-library')?.addEventListener('click', () => this.closeLibrary());
    document.getElementById('btn-new-antenna')?.addEventListener('click', () => this.openEditor(null));
    document.getElementById('library-search')?.addEventListener('input', (e) => this.filterLibrary(e.target.value));

    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;
            if (['design', 'simulation', 'analysis'].includes(target)) {
                this.switchTab(target);
            }
        });
    });

    const canvas3d = document.getElementById('canvas-3d');
    if (canvas3d) {
        canvas3d.addEventListener('antenna-click', () => {
            this.showToast('Atualizando análise da antena...', 'info');
            this.fetchAnalysis();
        });
    }

    document.querySelectorAll('.antenna-type-btn').forEach(btn => {
        btn.addEventListener('click', () => this.setAntennaType(btn.dataset.type));
    });

    const freqInput = document.getElementById('input-frequency');
    if (freqInput) {
        freqInput.addEventListener('change', (e) => {
            this.state.frequency = parseFloat(e.target.value) * 1e6;
            this.updateWavelength();
            this.createAntenna();
        });
    }

    const autoLength = document.getElementById('auto-length');
    if (autoLength) {
        autoLength.addEventListener('change', (e) => {
            const lengthInput = document.getElementById('input-length');
            if (lengthInput) {
                lengthInput.disabled = e.target.checked;
                if (e.target.checked) {
                    this.state.length = null;
                    this.createAntenna();
                }
            }
        });
    }

    const lengthInput = document.getElementById('input-length');
    if (lengthInput) {
        lengthInput.addEventListener('change', (e) => {
            this.state.length = parseFloat(e.target.value) || null;
            this.createAntenna();
        });
    }

    document.getElementById('btn-optimize')?.addEventListener('click', () => this.optimizeLength());

    const radiusInput = document.getElementById('input-radius');
    if (radiusInput) {
        radiusInput.addEventListener('change', (e) => {
            this.state.radius = parseFloat(e.target.value) / 1000;
            this.createAntenna();
        });
    }

    this.bindSlider('input-directors', 'directors-value', (val) => {
        this.state.numDirectors = parseInt(val);
    }, () => this.createAntenna());

    this.bindSlider('input-turns', 'turns-value', (val) => {
        this.state.turns = parseInt(val);
    }, () => this.createAntenna());

    ['input-horn-width', 'input-horn-height', 'input-horn-length'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', (e) => {
            let prop;
            if (id === 'input-horn-width') prop = 'hornWidth';
            else if (id === 'input-horn-height') prop = 'hornHeight';
            else prop = 'hornLength';
            this.state[prop] = parseFloat(e.target.value) || null;
            this.createAntenna();
        });
    });

    ['input-dish-diameter', 'input-dish-focal'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', (e) => {
            const prop = id === 'input-dish-diameter' ? 'dishDiameter' : 'dishFocal';
            this.state[prop] = parseFloat(e.target.value) || null;
            this.createAntenna();
        });
    });

    ['input-lpda-tau', 'input-lpda-sigma'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', (e) => {
            const prop = id === 'input-lpda-tau' ? 'lpdaTau' : 'lpdaSigma';
            this.state[prop] = parseFloat(e.target.value);
            this.createAntenna();
        });
    });

    const loopRadiusInput = document.getElementById('input-loop-radius');
    if (loopRadiusInput) {
        loopRadiusInput.addEventListener('change', (e) => {
            this.state.loopRadius = parseFloat(e.target.value) || null;
            this.createAntenna();
        });
    }

    ['input-biquad-side', 'input-biquad-reflector'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', (e) => {
            const prop = id === 'input-biquad-side' ? 'biquadSide' : 'biquadReflector';
            this.state[prop] = parseFloat(e.target.value) || null;
            this.createAntenna();
        });
    });

    ['input-discone-disc', 'input-discone-cone', 'input-discone-height'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', (e) => {
            let prop;
            if (id === 'input-discone-disc') prop = 'disconeDiscRadius';
            else if (id === 'input-discone-cone') prop = 'disconeConeRadius';
            else prop = 'disconeConeHeight';
            this.state[prop] = parseFloat(e.target.value) || null;
            this.createAntenna();
        });
    });

    this.bindSlider('input-resolution', 'resolution-value', (val) => {
        this.state.cellsPerWavelength = parseInt(val);
    });

    this.bindSlider('input-steps', 'steps-value', (val) => {
        this.state.numSteps = parseInt(val);
    });

    const qualitySelect = document.getElementById('input-sim-quality');
    if (qualitySelect) {
        qualitySelect.addEventListener('change', (e) => {
            const value = e.target.value;
            if (value === 'fast') {
                this.state.cellsPerWavelength = 10;
                this.state.numSteps = 150;
                this.state.pmlLayers = 6;
                this.state.courant = 0.99;
            } else if (value === 'balanced') {
                this.state.cellsPerWavelength = 20;
                this.state.numSteps = 200;
                this.state.pmlLayers = 8;
                this.state.courant = 0.99;
            } else if (value === 'high') {
                this.state.cellsPerWavelength = 30;
                this.state.numSteps = 350;
                this.state.pmlLayers = 10;
                this.state.courant = 0.98;
            }
            const resSlider = document.getElementById('input-resolution');
            const resLabel = document.getElementById('resolution-value');
            if (resSlider) {
                resSlider.value = this.state.cellsPerWavelength;
                if (resLabel) resLabel.textContent = String(this.state.cellsPerWavelength);
            }
            const stepsSlider = document.getElementById('input-steps');
            const stepsLabel = document.getElementById('steps-value');
            if (stepsSlider) {
                stepsSlider.value = this.state.numSteps;
                if (stepsLabel) stepsLabel.textContent = String(this.state.numSteps);
            }
            const courantInput = document.getElementById('setting-courant');
            const pmlInput = document.getElementById('setting-pml');
            if (courantInput) courantInput.value = this.state.courant;
            if (pmlInput) pmlInput.value = this.state.pmlLayers;
        });
    }

    const sourceType = document.getElementById('input-source-type');
    if (sourceType) {
        sourceType.addEventListener('change', (e) => {
            this.state.sourceType = e.target.value;
        });
    }

    const substrate = document.getElementById('input-substrate');
    if (substrate) {
        substrate.addEventListener('change', (e) => {
            this.state.substrateEr = parseFloat(e.target.value);
            this.createAntenna();
        });
    }

    const simBtn = document.getElementById('btn-simulate');
    if (simBtn) {
        simBtn.addEventListener('click', () => this.runSimulation());
    }

    document.getElementById('btn-reset-camera')?.addEventListener('click', () => this.renderer?.resetCamera?.());
    document.getElementById('btn-toggle-field3d')?.addEventListener('click', (e) => {
        const active = this.renderer?.toggleField3D?.();
        if (e.currentTarget && active !== undefined) e.currentTarget.classList.toggle('active', active);
    });
    document.getElementById('btn-toggle-grid')?.addEventListener('click', () => this.renderer?.toggleGrid?.());
    document.getElementById('btn-toggle-axes')?.addEventListener('click', () => this.renderer?.toggleAxes?.());
    document.getElementById('btn-toggle-radiation')?.addEventListener('click', () => this.renderer?.toggleRadiation?.());
    document.getElementById('btn-auto-rotate')?.addEventListener('click', () => this.renderer?.toggleAutoRotate?.());
    document.getElementById('btn-toggle-field-e')?.addEventListener('click', (e) => {
        if (this.renderer && typeof this.renderer.toggleField3D === 'function') {
            const active = this.renderer.toggleField3D();
            if (e.currentTarget) e.currentTarget.classList.toggle('active', active);
        }
    });
    document.getElementById('btn-toggle-field-h')?.addEventListener('click', (e) => {
        if (this.renderer && typeof this.renderer.toggleField3D === 'function') {
            const active = this.renderer.toggleField3D();
            if (e.currentTarget) e.currentTarget.classList.toggle('active', active);
        }
    });

    document.getElementById('btn-fullscreen')?.addEventListener('click', () => {
        const viewport = document.getElementById('viewport-3d');
        if (!document.fullscreenElement) {
            viewport.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    });

    document.getElementById('btn-theme')?.addEventListener('click', () => {
        this.state.isDarkMode = !this.state.isDarkMode;
        this.applyTheme();
    });

    document.getElementById('btn-help')?.addEventListener('click', () => {
        document.getElementById('help-overlay')?.classList.remove('hidden');
    });
    document.getElementById('btn-close-help')?.addEventListener('click', () => {
        document.getElementById('help-overlay')?.classList.add('hidden');
    });

    document.getElementById('btn-open-matching')?.addEventListener('click', () => this.calculateMatching());
    document.getElementById('btn-close-matching')?.addEventListener('click', () => {
        document.getElementById('matching-overlay')?.classList.add('hidden');
    });

    document.getElementById('btn-settings')?.addEventListener('click', () => {
        document.getElementById('settings-overlay')?.classList.remove('hidden');
        const courantInput = document.getElementById('setting-courant');
        const pmlInput = document.getElementById('setting-pml');
        const optimizedInput = document.getElementById('setting-optimized');
        if (courantInput) courantInput.value = this.state.courant;
        if (pmlInput) pmlInput.value = this.state.pmlLayers;
        if (optimizedInput) optimizedInput.checked = this.state.useOptimized;
    });

    document.getElementById('btn-close-settings')?.addEventListener('click', () => {
        document.getElementById('settings-overlay')?.classList.add('hidden');
    });

    document.getElementById('btn-save-settings')?.addEventListener('click', () => {
        const courantInput = document.getElementById('setting-courant');
        const pmlInput = document.getElementById('setting-pml');
        const optimizedInput = document.getElementById('setting-optimized');
        if (courantInput) this.state.courant = Math.min(parseFloat(courantInput.value), 1.0);
        if (pmlInput) this.state.pmlLayers = Math.max(parseInt(pmlInput.value), 4);
        if (optimizedInput) this.state.useOptimized = optimizedInput.checked;
        document.getElementById('settings-overlay')?.classList.add('hidden');
        this.showToast('Configurações salvas!', 'success');
    });

    document.getElementById('btn-close-modal')?.addEventListener('click', () => this.chartManager.closeModal());
    document.getElementById('modal-overlay')?.addEventListener('click', (e) => {
        if (e.target.id === 'modal-overlay') this.chartManager.closeModal();
    });

    document.getElementById('btn-expand-smith')?.addEventListener('click', () => this.chartManager.showExpanded('smith'));
    document.getElementById('btn-expand-radiation')?.addEventListener('click', () => this.chartManager.showExpanded('radiation'));
    document.getElementById('btn-expand-s11')?.addEventListener('click', () => this.chartManager.showExpanded('s11'));
    document.getElementById('btn-expand-vswr')?.addEventListener('click', () => this.chartManager.showExpanded('vswr'));
    document.getElementById('btn-expand-gain-match')?.addEventListener('click', () => this.chartManager.showExpanded('gain_match'));

    document.querySelectorAll('.results-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.results-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.results-content').forEach(c => c.classList.add('hidden'));
            tab.classList.add('active');
            document.getElementById(`results-${tab.dataset.results}`)?.classList.remove('hidden');
        });
    });

    document.getElementById('btn-play-pause')?.addEventListener('click', () => this.fieldRenderer.toggle());
    document.getElementById('animation-slider')?.addEventListener('input', (e) => {
        this.fieldRenderer.seekTo(parseFloat(e.target.value));
    });
    const fieldScaleMode = document.getElementById('field-scale-mode');
    if (fieldScaleMode) {
        fieldScaleMode.addEventListener('change', (e) => {
            this.fieldRenderer.setScaleMode(e.target.value);
        });
    }
    const fieldIntensity = document.getElementById('field-intensity');
    if (fieldIntensity) {
        fieldIntensity.addEventListener('input', (e) => {
            this.fieldRenderer.setIntensityScale(parseFloat(e.target.value));
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            this.chartManager.closeModal();
            document.getElementById('help-overlay')?.classList.add('hidden');
        }
    });

    document.getElementById('btn-compare-methods')?.addEventListener('click', () => this.startComparison());
    document.getElementById('btn-close-comparison')?.addEventListener('click', () => {
        document.getElementById('comparison-overlay').classList.add('hidden');
    });

    window.addEventListener('resize', () => this.chartManager.resize());
};

