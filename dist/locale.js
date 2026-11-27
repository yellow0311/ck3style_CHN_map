const uiCatalogs = {
  fr:{
    '切换国家':'Choisir un pays','显示语言':'Langue d’affichage','搜索行政区':'Rechercher un territoire','行政区候选':'Résultats',
    '图志手记':'Sources','图层典藏':'Couches cartographiques','地图主题':'Thèmes cartographiques','舆图图例':'Légende','显示设置':'Affichage',
    '地名标注':'Noms de lieux','地势晕渲':'Relief ombré','山河舆图编绘室':'Atlas Shanhe','交互地图':'Carte interactive · {country}',
    '方向键平移，加减键缩放，回到全国请按 Home':'Flèches pour déplacer la carte, + et − pour zoomer, Origine pour revenir à la vue nationale',
    '法国地图区域':'Territoire à afficher','图例':'Légende','关闭详情':'Fermer les détails','选择区县':'Choisir un arrondissement',
    '放大查看　↗':'Zoomer sur le lieu ↗','放大':'Zoom avant','缩小':'Zoom arrière','返回全国':'Vue nationale','载入舆图…':'Chargement de l’atlas…',
    '行政区划层级':'Niveau administratif','行政疆域':'Limites administratives','行政区划图':'Carte administrative · {country}',
    '山川地势':'Relief','海拔地形图':'Carte du relief · {country}','经济总量':'PIB','经济总量 · GDP':'PIB','地区生产总值':'Produit intérieur brut',
    '常住人口':'Population','法国基准人口':'Populations de référence · France','大学分布':'Enseignement supérieur',
    '高校分布':'Établissements d’enseignement supérieur · {country}','铁路网络':'Chemins de fer','主要铁路网':'Réseau ferroviaire · {country}',
    '民航机场':'Aéroports','民航机场与航线':'Aéroports et liaisons · {country}','公路网络':'Réseau routier','主要公路网':'Réseau routier national · {country}',
    '中国':'Chine','日本':'Japon','美国':'États-Unis','英国':'Royaume-Uni','法国':'France','大区':'Régions','省':'Départements',
    '行政专区':'Arrondissements','海外大区':'Région d’outre-mer','海外省':'Département d’outre-mer',
    '搜索大区、省、行政专区或行政区代码':'Région, département, arrondissement ou code',
    '法国本土':'France métropolitaine','瓜德罗普':'Guadeloupe','马提尼克':'Martinique','法属圭亚那':'Guyane','留尼汪':'La Réunion','马约特':'Mayotte',
    '主要线路与车站':'Lignes et gares principales','运输机场与直飞航线':'Aéroports et vols directs','高速公路与主要国道':'Autoroutes et routes nationales',
    '18 个大区':'18 régions','当年价':'Prix courants','基准人口':'Population de référence','暂无同口径数据':'Données comparables indisponibles',
    '按当前地区分档':'Classes calculées dans le territoire sélectionné','法国国家统计与经济研究所':'Insee','欧盟统计局':'Eurostat',
    '行政专区暂无同口径 GDP 数据。':'PIB comparable indisponible à l’échelle des arrondissements.',
    '马约特使用 2026 年人口普查数据。':'Mayotte utilise les chiffres du recensement de 2026.',
    '马约特的大区 GDP 使用 2023 年数据。':'Le PIB régional de Mayotte est celui de 2023.',
    '瓜德罗普 GDP 按来源口径含法属圣马丁。':'Le PIB de la Guadeloupe inclut Saint-Martin dans les données sources.',
    '大区边界':'Limites régionales','省界':'Limites départementales','行政专区边界':'Limites d’arrondissement',
    '暂无{level}边界':'Limites indisponibles · {level}','海拔（米）':'Altitude (m)','低于 {n}':'Moins de {n}','{n} 及以上':'{n} et plus','水域':'Eaux',
    '山脉、高原与盆地':'Massifs, plateaux et bassins','江河名称':'Cours d’eau','湖泊名称':'Lacs',
    '高程覆盖法国本土与科西嘉岛。':'L’altitude est disponible en France métropolitaine et en Corse.',
    '放大查看更多自然地名。':'Zoomez pour afficher davantage de noms de lieux.','地形与水系来源 ↗':'Sources du relief et des eaux ↗',
    '滚轮缩放 · 点击空白返回全国':'Molette pour zoomer · Cliquez hors du territoire pour revenir à la vue nationale',
    '滚轮缩放 · 拖动平移 · 点选地区':'Molette pour zoomer · Glissez pour déplacer · Cliquez sur un territoire',
    '全国':'Vue nationale','按行政区展示':'Par circonscription','按大区汇总':'Par région',
    '高程数据载入失败，请刷新重试。':'Échec du chargement des altitudes. Actualisez la page.','正在载入高程数据…':'Chargement des altitudes…',
    '约 {n} km':'Env. {n} km','暂无数据':'Aucune donnée','行政边界':'Limites administratives','行政区代码':'Code administratif',
    '行政区数据载入失败，请刷新重试。':'Échec du chargement des limites. Actualisez la page.',
    '亿欧元':'× 100 millions d’euros','万人':'× 10 000 personnes','没有找到匹配的行政区':'Aucun territoire trouvé','正在载入行政区…':'Chargement des territoires…',
    '公立':'Public','私立':'Privé','工程师学院':'Écoles d’ingénieurs','院校数据载入失败':'Échec du chargement des établissements',
    '正在载入院校…':'Chargement des établissements…','院校类别':'Types d’établissements','覆盖范围和来源 ↗':'Couverture et sources ↗',
    '校徽暂无':'Logo indisponible','院校名录':'Annuaire des établissements','院校网站':'Site de l’établissement','当前筛选下暂无已收录院校':'Aucun établissement ne correspond',
    '未选时显示全部，多选时显示符合任一标签的院校。放大后展开校徽，点选标记查看所在行政专区的院校名单。':
      'Sans filtre, tous les établissements sont affichés. Sélectionnez un marqueur pour consulter la liste locale.',
    '高速铁路（TGV）':'Lignes à grande vitesse (TGV)','常规铁路':'Lignes classiques','铁路类型':'Types de lignes','车站':'Gares',
    '铁路数据载入失败':'Échec du chargement des voies ferrées','正在载入铁路…':'Chargement du réseau ferroviaire…',
    '点选线路查看邻近车站。':'Sélectionnez une ligne pour voir ses gares.','铁路数据来源 ↗':'Sources du réseau ferroviaire ↗',
    '客运车站':'Gare voyageurs','货运节点':'Gare de fret','邻近线路':'Lignes desservant la gare','法国国家铁路公司 ↗':'SNCF Réseau ↗',
    '大型机场':'Grands aéroports','中型机场':'Aéroports moyens','小型机场':'Petits aéroports','等级待核验':'Non classé',
    '机场数据载入失败':'Échec du chargement des aéroports','正在载入机场…':'Chargement des aéroports…','机场类别':'Catégorie d’aéroport',
    '点选机场查看已收录的直飞航线。':'Sélectionnez un aéroport pour consulter les vols directs répertoriés.',
    '机场与航线来源 ↗':'Sources des aéroports et liaisons ↗','暂无已收录的直飞数据':'Aucun vol direct répertorié',
    '航线资料 ↗':'Sources des liaisons ↗','数据范围 ↗':'Couverture ↗','高速公路':'Autoroutes','主要国道':'Routes nationales principales',
    '公路数据载入失败':'Échec du chargement des routes','正在载入公路…':'Chargement du réseau routier…',
    '放大可查看区域线路。点选道路查看编号。':'Zoomez pour afficher les routes régionales et cliquez pour voir leur numéro.',
    '公路数据来源 ↗':'Sources du réseau routier ↗',
    '{n} 所院校':'{n} établissements','{n} 所院校 · {areas} 个地区':'{n} établissements · {areas} territoires','{n} 所':'{n}',
    '{n} 个已收录邻近车站':'{n} gares répertoriées','{lines} 条线路 · {stations} 个主要车站':'{lines} lignes · {stations} gares',
    '{n} 个图内直飞目的地':'{n} destinations directes sur la carte','{n} 个图外目的地':'{n} destinations hors carte',
    '{n} 座机场 · 航点快照 {date}':'{n} aéroports · Liaisons au {date}','{n} 条收录线路':'{n} routes répertoriées',
    '{n} / {total} 有数据':'{n} / {total} territoires renseignés','{year} 年':'{year}','{year} 年基准人口':'Population de référence {year}',
    '{label}资料 ↗':'Source · {label} ↗','分层地理图集':'Atlas géographique · {country}','{label}视图':'{label}'
  },
  ja:{
    '切换国家':'国を切り替える','显示语言':'表示言語','搜索行政区':'行政区域を検索','行政区候选':'検索結果',
    '图志手记':'地図の資料','图层典藏':'地図レイヤー','地图主题':'地図テーマ','舆图图例':'凡例','显示设置':'表示設定',
    '地名标注':'地名ラベル','地势晕渲':'地形の陰影','山河舆图编绘室':'山河地図帳','交互地图':'{country}のインタラクティブ地図',
    '方向键平移，加减键缩放，回到全国请按 Home':'矢印キーで移動、プラスとマイナスで拡大・縮小、Homeで全国表示',
    '日本地图区域':'日本の表示範囲','图例':'凡例','关闭详情':'詳細を閉じる','选择区县':'地区を選択','放大查看　↗':'拡大する ↗',
    '放大':'拡大','缩小':'縮小','返回全国':'全国表示','载入舆图…':'地図を読み込み中…','行政区划层级':'行政区域の階層',
    '行政疆域':'行政区域','行政区划图':'{country}の行政区域図','山川地势':'地形','海拔地形图':'{country}の標高図',
    '经济总量':'域内総生産','经济总量 · GDP':'域内総生産','地区生产总值':'域内総生産',
    '常住人口':'人口','日本人口普查':'日本の国勢調査','大学分布':'大学','高校分布':'{country}の大学分布',
    '铁路网络':'鉄道','主要铁路网':'{country}の鉄道網','民航机场':'空港','民航机场与航线':'{country}の空港と航空路線',
    '公路网络':'道路','主要公路网':'{country}の主要道路網','英国':'イギリス','美国':'アメリカ','法国':'フランス',
    '都道府县':'都道府県','市区町村':'市区町村','搜索都道府县、市区町村或行政区代码':'都道府県・市区町村・地域コードを検索',
    '日本全图':'日本全図','冲绳诸岛':'沖縄諸島','小笠原诸岛':'小笠原諸島',
    '主要线路与车站':'主な路線と駅','运输机场与直飞航线':'空港と直行便','高速公路与主要国道':'高速道路と主要国道',
    '47 个都道府县':'47都道府県','当年价':'名目値','全国人口普查':'国勢調査','暂无同口径数据':'比較できる統計値なし',
    '按当前地区分档':'選択地域内の区分','日本内阁府':'内閣府','日本总务省统计局':'総務省統計局',
    '市区町村 GDP 仅显示日本内阁府同一统计表中公布的城市。':'市区町村の域内総生産は、内閣府の同じ統計表で値が公表された市を表示します。',
    '都道府县边界':'都道府県界','市区町村边界':'市区町村界','暂无{level}边界':'{level}界のデータなし',
    '海拔（米）':'標高（メートル）','低于 {n}':'{n} 未満','{n} 及以上':'{n} 以上','水域':'水域',
    '山脉、高原与盆地':'山脈・高原・盆地','江河名称':'河川','湖泊名称':'湖沼','放大查看更多自然地名。':'拡大すると地形の地名が表示されます。',
    '地形与水系来源 ↗':'地形と水系の出典 ↗',
    '滚轮缩放 · 点击空白返回全国':'スクロールで拡大・縮小 · 地図の外をクリックすると全国表示',
    '滚轮缩放 · 拖动平移 · 点选地区':'スクロールで拡大・縮小 · ドラッグで移動 · クリックで地域選択',
    '全国':'全国','按市区町村展示':'市区町村別','按都道府县汇总':'都道府県別',
    '高程数据载入失败，请刷新重试。':'標高データを読み込めません。ページを再読み込みしてください。',
    '正在载入高程数据…':'標高データを読み込み中…','约 {n} km':'約 {n} km','暂无数据':'データなし',
    '行政边界':'行政界','行政区代码':'地域コード','行政区数据载入失败，请刷新重试。':'行政界を読み込めません。ページを再読み込みしてください。',
    '县':'県','特别区':'特別区','亿日元':'億円','万人':'万人','没有找到匹配的行政区':'該当する行政区域はありません',
    '正在载入行政区…':'行政区域を読み込み中…',
    '国立':'国立','公立':'公立','私立':'私立','院校数据载入失败':'大学データを読み込めません',
    '正在载入院校…':'大学を読み込み中…','院校类别':'大学の種別','覆盖范围和来源 ↗':'収録範囲と出典 ↗','校徽暂无':'校章データなし',
    '院校名录':'学校データ一覧','院校网站':'大学のウェブサイト','当前筛选下暂无已收录院校':'条件に該当する大学はありません',
    '未选时显示全部，多选时显示符合任一标签的院校。放大后展开校徽，点选标记查看所在市区町村的院校名单。':
      '未選択の場合は全大学を表示します。複数選択の場合はいずれかの種別に該当する大学を表示します。マーカーを選ぶと市区町村内の大学一覧が開きます。',
    '新干线':'新幹線','常规铁路、地铁与有轨电车':'在来線・地下鉄・路面電車','铁路类型':'鉄道の種類',
    '车站':'駅','铁路数据载入失败':'鉄道データを読み込めません','正在载入铁路…':'鉄道を読み込み中…',
    '点选线路查看沿途车站。':'路線を選択すると駅を表示します。','铁路数据来源 ↗':'鉄道の出典 ↗',
    '客运车站':'旅客駅','经过线路':'接続路線','日本国土交通省 ↗':'国土交通省 ↗',
    '大型机场':'大規模空港','中型机场':'中規模空港','小型机场':'小規模空港','等级待核验':'分類なし',
    '机场数据载入失败':'空港データを読み込めません','正在载入机场…':'空港を読み込み中…','机场类别':'空港の分類',
    '点选机场查看已收录的直飞航线。':'空港を選択すると収録した直行便を表示します。',
    '机场与航线来源 ↗':'空港と航空路線の出典 ↗','暂无已收录的直飞数据':'収録した直行便データなし',
    '航线资料 ↗':'航空路線データ ↗','数据范围 ↗':'収録範囲 ↗',
    '高速公路':'高速道路','主要国道':'主要国道','公路数据载入失败':'道路データを読み込めません',
    '正在载入公路…':'道路を読み込み中…','放大可查看区域线路。点选道路查看编号。':'拡大して地域の道路を表示し、クリックして詳細を確認できます。',
    '公路数据来源 ↗':'道路の出典 ↗','{n} 所院校':'{n} 校','{n} 所院校 · {areas} 个地区':'{n} 校 · {areas} 地域','{n} 所':'{n} 校',
    '{n} 个沿途车站':'収録駅 {n} 駅','{lines} 条线路 · {stations} 个车站':'{lines} 路線 · {stations} 駅',
    '{n} 个图内直飞目的地':'国内直行便 {n} 空港','{n} 个图外直飞城市':'国外直行便 {n} 都市',
    '{n} 座机场 · 国内 2025 财年 · 国际 2026 冬季':'{n} 空港 · 国内線 2025年度 · 国際線 2026年冬期','{n} 条收录线路':'{n} 路線を収録',
    '{n} / {total} 有数据':'{n} / {total} 地域に統計値あり','{year} 年':'{year} 年','{year} 财年':'{year} 年度',
    '{year} 年人口普查':'{year} 年国勢調査','{label}资料 ↗':'{label} ↗','分层地理图集':'{country}地理地図帳',
    '{label}视图':'{label}'
  },
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
    '州级':'States','县级':'Counties','市镇级':'Municipalities','组成国':'Nations','英格兰大区':'English regions','地方辖区':'Local authorities',
    '本土 48 州':'Lower 48','阿拉斯加':'Alaska','夏威夷':'Hawaii',
    '搜索州、县、市镇或 FIPS 编码':'Search states, counties, municipalities or FIPS codes',
    '州与联邦特区边界':'State and federal district boundaries','县及同级辖区':'Counties and equivalents',
    '市镇等地方单位边界':'Municipal and township boundaries','市镇级暂无同口径 GDP 数据。':'Comparable GDP is unavailable for municipalities.',
    '夏威夷市镇级显示人口普查指定地区。':'In Hawai‘i this level shows census-designated places.',
    '正在载入市镇边界…':'Loading municipality boundaries…','市镇边界载入失败，请重新选择市镇级。':'Municipality boundaries could not load. Select Municipalities to retry.',
    '此辖区按县级展示。':'This jurisdiction is shown at the county level.',
    '此辖区未收录下一级市镇。':'This county has no municipalities in the atlas.',
    '选择市镇等地方单位':'Choose a municipality or local area','市':'City','镇':'Town','村':'Village','独立市':'Independent city',
    '选择州后查看市镇，也可直接搜索市镇。':'Select a state to view municipalities, or search for one directly.',
    '乡镇':'Township','普查指定地区':'Census-designated place','市县合并区':'Consolidated city area',
    '镇级辖区':'Town-level jurisdiction','保留地':'Reservation',
    '美国人口普查局':'U.S. Census Bureau','本县辖区人口':'Population within this county',
    '完整辖区人口':'Population of the entire municipality','{n} 人':'{n} people',
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
function languageStorageKey(country) {
  const language = country.originalLocale?.split('-')[0];
  return language && language !== 'en' ? 'shanhe-atlas-language:'+language : 'shanhe-atlas-language';
}
function savedAtlasLanguage(country = atlasCountry) {
  try { return localStorage.getItem(languageStorageKey(country)); }
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
