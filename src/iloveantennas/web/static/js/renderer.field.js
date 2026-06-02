AntennaRenderer.prototype.clearFieldVisualization = function() {
    if (this.fieldPlaneE) {
        this.fieldGroup.remove(this.fieldPlaneE);
        this.fieldPlaneE.geometry.dispose();
        this.fieldPlaneE.material.dispose();
        if (this.fieldTextureE) this.fieldTextureE.dispose();
        this.fieldPlaneE = null;
        this.fieldTextureE = null;
    }
    if (this.fieldPlaneH) {
        this.fieldGroup.remove(this.fieldPlaneH);
        this.fieldPlaneH.geometry.dispose();
        this.fieldPlaneH.material.dispose();
        if (this.fieldTextureH) this.fieldTextureH.dispose();
        this.fieldPlaneH = null;
        this.fieldTextureH = null;
    }
    if (this.fieldPlane) {
        this.fieldGroup.remove(this.fieldPlane);
        this.fieldPlane.geometry.dispose();
        this.fieldPlane.material.dispose();
        if (this.fieldTexture) this.fieldTexture.dispose();
        this.fieldPlane = null;
    }
    this.fieldTexture = null;
    this.fieldMaterial = null;
};

AntennaRenderer.prototype.setupFieldVisualization = function(gridInfo, scale = 1.0) {
    if (!gridInfo) return;
    
    this.clearFieldVisualization();
    
    const { nx, ny, nz, dx } = gridInfo;
    const fieldScale = RENDER_CONFIG.field && typeof RENDER_CONFIG.field.scale === 'number'
        ? RENDER_CONFIG.field.scale
        : 1.0;
        
    const displacementScale = dx * scale * fieldScale * 2.0;
    const contourLevels = this.fieldContourLevels || 12.0;
    
    const vertexShader = `
        uniform sampler2D uDataTexture;
        uniform float uDisplacementScale;
        varying vec2 vUv;
        void main() {
            vUv = uv;
            float val = texture2D(uDataTexture, vUv).r;
            float centered = (val - 0.5) * 2.0;
            vec3 displacedPosition = position + normal * centered * uDisplacementScale;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(displacedPosition, 1.0);
        }
    `;

    const fragmentShader = `
        uniform sampler2D uDataTexture;
        uniform float uOpacity;
        uniform float uTime;
        uniform float uContourLevels;
        varying vec2 vUv;

        vec3 colormap(float t) {
            t = clamp(t, 0.0, 1.0);
            vec3 c1 = vec3(0.02, 0.02, 0.25);
            vec3 c2 = vec3(0.0, 0.7, 1.0);
            vec3 c3 = vec3(0.0, 1.0, 0.2);
            vec3 c4 = vec3(1.0, 1.0, 0.0);
            vec3 c5 = vec3(1.0, 0.0, 0.0);
            if (t < 0.25) {
                float u = t / 0.25;
                return mix(c1, c2, u);
            } else if (t < 0.5) {
                float u = (t - 0.25) / 0.25;
                return mix(c2, c3, u);
            } else if (t < 0.75) {
                float u = (t - 0.5) / 0.25;
                return mix(c3, c4, u);
            } else {
                float u = (t - 0.75) / 0.25;
                return mix(c4, c5, u);
            }
        }

        void main() {
            float val = texture2D(uDataTexture, vUv).r;
            float centered = (val - 0.5) * 2.0;
            float amplitude = abs(centered);
            float power = amplitude * amplitude;
            float norm = pow(clamp(power, 0.0, 1.0), 0.7);
            
            float levels = max(2.0, uContourLevels);
            float f = fract(norm * levels);
            float lineWidth = 0.03;
            float line = 1.0 - smoothstep(0.5 - lineWidth, 0.5 + lineWidth, abs(f - 0.5));
            
            float gridScale = 40.0;
            float gridX = abs(fract(vUv.x * gridScale) - 0.5);
            float gridY = abs(fract(vUv.y * gridScale) - 0.5);
            float grid = 1.0 - smoothstep(0.45, 0.5, min(gridX, gridY));
            
            vec3 baseColor = colormap(norm);
            
            vec3 contourColor = vec3(0.02, 0.02, 0.05);
            baseColor = mix(baseColor, contourColor, line * 0.7);
            
            float glow = 0.5 + 1.2 * pow(norm, 0.75);
            float pulse = 0.9 + 0.1 * sin(uTime * 3.0 + val * 10.0);
            
            vec3 color = baseColor * glow * pulse;
            
            color = mix(color, vec3(0.02, 0.02, 0.05), 0.7 * (1.0 - smoothstep(0.0, 0.2, norm)));
            
            color += vec3(0.3, 0.5, 1.0) * grid * 0.05 * smoothstep(0.1, 0.5, norm);
            
            float alpha = smoothstep(0.03, 0.15, norm) * uOpacity;
            alpha *= 0.9 + 0.1 * sin(uTime + vUv.x * 5.0);
            
            if (alpha < 0.01) discard;
            
            gl_FragColor = vec4(color, alpha);
        }
    `;
    
    const createPlane = (width, height, dimU, dimV, rotateX) => {
        const geometry = new THREE.PlaneGeometry(width, height, dimU - 1, dimV - 1);
        if (rotateX) geometry.rotateX(rotateX);
        
        const size = dimU * dimV;
        let type = THREE.UnsignedByteType;
        let format = THREE.RedFormat;
        
        if (!this.renderer.capabilities.isWebGL2) {
            format = THREE.LuminanceFormat;
        }

        const data = new Uint8Array(size);
        const texture = new THREE.DataTexture(data, dimU, dimV);
        texture.format = format;
        texture.type = type;
        texture.minFilter = THREE.LinearFilter;
        texture.magFilter = THREE.LinearFilter;
        texture.generateMipmaps = false;
        texture.needsUpdate = true;
        
        const material = new THREE.ShaderMaterial({
            uniforms: {
                uDataTexture: { value: texture },
                uOpacity: { value: 0.9 },
                uTime: { value: 0 },
                uDisplacementScale: { value: displacementScale },
                uContourLevels: { value: contourLevels }
            },
            vertexShader: vertexShader,
            fragmentShader: fragmentShader,
            transparent: true,
            side: THREE.DoubleSide,
            depthWrite: false,
            blending: THREE.AdditiveBlending
        });
        
        const mesh = new THREE.Mesh(geometry, material);
        return { mesh, texture, material };
    };
    
    const widthE = nx * dx * scale * fieldScale;
    const heightE = nz * dx * scale * fieldScale;
    const planeE = createPlane(widthE, heightE, nx, nz, -Math.PI / 2);
    
    this.fieldPlaneE = planeE.mesh;
    this.fieldTextureE = planeE.texture;
    this.fieldMaterialE = planeE.material;
    
    this.fieldGroup.add(this.fieldPlaneE);
    
    if (ny) {
        const widthH = nx * dx * scale * fieldScale;
        const heightH = ny * dx * scale * fieldScale;
        const planeH = createPlane(widthH, heightH, nx, ny, 0);
        
        this.fieldPlaneH = planeH.mesh;
        this.fieldTextureH = planeH.texture;
        this.fieldMaterialH = planeH.material;
        
        this.fieldGroup.add(this.fieldPlaneH);
    }
    
    this.fieldGroup.visible = this.settings.showField3D;
    
    this.fieldMaterial = this.fieldMaterialE;
};

