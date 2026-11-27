const atlasCountries = {
 fr:{
  name:'法国',originalName:'France',shortName:'FR',originalLocale:'fr-FR',languageName:'Français',
  notes:'fr-data',originalNotes:'notes-fr.html',west:-6,north:52,lonScale:49,latScale:69,
  viewWidth:780,viewHeight:760,center:[365,380],
  levels:['大区','省','行政专区'],
  search:'搜索大区、省、行政专区或行政区代码'
 },
 jp:{
  name:'日本',originalName:'日本',shortName:'Japan',originalLocale:'ja-JP',languageName:'日本語',
  notes:'jp-data',originalNotes:'notes-ja.html', west:122,north:46,lonScale:30,latScale:38,
  viewWidth:755,viewHeight:855,center:[368,431],
  levels:['都道府县','','市区町村'],
  search:'搜索都道府县、市区町村或行政区代码'
 },
 us:{
  name:'美国',originalName:'United States',shortName:'US',originalLocale:'en-US',languageName:'English',notes:'us-data',originalNotes:'notes-en.html', west:-125, north:50, lonScale:14, latScale:18,
  viewWidth:895, viewHeight:500, center:[420,223],
  levels:['州级','县级','市镇级'],
  search:'搜索州、县、市镇或 FIPS 编码'
 },
 uk:{
  name:'英国',originalName:'United Kingdom',shortName:'UK',originalLocale:'en-GB',languageName:'English',notes:'uk-data',originalNotes:'notes-en.html', west:-8.8, north:61.1, lonScale:51, latScale:78,
  viewWidth:595, viewHeight:900, center:[270,445],
  levels:['组成国','英格兰大区','地方辖区'],
  search:'搜索组成国、大区、地方辖区'
 },
 cn:{
  name:'中国',originalName:'China',shortName:'China', west:73, north:54, lonScale:14, latScale:17,
  viewWidth:890, viewHeight:635, center:[420,305],
  levels:['省级','地级','县级'],
  search:'搜索省、市、区县'
 }
};
const countryParam = new URLSearchParams(location.search).get('country');
const countryCode = Object.hasOwn(atlasCountries,countryParam) ? countryParam : 'cn';
const atlasCountry = atlasCountries[countryCode];
const atlasUK = countryCode === 'uk';
const atlasUS = countryCode === 'us';
const atlasJP = countryCode === 'jp';
const atlasFR = countryCode === 'fr';
const atlasCN = countryCode === 'cn';
const atlasData = file => 'data/'+(atlasCN ? '' : countryCode+'/')+file;
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
