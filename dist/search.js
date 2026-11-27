(() => {
  const input = byId('placeSearch');
  const list = byId('placeResults');
  const status = byId('placeSearchStatus');
  const form = input.form;
  const collator = new Intl.Collator(atlasLocale);
  const normalize = text => text.normalize(atlasFR ? 'NFKD' : 'NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
  const shortNames = {
    '150000':'内蒙古', '450000':'广西', '540000':'西藏', '640000':'宁夏', '650000':'新疆',
    '810000':'香港', '820000':'澳门'
  };
  let candidates = [];
  let active = -1;
  let indexedRecords;
  let index = [];
  const shortName = name => name.replace(/(?:省|市|县|区|街道|镇)$/,'');

  function updateIndex() {
    if (indexedRecords === records) return;
    indexedRecords = records;
    index = [...records.values()].map(region => {
      const chineseName = item => item.zh || item.n;
      const originalName = item => sourceName(item) || item.n;
      const chineseParents = administrativeParents(region,chineseName);
      const name = normalize(chineseName(region));
      const alias = normalize(shortNames[region.id] ?? shortName(chineseName(region)));
      const original = normalize(sourceName(region) || '');
      const paths = [normalize(chineseParents.join(''))+name,normalize(chineseParents.map(shortName).join(''))+alias];
      if (original) paths.push(normalize(administrativeParents(region,originalName).join(''))+original);
      return {region,parents:showOriginal ? administrativeParents(region) : chineseParents,name,alias,original,paths};
    });
  }

  function close() {
    list.hidden = status.hidden = true;
    input.setAttribute('aria-expanded','false');
    input.removeAttribute('aria-activedescendant');
    active = -1;
  }

  function navigate(region) {
    input.value = region.n;
    close();
    navigateToRegion(region);
    canvas.focus({preventScroll:true});
  }

  function search() {
    const query = normalize(input.value);
    if (!query) {
      candidates = [];
      close();
      return;
    }
    updateIndex();
    const words = input.value.trim().split(/[\s/／·,，]+/).map(normalize).filter(Boolean);
    candidates = index.flatMap(entry => {
      const {region,name,alias,original,paths} = entry;
      let rank;
      if (region.id.toLowerCase() === query || region.code?.toLowerCase() === query || name === query || original === query) rank = 0;
      else if (alias === query) rank = 1;
      else if (name.startsWith(query) || original.startsWith(query)) rank = 2;
      else if (name.includes(query) || original.includes(query) || region.id.toLowerCase().startsWith(query)) rank = 3;
      else if (paths.some(path => path.endsWith(query) || (words.length > 1 && words.every(word => path.includes(word))))) rank = 4;
      return rank === undefined ? [] : [{...entry,rank}];
    }).sort((a,b) => a.rank-b.rank || a.region.layer-b.region.layer ||
      collator.compare(a.region.n,b.region.n) || a.region.id.localeCompare(b.region.id)).slice(0,9);

    list.replaceChildren(...candidates.map(({region,parents},i) => {
      const option = document.createElement('li');
      option.id = 'placeOption'+i;
      option.setAttribute('role','option');
      const name = document.createElement('strong');
      name.textContent = region.n;
      const context = document.createElement('small');
      context.textContent = parents.join(' / ') || levelNames[region.layer];
      option.append(name,context);
      option.onclick = () => navigate(region);
      return option;
    }));
    active = -1;
    input.removeAttribute('aria-activedescendant');
    list.hidden = !candidates.length;
    input.setAttribute('aria-expanded',String(Boolean(candidates.length)));
    status.hidden = Boolean(candidates.length);
    status.textContent = ui(records.size ? '没有找到匹配的行政区' : '正在载入行政区…');
  }

  input.addEventListener('input',event => { if (!event.isComposing) search(); });
  input.addEventListener('compositionend',search);
  input.addEventListener('focus',search);
  list.addEventListener('mousedown',event => event.preventDefault());
  input.addEventListener('keydown',event => {
    if (event.isComposing || event.keyCode === 229) return;
    if (event.key === 'Escape') {
      close();
      event.preventDefault();
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if (list.hidden) search();
      if (!candidates.length) return;
      const step = event.key === 'ArrowDown' ? 1 : -1;
      active = active < 0 && step < 0 ? candidates.length-1 :
        (active+step+candidates.length)%candidates.length;
      for (const [i,option] of [...list.children].entries()) {
        option.setAttribute('aria-selected',String(i === active));
      }
      input.setAttribute('aria-activedescendant',list.children[active].id);
      list.children[active].scrollIntoView({block:'nearest'});
      event.preventDefault();
    }
  });
  form.addEventListener('submit',event => {
    event.preventDefault();
    if (list.hidden) search();
    if (candidates.length) navigate(candidates[Math.max(0,active)].region);
  });
  document.addEventListener('pointerdown',event => { if (!form.contains(event.target)) close(); });
  form.addEventListener('focusout',event => { if (!form.contains(event.relatedTarget)) close(); });
  document.addEventListener('atlas-regions-ready',() => { if (document.activeElement === input) search(); });
})();
