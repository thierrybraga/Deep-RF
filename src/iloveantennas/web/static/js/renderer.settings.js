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
        const background = themeColor('scene.darkBackground', '#0a0a1a');
        this.scene.background = new THREE.Color(background);
        this.scene.fog = new THREE.FogExp2(themeColor('scene.darkFog', background), 0.12);
        this.gridHelper.material.color.setHex(threeColor(themeColor('scene.grid', '#2dd4bf'), 0x00ffff));
    } else {
        const background = themeColor('scene.lightBackground', '#f5f5fa');
        this.scene.background = new THREE.Color(background);
        this.scene.fog = new THREE.FogExp2(themeColor('scene.lightFog', background), 0.08);
        this.gridHelper.material.color.setHex(threeColor(themeColor('scene.lightGrid', '#38bdf8'), 0x3366ff));
    }
};

AntennaRenderer.prototype.setPerformanceMetrics = function(metrics) {
    this.performanceMetrics = metrics || null;
};
