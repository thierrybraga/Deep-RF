
IloveAntenas.prototype.getSimulationPayload = function(method = 'fdtd') {
    return {
        antenna_type: this.state.antennaType,
        frequency: this.state.frequency,
        length: this.state.length,
        radius: this.state.radius,
        num_directors: this.state.numDirectors,
        substrate_er: this.state.substrateEr,
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
        cone_height: this.state.disconeConeHeight,
        cells_per_wavelength: this.state.cellsPerWavelength,
        num_steps: this.state.numSteps,
        source_type: this.state.sourceType,
        courant: this.state.courant,
        pml_layers: this.state.pmlLayers,
        use_optimized: this.state.useOptimized,
        method: method
    };
};

IloveAntenas.prototype.runSimulation = async function() {
    const btn = document.getElementById('btn-simulate');
    const progress = document.getElementById('simulation-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const methodEl = document.getElementById('input-method');
    const method = methodEl ? methodEl.value : 'fdtd';

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Simulando...';
    progress.classList.remove('hidden');

    try {
        const startRes = await fetch('/api/simulation/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(this.getSimulationPayload(method))
        });

        const startData = await startRes.json();
        if (!startData.success) throw new Error(startData.error);

        this.state.simulationId = startData.simulation_id;

        let completed = false;
        while (!completed) {
            await this.sleep(500);

            const statusRes = await fetch(`/api/simulation/${this.state.simulationId}/status`);
            const statusData = await statusRes.json();

            if (!statusData.success) throw new Error(statusData.error);

            const sim = statusData.data;
            progressFill.style.width = `${sim.progress}%`;
            progressText.textContent = `${sim.progress}%`;

            if (sim.status === 'completed') {
                completed = true;
                this.data.simulation = sim;

                const framesRes = await fetch(`/api/simulation/${this.state.simulationId}/frames`);
                const framesData = await framesRes.json();

                if (framesData.success) {
                    if (this.data.simulation && this.data.simulation.grid && this.renderer) {
                        const grid = this.data.simulation.grid;
                        const gridInfo = {
                            nx: grid.nx,
                            ny: grid.ny,
                            nz: grid.nz,
                            dx: grid.dx
                        };
                        const scale = typeof this.renderer.antennaScale === 'number'
                            ? this.renderer.antennaScale
                            : 1.0;
                        this.renderer.setupFieldVisualization(gridInfo, scale);
                    }

                    if (this.fieldRenderer) {
                        this.fieldRenderer.setFrames(framesData.frames, framesData.field_shape);
                    }

                    if (sim.stats && sim.stats.impedance) {
                        const z = sim.stats.impedance;
                        const zReal = z.real.toFixed(1);
                        const zImag = z.imag >= 0 ? `+j${z.imag.toFixed(1)}` : `-j${Math.abs(z.imag).toFixed(1)}`;
                        const impStr = `${zReal} ${zImag} Ω`;

                        const elImp = document.getElementById('info-impedance');
                        if (elImp) {
                            elImp.textContent = impStr;
                            elImp.classList.add('value-flash-success');
                            setTimeout(() => elImp.classList.remove('value-flash-success'), 2000);
                        }
                    }

                    if (this.fieldRenderer && framesData.frames.length > 0) {
                        this.fieldRenderer.play();
                    }
                }

                this.showToast('Simulação concluída!', 'success');
            } else if (sim.status === 'error') {
                throw new Error(sim.error || 'Erro na simulação');
            }
        }

    } catch (error) {
        console.error('Erro:', error);
        this.showToast('Erro: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play"></i> Iniciar Simulação';
        setTimeout(() => progress.classList.add('hidden'), 2000);
    }
};

