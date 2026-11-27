const chinaBoundaries = (() => {
  const detailed = new Map();
  const requested = new Set();
  const sarCodes = ['810000','820000'];
  let bundles = new Set();
  let national, overview;
  let enclosedByScale = {};
  let managementByScale = {};
  let labelAnchors = {};
  let administered = new Set();

  function register(entries) {
    for (const [id,g,b] of entries) detailed.set(id,{g,b});
    redraw();
  }

  function load(id) {
    if (!bundles.has(id) || requested.has(id)) return;
    requested.add(id);
    loadJson(`data/china-boundaries/${id}.json?v=enclaves`).then(register).catch(console.error);
  }

  function initialize(management) {
    administered = new Set(management?.administered);
    labelAnchors = management?.labelAnchors ?? {};
    managementByScale = Object.fromEntries(Object.entries(management?.boundaries || {}).map(([scale,entries]) =>
      [scale,new Map(entries.map(([id,g,b]) => [id,{g,b}]))]));
    loadJson('data/china-boundaries/overview.json?v=enclaves').then(data => {
      bundles = new Set(data.bundles);
      national = path({g:data.outline});
      register(data.provinces);
      overview = new Path2D();
      for (const province of layers[0]) {
        const outline = sarCodes.includes(province.id) ? detailed.get(province.id) ?? province : province;
        overview.addPath(path(outline));
      }
    }).catch(console.error);
    loadJson('data/china-boundaries/enclaves.json?v=1').then(data => {
      enclosedByScale = Object.fromEntries(Object.entries(data).map(([scale,scopes]) => [scale,
        Object.fromEntries(Object.entries(scopes).map(([id,entries]) => [id,entries.filter(([code]) => !administered.has(code)).map(([code,g,b,x,y]) =>
          ({region:records.get(code),shape:{g,b},x,y})).filter(entry => entry.region)]))]));
      redraw();
    }).catch(console.error);
  }

  function isDetailed() {
    return zoom >= 3.4;
  }

  function boundary(region) {
    const id = region.id;
    const management = managementByScale[isDetailed() ? 'detail' : 'base']?.get(id);
    if (management) return management;
    if (typeof id === 'string' && (isDetailed() || sarCodes.includes(id.slice(0,2)+'0000'))) {
      return detailed.get(id) ?? region;
    }
    return region;
  }

  function loadVisible(bounds) {
    if (sarCodes.includes(focusedProvince?.id)) load(focusedProvince.id);
    if (!isDetailed()) return;
    for (const province of layers[0]) {
      if (visible(province,bounds)) load(province.id);
    }
  }

  function outline() {
    return (isDetailed() ? national : overview) ?? country;
  }

  function enclosed() {
    const scope = focusedCity || focusedProvince;
    if (!scope || mode === 0 || (theme !== 'admin' && theme !== 'terrain')) return [];
    const level = isDetailed() && (detailed.has(scope.id) || managementByScale.detail?.has(scope.id)) ? 'detail' : 'base';
    return enclosedByScale[level]?.[scope.id] || [];
  }

  const keepsProvinceFill = region => administered.has(region.id);
  const labelAnchor = region => labelAnchors[region.id];
  return {initialize,loadVisible,boundary,outline,enclosed,keepsProvinceFill,labelAnchor,sarCodes};
})();
