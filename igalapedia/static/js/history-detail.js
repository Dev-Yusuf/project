/**
 * History article detail page: language toggle (English / Igala) and sticky bar.
 */
(function () {
  var contentEng = document.getElementById('content-english');
  var contentIga = document.getElementById('content-igala');
  var proseEng = contentEng && contentEng.querySelector('.prose');
  var proseIga = contentIga && contentIga.querySelector('.prose');
  var hasEnglish = proseEng && proseEng.innerText.trim().length > 0;
  var hasIgala = proseIga && proseIga.innerText.trim().length > 0;

  var btnEng = document.getElementById('toggle-english');
  var btnIga = document.getElementById('toggle-igala');
  var audioEngWrap = document.getElementById('audio-english-wrap');
  var audioIgaWrap = document.getElementById('audio-igala-wrap');

  var stickyBar = document.getElementById('history-sticky-bar');
  var stickyBtnEng = document.getElementById('sticky-toggle-english');
  var stickyBtnIga = document.getElementById('sticky-toggle-igala');

  function setActiveLanguage(lang) {
    var isEng = lang === 'english';
    if (contentEng) contentEng.classList.toggle('history-content-panel-hidden', !isEng);
    if (contentIga) contentIga.classList.toggle('history-content-panel-hidden', isEng);
    if (btnEng) {
      btnEng.classList.toggle('history-pill-active', isEng);
      btnEng.setAttribute('aria-pressed', isEng);
    }
    if (btnIga) {
      btnIga.classList.toggle('history-pill-active', !isEng);
      btnIga.setAttribute('aria-pressed', !isEng);
    }
    if (audioEngWrap) audioEngWrap.classList.toggle('history-audio-wrap-hidden', !isEng);
    if (audioIgaWrap) audioIgaWrap.classList.toggle('history-audio-wrap-hidden', isEng);
    if (stickyBtnEng) stickyBtnEng.classList.toggle('history-pill-active', isEng);
    if (stickyBtnIga) stickyBtnIga.classList.toggle('history-pill-active', !isEng);
  }

  function showEnglish() {
    setActiveLanguage('english');
  }

  function showIgala() {
    setActiveLanguage('igala');
  }

  if (hasEnglish && !hasIgala) {
    if (btnIga) btnIga.style.display = 'none';
    if (stickyBtnIga) stickyBtnIga.style.display = 'none';
  }
  if (hasIgala && !hasEnglish) {
    if (btnEng) btnEng.style.display = 'none';
    if (stickyBtnEng) stickyBtnEng.style.display = 'none';
    setActiveLanguage('igala');
  }

  if (btnEng) btnEng.addEventListener('click', showEnglish);
  if (btnIga) btnIga.addEventListener('click', showIgala);
  if (stickyBtnEng) stickyBtnEng.addEventListener('click', showEnglish);
  if (stickyBtnIga) stickyBtnIga.addEventListener('click', showIgala);

  if (stickyBar) {
    var titleBlock = document.getElementById('history-title-block');
    function onScroll() {
      if (!titleBlock) return;
      var rect = titleBlock.getBoundingClientRect();
      stickyBar.classList.toggle('history-sticky-bar-visible', rect.bottom < 70);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
  }
})();
