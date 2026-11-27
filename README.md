# 山河舆图 · Shanhe Atlas

受《十字军之王 III》（CK3）地图模式启发的交互地理图集。顶部可切换中国、法国、日本、英国和美国，使用各国的行政区划、地形、GDP、人口、高校和交通数据。中国另有人文地理、饮食风物和民族自治图层，英国设有权力下放专题，美国设有国家公园专题。

github静态托管网站：https://yellow0311.github.io/ck3style_country_map/

[更新日志](CHANGELOG.md)

## 如何浏览

- **切换国家**。顶部选择「中国」「法国」「日本」「英国」或「美国」，共有专题会切换到对应国家的数据。从国家专属专题切换到其他国家时，可回到行政地图。
- **切换语言**。在外国图集顶部选择「中文」或该国原语言。英国和美国提供中文与英文，共享英语图集的偏好。日本默认中文，可切换至日语。地图标签、图例与详情同步切换，搜索始终支持中文名、原名和行政区代码。
- **浏览英国**。四个组成国均可点选。英格兰按大区进一步下钻到地方辖区，其余三个组成国直接下钻到辖区。行政区搜索支持中文名、原名和 ONS 编码。英国 GDP 为 2024 年现价数据，人口为 2025 年年中估计。
- **浏览法国**。按大区、省和行政专区下钻，通过地图标题下方的菜单定位五个海外大区。默认显示简体中文，可切换法语。铁路图层可单独筛选高速铁路。法国本土与科西嘉岛可查看海拔地形。
- **浏览日本**。按都道府县和市区町村下钻，搜索支持中文、日文及五位行政区代码。查看 2025 年国势调查人口与 2023 财年现价 GDP。铁路图层可单独显示新干线，机场图层展示已收录的国内航线和国际直飞城市。
- **浏览美国**。点选州或联邦特区可进入县级视图，支持按名称和 FIPS 编码搜索。地图标题下可在本土 48 州、阿拉斯加和夏威夷间定位。可从国家公园图例下拉定位公园。美国统计使用 2024 年现价 GDP 和年中人口，铁路显示 Amtrak 城际与长途客运。

- **切换行政层级**：点选底部的省级、地级或县级。滚轮以指针为中心缩放，拖动可平移，触屏支持双指缩放。
- **搜索行政区**：在顶部输入名称、常用简称或行政区代码。候选显示上级行政区以区分同名地点。点选候选后地图定位并调整缩放，也可用方向键和回车选择。
- **逐级查看**：点选省份显示省内地级边界，再点选地级行政区显示该地区的县界。同省其他地级区轻度淡化，外省继续保持较强的淡化效果。底部的「地级」可返回省内地级视图。
- **省或自治区直辖县级行政区**：在地级视图中也可查看和点选，例如湖北的仙桃、潜江、天门和神农架林区。直辖县级边界以虚线标识。
- **直辖市和港澳**：点选北京、天津、上海、重庆、香港或澳门后，直接显示下辖区县或分区。可在地图上点选，也可用详情卡里的下拉菜单查看。
- **直辖镇街的地级市**：点选东莞、中山、儋州或嘉峪关后，显示各市直接管辖的镇、街道或办事处。详情卡也可按名称选择。
- **返回全国**：点选地图上的空白处、底部的「省级」或右下角返回按钮，也可在地图获得焦点后按 `Home`。逐级点选和返回全国都保留当前视角。
- **查阅专题**：切换图层并按图例阅读。点选行政区域或专题样本点可打开详情。
- **查看中国人文地理和饮食风物**。人文地理用渐变表示历史文化区域，饮食风物按城市标注代表食物。点选标记可查看说明。
- **查看山川地势**。图例以米标注六档海拔，水域使用蓝色。全国视图标注主要山脉、江河和湖泊，放大后可看更多自然地名。「地名标注」可一并开关自然与行政地名。切换图层时保留缩放、平移位置和当前行政区选择。
- **筛选民族自治地方**：打开「民族自治」，在图例分别开关自治区、自治州、自治县和自治旗。各层用独立颜色标记。
- **浏览高校**。缩小地图时查看省级汇总与城市预览，放大后在地级行政区代表点附近展开各校校徽。空间不足时，剩余院校用 `+N` 标记。点选校徽或汇总标记可查看所在地区的院校名单。可多选 985、211、双一流、中外／港澳合作、教育部直属等标签。
- **比较省内经济与人口**。进入省份后，图例按该省收录的地级数据分档。颜色越深，数值越高。灰色代表缺少该项数据。
- **查看铁路网络**。可筛选高铁与客运专线、普速客货干线、重点货运线及车站。点选线路可浏览沿途收录的主要车站，再点站名可定位。
- **查看民航机场**。机场按飞行区等级着色。点选机场可查看已收录的直飞目的地，图内航线用弧线连接，境外航点在详情中列出。资料为公开航点表快照，实时航班以承运方公布为准。
- **查看公路网络**。可分别筛选国家高速与普通国道，放大可见区域高速，点选道路可看编号。图层采用 OpenStreetMap 中有 G 编号的已绘制路段。

