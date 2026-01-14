class AnalisePage {
    constructor() {
        this.renderer = null;
        this.chartManager = new ChartManager();
        this.state = this.readParams();
        this.init();
    }

    readParams() {
        const params = new URLSearchParams(window.location.search);
        const type = params.get('type') || 'dipole';
        const freqMHz = parseFloat(params.get('freq_mhz') || '300');
        const length = params.get('length') ? parseFloat(params.get('length')) : null;
        const numDirectors = params.get('num_directors') ? parseInt(params.get('num_directors')) : 3;
        return {
            antennaType: type,
            frequency: freqMHz * 1e6,
            length,
            numDirectors
        };
    }

    async init() {
        this.renderer = new AntennaRenderer('analise-canvas-3d');
        await this.loadAntenna();
        await this.loadAnalysis();
    }

    async loadAntenna() {
        const body = {
            type: this.state.antennaType,
            frequency: this.state.frequency,
            length: this.state.length,
            num_directors: this.state.numDirectors
        };
        const res = await fetch('/api/antenna/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const json = await res.json();
        if (!json.success) return;
        const data = json.data;
        this.renderer.renderAntenna(data);
        this.updateInfo(data);
    }

    async loadAnalysis() {
        const basePayload = {
            type: this.state.antennaType,
            frequency: this.state.frequency,
            length: this.state.length,
            num_directors: this.state.numDirectors
        };

        const smithRes = await fetch('/api/smith-chart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(basePayload)
        });
        const smithJson = await smithRes.json();
        if (smithJson.success) {
            const smithData = smithJson.data;
            
            // Initialize and update Smith Chart
            this.chartManager.initSmithChart('analise-smith-canvas');
            this.chartManager.updateSmithChart(smithData);
            this.updateSmithInfo(smithData);
            
            // Initialize and update S11 Chart
            this.chartManager.initS11Chart('analise-s11-canvas');
            this.chartManager.updateS11Chart(smithData);
        }

        const radRes = await fetch('/api/radiation-pattern', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(basePayload)
        });
        const radJson = await radRes.json();
        if (radJson.success) {
            const rad = radJson.data;
            
            // Initialize and update Radiation Chart (Combined E/H plane)
            // Note: Currently displaying combined chart in the "Plano E" canvas
            this.chartManager.initRadiationChart('analise-rad-e-canvas');
            this.chartManager.updateRadiationChart(rad);
            this.updateRadiationInfo(rad);
        }
    }

    updateInfo(antennaData) {
        const freqMHz = (antennaData.frequency / 1e6).toFixed(0);
        const lambda = antennaData.wavelength;
        document.getElementById('analise-type').textContent = this.state.antennaType;
        document.getElementById('analise-freq').textContent = freqMHz + ' MHz';
        document.getElementById('analise-lambda').textContent = lambda.toFixed(3) + ' m';
    }

    updateSmithInfo(data) {
        const res = data.resonance;
        const best = data.best_match;
        const bw = data.bandwidth;
        const resText = res.frequency_mhz.toFixed(1) + ' MHz, ' + res.impedance + ', S11=' + res.s11_db.toFixed(1) + ' dB';
        const bestText = best.frequency_mhz.toFixed(1) + ' MHz, ' + best.impedance + ', VSWR=' + best.vswr.toFixed(2);
        const bwText = bw.min_mhz.toFixed(1) + '–' + bw.max_mhz.toFixed(1) + ' MHz (' + bw.percent.toFixed(1) + '%)';
        document.getElementById('analise-resonancia').textContent = resText;
        document.getElementById('analise-bestmatch').textContent = bestText;
        document.getElementById('analise-bandwidth').textContent = bwText;
    }

    updateRadiationInfo(rad) {
        const d = rad.directivity_db.toFixed(1) + ' dBi';
        const bw = rad['3db_beamwidth'].toFixed(1) + '°';
        document.getElementById('analise-directivity').textContent = d;
        document.getElementById('analise-beamwidth').textContent = bw;
        if (typeof rad.fb_ratio_db === 'number') {
            document.getElementById('analise-fb').textContent = rad.fb_ratio_db.toFixed(1) + ' dB';
        }
        if (typeof rad.fr_ratio_db === 'number') {
            document.getElementById('analise-fr').textContent = rad.fr_ratio_db.toFixed(1) + ' dB';
        }
        if (typeof rad.gain_db === 'number') {
            document.getElementById('analise-gain').textContent = rad.gain_db.toFixed(1) + ' dBi';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AnalisePage();
});
