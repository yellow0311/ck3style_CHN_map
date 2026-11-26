const airportLayer = (() => {
  const classes = {
    '4F':['4F 级','#8e392f',7.8],
    '4E':['4E 级','#8e5c25',7.1],
    '4D':['4D 级','#45655a',6.5],
    '4C':['4C 级','#4a647b',6],
    other:['其他等级','#6e596e',5.5],
    unknown:['等级待核验','#716b63',5.5]
  };
  const enabled = new Set(Object.keys(classes));
  const aircraft = new Path2D('M0-6c-.6 0-1 .8-1 1.6V-1L-6 2v1l5-1v2l-2 1v1L0 5l3 1V5L1 4V2l5 1V2L1-1v-3.4C1-5.2.6-6 0-6z');
  let data, pending, failed = false;
  let airports = [];
  let byCode = new Map();
  let marks = [];

  function legend() {
    const filters = Object.entries(classes).map(([key,[name,color]]) =>
      '<label><input type="checkbox" data-airport-grade="'+key+'" '+(enabled.has(key) ? 'checked' : '')+
      '><i class="swatch" style="background:'+color+'"></i>'+name+'</label>').join('');
    const status = failed ? '机场数据载入失败' : data ? airports.length+' 座机场 · 航点快照 '+data.date : '正在载入机场…';
    return '<div class="theme-filters" role="group" aria-label="飞行区等级">'+filters+'</div>'+
      '<p>'+status+'</p><p>点选机场查看已收录的直飞航线。</p>'+
      '<p><a href="notes.html#airport-data">机场与航线来源 ↗</a></p>';
  }
  function load() {
    if (data || pending) return;
    failed = false;
    pending = loadJson('data/airports.json').then(result => {
      airports = result.airports.map(([id,n,grade,lon,lat]) => {
        const [x,y] = project(lon,lat);
        const kind = classes[grade] ? grade : grade ? 'other' : 'unknown';
        return {id,n,grade,kind,x,y,overlay:'airports'};
      }).sort((a,b) => classes[a.kind][2]-classes[b.kind][2]);
      byCode = new Map(airports.map(airport => [airport.id,airport]));
      data = result;
    }).catch(error => {
      failed = true;
      console.error(error);
    }).finally(() => {
      pending = null;
      if (theme === 'airports') {
        byId('legend').innerHTML = byId('mobileLegend').innerHTML = legend();
        redraw();
      }
    });
  }
  function filter(event) {
    const key = event.target.dataset.airportGrade;
    if (!classes[key]) return;
    if (event.target.checked) enabled.add(key);
    else enabled.delete(key);
    for (const input of document.querySelectorAll('[data-airport-grade="'+key+'"]')) input.checked = enabled.has(key);
    if (selected?.overlay === 'airports' && !enabled.has(selected.kind)) select(null);
    hovered = null;
    tooltip.hidden = true;
    redraw();
  }
  function destinations(airport) {
    return data?.routes[airport?.id] || [];
  }
  function drawTrack(bounds,scale) {
    if (selected?.overlay !== 'airports') return;
    ctx.save();
    ctx.strokeStyle = '#416f8caa';
    ctx.lineCap = 'round';
    ctx.lineWidth = 1.35/scale;
    const [ax,ay] = [selected.x,selected.y];
    for (const code of destinations(selected)) {
      const target = byCode.get(code);
      if (!target) continue;
      const dx = target.x-ax, dy = target.y-ay;
      ctx.beginPath();
      ctx.moveTo(ax,ay);
      ctx.quadraticCurveTo(ax+dx/2,ay+dy/2-Math.min(75,Math.hypot(dx,dy)*.19),target.x,target.y);
      ctx.stroke();
    }
    ctx.restore();
  }
  function drawStations(scale) {
    marks = [];
    const linked = new Set(destinations(selected));
    function drawAirport(airport) {
      const active = airport === selected || airport === hovered;
      if (!enabled.has(airport.kind) && !linked.has(airport.id)) return;
      const [,color,size] = classes[airport.kind];
      const radius = size+(active ? 2 : 0);
      const sx = x+airport.x*scale, sy = y+airport.y*scale;
      if (sx < -radius || sy < -radius || sx > width+radius || sy > height+radius) return;
      ctx.save();
      ctx.translate(sx,sy);
      ctx.globalAlpha = selected?.overlay === 'airports' && !active && !linked.has(airport.id) ? .35 : 1;
      ctx.fillStyle = color;
      ctx.strokeStyle = '#fff1d8';
      ctx.lineWidth = active ? 2 : 1.15;
      ctx.beginPath();
      ctx.arc(0,0,radius,0,Math.PI*2);
      ctx.fill();
      ctx.stroke();
      ctx.scale(radius/8,radius/8);
      ctx.fillStyle = '#fff9e8';
      ctx.fill(aircraft);
      ctx.restore();
      marks.push({airport,sx,sy,radius});
    }
    for (const airport of airports) {
      if (airport !== selected && !linked.has(airport.id)) drawAirport(airport);
    }
    for (const code of linked) {
      const airport = byCode.get(code);
      if (airport) drawAirport(airport);
    }
    if (selected?.overlay === 'airports') drawAirport(selected);
  }
  function pick(sx,sy) {
    return marks.findLast(mark => Math.hypot(mark.sx-sx,mark.sy-sy) <= mark.radius+2)?.airport;
  }
  function show(airport) {
    const codes = destinations(airport);
    const local = codes.filter(code => byCode.has(code));
    const foreign = codes.filter(code => !byCode.has(code));
    byId('crumb').textContent = '民航机场 · '+(airport.grade ? airport.grade+' 级' : '等级待核验');
    byId('place').textContent = airport.n;
    byId('detailText').textContent = airport.id+' · '+(codes.length ? local.length+' 个图内直飞目的地'+
      (foreign.length ? ' · '+foreign.length+' 个境外目的地' : '') : '暂无已收录的直飞数据');
    byId('closer').hidden = zoom >= 70;
    const box = byId('universityDetail');
    const list = document.createElement('ul');
    list.className = 'school-city-list';
    for (const code of [...local,...foreign]) {
      const item = document.createElement('li');
      const target = byCode.get(code);
      if (target) {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = target.n+' · '+code;
        button.onclick = () => select(target);
        item.append(button);
      } else {
        item.textContent = (data.foreign[code] || code)+' · '+code;
      }
      list.append(item);
    }
    if (list.children.length) {
      box.replaceChildren(list);
      box.hidden = false;
    }
    const source = document.createElement('a');
    source.href = data.sources[airport.id] || 'notes.html#airport-data';
    source.textContent = data.sources[airport.id] ? '航线资料 ↗' : '数据范围 ↗';
    byId('detailSources').replaceChildren(source);
    byId('detailSources').hidden = false;
  }
  return {legend,load,filter,drawTrack,drawStations,pick,show};
})();

