const uiCatalogs = {
  en:{
    '切换国家':'Choose a country','显示语言':'Display language','搜索行政区':'Search administrative areas',
    '行政区候选':'Search results','图志手记':'Atlas notes','图层典藏':'Map layers','地图主题':'Map themes',
    '舆图图例':'Legend','显示设置':'Display','地名标注':'Place labels','地势晕渲':'Terrain shading',
    '山河舆图编绘室':'Shanhe Atlas','交互地图':'Interactive map of {country}',
    '方向键平移，加减键缩放，回到全国请按 Home':'Arrow keys to pan, plus or minus to zoom, Home for the country overview',
    '美国地图区域':'US map regions','图例':'Legend','关闭详情':'Close details','选择区县':'Choose a district',
    '放大查看　↗':'Zoom to place ↗','放大':'Zoom in','缩小':'Zoom out','返回全国':'Country overview',
    '载入舆图…':'Loading atlas…','行政区划层级':'Administrative levels',
    '行政疆域':'Boundaries','行政区划图':'Administrative map of {country}',
    '山川地势':'Terrain','海拔地形图':'Elevation map of {country}',
    '经济总量':'GDP','经济总量 · GDP':'GDP','地区生产总值':'Regional gross domestic product',
    '常住人口':'Population','年中人口估计':'Midyear population estimates',
    '国家公园':'National parks','美国国家公园':'US national parks',
    '权力下放':'Devolution','英国组成国与权力下放':'UK nations and devolution',
    '大学分布':'Universities','高校分布':'Universities in {country}',
    '铁路网络':'Railways','主要铁路网':'Major railways in {country}',
    '民航机场':'Airports','民航机场与航线':'Airports and routes in {country}',
    '公路网络':'Highways','主要公路网':'Major highways in {country}',
    '州级':'States','县级':'Counties','组成国':'Nations','英格兰大区':'English regions','地方辖区':'Local authorities',
    '本土 48 州':'Lower 48','阿拉斯加':'Alaska','夏威夷':'Hawaii',
    '搜索州、县或 FIPS 编码':'Search states, counties or FIPS codes',
    '搜索组成国、大区、地方辖区':'Search nations, regions or local authorities',
    '议会辖区':'Council areas','主要辖区':'Principal areas','地方政府区':'Local government districts',
    '主要线路与车站':'Main lines and stations','运输机场与直飞航线':'Airports and direct routes',
    '州际公路与主要美国国道':'Interstates and major US routes','高速公路与 A 级公路':'Motorways and A roads',
    '国家公园及相连保护区':'National parks and adjoining preserves',
    '50 州与哥伦比亚特区':'50 states and the District of Columbia','英国四个组成国':'Four UK nations',
    '当年价':'Current prices','年中常住':'Midyear resident population','暂无同口径数据':'Comparable figures unavailable',
    '按当前地区分档':'Grouped within the selected area','美国经济分析局（BEA）':'US Bureau of Economic Analysis (BEA)',
    '英国国家统计局（ONS）':'Office for National Statistics (ONS)',
    '州与联邦特区边界':'State and federal district boundaries','县及同级辖区':'Counties and equivalents',
    '组成国边界':'Nation boundaries','英格兰大区边界':'English region boundaries','{area}边界':'{area} boundaries','暂无{level}边界':'{level} boundaries unavailable',
    '地方治理类别':'Forms of regional government','苏格兰议会':'Scottish Parliament','威尔士议会':'Senedd Cymru',
    '北爱尔兰议会':'Northern Ireland Assembly','苏格兰、威尔士和北爱尔兰设有各自的分权立法机构。英格兰大区是统计地理区。':
      'Scotland, Wales and Northern Ireland each have a devolved legislature. England’s regions are statistical areas.',
    '英国政府 · 权力下放 ↗':'UK government · Devolution ↗',
    '海拔（米）':'Elevation (m)','低于 {n}':'Below {n}','{n} 及以上':'{n} and above','水域':'Water',
    '山脉、高原与盆地':'Ranges, plateaus and basins','江河名称':'Rivers','湖泊名称':'Lakes',
    '放大查看更多自然地名。':'Zoom in for more physical features.','地形与水系来源 ↗':'Terrain and water sources ↗',
    '滚轮缩放 · 点击空白返回全国':'Scroll to zoom · Click outside to return to the country view',
    '滚轮缩放 · 拖动平移 · 点选地区':'Scroll to zoom · Drag to pan · Click a region',
    '全国':'Country overview','按县展示':'By county','地方辖区统计':'By local authority','按州汇总':'By state','组成国汇总':'By nation',
    '高程数据载入失败，请刷新重试。':'Elevation data failed to load. Refresh to retry.',
    '正在载入高程数据…':'Loading elevation…','约 {n} km':'About {n} km','暂无数据':'No data',
    '年中人口':'Midyear population','来源统计沿用调整前区界':'Statistics use the previous boundary',
    '行政边界':'Boundaries','选择{area}':'Choose an area · {area}','行政区数据载入失败，请刷新重试。':
      'Administrative boundaries failed to load. Refresh to retry.',
    '州':'State','联邦特区':'Federal district','堂区':'Parish','自治市镇':'Borough','县级辖区':'County or equivalent',
    '伦敦金融城':'City of London','都市区':'Metropolitan district','非都市区':'Non-metropolitan district','郡':'County','行政郡':'Administrative county','非都市郡':'Non-metropolitan county','单一管理区':'Unitary authority',
    '都市自治市':'Metropolitan borough','伦敦自治市':'London borough','地方政府辖区':'Local government district',
    '英格兰郡辖区':'District','英格兰单一管理区':'Unitary authority','苏格兰议会辖区':'Scottish council area',
    '威尔士主要辖区':'Welsh principal area','北爱尔兰地方政府区':'Northern Ireland local government district',
    '亿英镑':'× £100 million','亿美元':'× $100 million','万人':'× 10,000 people',
    '省级行政区':'Top-level area','没有找到匹配的行政区':'No matching area','正在载入行政区…':'Loading regions…',
    '公立':'Public','私立非营利':'Private nonprofit','赠地院校':'Land-grant','历史悠久黑人院校':'Historically Black colleges and universities',
    '部落院校':'Tribal colleges','罗素大学集团':'Russell Group','研究学位授予权（英格兰）':'Research degree-awarding powers (England)',
    '专门院校':'Specialist institutions','院校数据载入失败':'Institution data failed to load','正在载入院校…':'Loading institutions…',
    '院校类别':'Institution types','覆盖范围和来源 ↗':'Coverage and sources ↗','校徽暂无':'Crest unavailable',
    '院校名录':'Institution register','院校网站':'Institution website','登记所在地':'Registered location',
    '当前筛选下暂无已收录院校':'No institutions match these filters',
    '未选时显示全部，多选时显示符合任一标签的院校。放大后展开校徽，点选标记查看所在县级辖区的院校名单。':
      'With no filters selected, all institutions appear. Select multiple filters to show any match. Zoom in to reveal crests and select a marker to see institutions in its county.',
    '未选时显示全部，多选时显示符合任一标签的院校。放大后展开校徽，点选标记查看所在地方辖区的院校名单。':
      'With no filters selected, all institutions appear. Select multiple filters to show any match. Zoom in to reveal crests and select a marker to see institutions in its local authority.',
    '东北走廊阿西乐（Acela）':'Acela (Northeast Corridor)','高速铁路（HS1 等）':'High-speed rail (including HS1)',
    '城际与长途客运线':'Intercity and long-distance passenger rail','普速客货干线':'Main passenger and freight lines',
    '重点货运线':'Major freight lines','铁路类型':'Railway categories','客站与货运节点':'Passenger stations and freight terminals',
    '铁路数据载入失败':'Railway data failed to load','正在载入铁路…':'Loading railways…',
    '点选线路查看邻近车站。':'Select a line to see nearby stations.','铁路数据来源 ↗':'Railway sources ↗',
    '客运车站':'Passenger station','货运节点':'Freight terminal','邻近车站':'Nearby stations','邻近线路':'Nearby lines',
    'Amtrak 或美国运输统计局 ↗':'Amtrak or US Bureau of Transportation Statistics ↗',
    '大型机场':'Large airports','中型机场':'Medium airports','小型机场':'Small airports','等级待核验':'Unclassified',
    '1,000 万人次及以上':'10 million passengers or more','100 万至不足 1,000 万人次':'1 to under 10 million passengers',
    '低于 100 万人次':'Under 1 million passengers','暂无客流数据':'Passenger statistics unavailable',
    '机场数据载入失败':'Airport data failed to load','正在载入机场…':'Loading airports…',
    '机场类别':'Airport categories','航站楼客流':'Terminal passengers','点选机场查看已收录的直飞航线。':'Select an airport to see listed direct routes.',
    '机场与航线来源 ↗':'Airport and route sources ↗','暂无已收录的直飞数据':'Direct-route data unavailable',
    '航线资料 ↗':'Route sources ↗','数据范围 ↗':'Coverage ↗',
    '州际公路（I）':'Interstates (I)','高速公路（M）':'Motorways (M)','主要美国国道（US）':'Major US routes (US)',
    '主要 A 级公路':'Major A roads','公路数据载入失败':'Highway data failed to load','正在载入公路…':'Loading highways…',
    '放大可查看区域线路。点选道路查看编号。':'Zoom in for regional roads. Select a highway to see its route number.',
    '公路数据来源 ↗':'Highway sources ↗','定位公园':'Find a park','选择公园':'Choose a park',
    '国家公园资料载入失败':'Park data failed to load','正在载入国家公园…':'Loading national parks…',
    '点选标记或范围查看公园。':'Select a marker or boundary to see the park.',
    '公园数据来源 ↗':'Park sources ↗','国家公园管理局 ↗':'National Park Service ↗',
    '{n} 所':'{n}','{n} 座国家公园':'{n} national parks','{n} 所院校':'{n} institutions','{n} 所院校 · {areas} 个地区':'{n} institutions · {areas} areas',
    '{n} 个已收录邻近车站':'{n} listed nearby stations','{n} 个已收录主要车站':'{n} listed main stations',
    '{lines} 条线路 · {stations} 个主要车站':'{lines} lines · {stations} main stations',
    '{n} 个图内直飞目的地':'{n} direct destinations on map','{n} 个图外目的地':'{n} destinations outside map',
    '{year} 年航站楼旅客 {n} 人次':'{year} terminal passengers · {n}',
    '{n} 座机场 · {date} 年统计':'{n} airports · {date} statistics',
    '{n} 座机场 · 航点快照 {date}':'{n} airports · Route snapshot {date}','{n} 条收录线路':'{n} mapped routes',
    '{n} / {total} 有数据':'{n} / {total} with data','{year} 年':'{year}','{year} 年年中人口':'{year} midyear population',
    '《{label}》':'{label}','{label}资料 ↗':'{label} source ↗',
    '分层地理图集':'Geographic atlas of {country}','{label}视图':'{label}'
  }
};

