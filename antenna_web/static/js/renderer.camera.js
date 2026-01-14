AntennaRenderer.prototype.fitCameraToObject = function() {
    const box = new THREE.Box3().setFromObject(this.antennaGroup);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = this.camera.fov * (Math.PI / 180);
    const distance = maxDim / (2 * Math.tan(fov / 2)) * 1.8;
    
    this.camera.position.set(
        center.x + distance * 0.7,
        center.y + distance * 0.5,
        center.z + distance * 0.7
    );
    
    this.controls.target.copy(center);
    this.controls.update();
};

AntennaRenderer.prototype.resetCamera = function() {
    const { defaultPosition } = RENDER_CONFIG.camera;
    this.camera.position.set(defaultPosition.x, defaultPosition.y, defaultPosition.z);
    this.controls.target.set(0, 0, 0);
    this.controls.update();
};

AntennaRenderer.prototype.setCameraView = function(view) {
    const d = 2.5;
    const views = {
        front: { x: 0, y: 0, z: d },
        back: { x: 0, y: 0, z: -d },
        top: { x: 0, y: d, z: 0.01 },
        bottom: { x: 0, y: -d, z: 0.01 },
        left: { x: -d, y: 0, z: 0 },
        right: { x: d, y: 0, z: 0 },
        iso: { x: d * 0.6, y: d * 0.4, z: d * 0.6 }
    };
    
    const pos = views[view] || views.iso;
    this.camera.position.set(pos.x, pos.y, pos.z);
    this.controls.update();
};

