const byId = id => document.getElementById(id);
const canvas = byId('map');
const ctx = canvas.getContext('2d');
const svgIcon = name => '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">' + icons[name] + '</svg>';
// Colors are assigned using the boundaries each region shares with its neighbors.
const provinceColors = {
  cn: {
    '110000':'#738953', '120000':'#927fa7', '130000':'#d0a552', '140000':'#79b8aa', '150000':'#ab596f',
    '210000':'#48918f', '220000':'#d4ad83', '230000':'#7c8b8e', '310000':'#989fbc', '320000':'#d48a79',
    '330000':'#c2bc71', '340000':'#618b72', '350000':'#49758e', '360000':'#d695a3', '370000':'#80a2c1',
    '410000':'#b75b52', '420000':'#736e9f', '430000':'#c46f4f', '440000':'#738953', '450000':'#aa94ba',
    '460000':'#bc8d8a', '500000':'#70a8ad', '510000':'#a76772', '520000':'#738953', '530000':'#c99660',
    '540000':'#989fbc', '610000':'#738953', '620000':'#6685a9', '630000':'#87a66a', '640000':'#ba926d',
    '650000':'#c17d6c', '710000':'#a77765', '810000':'#cdb595', '820000':'#8f629d',
  },
  fr: {
    '01':'#cb8773', '02':'#829bab', '03':'#72a087', '04':'#c083a1', '06':'#9a94bd',
    '11':'#8ab0cd', '24':'#d3a640', '27':'#3e7462', '28':'#ab596f', '32':'#d1b17c',
    '44':'#684a79', '52':'#aa94ba', '53':'#a2a863', '75':'#4c878c', '76':'#899954',
    '84':'#80628f', '93':'#c46f4f', '94':'#bd8650',
  },
  jp: {
    '01000':'#9a635a', '02000':'#a2a863', '03000':'#866350', '04000':'#899954', '05000':'#9a94bd',
    '06000':'#ab596f', '07000':'#8ab0cd', '08000':'#d3a640', '09000':'#684a79', '10000':'#c46f4f',
    '11000':'#80628f', '12000':'#c46f4f', '13000':'#72a087', '14000':'#80628f', '15000':'#3e7462',
    '16000':'#d3a640', '17000':'#c083a1', '18000':'#d1b17c', '19000':'#d3a640', '20000':'#829bab',
    '21000':'#684a79', '22000':'#c46f4f', '23000':'#d1b17c', '24000':'#4c878c', '25000':'#c083a1',
    '26000':'#684a79', '27000':'#8ab0cd', '28000':'#bd8650', '29000':'#cb8773', '30000':'#684a79',
    '31000':'#5b77a7', '32000':'#8ab0cd', '33000':'#8ab0cd', '34000':'#bd8650', '35000':'#557173',
    '36000':'#cb8773', '37000':'#8ab0cd', '38000':'#3e7462', '39000':'#8ab0cd', '40000':'#ab596f',
    '41000':'#a2a863', '42000':'#5b77a7', '43000':'#72a087', '44000':'#d3a640', '45000':'#866350',
    '46000':'#d3a640', '47000':'#829bab',
  },
  uk: {
    'E92000001':'#989267', 'N92000002':'#c29364', 'S92000003':'#927fa7', 'W92000004':'#a65170',
  },
  us: {
    '01':'#d1b17c', '02':'#bd8650', '04':'#8ab0cd', '05':'#d1b17c', '06':'#c46f4f',
    '08':'#8ab0cd', '09':'#8ab0cd', '10':'#5b77a7', '11':'#80628f', '12':'#9a635a',
    '13':'#829bab', '15':'#bd8650', '16':'#c083a1', '17':'#c46f4f', '18':'#684a79',
    '19':'#684a79', '20':'#80628f', '21':'#d3a640', '22':'#ab596f', '23':'#a2a863',
    '24':'#c46f4f', '25':'#cb8773', '26':'#d3a640', '27':'#a2a863', '28':'#4c878c',
    '29':'#829bab', '30':'#899954', '31':'#d3a640', '32':'#5b77a7', '33':'#866350',
    '34':'#c083a1', '35':'#d3a640', '36':'#557173', '37':'#d3a640', '38':'#557173',
    '39':'#72a087', '40':'#c46f4f', '41':'#d1b17c', '42':'#d3a640', '44':'#4c878c',
    '45':'#3e7462', '46':'#9a94bd', '47':'#684a79', '48':'#3e7462', '49':'#899954',
    '50':'#8ab0cd', '51':'#72a087', '53':'#866350', '54':'#80628f', '55':'#9a94bd',
    '56':'#684a79',
  },
}[countryCode];
const levelNames = atlasCountry.levels.map(uiLabel => ui(uiLabel));
const routeTier = Boolean(atlasHistory?.routeTier);
const prefectureLayer = routeTier ? 2 : 1;
const countyLayer = prefectureLayer+1;
const districtLevelNames = atlasUS || atlasJP || atlasFR ? {} : atlasUK ? {
  S92000003:'议会辖区',W92000004:'主要辖区',N92000002:'地方政府区'
} : {
  '110000':'区级', '120000':'区级', '310000':'区级', '500000':'区县级',
  '810000':'区级', '820000':'分区'
};
const sarLabelDirections = {'810000':1,'820000':-1};
const tooltip = byId('tooltip');
const number = new Intl.NumberFormat(atlasLocale,{maximumFractionDigits:atlasJP ? 4 : 3});
const transportLayers = {railway:railwayLayer,airports:airportLayer,roads:roadLayer,...(atlasUS ? {parks:parkLayer} : {})};
const transportScope = {railway:'主要线路与车站',airports:'运输机场与直飞航线',roads:atlasJP || atlasFR ? '高速公路与主要国道' : atlasUS ? '州际公路与主要美国国道' : atlasUK ? '高速公路与 A 级公路' : '国家高速与普通国道',parks:'国家公园及相连保护区'};
const terrainView = new AtlasTerrain(byId('terrainSurface'),redraw);
let waterFeatures = [];
let layers = levelNames.map(() => []);
let directCounties = [];
let historicalSeatHitboxes = [];
let modernChinaLandBorder;
const metricRegionsByProvince = new Map();
const localRegionsByNation = layers.map(() => new Map());
const usLocalitiesByCounty = new Map();
const usLocalityLoads = new Map();
const usLocalityTypes = ['市','镇','村','自治市镇','乡镇','普查指定地区','市县合并区','镇级辖区','保留地'];
const localMetricScales = new Map();
const missingMetricColor = '#b6b4a7';
let autonomyLayers = autonomyCategories.map(() => []);
const autonomyEnabled = autonomyCategories.map(() => true);
let country = new Path2D();
let historicalLinework;
let maritime = [];
let records = new Map();
let townshipGroups = new Map();
let localStatistics = {};
const requestedTheme = new URLSearchParams(location.search).get('view');
let theme = Object.hasOwn(themes,requestedTheme) ? requestedTheme : 'admin';
let width, height, dpr, fit;
let zoom = 1, x = 0, y = 0;
let mode = 0, raf = 0, hovered, selected, poiHitboxes = [], regionLabelHitboxes = [];
let cameraFrame = 0;
let focusedProvince = null;
let focusedRoute = null;
let focusedCity = null;
let viewTransition = null;
let displayedLabels = new Map();
let detailMotion = null;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
if (routeTier) {
  document.body.classList.add('history-route-tier');
  const button = document.createElement('button');
  button.type = 'button';
  button.dataset.level = countyLayer;
  byId('adminLevels').append(button);
}
const levelButtons = [...byId('adminLevels').querySelectorAll('button')];
const districtPicker = byId('districtPicker');
const provinceId = region => !atlasCN ? region.nation : region.id.slice(0,2)+'0000';
const maxMapZoom = atlasCN ? 160 : 95;
const isFocused = region => !focusedProvince || provinceId(region) === focusedProvince.id;
function routeOf(region) {
  if (!routeTier || !region) return null;
  const parent = records.get(region.p);
  const route = region.layer === 1 ? region : parent?.layer === 1 ? parent : records.get(parent?.p);
  return route?.layer === 1 ? route : null;
}
const childWeight = (region,weights) =>
  weights.get(region.p)?.[region.town ? 'town' : region.provinceDirect ? 'directCounty' : 'county'] ?? 0;
levelButtons.forEach((button,level) => {
  button.textContent = levelNames[level];
  button.hidden = !levelNames[level];
  button.onclick = () => {
    if (level === 0 && focusedProvince) {
      reset();
      return;
    }
    setLevel(level,focusedProvince,level === countyLayer ? focusedCity : null,level >= prefectureLayer ? focusedRoute : null);
    select(null);
  };
});

translateStatic(document.body);
document.title = showOriginal ? 'Shanhe Atlas · '+ui('分层地理图集',{country:countryName(atlasCountry)}) :
  '山河舆图 · '+atlasCountry.name+'分层地理图集';
byId('viewport').setAttribute('aria-label',showOriginal ? ui('交互地图',{country:countryName(atlasCountry)}) : atlasCountry.name+'交互地图');
byId('placeSearch').placeholder = ui(atlasCountry.search);
if (showOriginal) {
  document.body.classList.add('original-language');
  initializeOriginalChrome();
  document.querySelector('.brand h1').textContent = 'Shanhe Atlas';
  document.querySelector('.brand .latin').hidden = true;
}
if (countryCode === 'cn' || showOriginal || atlasJP || atlasFR) {
  document.querySelector('.titleplate').append(document.querySelector('.mobile-legend'));
}
const countryButtons = [];
for (const code of ['cn',...Object.keys(atlasCountries).filter(code => code !== 'cn').sort()]) {
  const config = atlasCountries[code];
  const link = document.createElement('a');
  link.dataset.country = code;
  link.textContent = showOriginal && !atlasJP && !atlasFR ? config.shortName || config.originalName : ui(config.name);
  link.title = atlasJP || atlasFR ? ui(config.name) : countryName(config);
  if (code === countryCode) link.setAttribute('aria-current','page');
  byId('countrySwitch').append(link);
  countryButtons.push(link);
}
const languageControl = byId('atlasLanguage');
if (atlasCountry.originalLocale) {
  languageControl.hidden = false;
  const original = new Option(atlasCountry.languageName || atlasCountry.originalName,'original');
  original.lang = atlasCountry.originalLocale;
  const chinese = new Option('中文','zh');
  chinese.lang = 'zh-CN';
  languageControl.append(chinese,original);
  languageControl.value = foreignLanguage;
  languageControl.onchange = switchLanguage;
}
if (atlasCountry.notes) document.querySelector('header .notes').href = atlasNotes(atlasCountry.notes);
if (atlasUK) {
  document.body.classList.add('uk-atlas');
}
if (atlasFR) {
  document.body.classList.add('fr-atlas');
  const controls = byId('usRegions');
  controls.hidden = false;
  const selectRegion = document.createElement('select');
  selectRegion.setAttribute('aria-label',ui('法国地图区域'));
  for (const region of frRegions) selectRegion.add(new Option(ui(region.label),region.id));
  selectRegion.onchange = () => {
    const {lon,lat,zoom:targetZoom} = frRegions.find(region => region.id === selectRegion.value);
    reset();
    fly(targetZoom,...(lon == null ? atlasCountry.center : project(lon,lat)));
  };
  controls.append(selectRegion);
}
if (countryCode === 'cn') {
  const periods = byId('usRegions');
  const periodSelect = document.createElement('select');
  periodSelect.setAttribute('aria-label','切换时代');
  const chronologicalPeriods = Object.entries(atlasPeriods).sort(([,a],[,b]) => a.year-b.year);
  for (const [id,period] of chronologicalPeriods) {
    periodSelect.add(new Option(period.name+' '+period.year,id));
  }
  periodSelect.add(new Option('现代中国',''));
  periodSelect.value = atlasHistory ? historyParam : '';
  periodSelect.onchange = () => {
    const query = new URLSearchParams();
    if (periodSelect.value) query.set('history',periodSelect.value);
    if (theme === 'terrain') query.set('view',theme);
    location.href = query.size ? '?'+query : './';
  };
  periods.hidden = false;
  periods.setAttribute('aria-label','中国地图时期');
  periods.append(periodSelect);
}
if (atlasUS || atlasJP) {
  document.body.classList.add(atlasUS ? 'us-atlas' : 'jp-atlas');
  if (atlasJP) document.querySelector('.brand .latin').hidden = true;
  byId('usRegions').setAttribute('aria-label',ui(atlasUS ? '美国地图区域' : '日本地图区域'));
  const regions = atlasUS ? usRegions : [
    {id:'japan-home',label:'日本全图',zoom:1},
    {id:'ryukyu',label:'冲绳诸岛',lon:127.8,lat:26.4,zoom:7.5},
    {id:'ogasawara',label:'小笠原诸岛',lon:142.2,lat:27.0,zoom:15}
  ];
  byId('usRegions').hidden = false;
  for (const {id,label,lon,lat,zoom:targetZoom} of regions) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.region = id;
    button.textContent = ui(label);
    button.onclick = () => {
      reset();
      fly(targetZoom,...(lon == null ? atlasCountry.center : project(lon,lat)));
    };
    byId('usRegions').append(button);
  }
}
document.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = svgIcon(el.dataset.icon));
byId('rose').innerHTML = [0,90,180,270].map(angle =>
  '<g transform="rotate('+angle+' 42 42)"><path d="M42 8l-6 34h6z" fill="currentColor"/><path d="M42 8l6 34h-6z" fill="#efe5c8" stroke="currentColor"/></g>'
).join('');
for (const [key,[label,english]] of Object.entries(themes)) {
  const button = document.createElement('button');
  button.className = 'theme';
  button.dataset.theme = key;
  button.innerHTML = svgIcon(key)+'<span><strong>'+ui(label)+'</strong>'+(showOriginal || atlasJP || atlasFR ? '' : '<small>'+english+'</small>')+'</span>';
  button.onclick = () => setTheme(key);
  byId('themes').append(button);
}
function swatch(label,color) {
  return '<div class="legendrow"><i class="swatch" style="background:'+color+'"></i>'+label+'</div>';
}
function setLegend(markup) {
  if (atlasCountry.capital || atlasCountry.capitals) {
    const capitalLegend = atlasCountry.capitalLegend || (atlasCountry.capitals ? '都城' : '国家首都');
    markup = '<div class="legendrow"><i class="capital-key" aria-hidden="true">★</i>'+ui(capitalLegend)+'</div>'+markup;
  }
  if (atlasHistory?.frontierLegend) markup += swatch(atlasHistory.frontierLegend,'#d2c5a6');
  if (atlasHistory?.extentNote) markup += '<div class="legendrow">'+atlasHistory.extentNote+'</div>';
  if (atlasHistory) markup += '<div class="legendrow"><i class="line modern-border"></i>现今中国陆地国界</div>';
  for (const id of ['legend','mobileLegend']) {
    const element = byId(id);
    element.innerHTML = markup;
    translateStatic(element);
  }
}
function switchLanguage() {
  const next = languageControl.value;
  const target = new URL(location.href);
  target.searchParams.set('lang',next);
  target.searchParams.set('view',theme);
  try {
    localStorage.setItem(languageStorageKey(atlasCountry),next);
    if (fit && records.size) sessionStorage.setItem('shanhe-atlas-view',JSON.stringify({
      country:countryCode,lang:next,theme,mode,zoom,center:world(width/2,height/2),
      province:focusedProvince?.id,city:focusedCity?.id,selection:records.get(selected?.id) === selected ? selected?.id : null
    }));
  } catch {}
  location.assign(target);
}
function restoreLanguageView() {
  let bookmark;
  try {
    bookmark = JSON.parse(sessionStorage.getItem('shanhe-atlas-view'));
    if (!bookmark || bookmark.country !== countryCode || bookmark.lang !== foreignLanguage || bookmark.theme !== theme) return;
    sessionStorage.removeItem('shanhe-atlas-view');
  } catch { return; }
  if (!fit) resize();
  zoom = bookmark.zoom;
  x = width/2-bookmark.center[0]*fit*zoom;
  y = height/2-bookmark.center[1]*fit*zoom;
  setLevel(bookmark.mode,records.get(bookmark.province) || null,records.get(bookmark.city) || null);
  if (bookmark.selection) select(records.get(bookmark.selection) || null);
}
function cityMetricYear(id,index) {
  if (atlasFR) return localStatistics[id]?.[index+2] ?? (index === 1 || mode>0 ? 2023 : 2024);
  if (atlasUS && index === 1) return records.get(id)?.populationYear ??
    (!id && mode === 2 ? (focusedProvince?.id === '15' ? 2020 : 2025) : 2024);
  return atlasJP ? [2023,2025][index] : atlasUS ? 2024 : atlasUK ? [2024,2025][index] : cityStatistics.years?.[id]?.[index] ?? cityStatistics.year;
}
const metricValues = region => !atlasCN ? region.stats ?? localStatistics[region.id] : region.layer === 0
  ? indicators[region.id.slice(0,2)] : cityStatistics.regions[region.id];
