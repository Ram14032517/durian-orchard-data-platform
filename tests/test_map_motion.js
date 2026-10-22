const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../web/assets/js/orchard_map_motion.js'), 'utf8');

function fixture(initialPreference = false, explicitPreference) {
  const frames = new Map(), calls = [], listeners = new Map(), classes = new Set();
  let frameId = 0, changeHandler = null;
  const query = {
    matches: initialPreference,
    addEventListener(name, handler) { assert.equal(name, 'change'); changeHandler = handler; },
    removeEventListener(name, handler) { assert.equal(name, 'change'); if (changeHandler === handler) changeHandler = null; }
  };
  const element = {
    clientWidth: 800, clientHeight: 600,
    classList: {toggle(name, on) { if (on) classes.add(name); else classes.delete(name); }},
    addEventListener(name, handler, opts) { listeners.set(name, {handler, opts}); },
    removeEventListener(name, handler) { if (listeners.get(name)?.handler === handler) listeners.delete(name); }
  };
  let viewport = {x: element.clientWidth, y: element.clientHeight};
  const map = {
    getContainer: () => element, getZoom: () => 7, getMinZoom: () => 4, getMaxZoom: () => 18,
    getSize: () => ({...viewport}),
    stop() { calls.push(['stop']); return this; },
    setView(...args) { calls.push(['setView', ...args]); return this; },
    fitBounds(...args) { calls.push(['fitBounds', ...args]); return this; },
    flyTo(...args) { calls.push(['flyTo', ...args]); return this; },
    flyToBounds(...args) { calls.push(['flyToBounds', ...args]); return this; },
    invalidateSize(...args) {
      calls.push(['invalidateSize', ...args]); viewport = {x: element.clientWidth, y: element.clientHeight}; return this;
    }
  };
  const window = {
    matchMedia(text) { assert.equal(text, '(prefers-reduced-motion: reduce)'); return query; },
    requestAnimationFrame(callback) { const id = ++frameId; frames.set(id, callback); return id; },
    cancelAnimationFrame(id) { frames.delete(id); }
  };
  new Function('window', source)(window);
  const motion = window.createOrchardMapMotion({map, element, reducedMotion: explicitPreference});
  calls.length = 0;
  return {motion, map, calls, element, listeners, classes, frames, factory: window.createOrchardMapMotion,
    changePreference(value) { query.matches = value; if (changeHandler) changeHandler(); },
    flush() { const pending = [...frames.values()]; frames.clear(); pending.forEach(callback => callback()); },
    hasPreferenceListener: () => !!changeHandler};
}

test('native wheel options allow small anchored zoom steps without a custom zoom loop', () => {
  const f = fixture();
  assert.deepEqual(f.factory.mapOptions, {
    scrollWheelZoom: true, zoomSnap: 0.1, zoomDelta: 0.5, wheelDebounceTime: 20,
    wheelPxPerZoomLevel: 100, zoomAnimation: true, fadeAnimation: true,
    markerZoomAnimation: true, inertia: true, bounceAtZoomLimits: false
  });
  const opts = f.factory.mapOptions; opts.zoomSnap = 3;
  assert.equal(f.factory.mapOptions.zoomSnap, 0.1);
  assert.deepEqual(f.listeners.get('wheel').opts, {capture: true, passive: true});
});

test('new targets cancel the previous flight and preserve location, bounds and padding', () => {
  const f = fixture(), position = [9.5, 99.5], bounds = [[9, 99], [10, 100]];
  assert.equal(f.motion.setView(position, 14), f.map);
  f.motion.fitBounds(bounds, {padding: [24, 24], maxZoom: 12});
  assert.deepEqual(f.calls.map(call => call[0]), ['stop', 'flyTo', 'stop', 'flyToBounds']);
  assert.equal(f.calls[1][1], position); assert.equal(f.calls[1][2], 14);
  assert.equal(f.calls[1][3].duration, 0.55);
  assert.equal(f.calls[3][1], bounds); assert.deepEqual(f.calls[3][2].padding, [24, 24]);
  assert.equal(f.calls[3][2].maxZoom, 12);
});

test('view navigation clamps zoom and duration; explicit immediate requests do not fly', () => {
  const f = fixture();
  f.motion.setView([0, 0], 99, {duration: 8});
  assert.equal(f.calls[1][2], 18); assert.equal(f.calls[1][3].duration, 1.2);
  f.motion.setView([0, 0], -99, {animate: false});
  assert.equal(f.calls[3][0], 'setView'); assert.equal(f.calls[3][2], 4);
  assert.equal(f.calls[3][3].animate, false);
  f.motion.setView([0, 0]); assert.equal(f.calls[5][2], 7);
  assert.throws(() => f.motion.setView([0, 0], NaN), /finite/);
});

