const atlasCountries = {
 us:{
  name:'美国',originalName:'United States',shortName:'US',originalLocale:'en-US',languageName:'English',notes:'us-data',originalNotes:'notes-en.html', west:-125, north:50, lonScale:14, latScale:18,
  viewWidth:895, viewHeight:500, center:[420,223],
  levels:['州级','','县级'],
  search:'搜索州、县或 FIPS 编码'
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
  population:'https://www.bea.gov/data/income-saving/personal-income-county-metro-and-other-areas'
};
const atlasStatSources = atlasUS ? usSources : ukSources;
const usRegions = [
  {id:'lower48',label:'本土 48 州',lon:-95,lat:37.6,zoom:1},
  {id:'alaska',label:'阿拉斯加',lon:-158,lat:62,zoom:1.3},
  {id:'hawaii',label:'夏威夷',lon:-157.4,lat:20.8,zoom:7.4}
];