const roadLayer = (() => {
  const styles = {
    expressway:['国家高速','#a04a34',1.7],
    national:['普通国道','#9a783e',1.2]
  };
  const enabled = new Set(Object.keys(styles));
  let roads, pending, failed = false;

  function legend() {
    return Object.entries(styles).map(([kind,[label,color]]) =>
      '<label class="legendrow"><input type="checkbox" data-road-kind="'+kind+'" '+(enabled.has(kind) ? 'checked' : '')+
      '><i class="rail-sample" style="color:'+color+'"></i>'+label+'</label>').join('')+
      '<p>'+(failed ? '公路数据载入失败' : roads ? roads.length+' 条收录线路' : '正在载入公路…')+'</p>'+
      '<p>放大可查看区域线路。点选道路查看编号。</p><p><a href="notes.html#road-data">公路数据来源 ↗</a></p>';
  }
  function load() {
    if (roads || pending) return;
    failed = false;
    pending = loadJson('data/roads.json').then(result => {
      roads = result.roads.map(([id,n,kind,b,d]) => ({id,n:n || id,kind,b,d,overlay:'roads'}));
    }).catch(error => {
      failed = true;
      console.error(error);
    }).finally(() => {
      pending = null;
      if (theme === 'roads') {
        byId('legend').innerHTML = byId('mobileLegend').innerHTML = legend();
        redraw();
      }
    });
  }
  function shown(road) {
    return enabled.has(road.kind) && (zoom >= 1.45 || road.kind === 'national' || road.id.length < 5 || road === selected);
  }
  function filter(event) {
    const kind = event.target.dataset.roadKind;
    if (!styles[kind]) return;
    if (event.target.checked) enabled.add(kind);
    else enabled.delete(kind);
    for (const input of document.querySelectorAll('[data-road-kind="'+kind+'"]')) input.checked = enabled.has(kind);
    if (selected?.overlay === 'roads' && !shown(selected)) select(null);
    hovered = null;
    tooltip.hidden = true;
    redraw();
  }
  function drawTrack(bounds,scale) {
    ctx.save();
    ctx.clip(country,'evenodd');
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    for (const road of roads || []) {
      if (!shown(road) || !visible(road,bounds)) continue;
      const [,color,lineWidth] = styles[road.kind];
      ctx.strokeStyle = road === selected ? '#713830' : color;
      ctx.lineWidth = (lineWidth+(road === selected ? 1.6 : road === hovered ? .75 : 0))/scale;
      ctx.stroke(path(road));
    }
    ctx.restore();
  }
  function pick(sx,sy) {
    const [px,py] = world(sx,sy);
    const hit = 5/(zoom*fit);
    const bounds = [px-hit,py-hit,px+hit,py+hit];
    ctx.save();
    ctx.resetTransform();
    ctx.lineWidth = hit*1.9;
    try {
      if (!ctx.isPointInPath(country,px,py,'evenodd')) return;
      return roads?.findLast(road => shown(road) && visible(road,bounds) && ctx.isPointInStroke(path(road),px,py));
    } finally {
      ctx.restore();
    }
  }
  function show(road) {
    byId('crumb').textContent = styles[road.kind][0];
    byId('place').textContent = road.n;
    byId('detailText').textContent = road.id;
    byId('closer').hidden = true;
    const source = document.createElement('a');
    source.href = 'notes.html#road-data';
    source.textContent = '公路数据来源 ↗';
    byId('detailSources').replaceChildren(source);
    byId('detailSources').hidden = false;
  }
  return {legend,load,filter,drawTrack,pick,show};
})();
