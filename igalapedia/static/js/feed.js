/**
 * Infinite scroll for the discovery feed. Fetches next page when sentinel is visible.
 */
(function () {
  var apiUrl = window.FEED_API_URL;
  var pageSize = window.FEED_PAGE_SIZE || 12;
  var hasMore = window.FEED_INITIAL_HAS_MORE !== false;
  var offset = window.FEED_OFFSET || 0;
  var loading = false;
  var listEl = document.getElementById('feed-list');
  var sentinelEl = document.getElementById('feed-sentinel');
  var loadingEl = document.getElementById('feed-loading');
  var hintEl = document.getElementById('feed-load-more-hint');
  var endEl = document.getElementById('feed-end-message');

  function formatDate(isoStr) {
    if (!isoStr) return '';
    try {
      var d = new Date(isoStr);
      var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return months[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear();
    } catch (e) {
      return '';
    }
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function buildCard(item) {
    var typeLabels = { word: 'Dictionary', blog: 'Blog', history: 'History' };
    var typeLabel = typeLabels[item.type] || 'Content';
    var typeClass = 'feed-type-' + item.type;
    var icons = { word: 'fa-book', blog: 'fa-newspaper', history: 'fa-landmark' };
    var icon = icons[item.type] || 'fa-file-alt';
    var imgHtml = item.thumbnail_url
      ? '<img src="' + escapeHtml(item.thumbnail_url) + '" alt="' + escapeHtml(item.title) + '" class="feed-card-img">'
      : '<div class="feed-card-placeholder d-flex align-items-center justify-content-center"><i class="fas ' + icon + ' fa-3x"></i></div>';
    var dateHtml = item.date ? '<p class="text-muted small mt-2 mb-0">' + escapeHtml(formatDate(item.date)) + '</p>' : '';
    var excerpt = (item.excerpt || '').substring(0, 100);
    if (item.excerpt && item.excerpt.length > 100) excerpt += '...';

    return (
      '<div class="col-md-6 col-lg-4 feed-item-col">' +
      '<a href="' + escapeHtml(item.url) + '" class="card h-100 text-decoration-none border-0 feed-card">' +
      '<div class="feed-card-image-wrap">' + imgHtml + '</div>' +
      '<div class="card-body p-4">' +
      '<span class="badge feed-type-badge ' + typeClass + ' mb-2">' + escapeHtml(typeLabel) + '</span>' +
      '<h3 class="h5 fw-bold mb-2 feed-card-title">' + escapeHtml(item.title) + '</h3>' +
      '<p class="text-muted small mb-0 feed-card-excerpt">' + escapeHtml(excerpt) + '</p>' +
      dateHtml +
      '</div></a></div>'
    );
  }

  function loadMore() {
    if (!apiUrl || !hasMore || loading || !listEl) return;
    loading = true;
    if (loadingEl) loadingEl.style.display = 'block';
    if (hintEl) hintEl.style.display = 'none';

    var url = apiUrl + '?offset=' + encodeURIComponent(offset) + '&limit=' + encodeURIComponent(pageSize);
    fetch(url, { headers: { 'Accept': 'application/json' } })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.items && data.items.length) {
          var html = data.items.map(buildCard).join('');
          listEl.insertAdjacentHTML('beforeend', html);
          offset += data.items.length;
        }
        hasMore = data.has_more === true;
        if (!hasMore && endEl) {
          endEl.style.display = 'block';
        }
      })
      .catch(function () {
        if (hintEl) hintEl.style.display = 'block';
        hintEl.textContent = 'Could not load more. Try again.';
      })
      .finally(function () {
        loading = false;
        if (loadingEl) loadingEl.style.display = 'none';
        if (hasMore && hintEl) hintEl.style.display = 'block';
      });
  }

  if (sentinelEl && hasMore) {
    var observer = new IntersectionObserver(
      function (entries) {
        if (entries[0].isIntersecting) loadMore();
      },
      { rootMargin: '100px', threshold: 0 }
    );
    observer.observe(sentinelEl);
  }
})();