const atlasQuery = new URLSearchParams(location.search);
function savedAtlasLanguage() {
  try { return localStorage.getItem('shanhe-atlas-language'); }
  catch { return null; }
}
const languageParam = atlasQuery.get('lang');
const foreignLanguage = (['zh','original'].includes(languageParam) ? languageParam : savedAtlasLanguage()) === 'original' ? 'original' : 'zh';
const showOriginal = Boolean(atlasCountry.originalLocale && foreignLanguage === 'original');
const atlasLocale = showOriginal ? atlasCountry.originalLocale : 'zh-CN';
const uiMessages = uiCatalogs[atlasLocale.split('-')[0]];
const nameFor = (chinese,original) => (showOriginal ? original || chinese : chinese || original) || '';
const countryName = config => nameFor(config.name,config.originalName);
const sourceName = record => record.original ?? record.en;
function ui(message, values = {}) {
  const text = (uiMessages && Object.hasOwn(uiMessages,message) ? uiMessages[message] : message) || '';
  return text.replace(/\{(\w+)\}/g,(key,field) => values[field] ?? key);
}
function translateStatic(root) {
  if (!uiMessages) return;
  for (const element of root.querySelectorAll('[aria-label],[placeholder]')) {
    for (const attr of ['aria-label','placeholder']) {
      if (element.hasAttribute(attr)) element.setAttribute(attr,ui(element.getAttribute(attr)));
    }
  }
  const walker = document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const phrase = node.data.trim();
    if (!phrase) continue;
    const translated = ui(phrase);
    if (translated !== phrase) node.data = node.data.replace(phrase,translated);
  }
}
function initializeOriginalChrome() {
  for (const heading of document.querySelectorAll('.legend h3,.settings h3')) heading.querySelector('span').hidden = true;
  document.querySelector('.sidetop .eyebrow').hidden = true;
}
function atlasNotes(anchor) {
  const page = showOriginal && atlasCountry.originalNotes ? atlasCountry.originalNotes : 'notes.html';
  return page+(!atlasCN ? '?country='+countryCode+'&lang='+foreignLanguage : '')+'#'+anchor;
}
document.documentElement.lang = atlasLocale;
