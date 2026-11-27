const railwayLayer = (() => {
  const groups = {
    passenger:{label:atlasFR ? '高速铁路（TGV）' : atlasJP ? '新干线' : atlasUS ? '东北走廊阿西乐（Acela）' : atlasUK ? '高速铁路（HS1 等）' : '高铁与客运专线',color:'#a13e37',dash:[],width:2.3},
    mixed:{label:atlasFR ? '常规铁路' : atlasJP ? '常规铁路、地铁与有轨电车' : atlasUS ? '城际与长途客运线' : '普速客货干线',color:'#406d80',dash:[],width:1.65},
    ...(atlasUS || atlasJP || atlasFR ? {} : {freight:{label:'重点货运线',color:'#90621d',dash:[5,3],width:2.1}})
  };
  const enabled = new Set([...Object.keys(groups),'stations']);
  let lines = [];
  let stations = [];
  let spots = [];
  let pending;
  let loaded = false;
  let failed = false;

  function legend() {
    const checkbox = (key,content,label) => '<label><input type="checkbox" data-rail-filter="'+key+'" '+
      (enabled.has(key) ? 'checked' : '')+'>'+content+label+'</label>';
    return '<div class="theme-filters" role="group" aria-label="铁路类型">'+
      Object.entries(groups).map(([key,{color,dash,label}]) => checkbox(key,
        '<i class="rail-sample'+(dash.length ? ' rail-dashed' : '')+'" style="color:'+color+'"></i>',label)).join('')+
      checkbox('stations','<i class="rail-dot"></i><i class="rail-square"></i>',(atlasJP || atlasFR ? '车站' : '客站与货运节点'))+'</div>'+
      (failed ? '<p role="status">铁路数据载入失败</p>' : loaded
        ? '<p>'+ui(atlasJP ? '{lines} 条线路 · {stations} 个车站' : '{lines} 条线路 · {stations} 个主要车站',{lines:lines.length,stations:stations.length})+'</p>' : '<p role="status">正在载入铁路…</p>')+
      '<p>点选线路查看'+(atlasCN || atlasJP ? '沿途车站' : '邻近车站')+'。</p><p><a href="'+atlasNotes(atlasFR ? 'fr-transport' : atlasJP ? 'jp-transport' : atlasUS ? 'us-transport' : atlasUK ? 'uk-transport' : 'railway-data')+'">铁路数据来源 ↗</a></p>';
  }

  function load() {
    if (loaded || pending) return;
    failed = false;
    pending = loadJson(atlasData('railways.json')).then(data => {
      lines = data.lines.map(line => ({...line,n:nameFor(line.n,sourceName(line)),rail:'line',track:new Path2D(line.d)}));
      stations = data.stations.map(station => ({...station,n:nameFor(station.n,sourceName(station)),rail:'station',lines:[]}));
      const byStation = new Map(stations.map(station => [station.id,station]));
      for (const line of lines) {
        line.stops = line.stops.map(id => byStation.get(id));
        for (const station of line.stops) station.lines.push(line);
      }
      loaded = true;
    }).catch(error => {
      failed = true;
      console.error(error);
    }).finally(() => {
      pending = null;
      if (theme !== 'railway') return;
      setLegend(legend());
      redraw();
    });
  }

  function shown(item) {
    return item.rail === 'line' ? enabled.has(item.kind) :
      enabled.has('stations') && item.lines.some(line => enabled.has(line.kind));
  }

  function filter(event) {
    const key = event.target.dataset.railFilter;
    if (!key) return;
    const on = event.target.checked;
    if (on) enabled.add(key);
    else enabled.delete(key);
    for (const input of document.querySelectorAll('[data-rail-filter="'+key+'"]')) input.checked = on;
    if (selected?.rail && !shown(selected)) select(null);
    hovered = null;
    tooltip.hidden = true;
    redraw();
  }

  function drawTrack(bounds,scale) {
    ctx.save();
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    for (const line of lines) {
      if (!shown(line) || !visible(line,bounds)) continue;
      const style = groups[line.kind];
      ctx.setLineDash([]);
      ctx.lineWidth = (style.width+1.3)/scale;
      ctx.strokeStyle = '#f8edce';
      ctx.stroke(line.track);
      ctx.lineWidth = (style.width+(line === selected || line === hovered ? 1.15 : 0))/scale;
      ctx.strokeStyle = style.color;
      ctx.setLineDash(style.dash.map(length => length/scale));
      ctx.stroke(line.track);
    }
    ctx.restore();
  }

  function drawStations(scale) {
    spots = [];
    if (!enabled.has('stations')) return;
    const labelSpots = [];
    const candidates = selected?.rail === 'station'
      ? [selected,...stations.filter(station => station !== selected)] : stations;
    ctx.save();
    for (const station of candidates) {
      if (!shown(station)) continue;
      const nearby = selected?.rail === 'line' && station.lines.includes(selected);
      if (zoom < 1.85 && !station.hub && station !== selected && !nearby) continue;
      const sx = x+station.x*scale, sy = y+station.y*scale;
      if (sx < 8 || sy < 8 || sx > width-8 || sy > height-8 ||
          spots.some(other => Math.hypot(sx-other.sx,sy-other.sy) < (zoom < 2 ? 13 : 8))) continue;
      const freight = !station.passenger;
      const radius = station === selected || station === hovered ? 4.7 : station.hub ? 3.8 : 2.8;
      const color = freight ? '#80551d' : '#264f62';
      ctx.fillStyle = '#fff8df';
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      if (freight) ctx.rect(sx-radius,sy-radius,radius*2,radius*2);
      else ctx.arc(sx,sy,radius,0,2*Math.PI);
      ctx.fill();
      ctx.stroke();
      let labelWidth = 0;
      if (byId('labels').checked && (zoom >= 2.55 || station === selected || station === hovered || nearby)) {
        ctx.font = '600 11px '+labelFamily;
        const left = sx+7;
        const measured = ctx.measureText(station.n).width;
        if (left+measured < width && !labelSpots.some(([a,b,c]) => left < c+5 && left+measured+5 > a && Math.abs(sy-b)<15)) {
          labelSpots.push([left,sy,left+measured]);
          labelWidth = measured;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.lineWidth = 3;
          ctx.lineJoin = 'round';
          ctx.strokeStyle = '#f8f0d7';
          ctx.fillStyle = color;
          ctx.strokeText(station.n,left,sy);
          ctx.fillText(station.n,left,sy);
        }
      }
      spots.push({station,sx,sy,labelWidth});
    }
    ctx.restore();
  }

  function pick(sx,sy) {
    const hit = spots.find(({station,sx:left,sy:top,labelWidth}) =>
      shown(station) && Math.abs(sy-top) <= 6 && sx >= left-6 && sx <= left+7+labelWidth);
    if (hit) return hit.station;
    const [px,py] = world(sx,sy);
    const tolerance = 5/(fit*zoom);
    const near = [px-tolerance,py-tolerance,px+tolerance,py+tolerance];
    ctx.save();
    ctx.resetTransform();
    ctx.setLineDash([]);
    ctx.lineWidth = tolerance*2;
    try {
      return lines.findLast(line => shown(line) && visible(line,near) && ctx.isPointInStroke(line.track,px,py));
    } finally {
      ctx.restore();
    }
  }

  function show(item) {
    byId('crumb').textContent = ui(item.rail === 'line' ? groups[item.kind].label : item.passenger ? '客运车站' : '货运节点');
    const detail = item.rail === 'line'
      ? ui(atlasJP ? '{n} 个沿途车站' : !atlasCN ? '{n} 个已收录邻近车站' : '{n} 个已收录主要车站',{n:item.stops.length}) : ui(atlasCN || atlasJP ? '经过线路' : '邻近线路');
    byId('detailText').textContent = !atlasJP && !atlasFR && sourceName(item) && sourceName(item) !== item.n ? sourceName(item)+'\n'+detail : detail;
    const content = byId('railDetail');
    const links = document.createElement('ul');
    links.className = 'school-city-list';
    for (const entry of item.rail === 'line' ? item.stops : item.lines.filter(shown)) {
      const row = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = entry.n;
      if (!atlasJP && !atlasFR && sourceName(entry)) button.title = sourceName(entry);
      button.onclick = () => {
        select(entry);
        if (entry.rail === 'station') fly(Math.max(zoom,5),entry.x,entry.y);
      };
      row.append(button);
      links.append(row);
    }
    const source = document.createElement('a');
    source.className = 'rail-source';
    source.href = item.source || 'https://www.openstreetmap.org/'+(item.osmType || 'relation')+'/'+(item.osmId || item.id);
    source.target = '_blank';
    source.rel = 'noopener';
    source.textContent = item.source ? ui(atlasFR ? '法国国家铁路公司 ↗' : atlasJP ? '日本国土交通省 ↗' : 'Amtrak 或美国运输统计局 ↗') : 'OpenStreetMap ↗';
    content.replaceChildren(links,source);
    content.hidden = false;
  }

  return {legend,load,filter,drawTrack,drawStations,pick,show};
})();
