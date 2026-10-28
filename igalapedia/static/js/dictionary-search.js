/* Search and pagination also work as normal GET requests. */
(() => {
    'use strict';
    const form = document.getElementById('dictionary-search-form');
    const results = document.getElementById('dictionary-results');
    if (!form || !results) return;
    const input = form.elements.word;
    const status = document.getElementById('dictionary-status');
    const browser = document.querySelector('.lexicon-browser');
    let timer;
    let controller;
    let version = 0;

    const cancel = () => {
        clearTimeout(timer);
        version += 1;
        controller?.abort();
        browser.removeAttribute('aria-busy');
    };
    const formUrl = () => {
        const url = new URL(results.dataset.baseUrl, location.origin);
        if (input.value.trim()) url.searchParams.set('word', input.value.trim());
        return url;
    };
    const browse = async (url, mode = 'replace', focus = false) => {
        cancel();
        const token = version;
        controller = new AbortController();
        const request = controller;
        const timeout = setTimeout(() => request.abort(), 10000);
        const fetchUrl = new URL(url);
        fetchUrl.searchParams.set('fragment', '1');
        browser.setAttribute('aria-busy', 'true');
        status.textContent = 'Searching the dictionary…';
        results.querySelector('.lexicon-load-error')?.remove();
        try {
            const response = await fetch(fetchUrl, {signal: request.signal, headers: {'Accept': 'text/html'}});
            if (!response.ok) throw new Error('Dictionary unavailable');
            const html = await response.text();
            if (token !== version) return;
            const parsed = new DOMParser().parseFromString(html, 'text/html');
            const content = parsed.querySelector('.lexicon-result-content');
            if (!content) throw new Error('Unexpected response');
            results.replaceChildren(document.importNode(content, true));
            const data = content.dataset;
            input.value = data.query;
            document.title = `Igala Dictionary${Number(data.page) > 1 ? ` · Page ${data.page}` : ''} · IgalaHeritage`;
            if (mode === 'push') history.pushState(null, '', url);
            if (mode === 'replace') history.replaceState(null, '', url);
            status.textContent = `${data.total} ${Number(data.total) === 1 ? 'word' : 'words'} found. Page ${data.page}.`;
            if (focus) {
                const heading = results.querySelector('#lexicon-results-heading');
                heading.focus({preventScroll: true});
                heading.scrollIntoView({block: 'start'});
            }
        } catch (error) {
            if (token !== version) return;
            const notice = document.createElement('div');
            notice.className = 'lexicon-load-error';
            notice.setAttribute('role', 'alert');
            notice.textContent = 'Couldn’t load the dictionary. Please try searching again.';
            results.prepend(notice);
            status.textContent = '';
        } finally {
            clearTimeout(timeout);
            if (token === version) browser.removeAttribute('aria-busy');
        }
    };
    input.addEventListener('input', () => {
        cancel();
        timer = setTimeout(() => browse(formUrl()), 150);
    });
    form.addEventListener('submit', event => {
        event.preventDefault();
        browse(formUrl());
    });
    results.addEventListener('click', event => {
        const link = event.target.closest('a[data-browse-link]');
        if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        browse(new URL(link.href), 'push', link.closest('.lexicon-pagination') !== null);
    });
    window.addEventListener('popstate', () => browse(new URL(location.href), 'none'));
})();
