// Lumen 4.0.0 enhances the existing HTML; application state remains in the map code.
import '@santi020k/lumen-elements/styles.css';
import { defineLumenElements } from '@santi020k/lumen-elements/define';

const aside = document.querySelector('aside');
const tabs = document.createElement('lumen-tabs');
tabs.id = 'workspace-tabs';
const links = [...document.querySelectorAll('.quick-nav a')];
const panels = links.map(link => document.querySelector(link.getAttribute('href')));
for (const section of [...aside.querySelectorAll(':scope > section')]) {
  if (!['area-section', 'training-section'].includes(section.id) && !panels.includes(section)) document.getElementById('training-section').append(section);
}
const nav = document.querySelector('.quick-nav');
nav.setAttribute('role', 'tablist');
for (const [index, link] of links.entries()) {
  const panel = panels[index];
  link.id = 'tab-' + panel.id;
  link.dataset.value = panel.id;
  link.setAttribute('role', 'tab');
  link.setAttribute('aria-controls', panel.id);
  link.setAttribute('aria-selected', String(!panel.hidden));
  link.onclick = event => event.preventDefault();
  panel.setAttribute('role', 'tabpanel');
  panel.setAttribute('aria-labelledby', link.id);
}
const top = document.querySelector('.workspace-top');
const editor = document.getElementById('area-section');
aside.prepend(tabs);
tabs.append(top, document.getElementById('view-summary'), ...panels);
tabs.addEventListener('ui:tabs-change', event => showWorkspaceView(event.detail.value, false));
defineLumenElements(['Tabs', 'RadioGroup', 'Tooltip']);
