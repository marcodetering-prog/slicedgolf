/* SLICED GOLF — Navigation & Galerie-Filter
   Implementiert nach Design-Brief B.1 und D.6. Kein Tracking,
   kein localStorage. */

(function () {
  'use strict';

  /* ── Mobile Navigation ─────────────────────────── */

  var burger = document.querySelector('.nav-burger');
  var overlay = document.querySelector('.nav-overlay');
  var closeBtn = document.querySelector('.nav-overlay-close');

  function closeOverlay() {
    if (!overlay) return;
    overlay.classList.remove('is-open');
    overlay.setAttribute('aria-hidden', 'true');
    if (burger) burger.setAttribute('aria-expanded', 'false');
    document.documentElement.style.overflow = '';
  }

  if (burger && overlay) {
    burger.addEventListener('click', function () {
      overlay.classList.add('is-open');
      overlay.setAttribute('aria-hidden', 'false');
      burger.setAttribute('aria-expanded', 'true');
      document.documentElement.style.overflow = 'hidden';
    });
  }

  if (closeBtn) closeBtn.addEventListener('click', closeOverlay);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeOverlay();
  });

  /* ── Galerie-Filter ────────────────────────────── */

  var filterBtns = document.querySelectorAll('.filter-btn[data-filter]');
  var artworkCards = document.querySelectorAll('.gallery-grid .artwork-card');

  function applyFilter(filter) {
    filterBtns.forEach(function (b) {
      b.classList.toggle('is-active', b.dataset.filter === filter);
    });

    artworkCards.forEach(function (card) {
      var show = filter === 'alle'
        || card.dataset.status === filter
        || card.dataset.series === filter;

      if (show) {
        card.style.display = '';
        requestAnimationFrame(function () {
          card.style.opacity = '1';
          card.style.transform = 'none';
        });
      } else {
        card.style.opacity = '0';
        card.style.transform = 'scale(0.98)';
        setTimeout(function () { card.style.display = 'none'; }, 300);
      }
    });
  }

  if (filterBtns.length) {
    filterBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var filter = btn.dataset.filter;
        applyFilter(filter);
        var url = filter === 'alle'
          ? window.location.pathname
          : window.location.pathname + '?filter=' + encodeURIComponent(filter);
        window.history.replaceState(null, '', url);
      });
    });

    /* Vorgefilterter Einstieg: /werke?filter=verfuegbar */
    var param = new URLSearchParams(window.location.search).get('filter');
    if (param) applyFilter(param);
  }
})();
