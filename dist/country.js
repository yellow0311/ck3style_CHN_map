const atlasCountries = {
 fr:{
  name:'法国',originalName:'France',shortName:'FR',originalLocale:'fr-FR',languageName:'Français',
  capital:{name:'巴黎',original:'Paris',coordinates:[2.3522,48.8566]},
  notes:'fr-data',originalNotes:'notes-fr.html',west:-6,north:52,lonScale:49,latScale:69,
  viewWidth:780,viewHeight:760,center:[365,380],
  levels:['大区','省','行政专区'],
  search:'搜索大区、省、行政专区或行政区代码'
 },
 jp:{
  name:'日本',originalName:'日本',shortName:'Japan',originalLocale:'ja-JP',languageName:'日本語',
  capital:{name:'东京',original:'東京',coordinates:[139.744,35.676]},
  notes:'jp-data',originalNotes:'notes-ja.html', west:122,north:46,lonScale:30,latScale:38,
  viewWidth:755,viewHeight:855,center:[368,431],
  levels:['都道府县','','市区町村'],
  search:'搜索都道府县、市区町村或行政区代码'
 },
 us:{
  name:'美国',originalName:'United States',shortName:'US',originalLocale:'en-US',languageName:'English',notes:'us-data',originalNotes:'notes-en.html', west:-125, north:50, lonScale:14, latScale:18,
  capital:{name:'华盛顿特区',original:'Washington, D.C.',coordinates:[-77.0365,38.8977]},
  viewWidth:895, viewHeight:500, center:[420,223],
  levels:['州级','县级','市镇级'],
  search:'搜索州、县、市镇或 FIPS 编码'
 },
 uk:{
  name:'英国',originalName:'United Kingdom',shortName:'UK',originalLocale:'en-GB',languageName:'English',notes:'uk-data',originalNotes:'notes-en.html', west:-8.8, north:61.1, lonScale:51, latScale:78,
  capital:{name:'伦敦',original:'London',coordinates:[-0.1276,51.5072]},
  viewWidth:595, viewHeight:900, center:[270,445],
  levels:['组成国','英格兰大区','地方辖区'],
  search:'搜索组成国、大区、地方辖区'
 },
 cn:{
  name:'中国',originalName:'China',shortName:'China', west:73, north:54, lonScale:14, latScale:17,
  capital:{name:'北京市',coordinates:[116.4074,39.9042]},
  viewWidth:890, viewHeight:635, center:[420,305],
  levels:['省级','地级','县级'],
  search:'搜索省、市、区县'
 }
};
const atlasPeriods = {
  'sanguo-262':{
    name:'三国时期',originalName:'三国时期',year:262,
    mapTitle:'三国时期局势图',
    caption:'魏景元三年 · 汉景耀五年 · 吴永安五年 · 262 年',notes:'sanguo-262-data',volume:'三',
    capitalLegend:'都城',
    capitals:[
      {name:'洛阳',coordinates:[112.454,34.620]},
      {name:'成都',coordinates:[104.066,30.659]},
      {name:'建业',coordinates:[118.780,32.042]}
    ],
    west:62,north:57,lonScale:14,latScale:17,
    viewWidth:1240,viewHeight:780,center:[620,360],
    terrainGrid:{west:60,north:55,rate:30,cols:2550,rows:1350},
    routeTier:true,geometryVersion:'sanguo262-v3',
    levels:['政权','州级','郡国及治所','县级治所'],
    search:'搜索政权、州、郡国或县',
    terrainNote:'海拔采用现代测量。水系参照第三册图幅，部分河湖采用后世历史及现代地理资料。'
  },
  'sui-612':{
    name:'隋朝',originalName:'隋朝',year:612,
    caption:'大业八年 · 612 年',notes:'sui-612-data',volume:'五',
    capital:{name:'大兴',coordinates:[108.940,34.260]},
    west:62,north:57,lonScale:14,latScale:17,
    viewWidth:1150,viewHeight:760,center:[665,365],
    terrainGrid:{west:60,north:55,rate:30,cols:2550,rows:1350},
    geometryVersion:'sui612-v3',
    levels:['郡级','','县级治所'],
    search:'搜索郡或县',
    terrainNote:'海拔采用现代测量。水系参照第五册图幅，部分河湖采用后世历史及现代地理资料。'
  },
  'tang-741':{
    name:'唐朝',originalName:'唐朝',year:741,
    caption:'开元二十九年 · 741 年',notes:'tang-741-data',volume:'五',
    capital:{name:'长安',coordinates:[108.940,34.260]},
    west:62,north:57,lonScale:14,latScale:17,
    viewWidth:1380,viewHeight:860,center:[565,315],
    terrainGrid:{west:45,north:62,rate:30,cols:3150,rows:1560},
    geometryVersion:'tang741-v8',
    outlineFades:[[129,48.5,56.5,.45]],
    levels:['道及辖区','府州及治所','县及同级'],
    search:'搜索道、都护府、府州或县',
    extentNote:'河北道东北部渐隐处为渤海、黑水、室韦等民族羁縻概略范围。',
    terrainNote:'海拔采用现代测量。水系参照第五册图幅，部分河湖采用后世历史及现代地理资料。'
  },
  'song-1111':{
    name:'北宋时期',originalName:'北宋时期',year:1111,
    mapTitle:'北宋时期各国局势图',
    caption:'宋政和元年 · 辽天庆元年 · 1111 年',notes:'song-1111-data',volume:'六',
    capitalLegend:'都城及汗廷',
    capitals:[
      {name:'东京',coordinates:[114.348,34.797]},
      {name:'上京',coordinates:[119.369,43.959]},
      {name:'兴庆府',coordinates:[106.249,38.473]},
      {name:'羊苴咩城',coordinates:[100.16,25.70]},
      {name:'高昌',coordinates:[89.533,42.852]},
      {name:'八剌沙衮',coordinates:[75.25,42.747]},
      {name:'谦州',coordinates:[94.45,51.72]}
    ],
    west:62,north:57,lonScale:14,latScale:17,
    viewWidth:1460,viewHeight:885,center:[512,305],
    terrainGrid:{west:45,north:62,rate:30,cols:3150,rows:1560},
    routeTier:true,geometryVersion:'song1111-v1',
    levels:['政权与诸部','路道级','府州及治所','县级治所'],
    search:'搜索政权、路、道、府、州、县或治所',
    extentNote:'吐蕃诸部、黄头回纥与黠戛斯依 1111 年全图描绘概略范围。',
    terrainNote:'海拔采用现代测量。水系参照第六册图幅，部分河湖采用后世历史及现代地理资料。'
  },
  'song-1208':{
    name:'南宋时期',originalName:'南宋时期',year:1208,
    mapTitle:'南宋时期各国局势图',
    caption:'宋嘉定元年 · 金泰和八年 · 1208 年',notes:'song-1208-data',volume:'六',
    capitalLegend:'都城及汗廷',
    capitals:[
      {name:'临安',coordinates:[120.177,30.228]},
      {name:'中都',coordinates:[116.34,39.88]},
      {name:'中兴府',coordinates:[106.249,38.473]},
      {name:'羊苴咩城',coordinates:[100.16,25.70]},
      {name:'虎思斡耳朵',coordinates:[75.25,42.747]},
      {name:'大斡耳朵',coordinates:[109.06,47.181]}
    ],
    west:62,north:57,lonScale:14,latScale:17,
    viewWidth:1460,viewHeight:845,center:[512,325],
    terrainGrid:{west:45,north:60,rate:30,cols:3150,rows:1500},
    routeTier:true,geometryVersion:'song-refined-v4',
    levels:['政权与诸部','路级','府州及治所','县级治所'],
    search:'搜索政权、路、府、州、县或治所',
    extentNote:'大蒙古国与吐蕃等部依 1208 年全图描绘概略范围。',
    terrainNote:'海拔采用现代测量。水系参照第六册图幅，部分河湖采用后世历史及现代地理资料。'
  },
  'yuan-1330':{
    name:'元朝',originalName:'元朝',year:1330,caption:'至顺元年 · 1330 年',notes:'yuan-1330-data',volume:'七',
    capital:{name:'大都',coordinates:[116.399,39.917]},
    west:62,north:57,lonScale:14,latScale:17,
    viewWidth:1160,viewHeight:1050,center:[665,190],
    terrainGrid:{west:65,north:75,rate:30,cols:2550,rows:1950},
    outlineFades:[[100,68,73,0],[122,58,63,.29]],
    extentNote:'北部渐隐处为图册所示概略范围。',
    levels:['行省及辖区','路府州等','县及同级'],
    search:'搜索行省、路、府、州或县',
    terrainNote:'海拔采用现代测量。水系参照元代图册和历史资料，北部部分水系采用现代地形资料。'
  },
  'ming-1582':{
    name:'明朝',originalName:'明朝',year:1582,caption:'万历十年 · 1582 年',notes:'ming-1582-data',volume:'七',geometryVersion:'seams-2',
    capital:{name:'京师',coordinates:[116.397,39.918]},
    west:62,north:57,lonScale:14,latScale:17,
    viewWidth:1150,viewHeight:772,center:[716,331],
    levels:['两京与辖区','府州卫等','县及同级'],
    search:'搜索两京、布政司、府州、卫所或县',
    terrainNote:'海拔采用现代测量，河湖按明代图册校对，部分水系采用后世历史资料作参考。',
    frontierLegend:'东北女真诸部活动与羁縻范围（概略）'
  },
  'qing-1820':{
    name:'清朝',originalName:'清朝',year:1820,caption:'嘉庆二十五年 · 1820 年',notes:'qing-1820-data',volume:'八',
    capital:{name:'京师',coordinates:[116.397,39.918]},
    west:62,north:57,lonScale:14,latScale:17,
    viewWidth:1190,viewHeight:720,center:[630,342],
    levels:['行省及辖区','府州厅等','县及同级'],
    search:'搜索行省、将军辖区、府州厅或县',
    terrainNote:'海拔采用现代测量，历史河湖采用 1820 年地理资料。'
  }
};
const atlasParams = new URLSearchParams(location.search);
const countryParam = atlasParams.get('country');
const historyParam = atlasParams.get('history');
const atlasHistory = (!countryParam || countryParam === 'cn') && Object.hasOwn(atlasPeriods,historyParam) ? atlasPeriods[historyParam] : null;
const countryCode = Object.hasOwn(atlasCountries,countryParam) ? countryParam : 'cn';
const atlasCountry = atlasHistory || atlasCountries[countryCode];
const atlasUK = countryCode === 'uk';
const atlasUS = countryCode === 'us';
const atlasJP = countryCode === 'jp';
const atlasFR = countryCode === 'fr';
const atlasCN = countryCode === 'cn' && !atlasHistory;
const atlasData = file => 'data/'+(atlasHistory ? historyParam+'/' : atlasCN ? '' : countryCode+'/')+file;
const project = (lon,lat) => [((atlasUS && lon > 0 ? lon-360 : lon)-atlasCountry.west)*atlasCountry.lonScale,(atlasCountry.north-lat)*atlasCountry.latScale];
const unproject = (x,y) => [atlasCountry.west+x/atlasCountry.lonScale,atlasCountry.north-y/atlasCountry.latScale];
const ukSources = {
  boundary:'https://www.data.gov.uk/dataset/eae2345e-bd82-4c7a-9cae-61c4eb1db7e0/local-authority-districts-december-2025-boundaries-uk-bsc',
  gdp:'https://www.ons.gov.uk/economy/grossdomesticproductgdp/datasets/regionalgrossdomesticproductlocalauthorities/1998to2024',
  gdpRegional:'https://www.ons.gov.uk/economy/grossdomesticproductgdp/datasets/regionalgrossdomesticproductallnutslevelregions/1998to2024',
  population:'https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/bulletins/annualmidyearpopulationestimates/mid2025',
  devolution:'https://www.gov.uk/guidance/devolution-of-powers-to-scotland-wales-and-northern-ireland',
  aviation:'https://www.caa.co.uk/data-and-analysis/uk-aviation-market/airports/uk-airport-data/uk-airport-data-2025/annual-2025/'
};
const usSources = {
  boundary:'https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html',
  gdp:'https://www.bea.gov/data/gdp/gdp-county-metro-and-other-areas',
  population:'https://www.bea.gov/data/income-saving/personal-income-county-metro-and-other-areas',
  localBoundary:'https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.2025.html',
  localPopulation:'https://www.census.gov/data/tables/time-series/demo/popest/2020s-total-cities-and-towns.html',
  hawaiiPopulation:'https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html'
};
const jpSources = {
  boundary:'https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-2025.html',
  gdp:'https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/main_2023.html',
  population:'https://www.e-stat.go.jp/stat-search/files?layout=datalist&stat_infid=000040507382',
  aviation:'https://www.mlit.go.jp/k-toukei/koukuuyusoutoukei.html',
  railway:'https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-2025.html'
};
const frSources = {
  boundary:'https://www.data.gouv.fr/datasets/contours-administratifs',
  gdp:'https://www.insee.fr/fr/statistiques/8391986',
  gdpDepartment:'https://ec.europa.eu/eurostat/databrowser/view/nama_10r_3gdp/default/table',
  population:'https://www.insee.fr/fr/statistiques/8680726',
  populationMayotte:'https://www.insee.fr/fr/statistiques/9021428',
  railway:'https://ressources.data.sncf.com/explore/dataset/lignes-lgv-et-par-ecartement/'
};
const atlasStatSources = atlasFR ? frSources : atlasJP ? jpSources : atlasUS ? usSources : ukSources;
const frRegions = [
  {id:'metropolitan',label:'法国本土',zoom:1},
  {id:'guadeloupe',label:'瓜德罗普',lon:-61.53,lat:16.23,zoom:12},
  {id:'martinique',label:'马提尼克',lon:-61.02,lat:14.65,zoom:15},
  {id:'guyane',label:'法属圭亚那',lon:-53.23,lat:3.92,zoom:2.9},
  {id:'reunion',label:'留尼汪',lon:55.54,lat:-21.12,zoom:13},
  {id:'mayotte',label:'马约特',lon:45.14,lat:-12.82,zoom:19}
];
const usRegions = [
  {id:'lower48',label:'本土 48 州',lon:-95,lat:37.6,zoom:1},
  {id:'alaska',label:'阿拉斯加',lon:-158,lat:62,zoom:1.3},
  {id:'hawaii',label:'夏威夷',lon:-157.4,lat:20.8,zoom:7.4}
];
