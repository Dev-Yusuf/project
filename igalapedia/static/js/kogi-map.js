(() => {
    'use strict';
    const explorer = document.querySelector('[data-kogi-explorer]');
    if (!explorer) return;
    const areas = [...explorer.querySelectorAll('[data-lga]')];
    const panels = [...explorer.querySelectorAll('.roots-place')];
    const picker = explorer.querySelector('#roots-lga');
    const caption = explorer.querySelector('[data-map-caption]');
    const status = explorer.querySelector('[data-map-status]');
    const detailsLink = explorer.querySelector('[data-map-details]');
    const ids = areas.map(area => area.dataset.lga);
    let current = explorer.dataset.selected;
    const map = explorer.querySelector('.roots-map');
    const zoom = explorer.querySelector('[data-map-zoom]');
    const compact = window.matchMedia('(max-width:700px)');
    let manualZoom = false;

    function setZoom(focusEast) {
        map.setAttribute('viewBox', focusEast ? '320 185 350 410' : '0 0 680 620');
        explorer.classList.toggle('is-zoomed', focusEast);
        zoom.setAttribute('aria-pressed', String(focusEast));
        zoom.textContent = focusEast ? 'Full state ↙' : 'Focus east ↗';
        zoom.setAttribute('aria-label', focusEast ? 'Show the full state map' : 'Focus map on Kogi East');
    }
    zoom.hidden = false;
    zoom.addEventListener('click', () => {
        manualZoom = true;
        setZoom(zoom.getAttribute('aria-pressed') !== 'true');
    });
    compact.addEventListener('change', () => { if (!manualZoom) setZoom(compact.matches); });
    setZoom(compact.matches);

    function select(id, {writeHistory = true, announce = true} = {}) {
        if (!ids.includes(id)) id = 'idah';
        current = id;
        let label = '';
        areas.forEach(area => {
            const active = area.dataset.lga === id;
            area.classList.toggle('is-selected', active);
            area.setAttribute('aria-pressed', String(active));
            area.setAttribute('tabindex', active ? '0' : '-1');
            if (active) label = area.dataset.name;
        });
        panels.forEach(panel => { panel.hidden = panel.id !== `place-${id}`; });
        picker.value = id;
        caption.textContent = label;
        if (detailsLink) detailsLink.setAttribute('href', `#place-${id}`);
        explorer.dataset.selected = id;
        if (announce) status.textContent = `Showing ${label}. Place details are beside or below the map.`;
        if (writeHistory) {
            const url = new URL(window.location.href);
            url.searchParams.set('lga', id);
            url.hash = 'explore-kogi';
            if (url.href !== window.location.href) window.history.pushState(null, '', url);
        }
    }

    areas.forEach((area, index) => {
        area.addEventListener('click', event => {
            // Keep normal open-in-new-tab and modified link behaviour.
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            select(area.dataset.lga);
        });
        area.addEventListener('keydown', event => {
            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                select(area.dataset.lga);
                return;
            }
            const direction = {ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1}[event.key];
            let next;
            if (direction) next = (index + direction + areas.length) % areas.length;
            else if (event.key === 'Home') next = 0;
            else if (event.key === 'End') next = areas.length - 1;
            else return;
            event.preventDefault();
            areas.forEach(item => item.setAttribute('tabindex', '-1'));
            areas[next].setAttribute('tabindex', '0');
            areas[next].focus();
        });
    });
    picker.addEventListener('change', () => select(picker.value));
    picker.form.addEventListener('submit', event => {
        event.preventDefault();
        select(picker.value);
    });
    explorer.querySelectorAll('[data-place-step]').forEach(button => {
        button.hidden = false;
        button.addEventListener('click', () => {
            const index = (ids.indexOf(current) + Number(button.dataset.placeStep) + ids.length) % ids.length;
            // Move focus to the equivalent control in the newly visible panel.
            const step = button.dataset.placeStep;
            select(ids[index]);
            explorer.querySelector(`#place-${current} [data-place-step="${step}"]`).focus({preventScroll:true});
        });
    });
    window.addEventListener('popstate', () => select(new URL(window.location.href).searchParams.get('lga'), {writeHistory:false}));
    select(current, {writeHistory:false, announce:false});
    explorer.classList.add('is-enhanced');
})();
