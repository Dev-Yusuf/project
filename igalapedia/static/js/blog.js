/**
 * Blog detail page: like toggle (AJAX), share buttons, reply toggle
 */
(function () {
  'use strict';

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
  }

  function getCsrfToken() {
    return getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  }

  // Like toggle
  document.querySelectorAll('.blog-like-form').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('.blog-like-btn');
      var countEl = form.querySelector('.blog-like-count');
      var icon = form.querySelector('.blog-like-btn i');
      var url = form.action;
      var fd = new FormData(form);

      fetch(url, {
        method: 'POST',
        body: fd,
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCsrfToken()
        },
        credentials: 'same-origin'
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.liked !== undefined) {
            btn.classList.toggle('blog-liked', data.liked);
            icon.classList.toggle('far', !data.liked);
            icon.classList.toggle('fas', data.liked);
            if (countEl) countEl.textContent = data.count;
          }
        })
        .catch(function () {});
    });
  });

  // Share: Twitter
  document.querySelectorAll('.blog-share-twitter').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      var url = encodeURIComponent(el.dataset.url || window.location.href);
      var title = encodeURIComponent(el.dataset.title || document.title);
      window.open('https://twitter.com/intent/tweet?url=' + url + '&text=' + title, '_blank', 'width=550,height=420');
    });
  });

  // Share: Facebook
  document.querySelectorAll('.blog-share-facebook').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      var url = encodeURIComponent(el.dataset.url || window.location.href);
      window.open('https://www.facebook.com/sharer/sharer.php?u=' + url, '_blank', 'width=550,height=420');
    });
  });

  // Share: Copy link
  document.querySelectorAll('.blog-share-copy').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      var url = el.dataset.url || window.location.href;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () {
          var orig = el.innerHTML;
          el.innerHTML = '<i class="fas fa-check me-2"></i>Copied!';
          setTimeout(function () { el.innerHTML = orig; }, 2000);
        });
      }
    });
  });

  // Reply toggle
  document.querySelectorAll('.blog-reply-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = btn.dataset.commentId;
      var wrap = document.getElementById('reply-form-' + id);
      if (wrap) {
        wrap.style.display = wrap.style.display === 'none' ? 'block' : 'none';
      }
    });
  });

  document.querySelectorAll('.blog-reply-cancel').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var wrap = btn.closest('.blog-reply-form-wrap');
      if (wrap) wrap.style.display = 'none';
    });
  });
})();
