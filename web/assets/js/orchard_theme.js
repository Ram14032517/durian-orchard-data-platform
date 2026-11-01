/* Presentation only. Runs in <head> before paint; never reads orchard data. */
(function (root) {
  'use strict';
  const key = 'durian.orchard.theme.v1';
  const valid = value => ['light', 'dark', 'system'].includes(value);
  const media = typeof root.matchMedia === 'function' ? root.matchMedia('(prefers-color-scheme: dark)') : null;
  let preference = 'system';
  try { const saved = root.localStorage.getItem(key); if (valid(saved)) preference = saved; } catch { /* Storage can be disabled. */ }
  const resolved = () => preference === 'system' ? (media?.matches ? 'dark' : 'light') : preference;
  function apply() {
    const theme = resolved();
    root.document.documentElement.dataset.theme = theme;
    root.document.documentElement.style.colorScheme = theme;
    root.document.querySelectorAll('[data-theme-select]').forEach(control => { control.value = preference; });
    root.dispatchEvent(new root.CustomEvent('orchard:theme-change', {detail: {preference, theme}}));
  }
  root.OrchardTheme = Object.freeze({
    getPreference: () => preference,
    getTheme: resolved,
    setPreference(value) {
      if (!valid(value)) return false;
      preference = value;
      try { root.localStorage.setItem(key, value); } catch { /* Still works for this page. */ }
      apply();
      return true;
    },
    subscribe(listener) {
      const notify = event => listener(event.detail);
      root.addEventListener('orchard:theme-change', notify);
      return () => root.removeEventListener('orchard:theme-change', notify);
    }
  });
  const systemChanged = () => { if (preference === 'system') apply(); };
  if (media?.addEventListener) media.addEventListener('change', systemChanged);
  else if (media?.addListener) media.addListener(systemChanged);
  root.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    preference = valid(event.newValue) ? event.newValue : 'system';
    apply();
  });
  root.document.addEventListener('DOMContentLoaded', () => {
    const header = root.document.querySelector('header.orchard-header');
    if (header && !root.document.getElementById('orchard-react-root')) {
      const label = root.document.createElement('label'), select = root.document.createElement('select');
      label.className = 'theme-control';
      select.dataset.themeSelect = '';
      select.setAttribute('aria-label', 'ธีมหน้าจอ');
      for (const [value, text] of [['system','ตามระบบ'],['light','Light · สว่าง'],['dark','Dark · มืด']]) {
        const option = root.document.createElement('option'); option.value = value; option.textContent = text; select.append(option);
      }
      label.append(select); header.append(label);
    }
    root.document.querySelectorAll('[data-theme-select]').forEach(control => {
      control.value = preference;
      control.addEventListener('change', () => root.OrchardTheme.setPreference(control.value));
    });
  }, {once: true});
  apply();
})(window);
