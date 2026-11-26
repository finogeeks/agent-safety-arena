/* One first-party enhancement. Language URLs remain authoritative. */
(() => {
  'use strict';
  const script = document.currentScript;
  const siteBase = new URL('.', script.src);
  const storageKey = 'arena-language:' + siteBase.pathname;
  const dismissalKey = storageKey + ':suggestion-dismissed';
  const lifetime = 180 * 24 * 60 * 60 * 1000;
  const picker = document.querySelector('.language-picker');
  if (!picker) return;
  const summary = picker.querySelector('summary');
  const links = [...picker.querySelectorAll('a[data-language]')];
  const currentLanguage = document.documentElement.lang;
  const available = new Map(links.map(link => [link.dataset.language, link]));
  const auto = picker.querySelector('[data-language-auto]');
  function preference() {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey));
      if (saved && typeof saved.language === 'string' && Number.isFinite(saved.expires)
          && saved.expires > Date.now() && saved.expires <= Date.now() + lifetime) return saved.language;
      localStorage.removeItem(storageKey);
    } catch (_) { /* Disabled or malformed storage cannot prevent navigation. */ }
    return null;
  }
  function remember(language) {
    try { localStorage.setItem(storageKey, JSON.stringify({language, expires: Date.now() + lifetime})); }
    catch (_) { /* Real links still work. */ }
  }
  function choose() {
    const saved = preference();
    if (available.has(saved)) return saved;
    for (const hint of navigator.languages || [navigator.language]) {
      const base = String(hint).toLowerCase().split('-')[0];
      const exact = [...available.keys()].find(code => code.toLowerCase() === String(hint).toLowerCase());
      const supported = exact || [...available.keys()].find(code => code.toLowerCase().split('-')[0] === base);
      if (supported) return supported;
    }
    return available.has('en') ? 'en' : links[0]?.dataset.language;
  }
  function automaticState() {
    if (!auto) return;
    const enabled = preference() === null;
    auto.setAttribute('aria-pressed', String(enabled));
    auto.querySelector('.language-check').textContent = enabled ? '✓' : '';
  }
  links.forEach(link => link.addEventListener('click', event => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    remember(link.dataset.language);
    if (link.dataset.language === currentLanguage && !document.body.hasAttribute('data-language-entry')) {
      event.preventDefault();
      picker.open = false;
      summary.focus();
    } else if (location.hash) {
      // Shared report and article section IDs survive changing the edition.
      link.hash = location.hash;
    }
  }));
  if (auto) {
    auto.parentElement.hidden = false;
    automaticState();
    auto.addEventListener('click', () => {
      try { localStorage.removeItem(storageKey); sessionStorage.removeItem(dismissalKey); }
      catch (_) { /* Keep the current explicit page usable. */ }
      automaticState();
      picker.querySelector('.language-status').textContent = auto.dataset.restored;
    });
  }
  picker.addEventListener('keydown', event => {
    if (event.key === 'Escape') { picker.open = false; summary.focus(); }
    const targets = [...links, ...(auto ? [auto] : [])];
    if (picker.open && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      event.preventDefault();
      const index = targets.indexOf(document.activeElement);
      const next = event.key === 'ArrowDown' ? (index + 1) % targets.length
        : (index < 0 ? targets.length - 1 : (index - 1 + targets.length) % targets.length);
      targets[next]?.focus();
    }
  });
  document.addEventListener('click', event => {
    if (!picker.contains(event.target)) picker.open = false;
  });
  if (document.body.hasAttribute('data-language-entry')) {
    const target = available.get(choose());
    if (target) location.replace(target.href);
    return;
  }
  if (!document.body.hasAttribute('data-language-home')) return;
  const proposed = choose();
  if (!proposed || proposed === currentLanguage) return;
  try { if (sessionStorage.getItem(dismissalKey)) return; }
  catch (_) { /* Suggestions do not depend on storage. */ }
  const target = available.get(proposed);
  const suggestion = document.createElement('aside');
  suggestion.className = 'language-suggestion';
  suggestion.setAttribute('aria-label', 'Language suggestion');
  const link = document.createElement('a');
  link.href = target.href;
  link.lang = proposed;
  link.textContent = proposed === 'zh-CN' ? '切换到简体中文' : 'Continue in ' + target.querySelector('[lang]').textContent;
  link.addEventListener('click', () => remember(proposed));
  const dismiss = document.createElement('button');
  dismiss.type = 'button';
  dismiss.textContent = 'Dismiss / 关闭';
  dismiss.addEventListener('click', () => {
    suggestion.hidden = true;
    try { sessionStorage.setItem(dismissalKey, '1'); } catch (_) { /* Optional memory. */ }
  });
  suggestion.append(link, dismiss);
  document.querySelector('.site-header').after(suggestion);
})();
