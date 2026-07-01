AntennaRenderer.prototype.clearAntenna = function() {
    while (this.antennaGroup.children.length > 0) {
        const child = this.antennaGroup.children[0];
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
            if (Array.isArray(child.material)) {
                child.material.forEach(m => m.dispose());
            } else {
                child.material.dispose();
            }
        }
        this.antennaGroup.remove(child);
    }
    this.performanceMetrics = null;
    if (this.particleSystem) {
        this.scene.remove(this.particleSystem);
        this.particleSystem = null;
    }
};

AntennaRenderer.prototype.renderAntenna = function(data) {
    if (!data || !data.geometries) {
        console.warn('Dados de antena inválidos');
        return;
    }
    
    this.clearAntenna();
    
    const scale = this.calculateScale(data.bounding_box);
    this.antennaScale = scale;
    this.antennaInfo = {
        boundingBox: data.bounding_box,
        wavelength: data.wavelength,
        frequency: data.frequency
    };
    const center = new THREE.Vector3(
        data.bounding_box.center[0] * scale,
        data.bounding_box.center[1] * scale,
        data.bounding_box.center[2] * scale
    );
    
    data.geometries.forEach(geom => {
        const mesh = this.createGeometryMesh(geom, scale, center);
        if (mesh) {
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            this.antennaGroup.add(mesh);
        }
    });
    
    if (data.feed_point) {
        const feed = this.createFeedPoint(data.feed_point, scale, center);
        feed.userData.isFeed = true;
        this.antennaGroup.add(feed);
    }
    
    if (this.settings.showRadiation && data.radiation) {
        this.setRadiationData(data.radiation);
    }
    
    this.fitCameraToObject();
    this.updateHelpers(data.bounding_box);
    console.log('📡 Antena renderizada:', data.geometries.length, 'geometrias');
};

AntennaRenderer.prototype.updateHelpers = function(bbox) {
    if (!bbox) return;
    
    const size = Math.max(bbox.size[0], bbox.size[1], bbox.size[2]);
    let gridSize = Math.pow(10, Math.ceil(Math.log10(size * 2)));
    if (gridSize / size > 5) gridSize /= 2;
    if (gridSize < size * 1.5) gridSize *= 2;
    
    if (this.gridHelper) {
        this.helpersGroup.remove(this.gridHelper);
        this.gridHelper.geometry.dispose();
    }
    
    const divisions = 20;
    this.gridHelper = new THREE.GridHelper(
        gridSize,
        divisions,
        threeColor(themeColor('scene.grid', '#2dd4bf'), 0x00ffff),
        threeColor(themeColor('scene.gridSecondary', '#14515a'), 0x004444)
    );
    this.gridHelper.position.y = -0.01;
    this.gridHelper.material.transparent = true;
    this.gridHelper.material.opacity = 0.3;
    this.helpersGroup.add(this.gridHelper);
    
    const ground = this.scene.children.find(c => c.geometry && c.geometry.type === 'PlaneGeometry' && c !== this.fieldPlane);
    if (ground) {
        this.scene.remove(ground);
        ground.geometry.dispose();
    }
    
    const groundGeom = new THREE.PlaneGeometry(gridSize * 2, gridSize * 2);
    groundGeom.rotateX(-Math.PI / 2);
    const newGround = new THREE.Mesh(groundGeom, this.materials.ground);
    newGround.position.y = -0.02;
    newGround.receiveShadow = true;
    this.scene.add(newGround);
};

AntennaRenderer.prototype.calculateScale = function(bbox) {
    return 1.0;
};

AntennaRenderer.prototype.createGeometryMesh = function(geom, scale, center) {
    let mesh;
    
    switch (geom.type) {
        case 'wire':
            mesh = this.createWire(geom, scale);
            break;
        case 'rectangle':
            mesh = this.createRectangle(geom, scale);
            break;
        case 'cylinder':
            mesh = this.createCylinder(geom, scale);
            break;
        case 'helix':
            mesh = this.createHelix(geom, scale);
            break;
        case 'horn':
            mesh = this.createHorn(geom, scale);
            break;
        case 'dish':
            mesh = this.createDish(geom, scale);
            break;
        default:
            return null;
    }
    
    if (mesh) mesh.position.sub(center);
    return mesh;
};

AntennaRenderer.prototype.createWire = function(geom, scale) {
    const start = new THREE.Vector3(...geom.start).multiplyScalar(scale);
    const end = new THREE.Vector3(...geom.end).multiplyScalar(scale);
    
    const direction = new THREE.Vector3().subVectors(end, start);
    const length = direction.length();
    const radius = Math.max(geom.radius * scale, 0.004);
    
    const geometry = new THREE.CylinderGeometry(radius, radius, length, 32);
    const material = this.getMaterial(geom.material);
    const mesh = new THREE.Mesh(geometry, material);
    
    const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
    mesh.position.copy(midpoint);
    mesh.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        direction.normalize()
    );
    
    return mesh;
};

