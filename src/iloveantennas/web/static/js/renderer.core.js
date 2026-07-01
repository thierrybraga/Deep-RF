/**
 * IloveAntenas - Engine de Renderização 3D Avançada
 * Three.js com shaders customizados, partículas, pós-processamento
 * @version 2.0.0
 */

// ============================================================================
// CONFIGURAÇÃO GLOBAL
// ============================================================================

const ENGINE_RENDER_THEME = (window.ENGINE_THEME && window.ENGINE_THEME.rendering) || {};

function themeColor(path, fallback) {
    const parts = path.split('.');
    let current = ENGINE_RENDER_THEME;
    for (const part of parts) {
        current = current && current[part];
    }
    return current || fallback;
}

function threeColor(value, fallback) {
    if (window.ENGINE_THEME && typeof window.ENGINE_THEME.hexToNumber === 'function') {
        return window.ENGINE_THEME.hexToNumber(value, fallback);
    }
    if (typeof value === 'number') return value;
    if (typeof value === 'string') {
        const parsed = Number.parseInt(value.replace('#', ''), 16);
        return Number.isFinite(parsed) ? parsed : fallback;
    }
    return fallback;
}

function themeMaterial(name, fallback) {
    const themed = (ENGINE_RENDER_THEME.materials && ENGINE_RENDER_THEME.materials[name]) || {};
    const merged = { ...fallback, ...themed };
    merged.color = threeColor(merged.color, fallback.color);
    return merged;
}

const RENDER_CONFIG = {
    quality: {
        low: { pixelRatio: 1, shadows: false, antialias: false },
        medium: { pixelRatio: 1.5, shadows: true, antialias: true },
        high: { pixelRatio: 2, shadows: true, antialias: true }
    },
    camera: {
        fov: 50,
        near: 0.001,
        far: 1000,
        defaultPosition: { x: 2, y: 1.5, z: 2 }
    },
    field: {
        scale: 1.0
    },
    materials: {
        copper: themeMaterial('copper', { color: 0xb87333, metalness: 1.0, roughness: 0.15, clearcoat: 1.0, clearcoatRoughness: 0.1 }),
        aluminum: themeMaterial('aluminum', { color: 0xe0e0e0, metalness: 1.0, roughness: 0.1, clearcoat: 1.0, clearcoatRoughness: 0.1 }),
        gold: themeMaterial('gold', { color: 0xffd700, metalness: 1.0, roughness: 0.05, clearcoat: 1.0, clearcoatRoughness: 0.05 }),
        silver: themeMaterial('silver', { color: 0xf0f0f0, metalness: 1.0, roughness: 0.05, clearcoat: 1.0, clearcoatRoughness: 0.05 }),
        pcb: themeMaterial('pcb', { color: 0x004400, metalness: 0.1, roughness: 0.5, clearcoat: 0.5, clearcoatRoughness: 0.1 }),
        teflon: themeMaterial('teflon', { color: 0xffffff, metalness: 0.0, roughness: 0.2, transmission: 0.9, opacity: 0.8, transparent: true, ior: 1.5 })
    }
};

// ============================================================================
// CLASSE: AntennaRenderer
// ============================================================================

class AntennaRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error('Canvas não encontrado:', canvasId);
            return;
        }
        
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.clock = new THREE.Clock();
        this.mouse = new THREE.Vector2();
        this.raycaster = new THREE.Raycaster();
        
        this.antennaGroup = new THREE.Group();
        this.helpersGroup = new THREE.Group();
        this.fieldGroup = new THREE.Group();
        this.particleSystem = null;
        
        this.materials = {};
        this.animationId = null;
        this.isAnimating = true;
        
        this.fieldPlane = null;
        this.fieldTexture = null;
        this.antennaScale = 1;
        this.antennaInfo = null;
        this.fieldContourLevels = 12;
        this.performanceMetrics = null;
        this.settings = {
            showGrid: true,
            showAxes: true,
            showRadiation: false,
            showField3D: true,
            autoRotate: false,
            quality: 'high'
        };
        
        this.init();
    }
    
    hasWebGLSupport() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl2') || canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            return !!gl;
        } catch (e) {
            console.error('Falha ao verificar suporte WebGL', e);
            return false;
        }
    }
    
    init() {
        this.createRenderer();
        if (!this.renderer) {
            return;
        }
        this.createScene();
        this.createCamera();
        this.createControls();
        this.createLights();
        this.createMaterials();
        this.createHelpers();
        this.setupInteraction();
        
        window.addEventListener('resize', () => this.onResize());
        this.onResize();
        
        this.animate();
        const overlay = document.getElementById('viewport-loading');
        if (overlay) {
            overlay.classList.add('hidden');
        }
        
        console.log('🎮 AntennaRenderer inicializado');
    }

    hideLoading() {
        const overlay = document.getElementById('viewport-loading');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }

    setupInteraction() {
        this.canvas.addEventListener('click', (event) => {
            const rect = this.canvas.getBoundingClientRect();
            this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

            this.raycaster.setFromCamera(this.mouse, this.camera);
            const intersects = this.raycaster.intersectObjects(this.antennaGroup.children, true);

            if (intersects.length > 0) {
                const customEvent = new CustomEvent('antenna-click', {
                    detail: { point: intersects[0].point }
                });
                this.canvas.dispatchEvent(customEvent);
            }
        });
    }
    
    createRenderer() {
        if (!this.hasWebGLSupport()) {
            console.error('WebGL não disponível');
            this.showWebGLError();
            return;
        }
        
        const quality = RENDER_CONFIG.quality[this.settings.quality];
        
        try {
            const contextAttributes = {
                alpha: true,
                antialias: false,
                powerPreference: 'high-performance',
                failIfMajorPerformanceCaveat: false,
                preserveDrawingBuffer: true
            };

            if (this.settings.quality === 'high' || this.settings.quality === 'medium') {
                 contextAttributes.antialias = true;
            }

            this.renderer = new THREE.WebGLRenderer({
                canvas: this.canvas,
                ...contextAttributes
            });
        } catch (e) {
            console.warn('Falha ao criar WebGLRenderer, tentando fallback...', e);
            try {
                this.renderer = new THREE.WebGLRenderer({
                    canvas: this.canvas,
                    alpha: true,
                    antialias: false,
                    powerPreference: 'default',
                    failIfMajorPerformanceCaveat: true
                });
            } catch (e2) {
                console.error('Erro fatal: WebGL não suportado', e2);
                this.showWebGLError();
                return;
            }
        }

        if (!this.renderer) {
            this.showWebGLError();
            return;
        }
        
        this.canvas.addEventListener('webglcontextlost', (e) => {
            e.preventDefault();
            this.cancelAnimation();
        }, false);

        this.canvas.addEventListener('webglcontextrestored', () => {
            this.renderer = null;
            this.init(); 
        }, false);
        
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, quality.pixelRatio));
        this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight);
        
        if (this.renderer.shadowMap) {
            this.renderer.shadowMap.enabled = quality.shadows;
            this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        }
        
        this.renderer.outputEncoding = THREE.sRGBEncoding;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.0;
    }

    initPostProcessing() {
        if (!this.renderer || !this.scene || !this.camera) return;

        if (typeof THREE.EffectComposer === 'undefined') {
            return;
        }

        const width = this.canvas.clientWidth;
        const height = this.canvas.clientHeight;

        this.composer = new THREE.EffectComposer(this.renderer);
        this.composer.setSize(width, height);

        const renderPass = new THREE.RenderPass(this.scene, this.camera);
        this.composer.addPass(renderPass);

        const bloomPass = new THREE.UnrealBloomPass(
            new THREE.Vector2(width, height),
            0.4,
            0.4,
            0.85
        );
        this.composer.addPass(bloomPass);
        this.hasPostProcessing = true;
    }

    showWebGLError() {
        const errorMsg = document.createElement('div');
        errorMsg.className = 'webgl-error';
        errorMsg.innerHTML = '<h3>Erro Gráfico 3D</h3><p>Não foi possível inicializar o motor de renderização (WebGL).</p>';
        
        const container = this.canvas.parentElement;
        if (container) {
            const existing = container.querySelector('.webgl-error');
            if (existing) existing.remove();
            container.appendChild(errorMsg);
        }
    }

    cancelAnimation() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        this.isAnimating = false;
    }
    
    createScene() {
        this.scene = new THREE.Scene();
        const background = themeColor('scene.darkBackground', '#0a0a1a');
        const fog = themeColor('scene.darkFog', background);
        this.scene.background = new THREE.Color(background);
        this.scene.fog = new THREE.FogExp2(fog, 0.12);
        
        this.scene.add(this.antennaGroup);
        this.scene.add(this.helpersGroup);
        this.scene.add(this.fieldGroup);
    }
    
    createCamera() {
        const aspect = this.canvas.clientWidth / this.canvas.clientHeight;
        const { fov, near, far, defaultPosition } = RENDER_CONFIG.camera;
        
        this.camera = new THREE.PerspectiveCamera(fov, aspect, near, far);
        this.camera.position.set(defaultPosition.x, defaultPosition.y, defaultPosition.z);
    }
    
    createControls() {
        this.controls = new THREE.OrbitControls(this.camera, this.canvas);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.rotateSpeed = 0.8;
        this.controls.zoomSpeed = 1.2;
        this.controls.minDistance = 0.1;
        this.controls.maxDistance = 50;
        this.controls.target.set(0, 0, 0);
    }
    
    createLights() {
        const ambient = new THREE.AmbientLight(0xffffff, 0.4);
        this.scene.add(ambient);
        
        const keyLight = new THREE.DirectionalLight(0xffffff, 1.0);
        keyLight.position.set(5, 5, 5);
        keyLight.castShadow = true;
        keyLight.shadow.mapSize.width = 2048;
        keyLight.shadow.mapSize.height = 2048;
        keyLight.shadow.camera.near = 0.1;
        keyLight.shadow.camera.far = 50;
        this.scene.add(keyLight);
        
        const fillLight = new THREE.DirectionalLight(threeColor(themeColor('scene.lightGrid', '#38bdf8'), 0x88aaff), 0.3);
        fillLight.position.set(-3, 2, -3);
        this.scene.add(fillLight);
        
        const rimLight = new THREE.PointLight(threeColor(themeColor('feed.glow', '#f59e0b'), 0xff8866), 0.2, 20);
        rimLight.position.set(0, -3, -5);
        this.scene.add(rimLight);
        
        const hemiLight = new THREE.HemisphereLight(
            threeColor(themeColor('scene.lightGrid', '#38bdf8'), 0x88aaff),
            threeColor(themeColor('scene.ground', '#202936'), 0x444422),
            0.3
        );
        this.scene.add(hemiLight);
    }
    
    createMaterials() {
        for (const [name, props] of Object.entries(RENDER_CONFIG.materials)) {
            const matConfig = {
                color: props.color,
                metalness: props.metalness,
                roughness: props.roughness,
                clearcoat: props.metalness > 0.5 ? 0.3 : 0,
                clearcoatRoughness: 0.2
            };

            if (props.transparent) {
                matConfig.transparent = true;
                matConfig.opacity = props.opacity || 1.0;
            }
            
            if (props.transmission) {
                matConfig.transmission = props.transmission;
            }

            this.materials[name] = new THREE.MeshPhysicalMaterial(matConfig);
        }
        
        this.materials.feed = new THREE.MeshBasicMaterial({
            color: threeColor(themeColor('feed.core', '#ef4444'), 0xff4444),
            transparent: true,
            opacity: 0.9
        });
        
        this.materials.glow = new THREE.MeshBasicMaterial({
            color: threeColor(themeColor('feed.glow', '#f59e0b'), 0xff6644),
            transparent: true,
            opacity: 0.3
        });
        
        this.materials.ground = new THREE.MeshStandardMaterial({
            color: threeColor(themeColor('scene.ground', '#202936'), 0x222233),
            metalness: 0.3,
            roughness: 0.8,
            transparent: true,
            opacity: 0.5
        });
    }
    
    createHelpers() {
        this.gridHelper = new THREE.GridHelper(
            4,
            40,
            threeColor(themeColor('scene.grid', '#2dd4bf'), 0x00ffff),
            threeColor(themeColor('scene.gridSecondary', '#14515a'), 0x004444)
        );
        this.gridHelper.position.y = -0.5;
        this.gridHelper.material.transparent = true;
        this.gridHelper.material.opacity = 0.3;
        this.helpersGroup.add(this.gridHelper);
        
        this.axesHelper = new THREE.AxesHelper(0.5);
        this.helpersGroup.add(this.axesHelper);
        
        this.createAxisLabels();
        
        const groundGeom = new THREE.PlaneGeometry(10, 10);
        groundGeom.rotateX(-Math.PI / 2);
        const ground = new THREE.Mesh(groundGeom, this.materials.ground);
        ground.position.y = -0.51;
        ground.receiveShadow = true;
        this.scene.add(ground);
    }
    
    createAxisLabels() {
        const labels = [
            { text: 'X', color: themeColor('axes.x', '#ef4444'), pos: [0.6, 0, 0] },
            { text: 'Y', color: themeColor('axes.y', '#22c55e'), pos: [0, 0.6, 0] },
            { text: 'Z', color: themeColor('axes.z', '#38bdf8'), pos: [0, 0, 0.6] }
        ];
        
        labels.forEach(({ text, color, pos }) => {
            const sprite = this.createTextSprite(text, color);
            sprite.position.set(...pos);
            sprite.scale.set(0.12, 0.12, 0.12);
            this.helpersGroup.add(sprite);
        });
    }
    
    createTextSprite(text, color) {
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = color;
        ctx.font = 'bold 48px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, 32, 32);
        
        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
        return new THREE.Sprite(material);
    }
    
    onResize() {
        if (!this.camera || !this.renderer) return;

        const width = this.canvas.clientWidth;
        const height = this.canvas.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height, false);
        
        if (this.hasPostProcessing && this.composer) {
            this.composer.setSize(width, height);
        }
    }
    
    animate() {
        if (!this.renderer || !this.scene || !this.camera) return;

        this.animationId = requestAnimationFrame(() => this.animate());
        
        if (!this.isAnimating) return;
        
        const delta = this.clock.getDelta();
        const elapsed = this.clock.getElapsedTime();
        
        this.controls.update();
        
        if (this.settings.autoRotate) {
            this.antennaGroup.rotation.y += delta * 0.3;
        }
        
        this.antennaGroup.children.forEach(child => {
            if (child.userData.isFeed) {
                const scale = 1 + Math.sin(elapsed * 4) * 0.1;
                child.scale.setScalar(scale);
            }
        });
        
        // Se updateParticles existir (definido em renderer.radiation.js ou similar)
        if (this.particleSystem && typeof this.updateParticles === 'function') {
            this.updateParticles(delta);
        }

        if (this.fieldMaterial && this.fieldMaterial.uniforms && this.fieldMaterial.uniforms.uTime) {
            this.fieldMaterial.uniforms.uTime.value = elapsed;
        }
        
        if (this.hasPostProcessing && this.composer) {
            this.composer.render();
        } else {
            this.renderer.render(this.scene, this.camera);
        }
    }
}

window.AntennaRenderer = AntennaRenderer;