test('reduced-motion initializes without animation and reacts to preference changes', () => {
  const f = fixture(true);
  assert.equal(f.motion.reducedMotion, true);
  assert.equal(f.factory.mapOptions.zoomAnimation, false);
  assert.equal(f.factory.mapOptions.inertia, false);
  assert.equal(f.classes.has('orchard-reduced-motion'), true);
  f.motion.setView([9, 99], 12); f.motion.fitBounds([[9, 99], [10, 100]]);
  assert.deepEqual(f.calls.map(call => call[0]), ['stop', 'setView', 'stop', 'fitBounds']);
  assert.equal(f.calls[1][3].animate, false); assert.equal(f.calls[3][2].animate, false);
  f.changePreference(false);
  assert.equal(f.motion.reducedMotion, false); assert.equal(f.classes.size, 0);
  f.motion.setView([9, 99], 12); assert.equal(f.calls.at(-1)[0], 'flyTo');
  f.changePreference(true); assert.equal(f.calls.at(-1)[0], 'stop');
});

test('explicit reduced-motion preference overrides OS and requires no listener', () => {
  const f = fixture(false, true);
  assert.equal(f.hasPreferenceListener(), false);
  f.changePreference(false); assert.equal(f.motion.reducedMotion, true);
  f.motion.fitBounds([[0, 0], [1, 1]], {animate: true});
  assert.equal(f.calls.at(-1)[0], 'fitBounds'); assert.equal(f.calls.at(-1)[2].animate, false);
});

test('normal wheel cancels a flight but stays anchored / consumed by Leaflet, not this adapter', () => {
  const f = fixture(); let stopped = false, prevented = false;
  f.listeners.get('wheel').handler({target: {closest: () => null},
    stopImmediatePropagation() { stopped = true; }, preventDefault() { prevented = true; }});
  assert.deepEqual(f.calls, [['stop']]); assert.equal(stopped, false); assert.equal(prevented, false);
  assert.equal(f.frames.size, 0);
});

test('browser zoom shortcuts and control scrolling are never consumed by map wheel handler', () => {
  const f = fixture();
  for (const event of [{ctrlKey: true}, {metaKey: true}, {target: {closest: () => ({})}}]) {
    let stopped = false, prevented = false;
    f.listeners.get('wheel').handler({...event, stopImmediatePropagation() { stopped = true; },
      preventDefault() { prevented = true; }});
    assert.equal(stopped, true); assert.equal(prevented, false);
  }
  assert.deepEqual(f.calls, []);
});

test('pointer and map-navigation keys interrupt flights without hijacking keys', () => {
  const f = fixture();
  f.listeners.get('pointerdown').handler({});
  f.listeners.get('keydown').handler({key: 'ArrowUp'});
  f.listeners.get('keydown').handler({key: 'a'});
  assert.deepEqual(f.calls, [['stop'], ['stop']]);
});

test('resize invalidation is coalesced to one frame and never animates', () => {
  const f = fixture();
  f.element.clientWidth = 1000;
  f.motion.invalidate({debounceMoveend: false}); f.motion.invalidate({pan: true});
  assert.equal(f.frames.size, 1); assert.deepEqual(f.calls, []);
  f.flush();
  assert.deepEqual(f.calls, [['stop'], ['invalidateSize', {pan: true, debounceMoveend: false, animate: false}]]);
});

test('a real resize stops a flight before changing its viewport geometry', () => {
  const f = fixture();
  f.motion.fitBounds([[9, 99], [10, 100]]);
  f.element.clientHeight = 700;
  f.motion.invalidate({pan: true}); f.flush();
  assert.deepEqual(f.calls.map(call => call[0]), ['stop', 'flyToBounds', 'stop', 'invalidateSize']);
  assert.equal(f.calls.at(-1)[1].pan, true);
});

test('unchanged-size observer notifications do not interrupt navigation', () => {
  const f = fixture();
  f.motion.setView([9, 99], 12); f.motion.invalidate(); f.flush();
  assert.deepEqual(f.calls.map(call => call[0]), ['stop', 'flyTo']);
});

test('hidden viewport waits for visible dimensions before invalidation', () => {
  const f = fixture();
  f.element.clientWidth = 0; f.motion.invalidate(); f.flush();
  assert.deepEqual(f.calls, []);
  f.element.clientWidth = 900; f.motion.invalidate({pan: true}); f.flush();
  assert.deepEqual(f.calls.map(call => call[0]), ['stop', 'invalidateSize']);
});

test('destroy cancels pending work, stops flight and removes every listener', () => {
  const f = fixture(); f.motion.invalidate(); f.motion.destroy();
  assert.equal(f.frames.size, 0); assert.equal(f.listeners.size, 0);
  assert.equal(f.hasPreferenceListener(), false); assert.deepEqual(f.calls, [['stop']]);
  f.flush(); f.motion.setView([0, 0], 8); f.motion.fitBounds([[0, 0], [1, 1]]); f.motion.invalidate(); f.motion.destroy();
  assert.deepEqual(f.calls, [['stop']]);
});

test('older or minimal Leaflet integrations fall back to immediate public navigation', () => {
  const f = fixture(); delete f.map.flyTo; delete f.map.flyToBounds;
  f.motion.setView([0, 0], 8); f.motion.fitBounds([[0, 0], [1, 1]]);
  assert.equal(f.calls[1][0], 'setView'); assert.equal(f.calls[1][3].animate, false);
  assert.equal(f.calls[3][0], 'fitBounds'); assert.equal(f.calls[3][2].animate, false);
});
