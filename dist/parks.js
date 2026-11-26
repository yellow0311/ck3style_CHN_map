const parkLayer = (() => {
  let parks, pending, failed = false;
  let marks = [];
  function legend() {
    const picker = parks ? '<label class="park-picker">定位公园 <select data-park-picker><option value="">选择公园</option>'+
      parks.map(park => '<option value="'+park.id+'" '+(park === selected ? 'selected' : '')+'>'+park.n+'</option>').join('')+
      '</select></label>' : '';
    return swatch('国家公园及相连保护区','#507659')+
      '<p>'+(failed ? '国家公园资料载入失败' : parks ? ui('{n} 座国家公园',{n:parks.length}) : '正在载入国家公园…')+'</p>'+
      picker+'<p>点选标记或范围查看公园。</p><p><a href="'+atlasNotes('us-parks')+'">公园数据来源 ↗</a></p>';
  }
  function filter(event) {
    if (!event.target.hasAttribute('data-park-picker')) return;
    const park = parks?.find(item => item.id === event.target.value);
    if (!park) return;
    reset();
    select(park);
    fly(Math.max(4,zoom),park.x,park.y);
  }
  function load() {
    if (parks || pending) return;
    failed = false;
    pending = loadJson(atlasData('parks.json')).then(data => {
      parks = data.map(park => ({...park,n:nameFor(park.n,sourceName(park)),overlay:'parks'})).sort((a,b) => a.n.localeCompare(b.n,atlasLocale));
    }).catch(error => {
      failed = true;
      console.error(error);
    }).finally(() => {
      pending = null;
      if (theme !== 'parks') return;
      setLegend(legend());
      redraw();
    });
  }
  function drawTrack(bounds,scale) {
    ctx.save();
    ctx.lineWidth = 1.2/scale;
    ctx.strokeStyle = '#315b43';
    for (const park of parks || []) {
      if (!visible(park,bounds) || !park.d) continue;
      ctx.fillStyle = park === selected ? '#537b56bd' : '#638e6577';
      ctx.fill(path(park),'evenodd');
      ctx.stroke(path(park));
    }
    ctx.restore();
  }
  function drawStations(scale) {
    marks = [];
    ctx.save();
    for (const park of parks || []) {
      const sx = x+park.x*scale, sy = y+park.y*scale;
      if (sx < 0 || sy < 0 || sx > width || sy > height) continue;
      marks.push({park,sx,sy});
      ctx.fillStyle = '#486c50';
      ctx.strokeStyle = '#f5ebd2';
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      ctx.arc(sx,sy,park === selected ? 8 : 5,0,Math.PI*2);
      ctx.fill();
      ctx.stroke();
    }
    ctx.restore();
  }
  function pick(sx,sy) {
    const marker = marks.findLast(mark => Math.hypot(mark.sx-sx,mark.sy-sy) <= 8);
    if (marker) return marker.park;
    const [px,py] = world(sx,sy);
    ctx.save();
    ctx.resetTransform();
    try {
      return parks?.find(park => park.d && visible(park,[px,py,px,py]) && ctx.isPointInPath(path(park),px,py,'evenodd'));
    } finally {
      ctx.restore();
    }
  }
  function show(park) {
    for (const input of document.querySelectorAll('[data-park-picker]')) input.value = park.id;
    byId('crumb').textContent = ui('美国国家公园');
    byId('place').textContent = park.n;
    byId('detailText').textContent = [sourceName(park) !== park.n ? sourceName(park) : '',park.states].filter(Boolean).join('\n');
    byId('closer').hidden = zoom >= 70;
    const link = document.createElement('a');
    link.href = 'https://www.nps.gov/'+park.id.toLowerCase()+'/index.htm';
    link.textContent = ui('国家公园管理局 ↗');
    byId('detailSources').replaceChildren(link);
    byId('detailSources').hidden = false;
  }
  return {legend,load,filter,drawTrack,drawStations,pick,show};
})();
