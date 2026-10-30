(() => {
    'use strict';
    const root = document.querySelector('[data-hero-map]');
    if (!root) return;
    const areas = [...root.querySelectorAll('[data-hero-lga]')];
    const status = root.querySelector('[data-hero-map-status]');
    const map = root.querySelector('.hero-map-svg');
    const compact = window.matchMedia('(max-width:767px)');
    const desktop = window.matchMedia('(min-width:1200px)');
    let selected = null;

    function pick(area) {
        selected = area === selected ? null : area;
        areas.forEach(item => {
            const active = item === selected;
            item.classList.toggle('is-picked', active);
            item.setAttribute('aria-pressed', String(active));
            item.setAttribute('tabindex', item === (selected || areas[0]) ? '0' : '-1');
        });
        status.textContent = selected ? `${selected.dataset.name} selected.` : 'Selection cleared.';
    }

    areas.forEach((area, index) => {
        area.setAttribute('role', 'button');
        area.setAttribute('aria-pressed', 'false');
        area.setAttribute('tabindex', index === 0 ? '0' : '-1');
        area.addEventListener('click', () => pick(area));
        area.addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                pick(area);
                return;
            }
            if (event.key === 'Escape') {
                event.preventDefault();
                if (selected) pick(selected);
                return;
            }
            const delta = {ArrowRight:1, ArrowDown:1, ArrowLeft:-1, ArrowUp:-1}[event.key];
            let next;
            if (delta) next = (index + delta + areas.length) % areas.length;
            else if (event.key === 'Home') next = 0;
            else if (event.key === 'End') next = areas.length - 1;
            else return;
            event.preventDefault();
            areas.forEach(item => item.setAttribute('tabindex', '-1'));
            areas[next].setAttribute('tabindex', '0');
            areas[next].focus();
        });
    });
    function resize() {
        // Give the nine highlighted LGAs more space and align them with the heading.
        const bounds = compact.matches ? '320 185 350 410' : desktop.matches ? '40 130 600 490' : '0 0 680 620';
        map.setAttribute('viewBox', bounds);
        root.classList.toggle('is-east-view', compact.matches);
    }
    compact.addEventListener('change', resize);
    desktop.addEventListener('change', resize);
    resize();
    root.classList.add('is-pickable');
})();
