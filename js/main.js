/* SLICED GOLF — Mobile Navigation.
   Kein Tracking, kein localStorage. */

(function () {
  'use strict';

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
})();