function localMetricPeers(province,level = mode,city = focusedCity) {
  if (atlasUS && level === 2 && city) return usLocalitiesByCounty.get(city.id) || [];
  const peers = province ? localRegionsByNation[level].get(province.id) || [] : layers[level];
  return city && level === 2 ? peers.filter(region => region.p === city.id) : peers;
}
function metricScale(key,province) {
  const figures = statistics[key];
  const cacheKey = [key,province?.id ?? 'national',!atlasCN ? mode : '',!atlasCN ? focusedCity?.id : ''].join(':');
  if (localMetricScales.has(cacheKey)) return localMetricScales.get(cacheKey);
  const peers = !atlasCN ? localMetricPeers(province) : province ? metricRegionsByProvince.get(province.id) ?? [] : layers[1];
  const covered = peers.filter(region => Number.isFinite(metricValues(region)?.[figures.index]));
  const years = [...new Set(covered.map(region => cityMetricYear(region.id,figures.index)))].sort();
  const yearLabel = ui('{year} 年',{year:years.length > 1 ? years.join(showOriginal ? ', ' : '、') : years[0] ?? cityMetricYear('',figures.index)});
  const levelBreaks = figures.breaksByLevel?.[mode];
  const palette = levelBreaks ? figures.levelColors : figures.cityColors ?? figures.colors;
  const scale = {breaks:levelBreaks ?? figures.cityBreaks,colors:palette,covered:covered.length,total:peers.length,yearLabel};
  localMetricScales.set(cacheKey,scale);
  if (!province || (atlasUS && mode === 2 && !focusedCity)) return scale;
  const values = covered.map(region => metricValues(region)[figures.index]).sort((a,b) => a-b);
  const groups = Math.min(palette.length,new Set(values).size);
  const limits = new Set();
  for (let i=1; i<groups; i++) {
    const value = values[Math.floor(values.length*i/groups)];
    if (value > values[0]) limits.add(value);
  }
  const breaks = [...limits];
  const colors = values.length ? Array.from({length:breaks.length+1},(_,i) =>
    palette[breaks.length ? Math.round(i*(palette.length-1)/breaks.length) : 2]) : [];
  Object.assign(scale,{breaks,colors,minimum:values[0]});
  return scale;
}
function metricColor(value,{breaks,colors}) {
  return Number.isFinite(value) ? colors[breaks.filter(limit => value >= limit).length] : missingMetricColor;
}
function usesCityMetrics() {
  return mode > 0 && (!atlasCN ? localMetricPeers(focusedProvince).length > 0 :
    (!focusedProvince || metricRegionsByProvince.has(focusedProvince.id)));
}
function metricLegend(key) {
  const usLocal = atlasUS && mode === 2;
  if (usLocal && key === 'gdp') return '<p>'+ui('市镇级暂无同口径 GDP 数据。')+'</p>'+
    swatch(ui('暂无同口径数据'),missingMetricColor);
  const figures = statistics[key];
  const city = usesCityMetrics();
  const scale = city ? metricScale(key,focusedProvince) : figures;
  const scope = !atlasCN ? (city ? (focusedCity || focusedProvince)?.n || levelNames[mode] : atlasFR ? '18 个大区' : atlasJP ? '47 个都道府县' : atlasUS ? '50 州与哥伦比亚特区' : '英国四个组成国') :
    city ? focusedProvince?.n || '全国地级' : '大陆 31 个省级地区';
  let legend = '<p>'+(atlasJP && key === 'gdp' ? ui('{year} 财年',{year:cityMetricYear('',figures.index)}) : city ? scale.yearLabel : ui('{year} 年',{year:cityMetricYear('',figures.index)}))+' · '+ui(scope)+'<br>'+ui(figures.unit)+
    ' · '+ui(key === 'gdp' ? '当年价' : atlasFR ? '基准人口' : atlasJP || (usLocal && focusedProvince?.id === '15') ? '全国人口普查' : !atlasCN ? '年中常住' : '年末常住')+'</p>';
  legend += scale.colors.map((color,i) => {
    const low = scale.breaks[i-1] ?? scale.minimum;
    const high = scale.breaks[i];
    const range = low !== undefined && high !== undefined ? number.format(low)+'–&lt;'+number.format(high) :
      low !== undefined ? '≥ '+number.format(low) : '&lt; '+number.format(high);
    return swatch(range,color);
  }).join('') + swatch(ui('暂无同口径数据'),missingMetricColor);
  if (city && scale.total) legend += '<p>'+(focusedProvince && (!usLocal || focusedCity) ? ui(!atlasCN ? '按当前地区分档' : '按省内数值分档')+' · ' : '')+
    ui('{n} / {total} 有数据',{n:scale.covered,total:scale.total})+'</p>';
  const statSource = atlasFR && key === 'gdp' && city ? frSources.gdpDepartment :
    atlasUK && key === 'gdp' && mode < 2 ? ukSources.gdpRegional : usLocal ?
      (focusedProvince?.id === '15' ? usSources.hawaiiPopulation : usSources.localPopulation) : atlasStatSources[key];
  legend += !atlasCN ? '<p><a href="'+statSource+'">'+ui(atlasFR ? key === 'gdp' && city ? '欧盟统计局' : '法国国家统计与经济研究所' : atlasJP ? key === 'gdp' ? '日本内阁府' : '日本总务省统计局' : atlasUS ? usLocal ? '美国人口普查局' : '美国经济分析局（BEA）' : '英国国家统计局（ONS）')+' ↗</a></p>' :
    city ? '<p>点选地区查看数值和来源。</p>' :
    '<p><a href="'+statsSource+'" target="_blank" rel="noopener">《2025 甘肃统计提要》↗</a></p>';
  if (atlasFR && key === 'gdp' && mode === 2) legend += '<p>'+ui('行政专区暂无同口径 GDP 数据。')+'</p>';
  if (atlasFR && key === 'gdp' && !city) legend += '<p>'+ui('马约特的大区 GDP 使用 2023 年数据。')+'</p>';
  if (atlasFR && key === 'gdp' && (!city || focusedProvince?.id === '01')) legend += '<p>'+ui('瓜德罗普 GDP 按来源口径含法属圣马丁。')+'</p>';
  if (atlasFR && key === 'population' && (!city || focusedProvince?.id === '06')) legend += '<p>'+ui('马约特使用 2026 年人口普查数据。')+'</p>';
  if (atlasJP && key === 'gdp' && city) legend += '<p>'+ui('市区町村 GDP 仅显示日本内阁府同一统计表中公布的城市。')+'</p>';
  return legend;
}
function administrativeLegend() {
  if (atlasHistory) return '<div class="legendrow"><i class="line"></i>'+levelNames[0]+'</div>'+
    (routeTier ? '<div class="legendrow"><i class="line route"></i>路界（部分为概略线）</div>' : '')+
    '<div class="legendrow"><i class="line city"></i>'+levelNames[prefectureLayer]+'</div>'+
    swatch('县及同级政区治所','#784b31')+
    '<p><a href="'+atlasNotes(atlasCountry.notes)+'">图册与数据来源 ↗</a></p>';
  const township = townshipGroups.get(focusedCity?.id);
  const local = districtLevelNames[focusedProvince?.id];
  if (atlasFR) return ['大区边界','省界','行政专区边界'].map((label,i) =>
    '<div class="legendrow"><i class="line '+['','city','county'][i]+'"></i>'+label+'</div>').join('');
  if (atlasJP) return '<div class="legendrow"><i class="line"></i>都道府县边界</div><div class="legendrow"><i class="line county"></i>市区町村边界</div>';
  if (atlasUS) return ['州与联邦特区边界','县及同级辖区','市镇等地方单位边界'].map((label,i) =>
    '<div class="legendrow"><i class="line '+['','city','county'][i]+'"></i>'+ui(label)+'</div>').join('')+
    (focusedProvince?.id === '15' ? '<p>'+ui('夏威夷市镇级显示人口普查指定地区。')+'</p>' : '');
  const labels = atlasUK ? ['组成国边界','英格兰大区边界',ui('{area}边界',{area:ui(local || levelNames[2])})] :
    ['省级政区','地级政区',township ? township.label+'边界' : local ? local+'边界' : '县级政区'];
  let legend = labels.map((name,i) => '<div class="legendrow"><i class="line '+['','city','county'][i]+'"></i>'+name+'</div>').join('');
  const direct = mode > 0 ? directCounties.filter(isFocused) : [];
  if (direct.length) {
    legend += '<div class="legendrow"><i class="line county"></i>省／自治区直辖县级政区</div>';
    if (direct.some(region => !region.b)) legend += swatch('驻地点位','#784b31');
  }
  if (township?.boundaryCount || direct.some(region => region.osmRelation || region.osmNode)) {
    legend += '<p><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap contributors</a></p>';
  }
  if (atlasCN) legend += '<p><a href="'+atlasNotes('china-boundaries')+'">行政边界来源 ↗</a></p>';
  return legend;
}
function autonomyLegend() {
  return '<div class="theme-filters" role="group" aria-label="'+(atlasUK ? '地方治理类别' : '民族自治地方层级')+'">'+
    autonomyCategories.map(({name,color},i) =>
      '<label><input type="checkbox" data-autonomy="'+i+'" '+(autonomyEnabled[i] ? 'checked' : '')+
      '><i class="swatch" style="background:'+color+'"></i>'+name+'<small>'+autonomyLayers[i].length+'</small></label>'
    ).join('')+'</div>'+(atlasUK
      ? '<p>苏格兰、威尔士和北爱尔兰设有各自的分权立法机构。英格兰大区是统计地理区。</p><p><a href="'+ukSources.devolution+'">英国政府 · 权力下放 ↗</a></p>'
      : '<p><a href="https://www.neac.gov.cn/seac/ztzl/mzzzdf/index.shtml" target="_blank" rel="noopener">国家民委名录 ↗</a></p>');
}
function shownAutonomy() {
  return autonomyLayers.flatMap((regions,i) => autonomyEnabled[i] ? regions.filter(isFocused) : []);
}
const showsAutonomy = region => autonomyEnabled[region.autonomy] && isFocused(region);
for (const legend of [byId('legend'),byId('mobileLegend')]) {
  legend.addEventListener('change',universityLayer.filter);
  for (const layer of Object.values(transportLayers)) {
    if (layer.filter) legend.addEventListener('change',layer.filter);
  }
  legend.addEventListener('change',event => {
    const input = event.target;
    if (input.dataset.autonomy === undefined) return;
    autonomyEnabled[Number(input.dataset.autonomy)] = input.checked;
    for (const other of document.querySelectorAll('[data-autonomy="'+input.dataset.autonomy+'"]')) {
      other.checked = input.checked;
    }
    hovered = null;
    redraw();
  });
}
function setTheme(key) {
  const keepRegion = (theme === 'terrain' || key === 'terrain' || key === 'universities') &&
    selected?.layer != null && !selected.universityPlace &&
    (key !== 'universities' || !(atlasCN || atlasUS) || selected.layer < 2 || selected.provinceDirect);
  theme = key;
  for (const link of countryButtons) {
    const query = new URLSearchParams();
    const destination = link.dataset.country;
    if (destination !== 'cn') {
      query.set('country',destination);
      const destinationCountry = atlasCountries[destination];
      if (languageStorageKey(destinationCountry) === languageStorageKey(atlasCountry) && (showOriginal || languageParam || savedAtlasLanguage())) {
        query.set('lang',foreignLanguage);
      }
    }
    if (key !== 'admin' && (destination === 'cn' || !Object.hasOwn(chinaOnlyThemes,key)) &&
        (key !== 'parks' || destination === 'us') && (key !== 'autonomy' || ['cn','uk'].includes(destination))) query.set('view',key);
    link.href = query.size ? '?'+query : './';
  }
  document.body.classList.toggle('terrain-view',key === 'terrain');
  document.body.classList.toggle('university-view',key === 'universities');
  document.body.classList.toggle('railway-view',key === 'railway');
  document.body.classList.toggle('airport-view',key === 'airports');
  if ((atlasCN || atlasUS) && key === 'universities' && mode > 1) {
    setLevel(focusedProvince && districtLevelNames[focusedProvince.id] ? 0 : 1,focusedProvince);
  }
  hovered = null;
  if (!keepRegion) selected = null;
  byId('detail').hidden = !keepRegion;
  tooltip.hidden = true;
  for (const button of byId('themes').children) {
    const active = button.dataset.theme === key;
    button.classList.toggle('active',active);
    button.setAttribute('aria-pressed',active);
  }
  const [label,english,title] = themes[key];
  byId('plateName').textContent = ui(title);
  byId('plateEnglish').textContent = english;
  byId('status').textContent = ui(key === 'gdp' ? '经济总量 · GDP' : label);
  let legend;
  if (statistics[key]) {
    legend = metricLegend(key);
  } else if (key === 'admin') {
    legend = administrativeLegend();
  } else if (key === 'autonomy') {
    legend = autonomyLegend();
  } else if (key === 'universities') {
    legend = universityLayer.legend();
    universityLayer.load();
  } else if (transportLayers[key]) {
    legend = transportLayers[key].legend();
    transportLayers[key].load();
  } else if (key === 'culture') {
    legend = swatch('历史文化区域示意','#aa976f')+'<p>以区域核心为线索，边缘呈渐变。</p>';
  } else if (key === 'terrain') {
    legend = '<p class="elevation-legend-title">海拔（米）</p>';
    legend += elevationBands.map(({below,color},i) => {
      const lower = elevationBands[i-1]?.below;
      const label = i === 0 ? ui('低于 {n}',{n:number.format(below)}) : Number.isFinite(below)
        ? number.format(lower)+'–&lt;'+number.format(below) : ui('{n} 及以上',{n:number.format(lower)});
      return swatch(label,cssColor(color));
    }).join('')+swatch('水域',cssColor(elevationWater));
    legend += Object.values(terrainNameStyles).map(({label,color}) => swatch(label,color)).join('');
    if (atlasFR) legend += '<p>'+ui('高程覆盖法国本土与科西嘉岛。')+'</p>';
    if (atlasHistory?.terrainNote) legend += '<p>'+atlasHistory.terrainNote+'</p>';
    legend += '<p>放大查看更多自然地名。</p><p><a href="'+atlasNotes(atlasHistory ? atlasCountry.notes : atlasFR ? 'fr-terrain' : atlasJP ? 'jp-terrain' : atlasUS ? 'us-terrain' : atlasUK ? 'uk-terrain' : 'terrain-data')+'">地形与水系来源 ↗</a></p>';
  } else if (key === 'food') {
    legend = swatch('辛香风味示例','#a94536')+swatch('沿海及江南风味示例','#548465')+swatch('其他地方风味示例','#a37c40')+'<p>点选图标查看代表食物。</p>';
  }
  setLegend(legend);
  updateLevel();
  if (keepRegion) select(selected);
  redraw();
}
function updateHint() {
  byId('hint').textContent = ui(focusedProvince ? '滚轮缩放 · 点击空白返回全国' : '滚轮缩放 · 拖动平移 · 点选地区');
}
function viewWeights(level,province,city) {
  if (routeTier) return routeViewWeights(level,province,focusedRoute,city);
  const hasChildren = province && (!atlasCN ? localMetricPeers(province,level,city).length > 0 :
    layers[level].some(region => provinceId(region) === province.id));
  const weights = new Map(layers[0].map(region => {
    const active = !province || region === province;
    return [region.id,{
      color: Number(active),
      cityMetrics: Number(active && level > 0 && (!atlasCN ? localMetricPeers(region,level,city).length > 0 : metricRegionsByProvince.has(region.id))),
      outline: Number(region === province),
      county: Number(active && level === 2 && !city),
      directCounty: !active || level === 0 ? 0 : city ? .52 : 1,
      label: !active ? .42 : region === province && hasChildren ? 0 : level === 0 ? 1 : .7
    }];
  }));
  for (const region of layers[1]) {
    const active = level >= 1 && (!province || region.p === province.id);
    const muted = active && city && region !== city;
    weights.set(region.id,{
      line: !active ? 0 : muted ? .52 : 1,
      mute: Number(Boolean(muted)),
      outline: Number(region === city),
      county: Number(active && level === 2 && (!city || region === city)),
      town: Number(level === 2 && region === city),
      label: !active ? 0 : muted ? .52 : level === 2 ? .7 : 1
    });
  }
  return weights;
}
function routeViewWeights(level,province,route,city) {
  const scope = city || route || province;
  const inNation = region => !province || region.nation === province.id;
  const inRoute = region => inNation(region) && (!route || routeOf(region) === route);
  const weights = new Map();
  for (const region of layers[0]) {
    const active = inNation(region);
    const routeFill = level > 0 && active && layers[1].some(route => route.nation === region.id);
    weights.set(region.id,{color:Number(active),routeFill:Number(routeFill),outline:Number(province === region),
      label:!active ? .42 : level === 0 ? 1 : scope === province ? 0 : .55});
  }
  for (const region of layers[1]) {
    const active = level > 0 && inNation(region);
    const minor = route && region !== route;
    weights.set(region.id,{line:!active ? 0 : minor ? .35 : 1,
      color:!active ? 0 : minor ? .22 : 1,outline:Number(region === route),
      label:!active || region === route ? 0 : level === 1 ? 1 : minor ? .45 : .65,
      county:Number(level === countyLayer && inRoute(region) && !city)});
  }
  for (const region of layers[prefectureLayer]) {
    const active = level >= prefectureLayer && inRoute(region);
    const minor = city && region !== city;
    weights.set(region.id,{line:!active ? 0 : minor ? .46 : 1,mute:Number(active && Boolean(minor)),
      outline:Number(region === city),label:!active || city === region ? 0 : minor ? .5 : 1,
      county:Number(active && level === countyLayer && !minor)});
  }
  return weights;
}
function currentWeights(now) {
  if (!viewTransition) return viewWeights(mode,focusedProvince,focusedCity);
  const {from,to,start} = viewTransition;
  const elapsed = now-start;
  if (elapsed >= 560) {
    viewTransition = null;
    return to;
  }
  if (from === to) return to;
  const focus = smooth(0,540,elapsed);
  const boundary = smooth(45,510,elapsed);
  const county = smooth(90,550,elapsed);
  return new Map([...to].map(([id,target]) => {
    const previous = from.get(id) || target;
    return [id,Object.fromEntries(Object.entries(target).map(([key,value]) => {
      const progress = key === 'county' || key === 'town' ? county :
        key === 'line' || key === 'outline' || key === 'directCounty' ? boundary : focus;
      return [key,previous[key]+(value-previous[key])*progress];
    }))];
  }));
}
function setLevel(level,province,city = null,route = null) {
  const start = performance.now();
  const from = currentWeights(start);
  mode = level;
  focusedProvince = province;
  focusedRoute = route;
  focusedCity = city;
  if (atlasUS) {
    const state = usLocalityLoads.get(province?.id);
    if (level === 2) {
      layers[2] = state?.regions ?? [];
      if (!state || state.error) loadUSLocalities(province);
    } else if (!province || layers[2][0]?.nation !== province.id) {
      layers[2] = [];
    }
  }
  viewTransition = from.size && !reducedMotion.matches
    ? {from,to:viewWeights(level,province,city),start,labels:displayedLabels} : null;
  hovered = null;
  tooltip.hidden = true;
  updateHint();
  updateLevel();
  redraw();
}
function updateLevel() {
  if (routeTier) {
    for (const [level,button] of levelButtons.entries()) {
      button.setAttribute('aria-pressed',level === mode);
      button.disabled = level > 0 && !layers[level].some(region => isFocused(region) &&
        (level === 1 || !focusedRoute || routeOf(region) === focusedRoute) &&
        (level !== countyLayer || !focusedCity || region.p === focusedCity.id));
    }
    levelButtons[prefectureLayer].textContent = focusedProvince && !layers[1].some(region => isFocused(region))
      ? focusedProvince.detailLevel : levelNames[prefectureLayer];
    const label = levelButtons[mode].textContent;
    const scope = (focusedCity || focusedRoute || focusedProvince)?.n || '全图';
    byId('level').textContent = ui('{label}视图',{label});
    byId('plateLevel').textContent = atlasCountry.caption+' · '+scope+' · '+label;
    return;
  }
  const districtLevel = districtLevelNames[focusedProvince?.id];
  const township = townshipGroups.get(focusedCity?.id);
  if (theme === 'admin') setLegend(administrativeLegend());
  if (statistics[theme]) setLegend(metricLegend(theme));
  const university = theme === 'universities';
  const provinceHasCities = !focusedProvince || (university && atlasCN
    ? !districtLevelNames[focusedProvince.id] : layers[1].some(region => region.p === focusedProvince.id));
  const provinceHasCounties = atlasUS ? Boolean(localMetricPeers(focusedProvince,2,focusedCity).length) :
    !focusedProvince || layers[2].some(region => isFocused(region));
  for (const [level,button] of levelButtons.entries()) {
    button.setAttribute('aria-pressed',level === mode);
    button.disabled = (level === 1 && !provinceHasCities) || (level === 2 && ((university && (atlasCN || atlasUS)) || (!provinceHasCounties && !township)));
  }
  levelButtons[2].textContent = township?.label || ui(districtLevel) || levelNames[2];
  levelButtons[1].textContent = focusedProvince?.detailLevel || levelNames[1];
  if (atlasUS) levelButtons[2].title = focusedProvince ? '' : ui('选择州后查看市镇，也可直接搜索市镇。');
  const levelName = levelButtons[mode].textContent;
  byId('level').textContent = ui('{label}视图',{label:levelName});
  const scope = (focusedCity || focusedProvince)?.n || ui('全国');
  if (atlasHistory) {
    byId('plateLevel').textContent = atlasCountry.caption+' · '+scope+' · '+levelName;
    return;
  }
  if (university) {
    byId('plateLevel').textContent = scope+' · '+ui(mode || focusedProvince ? (atlasFR ? '按行政区展示' : atlasJP ? '按市区町村展示' : atlasUS ? '按县展示' : atlasUK ? '地方辖区统计' : '地级统计') : (atlasFR ? '按大区汇总' : atlasJP ? '按都道府县汇总' : atlasUS ? '按州汇总' : atlasUK ? '组成国汇总' : '省级汇总'));
    return;
  }
  if (transportScope[theme]) {
    byId('plateLevel').textContent = scope+' · '+ui(transportScope[theme]);
    return;
  }
  const localCoverage = !focusedProvince || layers[mode].some(region =>
    focusedCity ? region.p === focusedCity.id : isFocused(region));
  const caption = scope+' · '+levelName+(!atlasCN || township || levelName === '分区' ? '' : '政区');
  const localLoad = atlasUS && mode === 2 ? usLocalityLoads.get(focusedProvince?.id) : null;
  const coverage = localLoad && !localLoad.regions ? caption+' · '+ui(localLoad.error ? '市镇边界载入失败，请重新选择市镇级。' : '正在载入市镇边界…') :
    township && township.boundaryCount < township.units.length
    ? caption+(township.boundaryCount ? ' · 部分边界' : ' · 名录')
    : focusedProvince && !provinceHasCities && !provinceHasCounties ? scope+' · 仅收录省级边界'
    : localCoverage ? caption : scope+' · '+ui('暂无{level}边界',{level:levelName});
  const suffix = statistics[theme] && !(atlasUS && mode === 2 && theme === 'gdp') ? (!atlasCN ? ' · '+ui(atlasJP && theme === 'gdp' ? '{year} 财年' : '{year} 年',{year:cityMetricYear('',statistics[theme].index)}) :
    usesCityMetrics() ? ' · 地级统计' : ' · 2024 年省级统计') : '';
  const plate = byId('plateLevel');
  if (plate.textContent !== coverage+suffix) plate.textContent = coverage+suffix;
}
function redraw() {
  if (!raf) raf = requestAnimationFrame(draw);
}
const clamp = (value,min,max) => Math.max(min,Math.min(max,value));
function smooth(start,end,value) {
  const t = clamp((value-start)/(end-start),0,1);
  return t*t*(3-2*t);
}
function path(region, detailed = false) {
  const useDetail = detailed && region.gDetail;
  const cacheKey = useDetail ? 'detailPath' : 'path';
  if (region[cacheKey]) return region[cacheKey];
  if (region.d) return region[cacheKey] = new Path2D(region.d);
  const boundary = new Path2D();
  for (const ring of (useDetail || region.g).split('!')) {
    let index = 0;
    function readDelta() {
      let value = 0, shift = 0, chunk;
      do {
        chunk = ring.charCodeAt(index++)-63;
        value |= (chunk & 31) << shift;
        shift += 5;
      } while (chunk >= 32);
      return (value & 1) ? -(value+1)/2 : value/2;
    }
    let px = readDelta(), py = readDelta();
    boundary.moveTo(px/1000,py/1000);
    while (index < ring.length) {
      px += readDelta();
      py += readDelta();
      boundary.lineTo(px/1000,py/1000);
    }
    if (!region.open) boundary.closePath();
  }
  return region[cacheKey] = boundary;
}
function mapPath(region) {
  if (atlasCN) {
    const boundary = chinaBoundaries.boundary(region);
    if (boundary !== region) return path(boundary);
  }
  return path(region,region === focusedProvince || region === focusedRoute || region === focusedCity);
}
function visible(region,bounds) {
  const [a,b,c,d] = (atlasCN ? chinaBoundaries.boundary(region) : region).b;
  return a <= bounds[2] && c >= bounds[0] && b <= bounds[3] && d >= bounds[1];
}
function provinceColor(region) {
  const figures = statistics[theme];
  if (!figures) return (atlasHistory ? region.color : provinceColors?.[region.id]) ?? '#ab9873';
  const value = metricValues(region)?.[figures.index];
  return metricColor(value,figures);
}
function draw(now) {
  raf = 0;
  if (!width || !height) return;
  const scale = fit*zoom;
  const elevation = theme === 'terrain';
  const bounds = [-x/scale,-y/scale,(width-x)/scale,(height-y)/scale];
  if (atlasCN) chinaBoundaries.loadVisible(bounds);
  const geographic = [...unproject(bounds[0],bounds[3]),...unproject(bounds[2],bounds[1])];
  const weights = currentWeights(now);
  const terrainAvailable = !atlasFR || (geographic[0] < 10 && geographic[2] > -6 && geographic[1] < 52 && geographic[3] > 41);
  const hasSurface = terrainView.render(geographic,terrainAvailable && !elevation && byId('shade').checked,terrainAvailable && elevation);
  const surfaceStatus = byId('terrainStatus');
  surfaceStatus.hidden = !elevation || !terrainAvailable || hasSurface || !byId('loading').hidden;
  if (!surfaceStatus.hidden) surfaceStatus.textContent = ui(terrainView.error ? '高程数据载入失败，请刷新重试。' : '正在载入高程数据…');
  byId('inset').hidden = !maritime.length || zoom > 1.48;
  if (!byId('inset').hidden) drawInset();
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,width,height);
  ctx.translate(x,y);
  ctx.scale(scale,scale);
  if (!hasSurface) {
    ctx.fillStyle = '#e2d7bb';
    for (const region of layers[0]) {
      if (visible(region,bounds)) ctx.fill(mapPath(region),'evenodd');
    }
  }
  drawWater(bounds,scale);
  if (theme === 'culture') {
    for (const [,color,lon,lat] of culture) {
      const [px,py] = project(lon,lat);
      const size = lon < 100 ? 90 : 58;
      const gradient = ctx.createRadialGradient(px,py,2,px,py,size);
      gradient.addColorStop(0,color+'bb');
      gradient.addColorStop(1,color+'00');
      ctx.fillStyle = gradient;
      ctx.fillRect(px-size,py-size,2*size,2*size);
    }
  }
  const outside = new Path2D(atlasCN ? chinaBoundaries.outline() : country);
  outside.rect(bounds[0]-1,bounds[1]-1,bounds[2]-bounds[0]+2,bounds[3]-bounds[1]+2);
  ctx.fillStyle = mapPaper;
  ctx.fill(outside,'evenodd');
  drawBoundaries(bounds,scale,weights);
  if (modernChinaLandBorder) {
    ctx.save();
    ctx.setLineDash([4/scale,3/scale]);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#f4eddc88';
    ctx.lineWidth = 2.2/scale;
    ctx.stroke(modernChinaLandBorder);
    ctx.strokeStyle = '#49545c99';
    ctx.lineWidth = 1.1/scale;
    ctx.stroke(modernChinaLandBorder);
    ctx.restore();
  }
  transportLayers[theme]?.drawTrack(bounds,scale);
  ctx.setTransform(dpr,0,0,dpr,0,0);
  poiHitboxes = [];
  const capitals = drawLabels(bounds,viewTransition?.to || weights,now);
  if (theme === 'universities') universityLayer.draw();
  transportLayers[theme]?.drawStations?.(scale);
  for (const capital of capitals) drawCapital(capital);
  if (viewTransition) redraw();
  const kmPerUnit = 111.32*Math.cos(unproject(0,(height/2-y)/scale)[1]*Math.PI/180)/atlasCountry.lonScale;
  const nominal = 85*kmPerUnit/scale;
  const exponent = 10**Math.floor(Math.log10(Math.max(1,nominal)));
  const distance = [5,2,1].find(v => v*exponent <= nominal)*exponent;
  byId('scaleValue').textContent = Number.isFinite(distance) ? ui('约 {n} km',{n:distance}) : '';
  document.querySelector('.scale div').style.width = (distance*scale/kmPerUnit)+'px';
}
function drawBoundaries(bounds,scale,weights) {
  const weight = region => weights.get(region.id);
  const countyOpacity = region => childWeight(region,weights);
  const provinces = layers[0].filter(region => visible(region,bounds));
  const activeIndex = provinces.indexOf(focusedProvince);
  if (activeIndex >= 0) provinces.push(provinces.splice(activeIndex,1)[0]);
  const autonomy = theme === 'autonomy';
  const figures = statistics[theme];
  const routes = routeTier ? layers[1].filter(region => weight(region).line > 0 && visible(region,bounds)) : [];
  const cities = autonomy ? [] : layers[prefectureLayer].filter(region => region.b && weight(region).line > 0 && visible(region,bounds));
  const enclosed = atlasCN ? chinaBoundaries.enclosed() : [];
  const counties = autonomy ? [] : layers[countyLayer].filter(region => region.b && !region.provinceDirect && countyOpacity(region) > 0 && visible(region,bounds));
  const direct = autonomy ? [] : directCounties.filter(region => region.b && countyOpacity(region) > 0 && visible(region,bounds));
  for (const region of provinces) {
    const {color,cityMetrics,routeFill = 0} = weight(region);
    const provinceOpacity = figures ? color*(1-cityMetrics)*.73 : color*(1-routeFill)*(region.frontier ? .28 : .72);
    if (provinceOpacity > 0 && (theme === 'admin' || figures)) {
      ctx.globalAlpha = provinceOpacity;
      ctx.fillStyle = provinceColor(region);
      ctx.fill(mapPath(region),'evenodd');
    }
    if (color < 1) {
      ctx.globalAlpha = (region.frontier ? .3 : .88)*(1-color);
      ctx.fillStyle = '#bdbbad';
      ctx.fill(mapPath(region),'evenodd');
    }
    if (region.frontier) {
      const [,top] = region.b;
      // The source map crops the northern extent. Fade that edge into the base map.
      const fade = ctx.createLinearGradient(0,top,0,top+132);
      fade.addColorStop(0,mapPaper);
      fade.addColorStop(.3,mapPaper);
      fade.addColorStop(1,mapPaper+(theme === 'terrain' ? '85' : '00'));
      ctx.globalAlpha = 1;
      ctx.fillStyle = fade;
      ctx.fill(mapPath(region),'evenodd');
    }
  }
  if (theme === 'admin') for (const region of routes) {
    const color = weight(region).color;
    ctx.fillStyle = region.color;
    ctx.globalAlpha = color*.72;
    ctx.fill(mapPath(region),'evenodd');
    if (color < 1) {
      ctx.fillStyle = '#c7c2b2';
      ctx.globalAlpha = (1-color)*.47;
      ctx.fill(mapPath(region),'evenodd');
    }
  }
  if (figures) {
    const local = metricScale(theme,focusedProvince);
    const national = focusedProvince ? metricScale(theme,null) : local;
    for (const region of !atlasCN && mode === 2 ? (atlasUS ? counties.slice().reverse() : counties) : [...cities,...direct]) {
      const nation = provinceId(region);
      const alpha = weights.get(nation).cityMetrics*(!atlasCN && region.layer === 2 ? countyOpacity(region) : 1);
      if (!alpha) continue;
      const value = metricValues(region)?.[figures.index];
      ctx.globalAlpha = alpha*.84;
      ctx.fillStyle = metricColor(value,nation === focusedProvince?.id ? local : national);
      ctx.fill(mapPath(region),'evenodd');
    }
  }
  if (atlasUS && theme === 'admin') {
    for (const region of counties.slice().reverse()) {
      ctx.fillStyle = region.id.startsWith('M') ? '#f7efd9' : '#794d3a';
      ctx.globalAlpha = .22*countyOpacity(region);
      ctx.fill(mapPath(region),'evenodd');
    }
  }
  ctx.fillStyle = '#c7c2b2';
  for (const region of cities) {
    const {mute} = weight(region);
    if (mute > 0) {
      ctx.globalAlpha = .46*mute;
      ctx.fill(mapPath(region),'evenodd');
    }
  }
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  const strokeRegions = (list,color,lineWidth,alpha) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth/scale;
    for (const region of list) {
      ctx.globalAlpha = typeof alpha === 'function' ? alpha(region) : alpha;
      if (ctx.globalAlpha > 0) ctx.stroke(mapPath(region));
    }
  };
  const strokeNetwork = (line,color,lineWidth,alpha) => {
    if (!line || alpha <= 0) return;
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth/scale;
    ctx.globalAlpha = alpha;
    ctx.stroke(line);
  };
  strokeRegions(counties,'#5f5243',.56,region => .65*countyOpacity(region));
  if (historicalLinework) {
    const prefectureWeights = new Map();
    for (const region of cities) prefectureWeights.set(region.p,Math.max(prefectureWeights.get(region.p) || 0,weight(region).line));
    for (const [id,alpha] of prefectureWeights) strokeNetwork(historicalLinework.prefecture[id],'#655442',.67,.72*alpha);
  } else strokeRegions(cities,'#514331',.82,region => .85*weight(region).line);
  ctx.setLineDash([3/scale,2/scale]);
  strokeRegions(direct,'#784b31',1.15,region => .95*countyOpacity(region));
  ctx.setLineDash([]);
  strokeRegions(cities,'#73432b',1.25,region => weight(region).outline);
  const provinceBoundaries = atlasHistory ? provinces.filter(region => !region.frontier) : provinces;
  const lineDetail = historicalLinework ? smooth(1.3,4.4,zoom) : 1;
  if (historicalLinework) {
    const routeWeights = new Map();
    for (const region of routes) routeWeights.set(region.p,Math.max(routeWeights.get(region.p) || 0,weight(region).line));
    for (const [id,alpha] of routeWeights) strokeNetwork(historicalLinework.route[id],'#634c38',.82,.83*alpha);
    strokeNetwork(country,'#634e37',.62+.23*lineDetail,.62+.16*lineDetail);
    strokeNetwork(historicalLinework.state,'#634e37',.95,.8);
  } else {
    strokeRegions(routes,'#5f4935',.95,region => .9*weight(region).line);
    strokeRegions(provinceBoundaries,'#f1e7d0',1.55,.55);
    strokeRegions(provinceBoundaries,'#5e4934',.92,region => .42+.45*weight(region).color);
  }
  strokeRegions(routes,'#73432b',1.25,region => weight(region).outline);
  strokeRegions(provinceBoundaries,'#73432b',historicalLinework ? 1+.34*lineDetail : 1.45,
    region => weight(region).outline*(.8+.2*lineDetail));
  for (const {region,shape} of enclosed) {
    if (!visible(shape,bounds)) continue;
    const active = region === hovered || region === selected;
    if (theme === 'admin') {
      ctx.fillStyle = provinceId(region) === focusedProvince.id ? '#d1b88d' : provinceColors[provinceId(region)] || '#a59a7e';
      ctx.globalAlpha = active ? .94 : .8;
      ctx.fill(path(shape),'evenodd');
    }
    ctx.strokeStyle = '#54463a';
    ctx.globalAlpha = .9;
    ctx.lineWidth = (active ? 1.45 : 1)/scale;
    ctx.stroke(path(shape));
  }
  if (atlasCN && zoom <= 1.48 && !focusedProvince) {
    strokeRegions(provinces.filter(region => chinaBoundaries.sarCodes.includes(region.id)),'#784733',1.05,.9);
  }
  if (autonomy) {
    for (const region of shownAutonomy()) {
      if (!visible(region,bounds)) continue;
      const {color} = autonomyCategories[region.autonomy];
      ctx.globalAlpha = [.40,.54,.62][region.layer];
      ctx.fillStyle = color;
      ctx.fill(mapPath(region),'evenodd');
      strokeRegions([region],color,region.layer === 0 ? 1.25 : 1,.95);
    }
  }
  strokeRegions(maritime,'#697a78',.75,.76);
  for (const region of new Set([selected,hovered])) {
    if (region?.layer == null || !region.b || (region.locality && !region.d) || region === focusedProvince || region === focusedRoute || region === focusedCity ||
        (region === selected && !isFocused(region))) continue;
    const autonomyVisible = autonomy && showsAutonomy(region);
    const opacity = autonomyVisible ? 1 : region.layer === countyLayer ? countyOpacity(region) :
      region.layer > 0 ? weight(region).line : 1;
    if (theme !== 'admin' || !atlasCN || !chinaBoundaries.keepsProvinceFill(region)) {
      ctx.globalAlpha = .22*opacity;
      ctx.fillStyle = '#fff1ba';
      ctx.fill(mapPath(region),'evenodd');
    }
    strokeRegions([region],'#883d29',1.35,opacity);
  }
  // Fade the atlas frame across the shared outline so adjacent areas
  // retain the same terrain color along their common boundary.
  for (const [lon,south,north,slope] of atlasHistory?.outlineFades || []) {
    const [left,top] = project(lon,north);
    const dx = slope/atlasCountry.lonScale;
    const dy = -1/atlasCountry.latScale;
    const distance = (south-north)/(dx*dx+dy*dy);
    const fade = ctx.createLinearGradient(left,top,left+dx*distance,top+dy*distance);
    fade.addColorStop(0,mapPaper);
    fade.addColorStop(.45,mapPaper+'bb');
    fade.addColorStop(1,mapPaper+'00');
    ctx.globalAlpha = 1;
    ctx.fillStyle = fade;
    ctx.fill(country,'evenodd');
    ctx.strokeStyle = fade;
    ctx.lineWidth = 2/scale;
    ctx.stroke(country);
  }
  ctx.globalAlpha = 1;
}
function drawWater(bounds,scale) {
  const elevation = theme === 'terrain';
  const baseRank = elevation ? (historyParam === 'song-1208' || historyParam === 'song-1111' || historyParam === 'tang-741' || historyParam === 'sui-612' || historyParam === 'sanguo-262' ? 4.5 : 6) : 4;
  const maxRank = Math.min(10,baseRank+Math.log2(Math.max(1,zoom))*1.4);
  ctx.fillStyle = elevation ? cssColor(elevationWater) : '#a7c0c0';
  ctx.strokeStyle = elevation ? '#6c98a5' : '#89a9ae';
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  for (const feature of waterFeatures) {
    if (feature.rank > maxRank || !visible(feature,bounds)) continue;
    if (feature.kind === 'lake') ctx.fill(path(feature),'evenodd');
    else {
      ctx.lineWidth = (feature.rank <= 1 ? 1.3 : feature.rank <= 3 ? .85 : .55)/scale;
      ctx.stroke(path(feature));
    }
  }
}
const labelFamily = '"Songti SC","STSong","Noto Serif CJK SC",SimSun,serif';
function drawTerrainLabels(screen,reserveLabel,paintLabel) {
  for (const [kind,label,minZoom,...anchors] of terrainNames) {
    const name = Array.isArray(label) ? nameFor(...label) : label;
    const alpha = minZoom === 1 ? 1 : smooth(minZoom,minZoom+.45,zoom);
    if (!alpha) continue;
    const {size,lift,color} = terrainNameStyles[kind];
    const fontSize = width > 750 ? size : size-1;
    for (const [lon,lat] of anchors) {
      const [sx,sy] = screen(...project(lon,lat));
      if (reserveLabel(name,sx,sy-lift,fontSize)) {
        paintLabel(name,sx,sy-lift,fontSize,color,alpha);
        break;
      }
    }
  }
}
const capitalStar = new Path2D('M0 -6.5 1.85 -2.45 6.3 -2 3 1 3.95 5.55 0 3.2 -3.95 5.55 -3 1 -6.3 -2 -1.85 -2.45Z');
const capitalColor = '#8e3528';

