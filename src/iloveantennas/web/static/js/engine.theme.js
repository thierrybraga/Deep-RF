(function() {
    if (window.ENGINE_THEME) return;

    const fieldGradientStops = [
        { offset: 0.00, hex: '#0b1026', rgb: [0.043, 0.063, 0.149] },
        { offset: 0.25, hex: '#38bdf8', rgb: [0.220, 0.741, 0.973] },
        { offset: 0.50, hex: '#22c55e', rgb: [0.133, 0.773, 0.369] },
        { offset: 0.75, hex: '#f59e0b', rgb: [0.961, 0.620, 0.043] },
        { offset: 1.00, hex: '#ef4444', rgb: [0.937, 0.267, 0.267] }
    ];

    const animation = {
        frameDurationMs: 50,
        contourLevels: 12,
        contourLineWidth: 0.03,
        fieldGridScale: 40,
        pulseFrequency: 3.0,
        alphaLow: 0.03,
        alphaHigh: 0.15,
        lowFieldFadeHigh: 0.20
    };

    const rendering = {
        scene: {
            darkBackground: '#0a0a1a',
            darkFog: '#0a0a1a',
            lightBackground: '#f5f5fa',
            lightFog: '#f5f5fa',
            grid: '#2dd4bf',
            gridSecondary: '#14515a',
            lightGrid: '#38bdf8',
            ground: '#202936'
        },
        axes: {
            x: '#ef4444',
            y: '#22c55e',
            z: '#38bdf8'
        },
        feed: {
            core: '#ef4444',
            glow: '#f59e0b'
        },
        materials: {
            copper: { color: '#b87333', metalness: 1.0, roughness: 0.15, clearcoat: 1.0, clearcoatRoughness: 0.1 },
            aluminum: { color: '#c4c4cc', metalness: 1.0, roughness: 0.1, clearcoat: 1.0, clearcoatRoughness: 0.1 },
            gold: { color: '#ffd700', metalness: 1.0, roughness: 0.05, clearcoat: 1.0, clearcoatRoughness: 0.05 },
            silver: { color: '#bfbfbf', metalness: 1.0, roughness: 0.05, clearcoat: 1.0, clearcoatRoughness: 0.05 },
            pcb: { color: '#007f00', metalness: 0.1, roughness: 0.5, clearcoat: 0.5, clearcoatRoughness: 0.1 },
            teflon: { color: '#f2f2f2', metalness: 0.0, roughness: 0.2, transmission: 0.9, opacity: 0.8, transparent: true, ior: 1.5 }
        }
    };

    function lerp(a, b, t) {
        return a + (b - a) * t;
    }

    function hexToNumber(hex, fallback = 0xffffff) {
        if (typeof hex === 'number') return hex;
        if (typeof hex !== 'string') return fallback;
        const normalized = hex.trim().replace('#', '');
        const parsed = Number.parseInt(normalized, 16);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    function colorAt(t) {
        const value = Math.max(0, Math.min(1, t));
        for (let i = 0; i < fieldGradientStops.length - 1; i++) {
            const left = fieldGradientStops[i];
            const right = fieldGradientStops[i + 1];
            if (value <= right.offset) {
                const span = Math.max(0.0001, right.offset - left.offset);
                const u = (value - left.offset) / span;
                return [
                    lerp(left.rgb[0], right.rgb[0], u),
                    lerp(left.rgb[1], right.rgb[1], u),
                    lerp(left.rgb[2], right.rgb[2], u)
                ];
            }
        }
        return fieldGradientStops[fieldGradientStops.length - 1].rgb.slice();
    }

    function generateColormap(size = 256) {
        const colors = [];
        const max = Math.max(1, size - 1);
        for (let i = 0; i < size; i++) {
            const [r, g, b] = colorAt(i / max);
            colors.push([
                Math.round(255 * r),
                Math.round(255 * g),
                Math.round(255 * b)
            ]);
        }
        return colors;
    }

    function shaderVec3(index) {
        const stop = fieldGradientStops[index] || fieldGradientStops[0];
        return `vec3(${stop.rgb.map((value) => value.toFixed(3)).join(', ')})`;
    }

    window.ENGINE_THEME = {
        fieldGradientStops,
        animation,
        rendering,
        colorAt,
        generateColormap,
        hexToNumber,
        shaderVec3
    };
})();