AntennaRenderer.prototype.createRectangle = function(geom, scale) {
    const width = geom.width * scale;
    const height = geom.height * scale;
    
    const geometry = new THREE.BoxGeometry(width, 0.003, height);
    const material = this.getMaterial(geom.material);
    const mesh = new THREE.Mesh(geometry, material);
    
    mesh.position.set(
        geom.center[0] * scale,
        geom.center[1] * scale,
        geom.center[2] * scale
    );
    
    const normal = new THREE.Vector3(...geom.normal);
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), normal);
    
    return mesh;
};

AntennaRenderer.prototype.createCylinder = function(geom, scale) {
    const radius = geom.radius * scale;
    const height = geom.height * scale;
    
    const geometry = new THREE.CylinderGeometry(radius, radius, height, 64);
    const material = this.getMaterial(geom.material);
    const mesh = new THREE.Mesh(geometry, material);
    
    mesh.position.set(
        geom.base[0] * scale,
        geom.base[1] * scale + height / 2,
        geom.base[2] * scale
    );
    
    return mesh;
};

AntennaRenderer.prototype.createHelix = function(geom, scale) {
    const points = geom.points.map(p =>
        new THREE.Vector3(p[0] * scale, p[1] * scale, p[2] * scale)
    );
    
    const curve = new THREE.CatmullRomCurve3(points);
    const tubeRadius = Math.max((geom.wire_radius || 0.001) * scale, 0.001);
    
    const geometry = new THREE.TubeGeometry(curve, 300, tubeRadius, 32, false);
    const material = this.getMaterial(geom.material);
    
    return new THREE.Mesh(geometry, material);
};

AntennaRenderer.prototype.createHorn = function(geom, scale) {
    const tw = geom.throat_width * scale;
    const th = geom.throat_height * scale;
    const aw = geom.aperture_width * scale;
    const ah = geom.aperture_height * scale;
    const len = geom.length * scale;
    
    const material = this.getMaterial(geom.material);
    material.side = THREE.DoubleSide;
    
    const t1 = [-tw / 2, -th / 2, 0];
    const t2 = [tw / 2, -th / 2, 0];
    const t3 = [tw / 2, th / 2, 0];
    const t4 = [-tw / 2, th / 2, 0];
    
    const a1 = [-aw / 2, -ah / 2, len];
    const a2 = [aw / 2, -ah / 2, len];
    const a3 = [aw / 2, ah / 2, len];
    const a4 = [-aw / 2, ah / 2, len];
    
    const vertices = [
        ...t1, ...t2, ...a2,
        ...t1, ...a2, ...a1,
        ...t4, ...a3, ...t3,
        ...t4, ...a4, ...a3,
        ...t2, ...t3, ...a3,
        ...t2, ...a3, ...a2,
        ...t1, ...a4, ...t4,
        ...t1, ...a1, ...a4
    ];
    
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.computeVertexNormals();
    
    const mesh = new THREE.Mesh(geometry, material);
    
    mesh.position.set(
        geom.center[0] * scale,
        geom.center[1] * scale,
        geom.center[2] * scale
    );
    
    return mesh;
};

AntennaRenderer.prototype.createDish = function(geom, scale) {
    const diameter = geom.diameter * scale;
    const f = geom.focal_length * scale;
    
    const points = [];
    const segments = 40;
    const radius = diameter / 2;
    
    for (let i = 0; i <= segments; i++) {
        const x = (i / segments) * radius;
        const y = (x * x) / (4 * f);
        points.push(new THREE.Vector2(x, y));
    }
    
    const geometry = new THREE.LatheGeometry(points, 64);
    const material = this.getMaterial(geom.material);
    material.side = THREE.DoubleSide;
    
    const mesh = new THREE.Mesh(geometry, material);
    
    const axis = new THREE.Vector3(...geom.axis).normalize();
    const defaultAxis = new THREE.Vector3(0, 1, 0);
    mesh.quaternion.setFromUnitVectors(defaultAxis, axis);
    
    mesh.position.set(
        geom.center[0] * scale,
        geom.center[1] * scale,
        geom.center[2] * scale
    );
    
    return mesh;
};

AntennaRenderer.prototype.createFeedPoint = function(feedPoint, scale, center) {
    const group = new THREE.Group();
    
    const sphereGeom = new THREE.SphereGeometry(0.02, 24, 24);
    const sphere = new THREE.Mesh(sphereGeom, this.materials.feed);
    group.add(sphere);
    
    const glowGeom = new THREE.SphereGeometry(0.03, 16, 16);
    const glow = new THREE.Mesh(glowGeom, this.materials.glow);
    group.add(glow);
    
    group.position.set(
        feedPoint[0] * scale - center.x,
        feedPoint[1] * scale - center.y,
        feedPoint[2] * scale - center.z
    );
    
    group.userData.feedSphere = sphere;
    group.userData.feedGlow = glow;
    
    return group;
};

AntennaRenderer.prototype.getMaterial = function(name) {
    const key = (name || 'copper').toLowerCase();
    return this.materials[key] || this.materials.copper;
};

