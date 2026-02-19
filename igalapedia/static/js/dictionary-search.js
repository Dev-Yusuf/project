(function () {
    'use strict';

    var DEBOUNCE_MS = 280;
    var SEARCH_API_PATH = '/dictionary/api/search/';

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function buildSingleWordUrl(slug) {
        var pathname = window.location.pathname.replace(/\/?$/, '/');
        return pathname + 'single-word/' + encodeURIComponent(slug) + '/';
    }

    function renderWordCard(word, slug) {
        var col = document.createElement('div');
        col.className = 'col-6 col-md-4 col-lg-3';
        var a = document.createElement('a');
        a.href = buildSingleWordUrl(slug);
        a.className = 'card h-100 text-decoration-none shadow-hover border-0';
        a.setAttribute('style', 'background: var(--bg-card);');
        var body = document.createElement('div');
        body.className = 'card-body text-center d-flex flex-column align-items-center justify-content-center py-4';
        var h3 = document.createElement('h3');
        h3.className = 'h4 fw-bold mb-0 text-primary';
        h3.textContent = word;
        var viewDetails = document.createElement('div');
        viewDetails.className = 'mt-2 text-muted small opacity-0';
        viewDetails.textContent = 'View Details';
        body.appendChild(h3);
        body.appendChild(viewDetails);
        a.appendChild(body);
        col.appendChild(a);
        return col;
    }

    function renderNoResults() {
        var col = document.createElement('div');
        col.className = 'col-12 text-center py-5';
        col.innerHTML = [
            '<div class="mb-3 text-muted"><i class="fas fa-search fa-3x opacity-25"></i></div>',
            '<h3 class="h5 text-muted">No words found matching your search.</h3>',
            '<p class="text-muted small">Try checking the spelling or submitting a new word.</p>',
            '<a href="/dictionary/submit/" class="btn btn-outline-primary btn-sm mt-2">Submit a Word</a>'
        ].join('');
        return col;
    }

    function renderLoading() {
        var col = document.createElement('div');
        col.className = 'col-12 text-center py-5 text-muted';
        col.innerHTML = '<p class="mb-0">Searching...</p>';
        return col;
    }

    function initDictionarySearch() {
        var form = document.getElementById('dictionary-search-form');
        var gridWrapper = document.getElementById('dictionary-word-grid');
        var paginationEl = document.getElementById('dictionary-pagination');
        if (!form || !gridWrapper || !paginationEl) return;

        var searchInput = form.querySelector('input[name="word"]');
        if (!searchInput) return;

        var row = gridWrapper.querySelector('.row.g-3');
        if (!row) return;

        var debounceTimer = null;

        function runSearch() {
            var q = searchInput.value.trim();
            if (!q) {
                window.location.href = window.location.pathname;
                return;
            }

            row.innerHTML = '';
            row.appendChild(renderLoading());
            paginationEl.style.display = 'none';

            var apiUrl = (gridWrapper.getAttribute('data-search-api-url') || SEARCH_API_PATH);
            if (apiUrl.indexOf('?') === -1) {
                apiUrl += '?q=' + encodeURIComponent(q);
            } else {
                apiUrl += '&q=' + encodeURIComponent(q);
            }

            fetch(apiUrl, { headers: { 'Accept': 'application/json' } })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    row.innerHTML = '';
                    var words = data.words || [];
                    if (words.length === 0) {
                        row.appendChild(renderNoResults());
                    } else {
                        words.forEach(function (item) {
                            row.appendChild(renderWordCard(item.word, item.slug));
                        });
                    }
                })
                .catch(function () {
                    row.innerHTML = '';
                    row.appendChild(renderNoResults());
                });
        }

        function onInput() {
            if (debounceTimer) clearTimeout(debounceTimer);
            var q = searchInput.value.trim();
            if (!q) {
                debounceTimer = setTimeout(function () {
                    window.location.href = window.location.pathname;
                }, DEBOUNCE_MS);
                return;
            }
            debounceTimer = setTimeout(runSearch, DEBOUNCE_MS);
        }

        searchInput.addEventListener('input', onInput);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDictionarySearch);
    } else {
        initDictionarySearch();
    }
})();