[图志手记](dist/notes.html) 记录了 CK3 地图调研、设计取舍和数据覆盖范围。网站发布后可从首页打开在线版。

## 本地运行

在含有本 README 的目录执行以下命令。Windows 也可使用 `python` 或 `py -3`。

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory dist
```

可直接打开[中国测试页](http://127.0.0.1:8765/)、[日本测试页](http://127.0.0.1:8765/?country=jp&lang=zh)、[英国测试页](http://127.0.0.1:8765/?country=uk)、[美国测试页](http://127.0.0.1:8765/?country=us)、[中国人文地理](http://127.0.0.1:8765/?view=culture)或[中国饮食风物](http://127.0.0.1:8765/?view=food)。项目使用原生 HTML、CSS、JavaScript 和 Canvas，支持 WebGL 2 加速平面底图。高程、边界、铁路和高校名录随站点提供，校徽按需联网读取。

## 部署到 GitHub Pages

在 GitHub 创建一个空仓库。GitHub Free 可使用公开仓库。将下面命令里的 `OWNER` 和 `REPO` 换成 GitHub 用户名或组织名及仓库名，然后在上传目录中执行。该目录应直接包含本 README、`.github/` 和 `dist/`。

```bash
git init -b main
git add -A
git commit -m "Initial release of Shanhe Atlas"
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin main
```

如果目录已经是 Git 仓库，可以跳过 `git init`。如果已有 `origin`，先用 `git remote -v` 确认它指向你要发布的仓库，再推送。

1. 在 GitHub 仓库打开 **Settings → Pages**，将 **Build and deployment → Source** 设为 **GitHub Actions**。
2. 在 **Actions → Deploy to GitHub Pages** 选择 **Run workflow**，分支选 `main`。如果首次推送后已经成功部署，可直接打开站点。
3. 部署成功后，从 **Settings → Pages** 打开站点。普通项目仓库通常使用 `https://OWNER.github.io/REPO/`，之后每次推送到 `main` 都会自动部署。

