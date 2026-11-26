const universityLayer = (() => {
  const categories = new Map([
    ['985','985'],['211','211'],['firstClass','双一流'],['coop','中外／港澳合作'],
    ['ministry','教育部直属'],['provincial','省重点（已核验）'],['military','军队院校']
  ]);
  const enabled = new Set();
  const images = new Map();
  const collator = new Intl.Collator('zh-CN');
  let data;
  let pending;
  let failed = false;
  let markers = [];
  let cities = new Map();
  let provinces = new Map();
  let matched = 0;

  function legend() {
    const controls = [...categories].map(([key,label]) =>
      '<label><input type="checkbox" data-university-filter="'+key+'" '+(enabled.has(key) ? 'checked' : '')+
      (data ? '' : ' disabled')+'>'+label+'</label>'
    ).join('');
    const count = failed ? '院校数据载入失败' : data ? matched+' 所院校' : '正在载入院校…';
    return '<div class="theme-filters" role="group" aria-label="院校类别">'+controls+'</div>'+
      '<p data-university-total role="status">'+count+'</p>'+
      '<p>未选时显示全部，多选时显示符合任一标签的院校。点选城市查看校徽和院校名单。</p>'+
      '<p><a href="notes.html#university-data">覆盖范围和来源 ↗</a></p>';
  }

  function load() {
    if (data || pending) return;
    failed = false;
    pending = loadJson('data/universities.json').then(result => {
      data = result;
      rebuild();
    }).catch(error => {
      failed = true;
      console.error(error);
    }).finally(() => {
      pending = null;
      if (theme !== 'universities') return;
      byId('legend').innerHTML = byId('mobileLegend').innerHTML = legend();
      if (selected) select(selected);
      redraw();
    });
  }

  function rebuild() {
    cities = new Map();
    provinces = new Map();
    matched = 0;
    if (!data) return;
    const filtered = enabled.size
      ? data.schools.filter(school => school.tags.some(tag => enabled.has(tag))) : data.schools;
    matched = filtered.length;
    if (!records.size) return;
    const extraPlaces = new Map(Object.entries(data.places || {}).map(([id,[n,p,lon,lat]]) => {
      const [x,y] = project(lon,lat);
      return [id,{id,n,p,x,y,layer:1,universityPlace:true}];
    }));
    for (const school of filtered) {
      for (const [id,campus] of Object.entries(school.placements)) {
        const region = records.get(id) || extraPlaces.get(id);
        if (!region) continue;
        if (!cities.has(id)) cities.set(id,{region,entries:[]});
        cities.get(id).entries.push({school,campus});
        const province = provinceId(region);
        if (!provinces.has(province)) provinces.set(province,{region:records.get(province),schools:new Set(),cities:new Set()});
        provinces.get(province).schools.add(school.id);
        provinces.get(province).cities.add(id);
      }
    }
    for (const {entries} of cities.values()) {
      entries.sort((a,b) => collator.compare(a.school.name,b.school.name));
    }
  }

  function filter(event) {
    const key = event.target.dataset.universityFilter;
    if (!categories.has(key)) return;
    if (event.target.checked) enabled.add(key);
    else enabled.delete(key);
    rebuild();
    for (const input of document.querySelectorAll('[data-university-filter="'+key+'"]')) {
      input.checked = enabled.has(key);
    }
    for (const count of document.querySelectorAll('[data-university-total]')) count.textContent = matched+' 所院校';
    if (selected) select(selected);
    hovered = null;
    tooltip.hidden = true;
    redraw();
  }

  function logoFor(school) {
    if (!school.logo) return;
    if (!images.has(school.logo)) {
      const image = new Image();
      image.onload = redraw;
      image.src = school.logo;
      images.set(school.logo,image);
    }
    const image = images.get(school.logo);
    return image.naturalWidth ? image : null;
  }

  function draw() {
    markers = [];
    if (!data) return;
    const countryView = mode === 0 && !focusedProvince;
    const groups = countryView ? [...provinces.values()] : [...cities.values()].filter(({region}) => isFocused(region));
    const size = group => countryView ? group.schools.size : group.entries.length;
    groups.sort((a,b) => Number(b.region === selected) - Number(a.region === selected) || size(b)-size(a));
    for (const group of groups) {
      const {region} = group;
      const [sx,sy] = [x+region.x*fit*zoom,y+region.y*fit*zoom-15];
      if (sx < 15 || sy < 15 || sx > width-15 || sy > height-15) continue;
      const entries = group.entries;
      const previews = !countryView && zoom >= 1.6
        ? entries.filter(({school}) => school.logo).slice(0,2) : [];
      const count = String(size(group));
      ctx.font = '600 11px system-ui,sans-serif';
      const pill = Math.max(24,ctx.measureText(count).width+12);
      const markerWidth = previews.length*19+pill;
      if (markers.some(other => Math.abs(other.sx-sx) < (other.width+markerWidth)/2+4 &&
          Math.abs(other.sy-sy) < 21)) continue;
      markers.push({region,sx,sy,width:markerWidth});
      const left = sx-markerWidth/2;
      ctx.fillStyle = region === selected || region === hovered ? '#946328' : '#34594c';
      ctx.strokeStyle = '#f4e9cb';
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.roundRect(left,sy-9,markerWidth,18,9);
      ctx.fill();
      ctx.stroke();
      for (const [i,{school}] of previews.entries()) {
        const image = logoFor(school);
        const logoX = left+5+i*19;
        ctx.fillStyle = '#fff8e7';
        ctx.beginPath();
        ctx.arc(logoX+7,sy,7,0,Math.PI*2);
        ctx.fill();
        if (image) {
          const factor = 13/Math.max(image.naturalWidth,image.naturalHeight);
          const w = image.naturalWidth*factor, h = image.naturalHeight*factor;
          ctx.drawImage(image,logoX+7-w/2,sy-h/2,w,h);
        } else {
          ctx.save();
          ctx.fillStyle = '#604b31';
          ctx.font = '600 8px system-ui,sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(school.name[0],logoX+7,sy+.5);
          ctx.restore();
        }
      }
      ctx.fillStyle = '#fff4d4';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(count,sx+previews.length*9.5,sy+.5);
    }
  }

  function pick(sx,sy) {
    return markers.find(mark => Math.abs(mark.sx-sx) <= mark.width/2+2 && Math.abs(mark.sy-sy) <= 11)?.region;
  }

  function focus(region) {
    const province = records.get(provinceId(region));
    const level = region === province && districtLevelNames[region.id] ? 0 : 1;
    if (focusedProvince !== province || mode !== level || focusedCity) setLevel(level,province);
  }

  function schoolItem({school,campus}) {
    const item = document.createElement('li');
    const crest = document.createElement('span');
    crest.className = 'school-crest';
    const showInitials = () => {
      crest.textContent = school.name.slice(0,2);
      crest.title = '校徽暂无';
    };
    if (school.logo) {
      const img = document.createElement('img');
      img.src = school.logo;
      img.alt = '';
      img.loading = 'lazy';
      img.onerror = showInitials;
      crest.append(img);
    } else showInitials();
    const block = document.createElement('div');
    const name = document.createElement('strong');
    name.textContent = school.name;
    block.append(name);
    const campusNames = campus?.filter(([label]) => !['院校名录','院校'].includes(label)) || [];
    if (campusNames.length) {
      const row = document.createElement('small');
      row.textContent = campusNames.map(([label]) => label).join('、');
      block.append(row);
    }
    const tags = school.tags.map(key => categories.get(key)).filter(Boolean);
    if (tags.length) {
      const row = document.createElement('small');
      row.textContent = tags.join(' · ');
      block.append(row);
    }
    const sources = campus?.filter(([,url]) => url) || [];
    if (school.provincialSource) sources.push(school.provincialSource);
    for (const [label,url] of sources) {
      const link = document.createElement('a');
      link.href = url;
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = (label === '院校' ? '院校网站' : label+'资料')+' ↗';
      block.append(link);
    }
    item.append(crest,block);
    return item;
  }

  function show(region) {
    const text = byId('detailText');
    const container = byId('universityDetail');
    container.replaceChildren();
    if (!data) {
      text.textContent = failed ? '院校数据载入失败' : '正在载入院校…';
      return;
    }
    const city = cities.get(region.id);
    if (region.layer > 0 || city) {
      const entries = city?.entries || [];
      text.textContent = entries.length ? entries.length+' 所院校' : '当前筛选下暂无已收录院校';
      if (!entries.length) return;
      const list = document.createElement('ul');
      list.className = 'school-list';
      list.append(...entries.map(schoolItem));
      container.append(list);
      container.hidden = false;
      return;
    }
    const province = provinces.get(region.id);
    text.textContent = province ? province.schools.size+' 所院校 · '+province.cities.size+' 个地区' : '当前筛选下暂无已收录院校';
    if (!province) return;
    const options = [...province.cities].map(id => cities.get(id)).sort((a,b) =>
      b.entries.length-a.entries.length || collator.compare(a.region.n,b.region.n));
    const list = document.createElement('ul');
    list.className = 'school-city-list';
    for (const group of options) {
      const item = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = group.region.n+'　'+group.entries.length+' 所';
      button.onclick = () => { focus(group.region); select(group.region); };
      item.append(button);
      list.append(item);
    }
    container.append(list);
    container.hidden = false;
  }

  return {legend,load,rebuild,filter,draw,pick,focus,show};
})();
