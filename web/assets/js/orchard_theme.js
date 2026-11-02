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
    root.document.querySelectorAll('[data-theme-toggle]').forEach(control => {
      control.textContent = 'Mode: ' + (theme === 'dark' ? 'Dark' : 'Light');
      control.dataset.mode = theme;
      control.setAttribute('aria-pressed', String(theme === 'dark'));
      control.setAttribute('aria-label', 'Mode: ' + (theme === 'dark' ? 'Dark' : 'Light') + '. Switch to ' + (theme === 'dark' ? 'light' : 'dark') + ' mode');
    });
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
      const button = root.document.createElement('button');
      button.type = 'button'; button.className = 'theme-control theme-toggle';
      button.dataset.themeToggle = '';
      button.addEventListener('click', () => root.OrchardTheme.setPreference(resolved() === 'dark' ? 'light' : 'dark'));
      header.append(button); apply();
    }
    root.document.querySelectorAll('[data-theme-select]').forEach(control => {
      control.value = preference;
      control.addEventListener('change', () => root.OrchardTheme.setPreference(control.value));
    });
  }, {once: true});
  apply();
})(window);