function paintLabel(text,px,py,fontSize,color,alpha) {
  if (alpha <= 0) return;
  ctx.font = '600 '+fontSize+'px '+labelFamily;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  ctx.lineWidth = 3;
  ctx.strokeStyle = '#f4ebd6';
  ctx.fillStyle = color;
  ctx.globalAlpha = alpha;
  ctx.strokeText(text,px,py);
  ctx.fillText(text,px,py);
  ctx.globalAlpha = 1;
}

function drawCapital({sx,sy,label}) {
  ctx.save();
  ctx.translate(sx,sy);
  ctx.strokeStyle = '#f7edd7';
  ctx.fillStyle = capitalColor;
  ctx.lineJoin = 'round';
  ctx.lineWidth = 2.6;
  ctx.stroke(capitalStar);
  ctx.fill(capitalStar);
  ctx.restore();
  if (label) paintLabel(label.text,label.x,label.y,label.size,capitalColor,1);
}

function drawLabels(bounds,weights,now) {
  const scale = fit*zoom;
  const screen = (px,py) => [x+px*scale,y+py*scale];
  const occupied = [];
  const labels = byId('labels').checked;
  regionLabelHitboxes = [];
  historicalSeatHitboxes = [];
  const chinaOverview = atlasCN && mode === 0;
  const inset = byId('inset');
  if (chinaOverview && !inset.hidden) {
    const {left,top} = canvas.getBoundingClientRect();
    const rect = inset.getBoundingClientRect();
    occupied.push([rect.left-left-3,rect.top-top-3,rect.right-left+3,rect.bottom-top+3]);
  }
  const sarLabelOffset = 19*(1-smooth(2,5,zoom));
  const provinceLabelPositions = [[0,-12],[0,12],[-12,0],[12,0],[-12,-12],[12,-12],[-12,12],[12,12],[0,-24],[0,24]];
  const sarLabelPositions = [[-24,0],[-36,0],[-24,18],[-36,18]];
  const provinceCallouts = {'120000':[[30,9],[34,-9],[26,18]],'710000':[[-29,0],[-29,-18],[0,-49]]};
  function reserveLabel(text,px,py,fontSize) {
    if (!(px >= 10 && py >= 12 && px <= width-10 && py <= height-12)) return;
    ctx.font = '600 '+fontSize+'px '+labelFamily;
    const half = ctx.measureText(text).width/2+4;
    const rect = [px-half,py-9,px+half,py+9];
    if (rect[0] < 3 || rect[2] > width-3 ||
        occupied.some(([a,b,c,d]) => a < rect[2] && b < rect[3] && c > rect[0] && d > rect[1])) return;
    occupied.push(rect);
    return half;
  }
  const capitalMarkers = [];
  const capitals = atlasCountry.capitals || (atlasCountry.capital ? [atlasCountry.capital] : []);
  for (const capital of capitals) {
    const [sx,sy] = screen(...project(...capital.coordinates));
    if (sx >= 0 && sx <= width && sy >= 0 && sy <= height) {
      const capitalMarker = {sx,sy};
      capitalMarkers.push(capitalMarker);
      occupied.push([sx-7,sy-7,sx+7,sy+7]);
      if (labels) {
        const size = width > 750 ? 15 : 12;
        const text = nameFor(capital.name,capital.original);
        ctx.font = '600 '+size+'px '+labelFamily;
        const margin = ctx.measureText(text).width/2+8;
        const labelX = clamp(sx,margin,width-margin);
        for (const labelY of [sy-17,sy+17]) {
          if (!reserveLabel(text,labelX,labelY,size)) continue;
          capitalMarker.label = {text,x:labelX,y:labelY,size};
          break;
        }
      }
    }
  }
  const points = {culture,food}[theme];
  if (points) {
    for (const [n,color,lon,lat,description] of points) {
      const [px,py] = project(lon,lat);
      const sx = x+px*scale, sy = y+py*scale;
      if (sx < 0 || sy < 0 || sx > width || sy > height) continue;
      const size = theme === 'food' ? 5 : 3;
      ctx.beginPath();
      ctx.arc(sx,sy,size,0,2*Math.PI);
      ctx.fillStyle = color;
      ctx.strokeStyle = '#f9edcf';
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();
      poiHitboxes.push({n,x:px,y:py,sx,sy,description});
      if (labels && reserveLabel(n,sx,sy-13,13)) paintLabel(n,sx,sy-13,13,'#49392b',1);
    }
  }
  for (const region of theme === 'autonomy' ? [] : directCounties) {
    if (region.b) continue;
    const alpha = childWeight(region,weights);
    if (!alpha) continue;
    const [sx,sy] = screen(region.x,region.y);
    ctx.beginPath();
    ctx.arc(sx,sy,region === selected || region === hovered ? 5 : 3.5,0,2*Math.PI);
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = '#f4ebd6';
    ctx.fillStyle = '#784b31';
    ctx.lineWidth = 1.5;
    ctx.fill();
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
  if (atlasHistory && mode > 0 && (focusedProvince || zoom >= 2.5)) {
    for (const region of layers[mode]) {
      if (!region.seat || !isFocused(region) || (focusedCity && region.p !== focusedCity.id) ||
          (focusedRoute && routeOf(region) !== focusedRoute)) continue;
      const [sx,sy] = screen(region.x,region.y);
      if (sx < 0 || sx > width || sy < 0 || sy > height) continue;
      const active = region === selected || region === hovered;
      ctx.beginPath();
      ctx.arc(sx,sy,active ? 4.5 : 2.6,0,Math.PI*2);
      ctx.fillStyle = active ? '#883d29' : '#784b31';
      ctx.strokeStyle = '#f4ebd6';
      ctx.lineWidth = 1.25;
      ctx.fill();
      ctx.stroke();
      historicalSeatHitboxes.push({region,sx,sy});
    }
  }
  if (!labels) {
    displayedLabels = new Map();
    return capitalMarkers;
  }
  const targetLabels = new Map();
  const metric = statistics[theme];
  const local = metric && usesCityMetrics();
  const shortName = n => n.replace(/壮族自治区|维吾尔自治区|回族自治区|特别行政区|自治区|省$|市$/g,'');
  function addRegionLabel(region) {
    if (targetLabels.has(region.id)) return;
    const i = region.layer;
    const weight = weights.get(i === countyLayer ? region.p : region.id);
    let alpha = i === countyLayer ? childWeight(region,weights) : weight?.label;
    if (transportLayers[theme]) alpha *= .44;
    if (theme === 'autonomy') {
      const emphasized = showsAutonomy(region);
      alpha = emphasized ? (i === 2 && !focusedProvince && zoom < 2.6 && region !== selected ? 0 : 1) :
        i === 0 && region.autonomy == null ? .42 : 0;
    }
    if (!alpha || (region.b ? !visible(region,bounds) : !region.provinceDirect && !region.seat)) return;
    const showsValue = local
      ? focusedProvince && zoom >= 3.6 && (!atlasCN ? i === mode : i === 1 || region.provinceDirect) && isFocused(region)
      : i === 0 && zoom < 1.7 && weight.color;
    const value = metric && showsValue ? metricValues(region)?.[metric.index] : undefined;
    const name = i === 0 && !atlasCN && !atlasHistory ? shortName(region.n) : region.n;
    const year = metric && cityMetricYear(region.id,metric.index);
    const text = name+(Number.isFinite(value) && width > 850 ? ' '+number.format(value)+
      (atlasCN && year !== cityStatistics.year ? '（'+year+'）' : '') : '');
    if (capitalMarkers.some(marker => text === marker.label?.text)) return;
    const provinceOverview = chinaOverview && i === 0;
    const provinceSize = provinceOverview && width < 1000 ? (width > 750 ? 13 : 11) : width > 750 ? 16 : 11;
    const size = i === 0 ? provinceSize : 12;
    const direction = sarLabelDirections[region.id] || 0;
    let offset = direction*sarLabelOffset;
    let lift = region.b ? 0 : 12;
    if (direction && provinceOverview) {
      const separation = 1-smooth(2,5,zoom);
      ctx.font = '600 '+size+'px '+labelFamily;
      offset = direction*(ctx.measureText(text).width/2+7)*separation;
      lift = -12*separation;
    }
    const anchor = atlasCN ? chinaBoundaries.labelAnchor(region) : undefined;
    const [px,py] = screen(...(anchor ?? [region.x,region.y]));
    let half = reserveLabel(text,px+offset,py-lift,size);
    let callout = direction && provinceOverview && Math.abs(offset) > 1;
    const areaOverview = provinceOverview || (routeTier && mode === 1 && i === 1);
    if (!half && areaOverview && px >= 0 && px <= width && py >= 0 && py <= height) {
      ctx.save();
      ctx.setTransform(dpr*scale,0,0,dpr*scale,dpr*x,dpr*y);
      const boundary = mapPath(region);
      for (const [shiftX,shiftY] of direction ? sarLabelPositions : provinceLabelPositions) {
        const dx = offset+shiftX, dy = shiftY-lift;
        if (!direction && !ctx.isPointInPath(boundary,(px+dx)*dpr,(py+dy)*dpr,'evenodd')) continue;
        half = reserveLabel(text,px+dx,py+dy,size);
        if (!half) continue;
        offset = dx;
        lift = -dy;
        break;
      }
      ctx.restore();
      if (!half) for (const [dx,dy] of provinceCallouts[region.id] || []) {
        half = reserveLabel(text,px+dx,py+dy,size);
        if (!half) continue;
        offset = dx;
        lift = -dy;
        callout = true;
        break;
      }
    }
    if (half) targetLabels.set(region.id,{region,text,size,offset,lift,half,anchor,callout,sx:px+offset,sy:py-lift,
      alpha:alpha*(points && mode===0 ? .56 : 1)});
  }
  const priorityRegion = selected?.layer === countyLayer || (theme === 'terrain' && selected?.layer != null) ? selected : null;
  if (atlasCN) for (const {region,shape,x,y} of chinaBoundaries.enclosed()) {
    if (!visible(shape,bounds)) continue;
    const [sx,sy] = screen(x,y);
    const size = 12;
    const half = reserveLabel(region.n,sx,sy,size);
    if (half) targetLabels.set(region.id,{region,text:region.n,size,offset:0,lift:0,half,sx,sy,alpha:1,anchor:[x,y],enclosed:true});
  }
  if (priorityRegion) addRegionLabel(priorityRegion);
  if (theme === 'terrain') drawTerrainLabels(screen,reserveLabel,paintLabel);
  for (const region of directCounties) {
    if (region !== selected) addRegionLabel(region);
  }
  for (const {region} of historicalSeatHitboxes) addRegionLabel(region);
  for (let i=countyLayer; i>=0; i--) {
    if (i === 0) {
      layers[0].filter(region => region !== priorityRegion && sarLabelDirections[region.id]).forEach(addRegionLabel);
    }
    for (const region of layers[i]) {
      if (region !== priorityRegion && (i !== countyLayer || !region.provinceDirect && !region.seat) &&
          !sarLabelDirections[region.id]) addRegionLabel(region);
    }
  }
  displayedLabels = new Map();
  if (viewTransition) {
    const elapsed = now-viewTransition.start;
    const leaving = 1-smooth(0,300,elapsed);
    const entering = smooth(190,560,elapsed);
    for (const [id,label] of viewTransition.labels) {
      if (!targetLabels.has(id) && leaving > 0) {
        const [px,sy] = screen(...(label.anchor || [label.region.x,label.region.y]));
        displayedLabels.set(id,{...label,sx:px+label.offset,sy:sy-label.lift,alpha:label.alpha*leaving});
      }
    }
    for (const [id,label] of targetLabels) {
      const previous = viewTransition.labels.get(id)?.alpha || 0;
      const alpha = previous+(label.alpha-previous)*(label.alpha < previous ? 1-leaving : entering);
      if (alpha > 0) displayedLabels.set(id,{...label,alpha});
    }
  } else {
    displayedLabels = targetLabels;
  }
  for (const {region,text,size,alpha,half,sx,sy,enclosed,callout} of displayedLabels.values()) {
    if (chinaOverview && callout) {
      const [px,py] = screen(region.x,region.y);
      ctx.beginPath();
      ctx.moveTo(px,py);
      ctx.lineTo(clamp(px,sx-half+2,sx+half-2),clamp(py,sy-7,sy+7));
      ctx.strokeStyle = '#625749';
      ctx.lineWidth = 1;
      ctx.globalAlpha = alpha;
      ctx.stroke();
    }
    paintLabel(text,sx,sy,size,'#403728',alpha);
    if ((enclosed || callout || sarLabelDirections[region.id] || townshipGroups.has(region.id) || region.town || region.provinceDirect || region.seat || (region.locality && region.d) ||
        (theme === 'autonomy' && showsAutonomy(region))) &&
        targetLabels.has(region.id) && alpha >= .36) {
      regionLabelHitboxes.push({region,sx,sy,half,enclosed});
    }
  }
  return capitalMarkers;
}
function resize() {
  const oldWidth = width, oldHeight = height, oldFit = fit;
  width = canvas.clientWidth;
  height = canvas.clientHeight;
  dpr = Math.min(2,window.devicePixelRatio || 1);
  canvas.width = Math.round(width*dpr);
  canvas.height = Math.round(height*dpr);
  const terrainDpr = Math.min(1.5,dpr);
  const terrainWidth = Math.round(width*terrainDpr), terrainHeight = Math.round(height*terrainDpr);
  if (terrainView.canvas.width !== terrainWidth || terrainView.canvas.height !== terrainHeight) {
    terrainView.canvas.width = terrainWidth;
    terrainView.canvas.height = terrainHeight;
  }
  fit = Math.min((width-28)/atlasCountry.viewWidth,(height-35)/atlasCountry.viewHeight);
  if (oldFit) {
    x = width/2+(x-oldWidth/2)*fit/oldFit;
    y = height/2+(y-oldHeight/2)*fit/oldFit;
  } else {
    x = width/2-atlasCountry.center[0]*fit;
    y = height/2-atlasCountry.center[1]*fit;
    showCoordinates(...atlasCountry.center);
  }
  redraw();
}
function world(sx,sy) {
  return [(sx-x)/(fit*zoom),(sy-y)/(fit*zoom)];
}
function showCoordinates(px,py) {
  const [rawLongitude,lat] = unproject(px,py);
  const lon = atlasUS && rawLongitude < -180 ? rawLongitude+360 : rawLongitude;
  byId('coords').textContent = Math.abs(lon).toFixed(2)+'° '+(lon < 0 ? 'W' : 'E')+'　'+
    Math.abs(lat).toFixed(2)+'° '+(lat < 0 ? 'S' : 'N');
}
function setZoom(next,sx,sy) {
  const [px,py] = world(sx,sy);
  zoom = clamp(next,.8,maxMapZoom);
  x = sx-px*fit*zoom;
  y = sy-py*fit*zoom;
  hovered = null;
  tooltip.hidden = true;
  redraw();
}
function fly(nextZoom,px,py) {
  cancelAnimationFrame(cameraFrame);
  const start = performance.now();
  const [startX,startY] = world(width/2,height/2);
  const startZoom = zoom;
  const animate = now => {
    const progress = reducedMotion.matches ? 1 : smooth(0,320,now-start);
    zoom = startZoom*Math.pow(nextZoom/startZoom,progress);
    x = width/2-(startX+(px-startX)*progress)*fit*zoom;
    y = height/2-(startY+(py-startY)*progress)*fit*zoom;
    redraw();
    if (progress < 1) cameraFrame = requestAnimationFrame(animate);
  };
  hovered = null;
  tooltip.hidden = true;
  cameraFrame = requestAnimationFrame(animate);
}
function reset() {
  setLevel(0,null);
  select(null);
}
function administrativeParents(region, label = parent => parent.n) {
  const parents = [];
  const seen = new Set([region.id]);
  for (let parent = records.get(region.p); parent && !seen.has(parent.id); parent = records.get(parent.p)) {
    seen.add(parent.id);
    parents.unshift(label(parent));
  }
  return parents;
}
function focusRegion(region) {
  const province = records.get(provinceId(region));
  const parent = records.get(region.p);
  if (routeTier) {
    const route = routeOf(region);
    switch (region.layer) {
      case 0:
        setLevel(layers[1].some(item => item.p === region.id) ? 1 : prefectureLayer,region);
        break;
      case 1:
        setLevel(prefectureLayer,province,null,route);
        break;
      case 2:
        if (layers[countyLayer].some(item => item.p === region.id)) setLevel(countyLayer,province,region,route);
        else setLevel(prefectureLayer,province,null,route);
        break;
      case 3:
        setLevel(countyLayer,province,parent?.layer === prefectureLayer ? parent : null,route);
        break;
    }
    return;
  }
  if (region.layer === 0) {
    const level = layers[1].some(item => item.p === region.id) ? 1 :
      layers[2].some(item => item.p === region.id) ? 2 : 0;
    setLevel(level,region);
  } else if (region.layer === 1) {
    if (atlasUS && !usLocalitiesByCounty.get(region.id)?.length) setLevel(1,province);
    else if (atlasHistory && region.seat && !layers[2].some(item => item.p === region.id)) setLevel(1,province);
    else setLevel(2,province,region);
  } else {
    setLevel(region.provinceDirect ? 1 : 2,province,parent?.layer === 1 ? parent : null);
  }
}
function navigateToRegion(region) {
  if ((atlasCN || atlasUS) && theme === 'universities' && region.layer === 2 && !region.provinceDirect) setTheme('admin');
  if (theme === 'universities') universityLayer.focus(region);
  else focusRegion(region);
  select(region);
  const parent = records.get(region.p);
  const target = Number.isFinite(region.x) ? region : parent;
  if (!target) return;
  if (!target.b) {
    fly(20,target.x,target.y);
    return;
  }
  const [left,top,right,bottom] = (atlasCN ? chinaBoundaries.boundary(target) : target).b;
  const sar = atlasCN && chinaBoundaries.sarCodes.includes(provinceId(region));
  const boxZoom = .66*Math.min(width/Math.max(.12,right-left),height/Math.max(.12,bottom-top))/fit;
  fly(clamp(boxZoom,1,sar ? maxMapZoom : 60),(left+right)/2,(top+bottom)/2);
}
function pick(sx,sy) {
  const transport = transportLayers[theme]?.pick(sx,sy);
  if (transport) return transport;
  if (theme === 'universities') {
    const schoolRegion = universityLayer.pick(sx,sy)?.region;
    if (schoolRegion) return schoolRegion;
  }
  const point = poiHitboxes.find(p => Math.hypot(sx-p.sx,sy-p.sy) < 11);
  if (point) return point;
  let nearestSeat, nearestDistance = 7;
  for (const {region,sx:seatX,sy:seatY} of historicalSeatHitboxes) {
    const distance = Math.hypot(sx-seatX,sy-seatY);
    if (distance >= nearestDistance) continue;
    nearestDistance = distance;
    nearestSeat = region;
  }
  if (nearestSeat) return nearestSeat;
  const label = regionLabelHitboxes.find(({region,sx:labelX,sy:labelY,half,enclosed}) =>
    (enclosed || !region.provinceDirect || (mode > 0 && isFocused(region))) &&
    (theme !== 'autonomy' || region.autonomy == null || showsAutonomy(region)) &&
    Math.abs(sx-labelX) <= half && Math.abs(sy-labelY) <= 10);
  if (label) return label.region;
  const [px,py] = world(sx,sy);
  ctx.save();
  ctx.resetTransform();
  try {
    if (!ctx.isPointInPath(atlasCN ? chinaBoundaries.outline() : country,px,py,'evenodd')) return null;
    const contains = region => region.b && visible(region,[px,py,px,py]) && ctx.isPointInPath(mapPath(region),px,py,'evenodd');
    if (atlasCN) {
      const entry = chinaBoundaries.enclosed().find(({shape}) => contains(shape));
      if (entry) return entry.region;
    }
    if (theme === 'autonomy') {
      const match = shownAutonomy().reverse().find(contains);
      if (match) return match;
      return layers[0].find(contains) ?? null;
    }
    if (mode > 0) {
      const direct = directCounties.find(region => isFocused(region) && (region.b ? contains(region) :
        Math.hypot(px-region.x,py-region.y)*fit*zoom <= 8));
      if (direct) return direct;
    }
    for (let i=mode; i>=0; i--) {
      const match = layers[i].find(region =>
        (i === 0 || isFocused(region)) &&
        (i <= 1 || !focusedRoute || routeOf(region) === focusedRoute) &&
        (i !== countyLayer || (!region.provinceDirect &&
          (region.town ? region.p === focusedCity?.id : !focusedCity || region.p === focusedCity.id))) &&
        contains(region));
      if (match) return match;
    }
    return null;
  } finally {
    ctx.restore();
  }
}
function select(region) {
  const changed = selected !== region;
  const districtChanged = changed && (region?.layer === countyLayer || selected?.layer === countyLayer);
  selected = region;
  if (districtChanged && !viewTransition && !reducedMotion.matches) {
    const weights = viewWeights(mode,focusedProvince,focusedCity);
    viewTransition = {from:weights,to:weights,start:performance.now(),labels:displayedLabels};
  }
  const detail = byId('detail');
  byId('universityDetail').hidden = true;
  byId('railDetail').hidden = true;
  detail.hidden = !region;
  if (changed) {
    detailMotion?.cancel();
    detailMotion = region && !reducedMotion.matches ? detail.animate(
      [{opacity:0,transform:'translateY(5px)'},{opacity:1,transform:'translateY(0)'}],
      {duration:260,easing:'ease-out'}
    ) : null;
  }
  if (!region) {
    redraw();
    return;
  }
  if (region.overlay === theme) {
    districtPicker.hidden = true;
    transportLayers[theme].show(region);
    redraw();
    return;
  }
  if (theme === 'railway' && region.rail) {
    byId('place').textContent = region.n;
    districtPicker.hidden = byId('detailSources').hidden = true;
    byId('closer').hidden = region.rail === 'line' || zoom >= 70;
    railwayLayer.show(region);
    redraw();
    return;
  }
  const parents = administrativeParents(region);
  const province = region.id && records.get(provinceId(region));
  const township = townshipGroups.get(region.town ? region.p : region.id);
  const figures = province && indicators[province.id.slice(0,2)];
  const dataset = region.layer === 1 || (region.provinceDirect && cityStatistics.regions[region.id]) ? cityStatistics :
    region.layer === 2 ? districtStatistics[province?.id] : null;
  const directType = region.provinceDirect
    ? (province.n.endsWith('自治区') ? '自治区' : '省')+'直辖'+
      (region.n.endsWith('市') ? '县级市' : region.n.endsWith('林区') ? '林区' : '县级行政区')
    : null;
  byId('crumb').textContent = parents.join(' / ') || (region.layer != null ? levelNames[region.layer]+(atlasCN ? '政区' : '') : ui(themes[theme][0]));
  byId('place').textContent = region.n;
  const sources = byId('detailSources');
  sources.replaceChildren();
  if (theme === 'universities') {
    districtPicker.hidden = sources.hidden = true;
    byId('closer').hidden = zoom >= 70;
    universityLayer.show(region);
    redraw();
    return;
  }
  const addSources = entries => {
    for (const [label,url] of entries) {
      const link = document.createElement('a');
      link.textContent = label+' ↗';
      link.href = url;
      link.target = '_blank';
      link.rel = 'noopener';
      sources.append(link);
    }
  };
  if (atlasHistory) {
    byId('crumb').textContent = [...parents,region.type || levelNames[region.layer]].join(' / ');
    byId('detailText').textContent = [atlasCountry.caption, region.seat ? '治所点位' : '辖区范围',
      region.description,region.sourcePage ? '《中国历史地图集》第'+atlasHistory.volume+'册，第 '+region.sourcePage+' 页' : null].filter(Boolean).join('\n');
    addSources([[atlasHistory.name+'图册与数据说明',atlasNotes(atlasCountry.notes)]]);
    if (region.source) addSources([['治所考证',region.source]]);
  } else if (atlasUS && region.locality) {
    const people = n => n == null ? ui('暂无数据') : ui('{n} 人',{n:number.format(n)});
    byId('crumb').textContent = parents.join(' / ')+' · '+ui(region.type);
    byId('detailText').textContent = [!showOriginal ? sourceName(region) : null,
      ui(region.populationYear === 2020 ? '{year} 年人口普查' : '{year} 年年中人口',{year:region.populationYear}),
      (region.total == null ? '' : ui('本县辖区人口')+'　')+people(region.population),
      region.total == null ? null : ui('完整辖区人口')+'　'+people(region.total),
      'FIPS　'+region.code].filter(Boolean).join('\n');
    addSources([[ui('美国人口普查局'),region.populationYear === 2020 ? usSources.hawaiiPopulation : usSources.localPopulation],
      [ui('行政边界'),usSources.localBoundary]]);
  } else if (!atlasCN) {
    const [gdp,population] = metricValues(region) ?? [];
    const value = (n,unit) => n == null ? ui('暂无数据') : number.format(n)+' '+ui(unit);
    byId('crumb').textContent = (parents.length ? parents.join(' / ')+' · ' : '')+(ui(region.type) || levelNames[region.layer]);
    byId('detailText').textContent = [!atlasJP && !atlasFR && sourceName(region) !== region.n ? sourceName(region) : null,
      ui(atlasJP ? '{year} 财年' : '{year} 年',{year:cityMetricYear(region.id,0)})+' GDP　'+value(gdp,statistics.gdp.unit),
      ui(atlasFR ? '{year} 年基准人口' : atlasJP ? '{year} 年人口普查' : '{year} 年年中人口',{year:cityMetricYear(region.id,1)})+'　'+value(population,'万人'),
      region.statCode ? ui('来源统计沿用调整前区界')+' · '+region.statCode : null,
      atlasJP || atlasFR ? ui('行政区代码')+'　'+(region.code || region.id) : (atlasUS ? 'FIPS' : 'ONS')+(showOriginal ? ' code · ' : ' 编码　')+region.id].filter(Boolean).join('\n');
    if (atlasFR && ['01','D971'].includes(region.id)) byId('detailText').textContent += '\n'+ui('瓜德罗普 GDP 按来源口径含法属圣马丁。');
    const statLabel = atlasUS ? 'BEA' : 'ONS';
    if (atlasFR) addSources([[ui(region.layer === 0 ? '法国国家统计与经济研究所' : '欧盟统计局')+' · GDP',region.layer === 0 ? frSources.gdp : frSources.gdpDepartment],
      [ui('基准人口'),['06','D976'].includes(region.id) ? frSources.populationMayotte : frSources.population],[ui('行政边界'),frSources.boundary]]);
    else if (atlasJP) addSources([[ui('日本内阁府')+' · GDP',jpSources.gdp],[ui('全国人口普查'),jpSources.population],[ui('行政边界'),jpSources.boundary]]);
    else addSources([[statLabel+' · GDP',atlasUK && region.layer !== 2 ? ukSources.gdpRegional : atlasStatSources.gdp],
      [region.censusPop ? ui('美国人口普查局') : statLabel+' · '+ui('年中人口'),region.censusPop ? usSources.localPopulation : atlasStatSources.population],
      [ui('行政边界'),atlasUS && region.layer === 1 ? usSources.localBoundary : atlasStatSources.boundary]]);
    if (atlasUS && region.layer === 1 && !usLocalitiesByCounty.has(region.id)) {
      byId('detailText').textContent += '\n'+ui(region.id === '11001' || region.type === '独立市' || region.aliases ?
        '此辖区按县级展示。' : '此辖区未收录下一级市镇。');
    }
  } else if (region.management) {
    byId('detailText').textContent = region.management.description;
    addSources([['区政府 · 人口区划',region.management.source],
      ['行政管理与地权',region.management.jurisdictionSource],
      ['边界 · OpenStreetMap',`https://www.openstreetmap.org/relation/${region.osmRelation}`]]);
  } else if (region.id === '232718') {
    byId('detailText').textContent = '位于内蒙古鄂伦春自治旗境内\n地权属内蒙古，行政管理由黑龙江大兴安岭地区负责';
    addSources([['大兴安岭地区行政公署','https://www.dxal.gov.cn/dxal/c100055/202510/c13_321398.shtml']]);
  } else if (region.id === '130200' && focusedProvince?.id === '120000') {
    byId('detailText').textContent = '津冀交界处由河北唐山市管理的地块，包括芦台经济开发区和汉沽管理区。';
    addSources([['唐山市政务资料','https://tsgjlyd.tangshan.gov.cn/gjlyd/cmrd/20240221/1591787.html']]);
  } else if (region.town) {
    const lines = [region.n.endsWith('办事处') ? '办事处' : region.n.endsWith('街道') ? '街道' : '镇'];
    if (!region.b) lines.push('地图暂缺独立边界');
    byId('detailText').textContent = lines.join('\n');
    if (region.osm) addSources([['边界 · OpenStreetMap',`https://www.openstreetmap.org/relation/${region.osm}`]]);
    addSources(township.sources);
  } else if (dataset) {
    const [gdp,population,source,area] = dataset.regions[region.id] ?? [];
    const display = (value,unit) => value == null ? '暂无数据' : number.format(value)+' '+unit;
    const city = dataset === cityStatistics;
    const statYear = (value,index) => city && value != null ? '（'+cityMetricYear(region.id,index)+' 年）' : '';
    const scope = city && cityStatistics.scopes?.[region.id];
    const lines = [
      (city ? '' : dataset.year+' 年 · ')+region.n+(region.layer === 1 ? ' · '+(scope || '全域') : ''),
      'GDP　'+display(gdp,'亿元')+statYear(gdp,0),
      (dataset.populationLabel || '年末常住人口')+'　'+display(population,'万人')+statYear(population,1)
    ];
    if (directType) lines.unshift(directType);
    if (area != null) lines.push('陆地面积　'+display(area,'平方公里'));
    lines.push('行政区代码　'+region.id);
    byId('detailText').textContent = lines.join('\n');
    addSources(dataset.defaultSources ?? dataset.sources?.[source] ?? []);
  } else if (directType) {
    const lines = [directType,'行政区代码　'+region.id];
    if (!region.b) lines.push('地图标出政府驻地，全域边界待补');
    byId('detailText').textContent = lines.join('\n');
    if (region.source) addSources([['设立公告',region.source]]);
    if (region.osmRelation) addSources([['边界 · OpenStreetMap',`https://www.openstreetmap.org/relation/${region.osmRelation}`]]);
    if (region.osmNode) addSources([['驻地 · OpenStreetMap',`https://www.openstreetmap.org/node/${region.osmNode}`]]);
  } else {
    const subregion = province && province !== region ? '所在省级地区 '+province.n+' · ' : '';
    byId('detailText').textContent = region.description || (figures
      ? subregion+'2024 年｜GDP '+number.format(figures[0])+' 亿元 · 年末常住人口 '+number.format(figures[1])+' 万人'
      : statistics[theme] ? '暂无同口径统计数据' : '行政区代码 '+region.id);
  }
  if (township && !region.town) {
    const count = township.units.length;
    const status = township.boundaryCount === count ? '' : `，地图收录 ${township.boundaryCount} 条独立边界`;
    const officeCount = township.units.filter(unit => unit.n.endsWith('办事处')).length;
    const summary = officeCount ? `${count-officeCount} 个镇、${officeCount} 个办事处` : `${count} 个镇街`;
    byId('detailText').textContent += `\n直辖 ${summary}${status}`;
    addSources(township.sources);
    if (township.boundaryCount && theme !== 'admin') addSources([['© OpenStreetMap contributors','https://www.openstreetmap.org/copyright']]);
  }
  sources.hidden = !sources.childElementCount;
  const districtLevel = districtLevelNames[province?.id];
  const usCounty = atlasUS ? (region.locality ? region.p : region.id) : null;
  const usUnits = usLocalitiesByCounty.get(usCounty);
  const pickerScope = usUnits ? usCounty : township ? (region.town ? region.p : region.id) : districtLevel && province.id;
  districtPicker.hidden = !pickerScope;
  if (pickerScope) {
    if (districtPicker.dataset.scope !== pickerScope) {
      const units = usUnits ? usUnits.slice().sort((a,b) => a.n.localeCompare(b.n,atlasLocale)) : township ? township.units : layers[2].filter(item => item.p === pickerScope);
      districtPicker.dataset.scope = pickerScope;
      const hint = usUnits ? ui('选择市镇等地方单位') : atlasUK ? ui('选择{area}',{area:ui(districtLevel)}) : township?.label === '乡镇级' ? '选择镇或办事处' : township ? '选择镇街' : '选择区县';
      districtPicker.setAttribute('aria-label',hint);
      districtPicker.replaceChildren(new Option(usUnits || township || atlasUK ? hint : '选择区县或分区',''),
        ...units.map(item => new Option(item.n,item.id)));
    }
    districtPicker.value = region.layer === 2 ? region.id : '';
  }
  byId('closer').hidden = (region.town && !region.b) || zoom >= 70;
  redraw();
}
function localPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return [event.clientX-rect.left,event.clientY-rect.top];
}
canvas.addEventListener('wheel',event => {
  if (event.ctrlKey && Math.abs(event.deltaY) === 0) return;
  event.preventDefault();
  cancelAnimationFrame(cameraFrame);
  const unit = [1,16,height][event.deltaMode] || 1;
  const factor = Math.exp(-clamp(event.deltaY*unit,-260,260)*.0026);
  setZoom(zoom*factor,...localPoint(event));
}, {passive:false});
const contacts = new Map();
let dragged = false;
canvas.addEventListener('pointerdown',event => {
  if (event.button !== 0) return;
  cancelAnimationFrame(cameraFrame);
  canvas.setPointerCapture(event.pointerId);
  const point = localPoint(event);
  contacts.set(event.pointerId,{point,start:point});
  dragged = contacts.size > 1;
});
canvas.addEventListener('pointermove',event => {
  const point = localPoint(event);
  const contact = contacts.get(event.pointerId);
  if (contact) {
    const previous = contact.point;
    contact.point = point;
    const dx = point[0]-previous[0], dy = point[1]-previous[1];
    if (contacts.size === 2) {
      const other = [...contacts.entries()].find(([id]) => id !== event.pointerId)[1].point;
      const before = Math.hypot(previous[0]-other[0],previous[1]-other[1]);
      const after = Math.hypot(point[0]-other[0],point[1]-other[1]);
      if (before > 4 && after > 4) setZoom(zoom*after/before,(point[0]+other[0])/2,(point[1]+other[1])/2);
      dragged = true;
    } else {
      if (Math.hypot(point[0]-contact.start[0],point[1]-contact.start[1])>4) dragged = true;
      if (dragged) {
        x += dx;
        y += dy;
        redraw();
      }
    }
    hovered = null;
    tooltip.hidden = true;
    return;
  }
  showCoordinates(...world(...point));
  const match = pick(...point);
  if (match !== hovered) {
    hovered = match;
    redraw();
  }
  tooltip.hidden = !match;
  if (match) {
    tooltip.textContent = (theme === 'universities' && universityLayer.pick(...point)?.school?.name) || match.n;
    const figures = statistics[theme];
    if (figures?.breaksByLevel?.[match.layer] || (atlasFR && theme === 'gdp' && match.layer === 1)) {
      const value = metricValues(match)?.[figures.index];
      if (Number.isFinite(value)) tooltip.textContent += ' · '+number.format(value)+' '+ui(figures.unit);
    }
    tooltip.style.left = Math.min(point[0]+14,width-tooltip.offsetWidth-4)+'px';
    tooltip.style.top = Math.min(point[1]+16,height-tooltip.offsetHeight-4)+'px';
  }
});
canvas.addEventListener('pointerup',event => {
  if (!contacts.delete(event.pointerId)) return;
  if (!dragged && event.button === 0) {
    const region = pick(...localPoint(event));
    if (!region && focusedProvince) {
      reset();
      return;
    }
    if (theme === 'universities' && region) {
      universityLayer.focus(region);
      select(region);
      return;
    }
    if (routeTier) {
      if (region && region.layer < countyLayer &&
          ![focusedProvince,focusedRoute,focusedCity].includes(region)) focusRegion(region);
      select(region);
      return;
    }
    if (region?.layer === 0 && region !== focusedProvince) {
      const nextLevel = layers[1].some(city => city.p === region.id) ? 1 :
        layers[2].some(county => county.p === region.id) ? 2 : 0;
      setLevel(nextLevel,region);
    }
    const enclosed = atlasCN && chinaBoundaries.enclosed().some(entry => entry.region === region);
    if (region?.layer === 1 && region !== focusedCity && !enclosed) focusRegion(region);
    if (theme === 'autonomy' && region?.layer === 2 && showsAutonomy(region)) focusRegion(region);
    if (region?.provinceDirect && focusedCity && !enclosed) {
      setLevel(1,records.get(region.p));
    }
    select(region);
  }
});
canvas.addEventListener('pointercancel',event => contacts.delete(event.pointerId));
canvas.addEventListener('pointerleave',() => {
  hovered = null;
  tooltip.hidden = true;
  redraw();
});
function zoomCenter(multiplier) {
  const [px,py] = world(width/2,height/2);
  fly(clamp(zoom*multiplier,.8,maxMapZoom),px,py);
}
canvas.addEventListener('keydown',event => {
  const delta = {ArrowLeft:[60,0],ArrowRight:[-60,0],ArrowUp:[0,60],ArrowDown:[0,-60]}[event.key];
  if (delta) {
    cancelAnimationFrame(cameraFrame);
    x += delta[0];
    y += delta[1];
    redraw();
  } else if (event.key === '+' || event.key === '=') zoomCenter(1.65);
  else if (event.key === '-') zoomCenter(1/1.65);
  else if (event.key === 'Home') reset();
  else if (event.key === 'Escape') select(null);
  else return;
  event.preventDefault();
});
byId('plus').onclick = () => zoomCenter(1.65);
byId('minus').onclick = () => zoomCenter(1/1.65);
byId('home').onclick = reset;
for (const [desktop,mobile] of [['labels','mobileLabels'],['shade','mobileShade']]) {
  for (const [from,to] of [[desktop,mobile],[mobile,desktop]]) {
    byId(from).onchange = () => {
      byId(to).checked = byId(from).checked;
      redraw();
    };
  }
}
document.querySelector('.dismiss').onclick = () => select(null);
districtPicker.onchange = () => {
  const region = records.get(districtPicker.value) || records.get(districtPicker.dataset.scope);
  if (region?.locality) navigateToRegion(region);
  else select(region);
};
byId('closer').onclick = () => {
  if (!selected) return;
  const area = atlasCN ? chinaBoundaries.enclosed().find(entry => entry.region === selected) : null;
  const anchor = atlasCN ? chinaBoundaries.labelAnchor(selected) : undefined;
  fly(Math.min(zoom*2,maxMapZoom),...(anchor ?? [(area || selected).x,(area || selected).y]));
};
new ResizeObserver(resize).observe(canvas);
updateHint();
setTheme(theme);
async function loadJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(url+' ('+response.status+')');
  return response.json();
}
function loadUSLocalities(province) {
  if (!province) return;
  const state = {error:false};
  usLocalityLoads.set(province.id,state);
  loadJson(atlasData('localities/'+province.id+'.json?v=2025')).then(paths => {
    const regions = localRegionsByNation[2].get(province.id) || [];
    state.regions = regions.filter(region => Object.hasOwn(paths,region.id));
    for (const region of state.regions) region.d = paths[region.id];
    if (mode === 2 && focusedProvince === province) layers[2] = state.regions;
  }).catch(error => {
    state.error = true;
    console.error(error);
  }).finally(() => {
    if (mode === 2 && focusedProvince === province) {
      updateLevel();
      redraw();
    }
  });
}
function registerUSLocalities(entries) {
  // Prefer incorporated places where a village and a township overlap.
  entries.sort((a,b) => Number(a[0][0] === 'M')-Number(b[0][0] === 'M'));
  for (const [id,p,zh,original,code,kind,x,y,population,total,populationYear,b] of entries) {
    const nation = p.slice(0,2);
    const region = {id,p,nation,zh,original,code,n:nameFor(zh,original),x,y,b,layer:2,locality:true,
      type:usLocalityTypes[kind],stats:[null,population == null ? null : population/10000],population,total,populationYear};
    if (!usLocalitiesByCounty.has(p)) usLocalitiesByCounty.set(p,[]);
    usLocalitiesByCounty.get(p).push(region);
    if (!localRegionsByNation[2].has(nation)) localRegionsByNation[2].set(nation,[]);
    localRegionsByNation[2].get(nation).push(region);
    records.set(id,region);
  }
}
const boundaryVersion = atlasHistory?.geometryVersion || (atlasCN ? 'dissolved-rings' : atlasUS ? 'localities' : '');
Promise.all([loadJson(atlasData('admin-boundaries.json')+(boundaryVersion ? '?v='+boundaryVersion : '')),!atlasCN ? {} : loadJson('data/townships.json').catch(error => {
  console.error(error);
  return {};
}),!atlasCN ? [] : loadJson('data/direct-counties.json').catch(error => {
  console.error(error);
  return [];
}),!atlasCN && !atlasHistory ? loadJson(atlasData('statistics.json')+(atlasUS ? '?v=localities' : '')) : {},atlasUS ? loadJson(atlasData('localities/index.json?v=2025')).catch(error => {
  console.error(error);
  return [];
}) : [],atlasCN ? loadJson('data/china-boundaries/managed-districts.json?v=daq-seams').catch(error => {
  console.error(error);
  return null;
}) : null]).then(([data,townships,supplement,stats,usLocalities,management]) => {
  localStatistics = stats;
  const prefectureParents = new Set(data.city.map(region => region.p));
  const countyIds = new Set(data.county.map(region => region.id));
  data.county.push(...[...supplement,...(management?.districts || [])].filter(region => !countyIds.has(region.id)));
  const layerKeys = routeTier ? ['province','route','city','county'] : ['province','city','county'];
  layers = layerKeys.map((key,layer) => data[key].map(region => ({...region,zh:region.n,n:nameFor(region.n,sourceName(region)),layer})));
  if (!atlasCN) for (const [level,areas] of layers.entries()) {
    for (const area of areas) {
      if (!localRegionsByNation[level].has(area.nation)) localRegionsByNation[level].set(area.nation,[]);
      localRegionsByNation[level].get(area.nation).push(area);
    }
  }
  autonomyLayers = autonomyCategories.map(({layer,suffix},kind) => {
    const regions = layers[layer].filter(region => region.b && suffix.test(region.zh));
    for (const region of regions) region.autonomy = kind;
    return regions;
  });
  directCounties = !atlasCN ? [] : layers[2].filter(region => prefectureParents.has(region.p));
  for (const region of directCounties) region.provinceDirect = true;
  for (const region of [...layers[prefectureLayer],...directCounties]) {
    if (!metricRegionsByProvince.has(region.p)) metricRegionsByProvince.set(region.p,[]);
    metricRegionsByProvince.get(region.p).push(region);
  }
  localMetricScales.clear();
  townshipGroups = new Map(Object.entries(townships).map(([id,group]) => {
    const units = group.units.map(region => ({...region,p:id,layer:2,town:true}));
    return [id,{...group,units,boundaryCount:units.filter(region => region.b).length}];
  }));
  const townshipsByRegion = [...townshipGroups.values()].flatMap(group => group.units);
  layers[countyLayer].push(...townshipsByRegion.filter(region => region.b));
  country = data.outline ? path({g:data.outline}) : new Path2D();
  if (data.linework) {
    const openPath = g => g ? path({g,open:true}) : null;
    const convert = group => Object.fromEntries(Object.entries(group).map(([id,g]) => [id,openPath(g)]));
    historicalLinework = {state:openPath(data.linework.state),route:convert(data.linework.route),
      prefecture:convert(data.linework.prefecture)};
  }
  if (!data.outline) for (const province of layers[0]) country.addPath(path(province));
  records = new Map([...layers.flat(),...townshipsByRegion].map(region => [region.id,region]));
  if (atlasCN) chinaBoundaries.initialize(management);
  if (atlasUS) registerUSLocalities(usLocalities);
  universityLayer.rebuild();
  if (theme === 'autonomy') setLegend(autonomyLegend());
  document.dispatchEvent(new Event('atlas-regions-ready'));
  byId('loading').hidden = true;
  restoreLanguageView();
  updateLevel();
  redraw();
}).catch(error => {
  byId('loading').textContent = ui('行政区数据载入失败，请刷新重试。');
  console.error(error);
});
if (atlasCN) loadJson('data/maritime.json').then(data => {
  maritime = data;
  redraw();
}).catch(console.error);
if (atlasHistory) loadJson('data/history/china-land-border.json').then(lines => {
  const border = new Path2D();
  for (const [first,...rest] of lines) {
    border.moveTo(...project(...first));
    for (const point of rest) border.lineTo(...project(...point));
  }
  modernChinaLandBorder = border;
  redraw();
}).catch(console.error);
loadJson(atlasData('terrain/water.json')+(boundaryVersion ? '?v='+boundaryVersion : '')).then(data => {
  waterFeatures = data.map(([kind,rank,b,d]) => ({kind,rank,b,d}));
  redraw();
}).catch(console.error);

function drawInset() {
  const inset = byId('insetMap').getContext('2d');
  inset.setTransform(1,0,0,1,0,0);
  inset.fillStyle = '#b8ceca';
  inset.fillRect(0,0,216,204);
  inset.setTransform(.56,0,0,.56,-440*.56,-512*.56);
  inset.lineWidth = 1.7;
  inset.lineJoin = 'round';
  inset.lineCap = 'round';
  inset.strokeStyle = '#766651';
  inset.fillStyle = '#cbb68a';
  const hainan = records.get('460000');
  if (hainan) {
    inset.fill(path(hainan),'evenodd');
    inset.stroke(path(hainan));
  }
  for (const feature of maritime) inset.stroke(path(feature));
}
