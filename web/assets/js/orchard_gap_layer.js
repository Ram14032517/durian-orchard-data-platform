/* Public GAP registry locations are contextual map evidence, not field-verified orchards. */
(function (root) {
  'use strict';

  const PAGE_SIZE = 10;
  const MAX_INDIVIDUAL_POINTS = 1200;
  const DATE_LABELS = {
    within_dates: 'อยู่ในช่วงวันที่ทะเบียน',
    future_issue: 'วันออกทะเบียนอยู่หลังวัน snapshot',
    expired: 'วันหมดอายุผ่านแล้ว ณ snapshot',
    invalid_dates: 'วันที่ไม่ครบ / ตรวจรูปแบบไม่ได้'
  };

  function asText(value, fallback) {
    return value === null || value === undefined || value === '' ? (fallback === undefined ? 'ไม่ระบุ' : fallback) : String(value);
  }

  function validFeature(feature) {
    if (!feature || feature.type !== 'Feature' || !feature.properties || feature.geometry?.type !== 'Point') return false;
    const coordinates = feature.geometry.coordinates;
    return Array.isArray(coordinates) && coordinates.length >= 2 &&
      typeof coordinates[0] === 'number' && typeof coordinates[1] === 'number' &&
      Number.isFinite(coordinates[0]) && Number.isFinite(coordinates[1]) &&
      coordinates[0] >= -180 && coordinates[0] <= 180 && coordinates[1] >= -90 && coordinates[1] <= 90 &&
      !!(feature.id || feature.properties.id);
  }

  function qualityFlags(feature) {
    return Array.isArray(feature.properties.quality_flags) ? feature.properties.quality_flags : [];
  }

  function filterFeatures(features, filters) {
    return features.filter(feature => {
      const p = feature.properties, flags = qualityFlags(feature);
      if (filters.district && asText(p.district, '') !== filters.district) return false;
      if (filters.dateStatus && p.date_status !== filters.dateStatus) return false;
      if (filters.quality === 'shared' && !flags.includes('shared_coordinate')) return false;
      if (filters.quality === 'conflict' && !flags.includes('metadata_conflict')) return false;
      if (filters.quality === 'no_additional_flags' && (flags.includes('shared_coordinate') || flags.includes('metadata_conflict'))) return false;
      return true;
    });
  }

  function sourceUrl(value) {
    try {
      const url = new URL(value);
      const hostname = url.hostname.toLowerCase();
      const government = hostname.endsWith('.go.th') || hostname.endsWith('.gov.cn') || hostname === 'go.th' || hostname === 'gov.cn';
      return ['https:', 'http:'].includes(url.protocol) && government && !url.username && !url.password ? url.href : null;
    } catch (_) { return null; }
  }

  function dataUrl(base, filename, documentUrl) {
    const origin = new URL(documentUrl);
    const baseUrl = new URL(base.replace(/\/?$/, '/'), origin);
    const resolved = new URL(filename, baseUrl);
    if (!['http:', 'https:'].includes(origin.protocol) || resolved.origin !== origin.origin ||
        !resolved.pathname.startsWith(baseUrl.pathname) || resolved.search || resolved.hash ||
        resolved.username || resolved.password) throw new Error('ข้อมูลแผนที่ต้องโหลดผ่านเซิร์ฟเวอร์ของโปรเจกต์เดียวกัน');
    return resolved.href;
  }

  function groupViewport(features, project, zoom) {
    if (zoom >= 14 && features.length <= MAX_INDIVIDUAL_POINTS) {
      const positions = new Map();
      for (const feature of features) {
        const [lon, lat] = feature.geometry.coordinates, key = `${lon}:${lat}`;
        if (!positions.has(key)) positions.set(key, {key: `point:${key}`, features: [], lat, lon});
        positions.get(key).features.push(feature);
      }
      return [...positions.values()];
    }
    const size = zoom < 9 ? 64 : 48, cells = new Map();
    for (const feature of features) {
      const [lon, lat] = feature.geometry.coordinates, point = project(lat, lon);
      const key = `${Math.floor(point.x / size)}:${Math.floor(point.y / size)}`;
      let group = cells.get(key);
      if (!group) { group = {key: `cell:${size}:${key}`, features: [], lat: 0, lon: 0}; cells.set(key, group); }
      group.features.push(feature); group.lat += lat; group.lon += lon;
    }
    return [...cells.values()].map(group => ({key: group.key, features: group.features, lat: group.lat / group.features.length, lon: group.lon / group.features.length}));
  }

  function createGapOrchardLayer(options) {
    const {map, L, container, selectPoint} = options;
    if (!map || !L || !container || typeof selectPoint !== 'function') throw new Error('GAP layer requires map, Leaflet, container and selectPoint');
    const doc = container.ownerDocument || root.document;
    const dataBaseUrl = options.dataBaseUrl || '../gap_registry/';
    const cache = new Map(), requests = new Map();
    let manifest = null, manifestRequest = null, provinceCode = '', currentFeatures = [], filtered = [];
    let visible = true, destroyed = false, loading = false, version = 0, page = 0, selectedId = null, redrawTimer = null, clusterFeatures = null;
    let zooming = false;
    const markerRecords = new Map(), clusterCache = new Map(), featurePositions = new WeakMap();
    const requestFrame = typeof root.requestAnimationFrame === 'function' ? callback => root.requestAnimationFrame(callback) : callback => root.setTimeout(callback, 16);
    const cancelFrame = typeof root.cancelAnimationFrame === 'function' ? handle => root.cancelAnimationFrame(handle) : handle => root.clearTimeout(handle);
    const filters = {district: '', quality: '', dateStatus: ''};
    const formatCount = value => Number(value || 0).toLocaleString('th-TH');

    function el(tag, text, className) {
      const node = doc.createElement(tag);
      if (text !== undefined && text !== null) node.textContent = String(text);
      if (className) node.className = className;
      return node;
    }
    function option(select, value, label) {
      const node = el('option', label); node.value = value; select.append(node);
    }
    function labeledSelect(label, choices) {
      const wrapper = el('label', null, 'gap-field'), text = el('span', label), input = el('select');
      input.setAttribute('aria-label', label);
      choices.forEach(([value, name]) => option(input, value, name)); wrapper.append(text, input); return {wrapper, input};
    }
    function button(text, action) {
      const node = el('button', text); node.type = 'button'; node.addEventListener('click', action); return node;
    }

    container.classList.add('gap-orchards');
    const heading = el('h3', 'แปลงตามทะเบียน GAP');
    const visibility = el('label', null, 'gap-visibility'), checkbox = el('input');
    checkbox.type = 'checkbox'; checkbox.checked = true;
    visibility.append(checkbox, el('span', 'แสดงหมุดทะเบียน GAP'));
    const introduction = el('p', 'ตำแหน่งจากทะเบียน ไม่ใช่พิกัดสวนที่ลงพื้นที่ยืนยัน และไม่ใช่เซนเซอร์ IoT', 'gap-scope');
    const controls = el('div', null, 'gap-filters');
    const province = labeledSelect('จังหวัดของหมุด GAP', [['', 'เลือกจังหวัดจากพื้นที่ A/B หรือเลือกที่นี่']]);
    const district = labeledSelect('อำเภอของหมุด GAP', [['', 'ทุกอำเภอ']]);
    const quality = labeledSelect('ธงตรวจคุณภาพพิกัด', [
      ['', 'ทั้งหมด (ยังไม่ยืนยันภาคสนาม)'], ['no_additional_flags', 'ไม่มีธงซ้ำพิกัด / ข้อมูลขัดกัน'],
      ['shared', 'พิกัดซ้ำกับแปลงอื่น'], ['conflict', 'ข้อมูลทะเบียนขัดกัน']
    ]);
    const certification = labeledSelect('ช่วงวันที่ทะเบียน ณ snapshot', [['', 'ทุกช่วงวันที่'], ...Object.entries(DATE_LABELS)]);
    controls.append(province.wrapper, district.wrapper, quality.wrapper, certification.wrapper);
    const status = el('p', 'เลือกจังหวัดเพื่อโหลดหมุดเฉพาะจังหวัดนั้น', 'gap-status');
    status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
    const summary = el('p', '', 'gap-scope');
    const retry = button('ลองโหลดทะเบียนอีกครั้ง', () => { manifestRequest = null; setProvince(provinceCode); }); retry.hidden = true;
    const selected = el('div', null, 'gap-selected'); selected.hidden = true; selected.setAttribute('aria-label', 'รายละเอียดแปลงทะเบียนที่เลือก');
    const selectedTitle = el('h4', 'รายละเอียดแปลงที่เลือก'), selectedBody = el('div'); selected.append(selectedTitle, selectedBody);
    const listDetails = el('details', null, 'gap-list-details');
    listDetails.append(el('summary', 'เลือกแปลงจากรายการ (ใช้คีย์บอร์ดได้)'));
    const list = el('ol', null, 'gap-orchard-list'), pager = el('div', null, 'gap-pager');
    list.setAttribute('aria-label', 'แปลงทะเบียนตามตัวกรองทั้งหมด ไม่จำกัดขอบจอแผนที่');
    const previous = button('ก่อนหน้า', () => { page--; renderList(true); });
    const next = button('ถัดไป', () => { page++; renderList(true); });
    const pageLabel = el('span'); pageLabel.setAttribute('role', 'status');
    const clearCluster = button('แสดงรายการตามตัวกรองทั้งหมด', () => { clusterFeatures = null; page = 0; renderList(false); }); clearCluster.hidden = true;
    pager.append(previous, pageLabel, next); listDetails.append(clearCluster, list, pager);
    const sources = el('details', null, 'gap-source-details'); sources.append(el('summary', 'แหล่งข้อมูลและข้อจำกัด'));
    const sourcesBody = el('div'); sources.append(sourcesBody);
    const warning = el('p', 'หมุดไม่ทำให้ผลผลิตจังหวัดกลายเป็นผลผลิตรายสวน อากาศ NASA เป็นข้อมูลกริด ไม่ใช่ค่าจากเซนเซอร์ในสวน และทะเบียน snapshot ปัจจุบันไม่ยืนยันตำแหน่งย้อนหลัง', 'gap-warning');
    container.replaceChildren(heading, visibility, introduction, controls, status, retry, summary, selected, listDetails, sources, warning);

    const paneName = 'gap-registry-pane';
    if (!map.getPane(paneName)) { const pane = map.createPane(paneName); pane.style.zIndex = '450'; }
    const renderer = L.canvas({pane: paneName, padding: 0.15});
    const markers = L.layerGroup().addTo(map);

    function cancelRedraw() {
      if (redrawTimer !== null) { cancelFrame(redrawTimer); redrawTimer = null; }
    }
    function clearMarkers() { markers.clearLayers(); markerRecords.clear(); }
    function resetClusters() { cancelRedraw(); clusterCache.clear(); clearMarkers(); }
    function featurePosition(feature) {
      let position = featurePositions.get(feature);
      if (!position) {
        position = [feature.geometry.coordinates[1], feature.geometry.coordinates[0]];
        featurePositions.set(feature, position);
      }
      return position;
    }
    function motionOptions() {
      return {animate: !root.matchMedia?.('(prefers-reduced-motion: reduce)').matches, duration: 0.45};
    }
    function setMapView(position, zoom) {
      if (options.motion) options.motion.setView(position, zoom);
      else map.setView(position, zoom, motionOptions());
    }
    function fitMapBounds(bounds, settings) {
      if (options.motion) options.motion.fitBounds(bounds, settings);
      else map.fitBounds(bounds, {...settings, ...motionOptions()});
    }

    async function fetchJson(filename) {
      const url = dataUrl(dataBaseUrl, filename, doc.baseURI || root.location.href);
      const response = await root.fetch(url, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
      if (!response.ok) throw new Error(`โหลดทะเบียนไม่สำเร็จ (${response.status})`);
      return response.json();
    }
    async function loadManifest() {
      if (manifest) return manifest;
      if (!manifestRequest) manifestRequest = fetchJson('manifest.json').then(data => {
        if (data.schema_version !== 1 || !Array.isArray(data.provinces)) throw new Error('รูปแบบ manifest ทะเบียน GAP ไม่รองรับ');
        manifest = data; renderManifest(); return data;
      }).catch(error => { manifestRequest = null; throw error; });
      return manifestRequest;
    }
    function renderManifest() {
      if (destroyed) return;
      province.input.replaceChildren(); option(province.input, '', 'เลือกจังหวัด');
      for (const item of manifest.provinces) option(province.input, String(item.code ?? item.province_code), item.name ?? item.province_name);
      province.input.value = provinceCode;
      sourcesBody.replaceChildren(el('p', `ทะเบียน snapshot ${asText(manifest.snapshot_date)} · รายการที่มีพิกัดผ่านเกณฑ์แสดงผล ไม่ใช่จำนวนสวนที่ยืนยันภาคสนาม`));
      const sourceList = el('ul');
      for (const [id, source] of Object.entries(manifest.sources || {})) {
        const item = el('li'), url = sourceUrl(source.url);
        if (url) { const link = el('a', id); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; item.append(link); }
        else item.append(el('span', id));
        item.append(doc.createTextNode(` · ดึงข้อมูล ${asText(source.retrieved_utc ?? source.retrieved_date)}`)); sourceList.append(item);
      }
      sourcesBody.append(sourceList);
      for (const note of manifest.warnings || []) sourcesBody.append(el('p', note, 'gap-scope'));
    }
    function updateDisabled() {
      for (const input of [district.input, quality.input, certification.input]) input.disabled = loading || !currentFeatures.length;
      container.setAttribute('aria-busy', String(loading));
    }
    function currentProvince() { return manifest?.provinces.find(item => String(item.code ?? item.province_code) === provinceCode); }
    function refreshFilters() {
      const districts = [...new Set(currentFeatures.map(feature => asText(feature.properties.district, '')).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'th'));
      district.input.replaceChildren(); option(district.input, '', 'ทุกอำเภอ');
      districts.forEach(name => option(district.input, name, name));
      if (!districts.includes(filters.district)) filters.district = '';
      district.input.value = filters.district;
    }
    function applyFilters() {
      resetClusters();
      filtered = filterFeatures(currentFeatures, filters); page = 0; clusterFeatures = null;
      if (selectedId && !filtered.some(feature => String(feature.id || feature.properties.id) === selectedId)) {
        selectedId = null; selected.hidden = true;
      }
      renderList(false); redraw();
    }
    function renderList(focusFirst) {
      const rows = clusterFeatures || filtered;
      clearCluster.hidden = !clusterFeatures;
      const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE)); page = Math.max(0, Math.min(page, pages - 1));
      list.replaceChildren(); list.start = page * PAGE_SIZE + 1;
      for (const feature of rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)) {
        const p = feature.properties, item = el('li'), id = String(feature.id || p.id);
        const label = `${asText(p.district)} · ${id} · ${DATE_LABELS[p.date_status] || 'ตรวจวันที่ไม่ได้'}`;
        const select = button(label, () => chooseFeature(feature, true));
        select.setAttribute('aria-pressed', String(id === selectedId)); item.append(select); list.append(item);
      }
      previous.disabled = page === 0 || !rows.length; next.disabled = page >= pages - 1 || !rows.length;
      pageLabel.textContent = rows.length ? `${clusterFeatures ? 'เฉพาะกลุ่มที่คลิก · ' : ''}${formatCount(page * PAGE_SIZE + 1)}–${formatCount(Math.min((page + 1) * PAGE_SIZE, rows.length))} / ${formatCount(rows.length)} รายการ · หน้า ${page + 1}/${pages}` : 'ไม่มีรายการตรงตัวกรอง';
      if (focusFirst) list.querySelector('button')?.focus();
    }
    function detail(label, value) {
      const row = el('div', null, 'gap-detail-row'); row.append(el('dt', label), el('dd', asText(value))); return row;
    }
    function showFeature(feature) {
      const p = feature.properties, [lon, lat] = feature.geometry.coordinates, rows = el('dl');
      rows.append(detail('รหัสแสดงผล (ไม่ใช่รหัสรับรอง)', feature.id || p.id),
        detail('พื้นที่ตามทะเบียน', [p.province_name, p.district, p.tambon].filter(Boolean).join(' / ')),
        detail('พิกัดทะเบียน', `${lat.toFixed(6)}, ${lon.toFixed(6)}`),
        detail('สถานะที่แหล่งข้อมูลรายงาน', p.status_reported),
        detail('วันออก / หมดอายุ', `${asText(p.issued)} / ${asText(p.expired)}`),
        detail('ประเมินช่วงวันที่ ณ snapshot', DATE_LABELS[p.date_status] || 'ตรวจวันที่ไม่ได้'),
        detail('พื้นที่ในทะเบียน (ไร่)', p.area_rai === null || p.area_rai === undefined ? 'ไม่ระบุ' : p.area_rai),
        detail('ระเบียนที่รวมเป็นหมุดนี้', p.registry_rows ?? 1),
        detail('คุณภาพตำแหน่ง', 'พิกัดจากทะเบียน ผ่านเกณฑ์แสดงแผนที่ แต่ยังไม่ยืนยันภาคสนาม'));
      const flags = qualityFlags(feature);
      if (flags.includes('shared_coordinate')) rows.append(detail('ธงพิกัด', 'มีแปลงอื่นใช้พิกัดเดียวกัน ไม่ยืนยันว่าเป็นสวนเดียวกัน'));
      if (flags.includes('metadata_conflict')) rows.append(detail('ธงทะเบียน', 'ข้อมูลในระเบียนซ้ำขัดกัน ต้องตรวจต้นทาง'));
      selectedBody.replaceChildren(rows, el('p', 'สถานะที่รายงานกับช่วงวันที่เป็นคนละหลักฐาน ไม่ใช่การตรวจใบรับรองปัจจุบัน และไม่มีผลผลิตรายปีหรือผลตรวจโรครายแปลงในหมุดนี้', 'gap-scope'));
      const links = el('div', null, 'gap-selected-sources');
      for (const id of p.source_ids || []) {
        const url = sourceUrl(manifest?.sources?.[id]?.url);
        if (!url) continue;
        const link = el('a', `แหล่งข้อมูล ${id}`); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; links.append(link);
      }
      selectedBody.append(links); selected.hidden = false;
    }
    function chooseFeature(feature, center) {
      const p = feature.properties, [lon, lat] = feature.geometry.coordinates;
      selectedId = String(feature.id || p.id); showFeature(feature); renderList(false);
      if (center && !options.selectionOwnsNavigation) setMapView([lat, lon], Math.max(14, map.getZoom()));
      const selectedPoint = {
        lat, lon, code: String(p.province_code), district: p.district || undefined,
        label: `${asText(p.province_name)} ${asText(p.district)} · แปลงทะเบียน GAP ${selectedId}`,
        note: `ตำแหน่งทะเบียน GAP ณ ${asText(manifest?.snapshot_date)} ยังไม่ยืนยันภาคสนาม; อากาศ NASA เป็นข้อมูลกริด ไม่ใช่เซนเซอร์สวน; ผลผลิตยังเป็นระดับจังหวัด`,
        point_kind: 'gap_registry', gap_id: selectedId, gap_snapshot_date: manifest?.snapshot_date,
        coordinate_quality: p.coordinate_quality || p.quality, gap_quality_flags: [...qualityFlags(feature)]
      };
      try {
        Promise.resolve(selectPoint(selectedPoint)).catch(error => {
          if (!destroyed) status.textContent = `เลือกหมุดแล้ว แต่เชื่อมพื้นที่ A/B ไม่สำเร็จ: ${error.message}`;
          if (typeof options.onError === 'function') options.onError(error);
        });
      } catch (error) {
        status.textContent = `เลือกหมุดแล้ว แต่เชื่อมพื้นที่ A/B ไม่สำเร็จ: ${error.message}`;
        if (typeof options.onError === 'function') options.onError(error);
      }
      redraw();
    }
    function stopMapClick(event) {
      if (event?.originalEvent) L.DomEvent.stopPropagation(event.originalEvent);
    }
    function redraw() {
      if (destroyed) return;
      if (!visible || !provinceCode || loading) {
        clearMarkers();
        if (!visible && !loading) status.textContent = 'ซ่อนหมุด GAP แล้ว รายการและข้อมูลทะเบียนยังอ่านได้';
        return;
      }
      // Let Leaflet transform the existing canvas during zoom. Rebuild only once
      // the transition settles, never in the middle of a wheel/zoom animation.
      if (zooming) return;
      const bounds = map.getBounds().pad(0.08);
      const zoom = Math.round(map.getZoom());
      let groups = clusterCache.get(zoom);
      if (!groups) {
        // World pixels, unlike container pixels, do not move when the map pans.
        // Group the whole filtered province so an edge entering the viewport
        // cannot move a cluster centroid or change its registry membership.
        groups = groupViewport(filtered, (lat, lon) => map.project([lat, lon], zoom), zoom);
        clusterCache.set(zoom, groups);
        if (clusterCache.size > 2) clusterCache.delete(clusterCache.keys().next().value);
      }
      const activeKeys = new Set();
      let viewportCount = 0;
      for (const group of groups) {
        let inBounds = 0;
        for (const feature of group.features) {
          if (bounds.contains(featurePosition(feature))) inBounds++;
        }
        viewportCount += inBounds;
        if (!inBounds) continue;
        const key = `${zoom}:${group.key}`;
        activeKeys.add(key);
        const count = group.features.length, isSelected = count === 1 && String(group.features[0].id || group.features[0].properties.id) === selectedId;
        const retained = markerRecords.get(key);
        if (retained) {
          if (count === 1 && retained.isSelected !== isSelected) {
            retained.marker.setStyle({color: isSelected ? '#111827' : '#087f8c', weight: isSelected ? 3 : 1.5});
            retained.marker.setRadius(count === 1 ? (isSelected ? 8 : 5) : Math.min(23, 10 + Math.log2(count) * 1.4));
            retained.isSelected = isSelected;
          }
          continue;
        }
        const clusterLabel = `${formatCount(count)} แปลงตามทะเบียน GAP · ยังไม่ยืนยันภาคสนาม · คลิกเพื่อซูมและเลือกรายการ`;
        let marker;
        if (count > 1 && typeof L.marker === 'function' && typeof L.divIcon === 'function') {
          const number = el('span', formatCount(count), 'gap-cluster-number');
          number.setAttribute('aria-hidden', 'true');
          marker = L.marker([group.lat, group.lon], {
            pane: paneName, keyboard: true, title: clusterLabel, alt: clusterLabel,
            bubblingMouseEvents: false,
            icon: L.divIcon({html: number, className: 'gap-cluster-icon', iconSize: [36, 36], iconAnchor: [18, 18]})
          });
        } else marker = L.circleMarker([group.lat, group.lon], {
          renderer, pane: paneName, radius: count === 1 ? (isSelected ? 8 : 5) : Math.min(23, 10 + Math.log2(count) * 1.4),
          color: isSelected ? '#111827' : '#087f8c', fillColor: count > 1 ? '#087f8c' : '#f5d782',
          fillOpacity: count > 1 ? 0.85 : 0.9, weight: isSelected ? 3 : 1.5, bubblingMouseEvents: false
        });
        const tooltip = el('span', count > 1 ? `${clusterLabel} · ไม่ใช่ระดับความเสี่ยง` : `แปลงทะเบียน GAP · ${asText(group.features[0].properties.district)} · ยังไม่ยืนยันภาคสนาม`);
        marker.bindTooltip(tooltip, {direction: 'top'});
        marker.on('click', event => {
          stopMapClick(event);
          if (count === 1) chooseFeature(group.features[0], false);
          else {
            clusterFeatures = group.features; page = 0; renderList(false); listDetails.open = true;
            const positions = group.features.map(featurePosition);
            if (positions.every(position => position[0] === positions[0][0] && position[1] === positions[0][1])) {
              setMapView(positions[0], Math.min(18, map.getZoom() + 2));
              status.textContent = `${formatCount(count)} แปลงใช้พิกัดเดียวกัน เลือกแต่ละรายการจากตัวกรองอำเภอและรายการด้านล่าง ไม่รวมว่าเป็นสวนเดียวกัน`;
            } else fitMapBounds(positions, {padding: [24, 24], maxZoom: Math.min(18, map.getZoom() + 3)});
          }
        });
        markers.addLayer(marker); markerRecords.set(key, {marker, isSelected});
      }
      for (const [key, record] of markerRecords) {
        if (!activeKeys.has(key)) { markers.removeLayer(record.marker); markerRecords.delete(key); }
      }
      const item = currentProvince();
      status.textContent = `${asText(item?.name ?? item?.province_name)} · ตามตัวกรอง ${formatCount(filtered.length)} หมุด · อยู่ในขอบจอ ${formatCount(viewportCount)} · วาด ${formatCount(activeKeys.size)} จุด/กลุ่ม`;
      if (filtered.length && !viewportCount) status.textContent += ' · ซูมกลับจังหวัดเพื่อดูหมุด';
      const excludedCount = item?.excluded_rows ?? Object.values(item?.excluded_counts || {}).reduce((total, value) => total + Number(value || 0), 0);
      summary.textContent = `snapshot ${asText(manifest?.snapshot_date)} · แสดงได้ ${formatCount(currentFeatures.length)} หมุดจาก ${formatCount(item?.source_rows)} ระเบียนจังหวัดนี้ · คัดออก ${formatCount(excludedCount)} ระเบียน · สีหมุดไม่ใช่ความเสี่ยงโรค`;
    }
    function scheduleRedraw() {
      if (destroyed || zooming || redrawTimer !== null) return;
      redrawTimer = requestFrame(() => { redrawTimer = null; redraw(); });
    }
    function onZoomStart() { zooming = true; cancelRedraw(); }
    function onZoomEnd() { zooming = false; scheduleRedraw(); }
    async function setProvince(code) {
      if (destroyed) return;
      if (String(code || '') === provinceCode && currentFeatures.length && !loading) { redraw(); return; }
      const requestVersion = ++version;
      provinceCode = String(code || ''); province.input.value = provinceCode;
      currentFeatures = []; filtered = []; clusterFeatures = null; page = 0; selectedId = null; selected.hidden = true;
      filters.district = ''; refreshFilters(); resetClusters(); renderList(false);
      retry.hidden = true; summary.textContent = '';
      if (!provinceCode) { loading = false; updateDisabled(); status.textContent = 'เลือกจังหวัดเพื่อโหลดหมุดเฉพาะจังหวัดนั้น'; return; }
      loading = true; updateDisabled(); status.textContent = 'กำลังโหลดทะเบียน GAP เฉพาะจังหวัด…';
      try {
        await loadManifest();
        if (destroyed || requestVersion !== version) return;
        const item = currentProvince();
        if (!item || !/^province_[0-9]+\.geojson$/.test(item.file)) throw new Error('จังหวัดนี้ไม่มีไฟล์ทะเบียน GAP ที่ผ่านเกณฑ์');
        if (!cache.has(provinceCode)) {
          if (!requests.has(provinceCode)) {
            const requestedCode = provinceCode;
            requests.set(requestedCode, fetchJson(item.file).then(data => {
              if (data.type !== 'FeatureCollection' || !Array.isArray(data.features) ||
                  data.features.some(feature => !validFeature(feature) || String(feature.properties.province_code) !== requestedCode)) {
                throw new Error('ข้อมูลพิกัดจังหวัดไม่ผ่านการตรวจรูปแบบ');
              }
              cache.set(requestedCode, data.features); return data.features;
            }).finally(() => requests.delete(requestedCode)));
          }
          await requests.get(provinceCode);
        }
        if (destroyed || requestVersion !== version) return;
        currentFeatures = cache.get(provinceCode); loading = false; refreshFilters(); updateDisabled(); applyFilters();
      } catch (error) {
        if (destroyed || requestVersion !== version) return;
        loading = false; updateDisabled(); status.textContent = `${error.message} · เปิดผ่านเซิร์ฟเวอร์โปรเจกต์ ไม่ใช้ file://`; retry.hidden = false;
        if (typeof options.onError === 'function') options.onError(error);
      }
    }
    function setVisible(value) { visible = !!value; checkbox.checked = visible; cancelRedraw(); redraw(); }
    checkbox.addEventListener('change', () => setVisible(checkbox.checked));
    province.input.addEventListener('change', async () => {
      const code = province.input.value; await setProvince(code);
      const bbox = currentProvince()?.bbox;
      if (code === provinceCode && Array.isArray(bbox) && bbox.length === 4) fitMapBounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]], {padding: [20, 20], maxZoom: 11});
    });
    for (const [input, key] of [[district.input, 'district'], [quality.input, 'quality'], [certification.input, 'dateStatus']]) {
      input.addEventListener('change', () => {
        filters[key] = input.value; applyFilters();
        if(key==='district'&&input.value&&filtered.length)fitMapBounds(filtered.map(featurePosition),{padding:[32,32],maxZoom:12});
      });
    }
    map.on('moveend', scheduleRedraw); map.on('zoomstart', onZoomStart); map.on('zoomend', onZoomEnd); updateDisabled();
    return {
      setProvince, setVisible,
      getState: () => ({provinceCode, visible, loading, loadedCount: currentFeatures.length, filteredCount: filtered.length, selectedId, filters: {...filters}}),
      destroy: () => {
        destroyed = true; version++; resetClusters();
        map.off('moveend', scheduleRedraw); map.off('zoomstart', onZoomStart); map.off('zoomend', onZoomEnd);
        map.removeLayer(markers); map.removeLayer(renderer); container.replaceChildren();
      }
    };
  }

  createGapOrchardLayer.helpers = Object.freeze({validFeature, filterFeatures, sourceUrl, dataUrl, groupViewport});
  root.createGapOrchardLayer = createGapOrchardLayer;
})(window);