工作流直接发布 `dist/` 中的静态文件。地图、数据和图志手记使用相对路径，支持带仓库名前缀的站点地址。部署无需安装依赖或运行数据生成脚本。 [GitHub Pages 发布源官方文档](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

## 项目结构

```text
.
├── .github/workflows/pages.yml   # GitHub Pages 部署
├── .gitignore
├── README.md
├── dist/                        # 可直接托管的静态网站
│   ├── index.html               # 交互地图
│   ├── atlas.js                 # 地图绘制、镜头及交互
│   ├── themes.js                # 图层配置、专题样本和省级统计
│   ├── terrain.js               # 平面地形晕渲与海拔分级配色
│   ├── search.js                # 行政区搜索与定位
│   ├── universities.js          # 高校分布与筛选
│   ├── railways.js              # 铁路线和站点交互
│   ├── transport.js             # 机场、航线与公路交互
│   ├── style.css
│   ├── notes.html               # 调研、设计和数据说明
│   └── data/
│       ├── admin-boundaries.json # 三级行政边界，按环编码坐标差值
│       ├── direct-counties.json  # 新疆直辖县级市的补充边界和驻地
│       ├── city-stats.js        # 地级统计、年份及来源
│       ├── district-stats.js    # 直辖市及港澳分区统计及来源
│       ├── townships.json       # 四个地级市的直辖镇街名录及边界
│       ├── universities.json    # 院校、标签及按地级行政区归并的校区
│       ├── railways.json         # 铁路矢量线路及主要站点
│       ├── airports.json         # 机场点位、飞行区等级与客运航点快照
│       ├── roads.json            # 国家高速与普通国道线路
│       ├── maritime.json        # 海域示意
│       └── terrain/             # 数值高程网格和矢量水系
└── scripts/
    ├── prepare_boundaries.py    # 更新行政边界数据
    ├── prepare_direct_counties.py # 导入新疆直辖县级市的补充数据
    ├── prepare_townships.py     # 导入直辖镇街边界
    ├── prepare_universities.py  # 合并院校名录和校区资料
    ├── university_additions.json # 补充校区、地方建设批次和地区名录
    ├── prepare_railways.py       # 生成铁路线和车站数据
    ├── railway_routes.json      # 选取的主线与站点
    ├── prepare_terrain.py       # 生成高程网格和水系数据
    ├── prepare_airports.py      # 整理机场、等级和航点快照
    └── prepare_roads.py         # 从 OSM 提取带 G 编号的路段
```

## 数据来源和口径

- **行政区划**的 DataV 快照收录 34 个省级、333 个地级及 2,870 个县级记录，台湾部分收录省级轮廓。新疆新星市、白杨市的边界及草湖市的政府驻地点位由 OpenStreetMap（ODbL）补充，草湖市全域边界待补。另收录东莞、中山、儋州和嘉峪关的 76 个镇街及儋州的 3 个办事处，名称和隶属关系按各市政府名录核对，边界来自 OpenStreetMap。 [阿里云 DataV 地理小工具](https://datav.aliyun.com/portal/school/atlas/area_selector) · [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
- **地形**使用 Mapzen Terrain Tiles 的数字高程。「山川地势」按海拔分级着色，并绘制 Natural Earth 矢量河流和湖泊。其他图层可选用实时地势晕渲。所有底图均按中国行政区边界裁切。全国视野使用 2 角分网格，放大后在东经 70–140°、北纬 15–55° 载入 30 角秒网格。 [Mapzen 数据与署名](https://registry.opendata.aws/terrain-tiles/) · [Natural Earth 水系](https://www.naturalearthdata.com/downloads/10m-physical-vectors/)
- **GDP 与人口**图层使用 2024 年大陆 31 个省级地区数据。地级数据优先采用 2024 年现价 GDP 和年末常住人口，缺项可采用相邻年份的同口径数据。详情逐项标出年份、数值和来源。重庆统计按 2024 年区划，綦江区含万盛。香港分区显示 2024 年陆上非住院人口。澳门分区显示 2021 年陆地面积，七个堂区另列 2021 年人口普查的 13–35 岁人口。缺项显示「暂无数据」。 [省级数据来源](https://tjj.gansu.gov.cn/tjj/c117468/202505/174143566/files/4db368f09fac4efb95b5d73aa316e1bf.pdf)
- **铁路网络**选取 63 条代表性线路，使用 OpenStreetMap 的轨道几何和 853 个站点记录。归类依据线路的主要用途。车站圆点表示客站，方点表示货运节点。 [铁路数据口径](dist/notes.html#railway-data) · [© OpenStreetMap contributors（ODbL）](https://www.openstreetmap.org/copyright)

英国数据存放于 `dist/data/uk/`，来源和覆盖范围见[英国图志手记](dist/notes.html#uk-data)。`scripts/prepare_uk_*.py` 负责整理英国各主题的数据。重建英国铁路、公路或高校数据后，运行 `python3 scripts/localize_uk_names.py` 应用中文名称。

美国数据存放于 `dist/data/us/`，由 `scripts/prepare_us_admin.py`、`scripts/prepare_us_themes.py` 和 `scripts/prepare_us_terrain.py` 生成。重建美国边界、高校、铁路和机场数据后，运行 `python3 scripts/localize_us_names.py` 应用双语名称。数据年份与覆盖说明见[美国图志手记](dist/notes.html#us-data)。

法国资料见[法国图志手记](dist/notes.html#fr-data)。制图数据由 `scripts/prepare_fr.py` 和 `scripts/prepare_fr_terrain.py` 生成，静态数据存放于 `dist/data/fr/`。

日本各图层的数据年份、覆盖范围和来源见[日本图志手记](dist/notes.html#jp-data)。制图数据由 `scripts/prepare_jp.py` 和 `scripts/prepare_jp_terrain.py` 生成，静态数据存放于 `dist/data/jp/`。

新增外国图集时，在 `dist/country.js` 登记原语言地区代码 `originalLocale`、原文国名 `originalName` 和语言菜单名称 `languageName`。菜单会自动出现。图层名称字段保持中文和原文并存。对象数据可用原文字段 `original`，已有的 `en` 仍兼容。界面词表在 `dist/locale.js` 中按语言添加，已有词表可复用。参数 `lang=zh` 和 `lang=original` 可用于分享指定语言的视图。

仓库自带运行所需的静态数据。需要刷新中国边界时，可运行 `python3 scripts/prepare_boundaries.py`。脚本使用 Python 3、`curl` 和网络连接，更新 `dist/data/admin-boundaries.json` 与 `dist/data/maritime.json`。

要更新镇街边界，安装 Python 包 `osmium` 和 `shapely`，下载 Geofabrik 的广东、海南、甘肃 OpenStreetMap 提取文件，并分别命名为 `guangdong.osm.pbf`、`hainan.osm.pbf`、`gansu.osm.pbf`。运行 `python3 scripts/prepare_townships.py <提取文件目录>` 生成 `dist/data/townships.json`。 [Geofabrik 中国分区下载](https://download.geofabrik.de/asia/china.html)

要更新新疆直辖县级市的补充数据，使用相同的 Python 包，运行 `python3 scripts/prepare_direct_counties.py <新疆提取文件>` 生成 `dist/data/direct-counties.json`。 [Geofabrik 新疆提取文件](https://download.geofabrik.de/asia/china/xinjiang.html)

要重建地形数据，安装 Python 包 `numpy`、`Pillow` 和 `pyshp` 后运行 `python3 scripts/prepare_terrain.py`。脚本缓存源数据并写入 `dist/data/terrain/`，网站运行时直接读取打包后的高程数据。

要重建铁路数据，安装 Python 包 `shapely`，运行 `python3 scripts/prepare_railways.py <OSM 关系缓存目录>`。脚本将缺少的关系下载到缓存目录，并生成 `dist/data/railways.json`。

要重建公路数据，安装 Python 包 `osmium` 和 `shapely`，从 Geofabrik 下载中国 OSM PBF，再运行 `python3 scripts/prepare_roads.py <中国 PBF 路径> --date <快照日期>`。 [Geofabrik 中国快照](https://download.geofabrik.de/asia/china/)

要重建机场与航线数据，安装 Python 包 `beautifulsoup4` 和 `lxml`。缓存目录包含 AirportMiles 的 `airports.json`、机场等级表 `airport-grades.html` 和 `airport-pages/`。后者保存各机场客运航点页面，文件名采用 `IATA.html`，并在 `urls.json` 记录 IATA 代码与来源网址的对应关系。运行 `python3 scripts/prepare_airports.py <缓存目录> --date <收集日期>`。 [机场数据与口径](dist/notes.html#airport-data)

## 重建院校名录

将以下源文件保存到同一目录，安装 `xlrd`，再运行 `python3 scripts/prepare_universities.py <源文件目录>`。在 `scripts/university_additions.json` 中补录有办学依据的异地校区和省级建设批次。院校按学校标识和地区记录，同一院校在同一个地级区域内只计一次。

| 文件名 | 来源 |
| --- | --- |
| `official.xls` | [教育部《全国普通高等学校名单》](https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/A03/202606/W020260618416094865984.xls) |
| `universities.jsonl` | [cn-universities 的工程标签和军队院校整理](https://github.com/roy-tian/cn-universities/blob/master/data/universities.jsonl) |
| `eol-list.json` | [教育在线院校库校名与校徽索引](https://static-data.gaokao.cn/www/2.0/school/list.json) |
| `rank.json` | [软科校徽索引的公开整理](https://github.com/damitheswitch/china-universities-dataset/blob/main/data/universities.json) |
| `tw.csv` | [台湾 114 学年度大专校院及校长名录](https://udb.moe.edu.tw/ulist/Resource)中的同名 CSV |
| `tw-logos.html` | [海外联合招生委员会官方校徽页](https://cmn-hant.overseas.ncnu.edu.tw/about-us/university-introduction/university-introduction-logo/) |
