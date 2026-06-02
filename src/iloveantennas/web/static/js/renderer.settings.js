AntennaRenderer.prototype.toggleGrid = function() {
    this.settings.showGrid = !this.settings.showGrid;
    this.gridHelper.visible = this.settings.showGrid;
    return this.settings.showGrid;
};

AntennaRenderer.prototype.toggleAxes = function() {
    this.settings.showAxes = !this.settings.showAxes;
    this.axesHelper.visible = this.settings.showAxes;
    return this.settings.showAxes;
};

AntennaRenderer.prototype.toggleAutoRotate = function() {
    this.settings.autoRotate = !this.settings.autoRotate;
    return this.settings.autoRotate;
};

AntennaRenderer.prototype.setTheme = function(isDark) {
    if (!this.scene || !this.gridHelper) return;

    if (isDark) {
        this.scene.background = new THREE.Color(0x0a0a1a);
        this.scene.fog = new THREE.FogExp2(0x0a0a1a, 0.12);
        this.gridHelper.material.color.setHex(0x00ffff);
    } else {
        this.scene.background = new THREE.Color(0xf5f5fa);
        this.scene.fog = new THREE.FogExp2(0xf5f5fa, 0.08);
        this.gridHelper.material.color.setHex(0x3366ff);
    }
};

AntennaRenderer.prototype.setPerformanceMetrics = function(metrics) {
    this.performanceMetrics = metrics || null;
};
