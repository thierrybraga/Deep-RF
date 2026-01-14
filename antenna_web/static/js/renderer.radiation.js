AntennaRenderer.prototype.createRadiationMesh = function() {
    if (!this.radiationData || !this.scene) {
        return;
    }

    const thetaSegments = 36;
    const phiSegments = 72;
    const geometry = new THREE.SphereGeometry(1, phiSegments, thetaSegments);
    
    const positionAttribute = geometry.attributes.position;
    const vertex = new THREE.Vector3();
    const colors = [];
    const color = new THREE.Color();
    
    const getBlueRedColor = v => {
        const t = Math.max(0, Math.min(1, v));
        const c1 = { r: 0.02, g: 0.02, b: 0.25 };
        const c2 = { r: 0.0, g: 0.7, b: 1.0 };
        const c3 = { r: 0.0, g: 1.0, b: 0.2 };
        const c4 = { r: 1.0, g: 1.0, b: 0.0 };
        const c5 = { r: 1.0, g: 0.0, b: 0.0 };
        if (t < 0.25) {
            const u = t / 0.25;
            return {
                r: c1.r + (c2.r - c1.r) * u,
                g: c1.g + (c2.g - c1.g) * u,
                b: c1.b + (c2.b - c1.b) * u
            };
        } else if (t < 0.5) {
            const u = (t - 0.25) / 0.25;
            return {
                r: c2.r + (c3.r - c2.r) * u,
                g: c2.g + (c3.g - c2.g) * u,
                b: c2.b + (c3.b - c2.b) * u
            };
        } else if (t < 0.75) {
            const u = (t - 0.5) / 0.25;
            return {
                r: c3.r + (c4.r - c3.r) * u,
                g: c3.g + (c4.g - c3.g) * u,
                b: c3.b + (c4.b - c3.b) * u
            };
        } else {
            const u = (t - 0.75) / 0.25;
            return {
                r: c4.r + (c5.r - c4.r) * u,
                g: c4.g + (c5.g - c4.g) * u,
                b: c4.b + (c5.b - c4.b) * u
            };
        }
    };

    for (let i = 0; i < positionAttribute.count; i++) {
        vertex.fromBufferAttribute(positionAttribute, i);
        
        const r_base = 1.0;
        const theta = Math.acos(Math.max(-1, Math.min(1, vertex.y / r_base)));
        const phi = Math.atan2(vertex.z, vertex.x);
        
        const thetaIdx = Math.min(36, Math.floor((theta / Math.PI) * 36));
        
        let phiNorm = phi;
        if (phiNorm < 0) phiNorm += 2 * Math.PI;
        const phiIdx = Math.min(72, Math.floor((phiNorm / (2 * Math.PI)) * 72));
        
        let gain = 0;
        if (this.radiationData && this.radiationData[thetaIdx]) {
            gain = this.radiationData[thetaIdx][phiIdx] || 0;
        }
        
        const power = Math.max(0, gain);
        const r_new = 0.1 + Math.pow(power, 0.7) * 1.5;
        
        vertex.normalize().multiplyScalar(r_new);
        
        positionAttribute.setXYZ(i, vertex.x, vertex.y, vertex.z);
        
        const c = getBlueRedColor(power);
        colors.push(c.r, c.g, c.b);
    }
    
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    geometry.computeVertexNormals();
    
    const material = new THREE.MeshPhongMaterial({
        vertexColors: true,
        shininess: 30,
        transparent: true,
        opacity: 0.8,
        side: THREE.DoubleSide,
        wireframe: false
    });
    
    this.radiationMesh = new THREE.Mesh(geometry, material);
    
    this.scene.add(this.radiationMesh);
    
    const wireGeo = new THREE.WireframeGeometry(geometry);
    const wireMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.15 });
    this.radiationWireframe = new THREE.LineSegments(wireGeo, wireMat);
    this.radiationMesh.add(this.radiationWireframe);
};

AntennaRenderer.prototype.setRadiationData = function(data) {
    this.radiationData = data;
    if (this.settings.showRadiation) {
        if (this.radiationMesh) {
            this.scene.remove(this.radiationMesh);
            if (this.radiationMesh.geometry) this.radiationMesh.geometry.dispose();
            this.radiationMesh = null;
        }
        this.createRadiationMesh();
    }
};

AntennaRenderer.prototype.toggleRadiation = function() {
    this.settings.showRadiation = !this.settings.showRadiation;
    
    if (this.settings.showRadiation) {
        if (!this.radiationMesh && this.radiationData) {
            this.createRadiationMesh();
        } else if (this.radiationMesh) {
            this.radiationMesh.visible = true;
        }
    } else {
        if (this.radiationMesh) {
            this.radiationMesh.visible = false;
        }
    }
    
    return this.settings.showRadiation;
};

AntennaRenderer.prototype.updateParticles = function(delta) {
    if (this.particleSystem && this.particleSystem.visible) {
        const positions = this.particleSystem.geometry.attributes.position;
        const count = positions.count;
        for (let i = 0; i < count; i++) {
        }
        if (this.particleSystem.material.uniforms && this.particleSystem.material.uniforms.uTime) {
            this.particleSystem.material.uniforms.uTime.value += delta;
        }
    }
};
