/* Smooth, cancellable navigation using Leaflet's public API only.
 * Wheel / touch zoom remains Leaflet-owned so anchors, bounds and gestures agree.
 */
(function (root) {
  'use strict';

  const QUERY = '(prefers-reduced-motion: reduce)';
  const CONTROL_SELECTOR = 'input, select, textarea, button, [contenteditable="true"], [data-map-scroll], .leaflet-control';
  const NAVIGATION_KEYS = new Set(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', '+', '-', '=', 'Escape']);

  function motionQuery() {
    return typeof root.matchMedia === 'function' ? root.matchMedia(QUERY) : null;
  }

  function createOrchardMapMotion(options) {
    const map = options && options.map;
    if (!map || typeof map.setView !== 'function' || typeof map.fitBounds !== 'function') {
      throw new TypeError('Map motion requires a Leaflet map');
    }
    const element = options.element || (typeof map.getContainer === 'function' ? map.getContainer() : null);
    const query = motionQuery();
    const explicitPreference = typeof options.reducedMotion === 'boolean';
    let reduced = explicitPreference ? options.reducedMotion : !!(query && query.matches);
    let destroyed = false, resizeFrame = null, resizeOptions = null;
    const frame = typeof root.requestAnimationFrame === 'function'
      ? callback => root.requestAnimationFrame(callback)
      : callback => root.setTimeout(callback, 16);
    const cancelFrame = typeof root.cancelAnimationFrame === 'function'
      ? id => root.cancelAnimationFrame(id)
      : id => root.clearTimeout(id);

    function stop() {
      if (!destroyed && typeof map.stop === 'function') map.stop();
      return map;
    }

    function updatePreference() {
      reduced = explicitPreference ? options.reducedMotion : !!(query && query.matches);
      if (element && element.classList) element.classList.toggle('orchard-reduced-motion', reduced);
      stop();
    }

    function settings(value) {
      const supplied = value || {};
      const duration = Number.isFinite(supplied.duration) ? Math.max(0, Math.min(1.2, supplied.duration)) : 0.55;
      return {...supplied, duration, easeLinearity: supplied.easeLinearity === undefined ? 0.25 : supplied.easeLinearity,
        animate: !reduced && supplied.animate !== false && duration > 0};
    }

    function clampZoom(value) {
      const zoom = value === undefined ? map.getZoom() : value;
      if (!Number.isFinite(zoom)) throw new TypeError('Map zoom must be finite');
      const lower = typeof map.getMinZoom === 'function' ? map.getMinZoom() : -Infinity;
      const upper = typeof map.getMaxZoom === 'function' ? map.getMaxZoom() : Infinity;
      return Math.max(Number.isFinite(lower) ? lower : -Infinity,
        Math.min(Number.isFinite(upper) ? upper : Infinity, zoom));
    }

    function setView(latlng, zoom, value) {
      if (destroyed) return map;
      const targetZoom = clampZoom(zoom), opts = settings(value);
      stop();
      if (opts.animate && typeof map.flyTo === 'function') return map.flyTo(latlng, targetZoom, opts);
      return map.setView(latlng, targetZoom, {...opts, animate: false});
    }

    function fitBounds(bounds, value) {
      if (destroyed) return map;
      const opts = settings(value);
      stop();
      if (opts.animate && typeof map.flyToBounds === 'function') return map.flyToBounds(bounds, opts);
      return map.fitBounds(bounds, {...opts, animate: false});
    }

    // ResizeObserver may fire repeatedly while a panel or mobile viewport resizes.
    // One public invalidation per animation frame avoids redundant layer redraws.
    function invalidate(value) {
      if (destroyed) return map;
      resizeOptions = {...resizeOptions, ...value};
      if (resizeFrame !== null) return map;
      resizeFrame = frame(() => {
        resizeFrame = null;
        const opts = {pan: true, debounceMoveend: true, ...resizeOptions, animate: false};
        resizeOptions = null;
        if (destroyed || typeof map.invalidateSize !== 'function') return;
        // Leaflet's flyTo computes a path from the viewport at flight start.
        // Stop that path before changing viewport geometry, but do not cancel
        // navigation for ResizeObserver's initial / unchanged-size notification.
        if (element && Number.isFinite(element.clientWidth) && Number.isFinite(element.clientHeight)) {
          const width = element.clientWidth, height = element.clientHeight;
          if (width <= 0 || height <= 0) return; // Wait for a visible viewport.
          const previous = typeof map.getSize === 'function' ? map.getSize() : null;
          if (previous && previous.x === width && previous.y === height) return;
        }
        stop();
        map.invalidateSize(opts);
      });
      return map;
    }

    function interrupt() { stop(); }
    function onKey(event) { if (NAVIGATION_KEYS.has(event.key)) stop(); }
    function onWheel(event) {
      // Do not consume browser page-zoom shortcuts or scrolling inside controls.
      // No preventDefault: Leaflet handles ordinary map wheel events itself.
      const target = event.target;
      if (event.ctrlKey || event.metaKey || (target && typeof target.closest === 'function' && target.closest(CONTROL_SELECTOR))) {
        if (typeof event.stopImmediatePropagation === 'function') event.stopImmediatePropagation();
        return;
      }
      stop();
    }

    if (element && typeof element.addEventListener === 'function') {
      element.addEventListener('wheel', onWheel, {capture: true, passive: true});
      element.addEventListener('pointerdown', interrupt, {passive: true});
      element.addEventListener('keydown', onKey);
    }
    if (!explicitPreference && query) {
      if (typeof query.addEventListener === 'function') query.addEventListener('change', updatePreference);
      else if (typeof query.addListener === 'function') query.addListener(updatePreference);
    }
    updatePreference();

    return {
      setView, fitBounds, invalidate, stop,
      get reducedMotion() { return reduced; },
      destroy() {
        if (destroyed) return;
        stop(); destroyed = true;
        if (resizeFrame !== null) cancelFrame(resizeFrame);
        resizeFrame = null; resizeOptions = null;
        if (element && typeof element.removeEventListener === 'function') {
          element.removeEventListener('wheel', onWheel, true);
          element.removeEventListener('pointerdown', interrupt);
          element.removeEventListener('keydown', onKey);
        }
        if (!explicitPreference && query) {
          if (typeof query.removeEventListener === 'function') query.removeEventListener('change', updatePreference);
          else if (typeof query.removeListener === 'function') query.removeListener(updatePreference);
        }
      }
    };
  }

  // Read before constructing the map. A fresh object avoids shared option state.
  Object.defineProperty(createOrchardMapMotion, 'mapOptions', {get() {
    const query = motionQuery(), animate = !(query && query.matches);
    return {scrollWheelZoom: true, zoomSnap: 0.1, zoomDelta: 0.5, wheelDebounceTime: 20,
      wheelPxPerZoomLevel: 100, zoomAnimation: animate, fadeAnimation: animate,
      markerZoomAnimation: animate, inertia: animate, bounceAtZoomLimits: false};
  }});
  root.createOrchardMapMotion = createOrchardMapMotion;
})(window);
