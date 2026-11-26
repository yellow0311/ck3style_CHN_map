const universityLayer = (() => {
  const categories = new Map(atlasUS ? [
    ['public','公立'],['nonprofit','私立非营利'],['landgrant','赠地院校'],
    ['hbcu','历史悠久黑人院校'],['tribal','部落院校']
  ] : atlasUK ? [
    ['russell','罗素大学集团'],['research','研究学位授予权（英格兰）'],['specialist','专门院校']
  ] : [
    ['985','985'],['211','211'],['firstClass','双一流'],['coop','中外／港澳合作'],
    ['ministry','教育部直属'],['provincial','省重点（已核验）'],['military','军队院校']
  ]);
  const enabled = new Set();
  const images = new Map();
  const collator = new Intl.Collator(atlasLocale);
  const crestZoom = 3.2;
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
    const count = failed ? '院校数据载入失败' : data ? ui('{n} 所院校',{n:matched}) : '正在载入院校…';
    return '<div class="theme-filters" role="group" aria-label="院校类别">'+controls+'</div>'+
      '<p data-university-total role="status">'+count+'</p>'+
      '<p>未选时显示全部，多选时显示符合任一标签的院校。放大后展开校徽，点选标记查看所在'+(atlasUS ? '县级辖区' : atlasUK ? '地方辖区' : '城市')+'的院校名单。</p>'+
      '<p><a href="'+atlasNotes(atlasUS ? 'us-universities' : atlasUK ? 'uk-universities' : 'university-data')+'">覆盖范围和来源 ↗</a></p>';
  }

  function load() {
    if (data || pending) return;
    failed = false;
    pending = loadJson(atlasData('universities.json')).then(result => {
      for (const school of result.schools) school.name = nameFor(school.name,sourceName(school));
      data = result;
      rebuild();
    }).catch(error => {
      failed = true;
      console.error(error);
    }).finally(() => {
      pending = null;
      if (theme !== 'universities') return;
      setLegend(legend());
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
    for (const count of document.querySelectorAll('[data-university-total]')) count.textContent = ui('{n} 所院校',{n:matched});
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

  function drawCrest(school,sx,sy,radius,highlighted = false) {
    const image = logoFor(school);
    ctx.fillStyle = '#fff8e7';
    ctx.beginPath();
    ctx.arc(sx,sy,radius,0,Math.PI*2);
    ctx.fill();
    ctx.strokeStyle = highlighted ? '#946328' : '#597766';
    ctx.lineWidth = highlighted ? 2 : 1;
    ctx.stroke();
    if (image) {
      const factor = (radius*2-2)/Math.max(image.naturalWidth,image.naturalHeight);
      const w = image.naturalWidth*factor, h = image.naturalHeight*factor;
      ctx.drawImage(image,sx-w/2,sy-h/2,w,h);
    } else {
      ctx.fillStyle = '#604b31';
      ctx.font = '600 '+(radius-2)+'px system-ui,sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText((school.abbr || school.name).slice(0,radius > 8 ? 2 : 1),sx,sy+.5);
    }
  }

  function drawExpanded(groups) {
    const step = width < 600 ? 24 : 28;
    const diameter = step-4;
    const used = new Set();
    const layouts = [];
    const scale = fit*zoom;
    // Reserve the nearest slot for each visible city before allocating its remaining crests.
    for (const {region,entries} of groups) {
      const sx = x+region.x*scale, sy = y+region.y*scale-15;
      if (sx < 0 || sy < 0 || sx > width || sy > height) continue;
      const column = Math.round((sx-x)/step), row = Math.round((sy-y)/step);
      const span = Math.ceil((Math.sqrt(entries.length)-1)/2)+1;
      const candidates = [];
      for (let dy=-span; dy<=span; dy++) {
        for (let dx=-span; dx<=span; dx++) {
          const cx = x+(column+dx)*step, cy = y+(row+dy)*step;
          if (cx < step/2 || cx > width-step/2 || cy < step/2 || cy > height-step/2) continue;
          const key = (column+dx)+','+(row+dy);
          candidates.push({key,sx:cx,sy:cy,distance:(cx-sx)**2+(cy-sy)**2});
        }
      }
      candidates.sort((a,b) => a.distance-b.distance);
      const nearest = candidates.find(slot => !used.has(slot.key));
      if (!nearest) continue;
      used.add(nearest.key);
      layouts.push({region,entries,candidates,slots:[nearest]});
    }
    for (const {region,entries,candidates,slots} of layouts) {
      for (const slot of candidates) {
        if (slots.length === entries.length) break;
        if (used.has(slot.key)) continue;
        used.add(slot.key);
        slots.push(slot);
      }
      const shown = slots.length === entries.length ? entries.length : slots.length-1;
      for (const [i,{sx,sy}] of slots.entries()) {
        const school = i < shown ? entries[i].school : null;
        markers.push({region,school,sx,sy,width:diameter,height:diameter});
        if (school) {
          drawCrest(school,sx,sy,diameter/2,region === selected);
        } else {
          const remainder = '+'+(entries.length-shown);
          ctx.beginPath();
          ctx.arc(sx,sy,diameter/2,0,Math.PI*2);
          ctx.fillStyle = '#34594c';
          ctx.fill();
          ctx.fillStyle = '#fff4d4';
          ctx.font = '600 9px system-ui,sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(remainder,sx,sy+.5);
        }
      }
    }
  }

  function draw() {
    markers = [];
    if (!data) return;
    const expanded = zoom >= crestZoom;
    const countryView = !expanded && mode === 0 && !focusedProvince;
    const groups = countryView ? [...provinces.values()] : [...cities.values()].filter(({region}) =>
      isFocused(region) && (atlasCN || !focusedCity || region.p === focusedCity.id));
    const size = group => countryView ? group.schools.size : group.entries.length;
    groups.sort((a,b) => Number(b.region === selected) - Number(a.region === selected) || size(b)-size(a));
    if (expanded) {
      drawExpanded(groups);
      return;
    }
    for (const group of groups) {
      const {region} = group;
      const [sx,sy] = [x+region.x*fit*zoom,y+region.y*fit*zoom-15];
      if (sx < 15 || sy < 15 || sx > width-15 || sy > height-15) continue;
      const entries = group.entries;
      const previews = !countryView && zoom >= 1.6
        ? entries.filter(({school}) => school.logo).slice(0,2) : [];
      const count = String(size(group));
      const pill = 24;
      const markerWidth = previews.length*19+pill;
      if (markers.some(other => Math.abs(other.sx-sx) < (other.width+markerWidth)/2+4 &&
          Math.abs(other.sy-sy) < 21)) continue;
      markers.push({region,sx,sy,width:markerWidth,height:18});
      const left = sx-markerWidth/2;
      ctx.fillStyle = region === selected || region === hovered ? '#946328' : '#34594c';
      ctx.strokeStyle = '#f4e9cb';
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.roundRect(left,sy-9,markerWidth,18,9);
      ctx.fill();
      ctx.stroke();
      for (const [i,{school}] of previews.entries()) {
        drawCrest(school,left+12+i*19,sy,7);
      }
      ctx.fillStyle = '#fff4d4';
      ctx.font = '600 11px system-ui,sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(count,sx+previews.length*9.5,sy+.5);
    }
  }

  function pick(sx,sy) {
    return markers.find(mark => Math.abs(mark.sx-sx) <= mark.width/2+1 &&
      Math.abs(mark.sy-sy) <= mark.height/2+1);
  }

  function focus(region) {
    if (!atlasCN) {
      focusRegion(region);
      return;
    }
    const province = records.get(provinceId(region));
    const level = region === province && districtLevelNames[region.id] ? 0 : 1;
    if (focusedProvince !== province || mode !== level || focusedCity) setLevel(level,province);
  }

  function schoolItem({school,campus}) {
    const item = document.createElement('li');
    const crest = document.createElement('span');
    crest.className = 'school-crest';
    const showInitials = () => {
      crest.textContent = school.abbr || school.name.slice(0,2);
      crest.title = ui('校徽暂无');
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
    if (sourceName(school)) name.title = sourceName(school);
    block.append(name);
    const campusNames = campus?.filter(([label]) => !['院校名录','院校'].includes(label)) || [];
    if (campusNames.length) {
      const row = document.createElement('small');
      row.textContent = campusNames.map(([label,,original]) => ui(nameFor(label,original))).join(showOriginal ? ', ' : '、');
      const originals = campusNames.map(([, ,en]) => en).filter(Boolean);
      if (originals.length) row.title = originals.join(' / ');
      block.append(row);
    }
    const tags = school.tags.map(key => ui(categories.get(key))).filter(Boolean);
    if (tags.length) {
      const row = document.createElement('small');
      row.textContent = tags.join(' · ');
      block.append(row);
    }
    const sources = campus?.filter(([,url]) => url) || [];
    if (school.provincialSource) sources.push(school.provincialSource);
    for (const [label,url,original] of sources) {
      const link = document.createElement('a');
      link.href = url;
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = label === '院校' ? ui('院校网站')+' ↗' : ui('{label}资料 ↗',{label:ui(nameFor(label,original))});
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
      text.textContent = ui(failed ? '院校数据载入失败' : '正在载入院校…');
      return;
    }
    const city = cities.get(region.id);
    if ((!atlasCN ? region.layer === 2 : region.layer > 0) || city) {
      const entries = city?.entries || [];
      text.textContent = entries.length ? ui('{n} 所院校',{n:entries.length}) : ui('当前筛选下暂无已收录院校');
      if (!entries.length) return;
      const list = document.createElement('ul');
      list.className = 'school-list';
      list.append(...entries.map(schoolItem));
      container.append(list);
      container.hidden = false;
      return;
    }
    const province = provinces.get(region.id);
    const options = atlasUK && region.layer === 1
      ? [...cities.values()].filter(({region:place}) => place.p === region.id)
      : [...province?.cities || []].map(id => cities.get(id));
    const count = province?.schools.size ?? new Set(options.flatMap(group => group.entries.map(({school}) => school.id))).size;
    text.textContent = count ? ui('{n} 所院校 · {areas} 个地区',{n:count,areas:options.length}) : ui('当前筛选下暂无已收录院校');
    if (!options.length) return;
    options.sort((a,b) => b.entries.length-a.entries.length || collator.compare(a.region.n,b.region.n));
    const list = document.createElement('ul');
    list.className = 'school-city-list';
    for (const group of options) {
      const item = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = group.region.n+'　'+ui('{n} 所',{n:group.entries.length});
      button.onclick = () => { focus(group.region); select(group.region); };
      item.append(button);
      list.append(item);
    }
    container.append(list);
    container.hidden = false;
  }

  return {legend,load,rebuild,filter,draw,pick,focus,show};
})();