AntennaRenderer.prototype.updateField3D = function(frame) {
    if (!frame) return;
    
    const updateTex = (texture, fieldData) => {
        if (!texture || !fieldData) return;
        const width = texture.image.width;
        const height = texture.image.height;
        const data = texture.image.data;
        
        let ptr = 0;
        for (let v = 0; v < height; v++) {
            for (let u = 0; u < width; u++) {
                let val = 0;
                if (fieldData[u] && typeof fieldData[u][v] !== 'undefined') {
                    val = fieldData[u][v];
                }
                data[ptr++] = Math.floor((Math.max(-1, Math.min(1, val)) + 1) * 127.5);
            }
        }
        texture.needsUpdate = true;
    };
    
    const fieldE = frame.fieldE || frame.field;
    if (this.fieldTextureE && fieldE) {
        updateTex(this.fieldTextureE, fieldE);
    } else if (this.fieldTexture && fieldE) {
        updateTex(this.fieldTexture, fieldE);
    }
    
    if (this.fieldTextureH && frame.fieldH) {
        updateTex(this.fieldTextureH, frame.fieldH);
    }
};

AntennaRenderer.prototype.toggleField3D = function() {
    this.settings.showField3D = !this.settings.showField3D;
    this.fieldGroup.visible = this.settings.showField3D;
    return this.settings.showField3D;
};

