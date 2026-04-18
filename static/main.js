/**
 * Fureoska — main.js
 * Подключать перед </body>: <script src="/static/main.js"></script>
 */

/* ─────────────────────────────────────────────
   1. УТИЛИТЫ
───────────────────────────────────────────── */
function saveSize(pid, size) {
  try { localStorage.setItem('size_' + pid, size); } catch (e) {}
}

function restoreSizes() {
  document.querySelectorAll("[id^='size-']").forEach(function (sel) {
    var pid = sel.id.replace('size-', '');
    try { var s = localStorage.getItem('size_' + pid); if (s) sel.value = s; } catch (e) {}
  });
}

function updateCartBadge(count) {
  var wrap = document.getElementById('cart-badge-wrap');
  if (!wrap) return;
  wrap.innerHTML = count > 0 ? '<span class="badge" id="cart-badge">' + count + '</span>' : '';
}

function showToast(msg) {
  var t = document.getElementById('cart-toast');
  if (!t) return;
  t.textContent = msg;
  t.style.display = 'block';
  t.classList.add('show');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(function () {
    t.classList.remove('show');
    setTimeout(function () { t.style.display = 'none'; }, 300);
  }, 2000);
}

/* ─────────────────────────────────────────────
   2. КОРЗИНА
───────────────────────────────────────────── */
function addToCart(pid) {
  if (pid === undefined) { addToCartProduct(); return; }

  var sizeEl = document.getElementById('size-' + pid);
  var size = sizeEl ? sizeEl.value : 'M';
  var btn = document.querySelector("[data-pid='" + pid + "']");
  var card = btn ? btn.closest('.card') : null;

  if (btn) { btn.disabled = true; btn.textContent = '⏳'; }

  fetch('/cart/add/' + pid + '?size=' + size, {
    method: 'GET',
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(function (r) { return r.json(); })
  .then(function (data) {
    if (btn) { btn.disabled = false; btn.textContent = btn.dataset.label || '🛒 В корзину'; }
    if (data.ok) {
      updateCartBadge(data.count);
      showToast(data.msg || 'Добавлено!');
      animateCartBtn(btn);
      if (card) animateFlyToCart(card);
      else animateBadge();
    } else if (data.redirect) {
      window.location.href = data.redirect;
    }
  })
  .catch(function () {
    if (btn) { btn.disabled = false; btn.textContent = btn.dataset.label || '🛒 В корзину'; }
    showToast('Ошибка, попробуйте снова');
  });
}

function addToCartProduct() {
  var sizeInput = document.querySelector('input[name="size"]:checked');
  var size = sizeInput ? sizeInput.value : 'M';
  var pid = document.getElementById('product-id-data');
  if (pid) window.location.href = '/cart/add/' + pid.dataset.id + '?size=' + size;
}

/* ─────────────────────────────────────────────
   3. ФИЛЬТР ЦЕН
───────────────────────────────────────────── */
function toggleFilter() {
  var dd = document.getElementById('filterDropdown');
  var arrow = document.getElementById('filterArrow');
  var btn = document.getElementById('filterToggle');
  if (!dd) return;
  var open = dd.classList.toggle('open');
  if (arrow) arrow.textContent = open ? '▴' : '▾';
  if (btn) btn.classList.toggle('open', open);
}

document.addEventListener('click', function (e) {
  var wrap = document.querySelector('.filter-wrap');
  if (!wrap || wrap.contains(e.target)) return;
  var dd = document.getElementById('filterDropdown');
  var arrow = document.getElementById('filterArrow');
  var btn = document.getElementById('filterToggle');
  if (dd) dd.classList.remove('open');
  if (arrow) arrow.textContent = '▾';
  if (btn) btn.classList.remove('open');
});

/* ─────────────────────────────────────────────
   4. ПОДКАТЕГОРИИ
───────────────────────────────────────────── */
var SUBCATEGORIES = {
  'Мужская': ['Верхняя одежда', 'Футболки', 'Брюки', 'Обувь'],
  'Женская':  ['Платья', 'Юбки', 'Блузки', 'Обувь'],
  'Детская':  ['Верхняя одежда', 'Футболки', 'Брюки', 'Обувь']
};

function updateSubcategories() {
  var cat = document.getElementById('category');
  var sub = document.getElementById('subcategory');
  if (!cat || !sub) return;
  sub.innerHTML = '';
  (SUBCATEGORIES[cat.value] || []).forEach(function (s) {
    var opt = document.createElement('option');
    opt.value = s; opt.textContent = s;
    sub.appendChild(opt);
  });
}

function updateSubs() {
  var c = document.getElementById('cat');
  var s = document.getElementById('sub');
  if (!c || !s) return;
  var cur = s.value;
  var source = (typeof subcats !== 'undefined') ? subcats : SUBCATEGORIES;
  s.innerHTML = '';
  (source[c.value] || []).forEach(function (v) {
    var o = document.createElement('option');
    o.value = o.textContent = v;
    if (v === cur) o.selected = true;
    s.appendChild(o);
  });
}

/* ─────────────────────────────────────────────
   5. ФОТО
───────────────────────────────────────────── */
function previewPhoto(e) {
  var file = e.target.files[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) {
    alert('Файл слишком большой. Максимум 5 МБ.');
    e.target.value = ''; return;
  }
  var reader = new FileReader();
  reader.onload = function (ev) {
    var img = document.getElementById('preview-img');
    var wrap = document.getElementById('photo-preview');
    if (img) img.src = ev.target.result;
    if (wrap) wrap.style.display = 'flex';
  };
  reader.readAsDataURL(file);
}

function clearPhoto() {
  var input = document.getElementById('photoInput');
  var wrap = document.getElementById('photo-preview');
  var img = document.getElementById('preview-img');
  if (input) input.value = '';
  if (wrap) wrap.style.display = 'none';
  if (img) img.src = '';
}

/* ─────────────────────────────────────────────
   6. ПАРОЛЬ
───────────────────────────────────────────── */
function togglePw(id, btn) {
  var inp = document.getElementById(id);
  if (!inp) return;
  inp.type = inp.type === 'password' ? 'text' : 'password';
  btn.textContent = inp.type === 'text' ? '🙈' : '👁';
}

/* ─────────────────────────────────────────────
   7. ТАБЫ
───────────────────────────────────────────── */
function showTab(name) {
  document.querySelectorAll('.tab-content').forEach(function (t) { t.style.display = 'none'; });
  document.querySelectorAll('.ptab').forEach(function (t) { t.classList.remove('active'); });
  var tab = document.getElementById('tab-' + name);
  if (tab) tab.style.display = 'block';
  if (event && event.target) event.target.classList.add('active');
}

/* ─────────────────────────────────────────────
   8. АДМИНКА
───────────────────────────────────────────── */
function filterTable(tableId, query) {
  var lq = query.toLowerCase();
  document.querySelectorAll('#' + tableId + ' tbody tr').forEach(function (row) {
    if (row.classList.contains('oi-row')) return;
    row.style.display = row.textContent.toLowerCase().includes(lq) ? '' : 'none';
  });
}

function toggleItems(id) {
  var row = document.getElementById('oi-' + id);
  if (!row) return;
  row.style.display = row.style.display === 'none' ? '' : 'none';
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('open');
}

/* ─────────────────────────────────────────────
   9. АНИМАЦИИ — только после загрузки DOM
───────────────────────────────────────────── */

/* ── Полёт картинки товара в корзину ── */
function animateCartBtn(btn) {
  if (!btn) return;
  // Пульс на кнопке
  btn.style.transition = 'transform 0.12s ease';
  btn.style.transform = 'scale(0.9)';
  setTimeout(function () {
    btn.style.transform = 'scale(1)';
    setTimeout(function () { btn.style.transform = ''; btn.style.transition = ''; }, 120);
  }, 120);
}

function animateFlyToCart(card) {
  var cartLink = document.getElementById('cart-link') || document.querySelector('a[href="/cart"]');
  if (!cartLink) return;

  var cardRect = card.getBoundingClientRect();
  var cartRect = cartLink.getBoundingClientRect();

  // Размер и стартовая позиция клона
  var cloneSize = Math.min(cardRect.width * 0.5, 100);
  var startX = cardRect.left + cardRect.width / 2 - cloneSize / 2;
  var startY = cardRect.top + cardRect.height / 2 - cloneSize / 2;
  var endX   = cartRect.left + cartRect.width / 2;
  var endY   = cartRect.top  + cartRect.height / 2;

  // Клон — фото или эмодзи
  var clone = document.createElement('div');
  clone.style.cssText = [
    'position:fixed',
    'left:' + startX + 'px',
    'top:' + startY + 'px',
    'width:' + cloneSize + 'px',
    'height:' + cloneSize + 'px',
    'border-radius:14px',
    'overflow:hidden',
    'box-shadow:0 12px 36px rgba(0,0,0,0.28)',
    'pointer-events:none',
    'z-index:99999',
    'will-change:transform,opacity'
  ].join(';');

  var img = card.querySelector('img');
  if (img) {
    var i = document.createElement('img');
    i.src = img.src;
    i.style.cssText = 'width:100%;height:100%;object-fit:cover;display:block;';
    clone.appendChild(i);
  } else {
    clone.style.cssText += ';background:#e44;display:flex;align-items:center;justify-content:center;font-size:30px;';
    clone.textContent = '🛍️';
  }

  document.body.appendChild(clone);

  // Дуговая траектория через Canvas-like расчёт контрольной точки
  var dur = 620; // мс
  var steps = 60;
  var step = 0;

  // Контрольная точка дуги — посередине, но выше
  var cx = (startX + cloneSize / 2 + endX) / 2;
  var cy = Math.min(startY, endY) - Math.abs(endX - startX) * 0.35 - 60;

  var raf;
  var startTime = null;

  function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function tick(ts) {
    if (!startTime) startTime = ts;
    var elapsed = ts - startTime;
    var t = Math.min(elapsed / dur, 1);
    var e = easeInOutCubic(t);

    // Квадратичная кривая Безье: B(t) = (1-t)²P0 + 2(1-t)tP1 + t²P2
    var bx = (1 - e) * (1 - e) * (startX + cloneSize / 2) + 2 * (1 - e) * e * cx + e * e * endX;
    var by = (1 - e) * (1 - e) * (startY + cloneSize / 2) + 2 * (1 - e) * e * cy + e * e * endY;

    // Масштаб: начинает с 1, к концу сжимается до 0
    var scale = 1 - e * 0.85;
    // Прозрачность: в конце исчезает
    var opacity = t > 0.75 ? 1 - (t - 0.75) / 0.25 : 1;

    clone.style.transform = [
      'translate(' + (bx - startX - cloneSize / 2) + 'px, ' + (by - startY - cloneSize / 2) + 'px)',
      'scale(' + scale + ')',
      'rotate(' + (e * 18) + 'deg)'
    ].join(' ');
    clone.style.opacity = opacity;

    if (t < 1) {
      raf = requestAnimationFrame(tick);
    } else {
      document.body.removeChild(clone);
      animateBadge();
    }
  }

  // Маленький pop-эффект перед стартом
  clone.style.transform = 'scale(0.85)';
  clone.style.transition = 'transform 0.12s ease';
  setTimeout(function () {
    clone.style.transition = 'none';
    clone.style.transform = 'scale(1)';
    raf = requestAnimationFrame(tick);
  }, 130);
}

function animateBadge() {
  var badge = document.getElementById('cart-badge');
  if (!badge) return;
  badge.style.transition = 'transform 0.2s cubic-bezier(.36,.07,.19,.97)';
  badge.style.transform = 'scale(1.8)';
  setTimeout(function () {
    badge.style.transform = 'scale(1)';
    setTimeout(function () { badge.style.transition = ''; }, 200);
  }, 200);
}

/* ── Всё остальное — после загрузки DOM ── */
document.addEventListener('DOMContentLoaded', function () {

  restoreSizes();
  updateSubcategories();

  // Форма редактирования профиля
  var editForm = document.getElementById('editForm');
  if (editForm) {
    editForm.addEventListener('submit', function (e) {
      var np = document.getElementById('new_pw');
      var cp = document.getElementById('conf_pw');
      var hint = document.getElementById('pw-match-hint');
      if (np && cp && np.value && np.value !== cp.value) {
        e.preventDefault();
        if (hint) hint.style.display = 'block';
        if (cp) cp.focus();
      }
    });
    var confPw = document.getElementById('conf_pw');
    if (confPw) {
      confPw.addEventListener('input', function () {
        var np = document.getElementById('new_pw');
        var hint = document.getElementById('pw-match-hint');
        if (hint && np) hint.style.display = (np.value && this.value && np.value !== this.value) ? 'block' : 'none';
      });
    }
  }

  // Форма регистрации
  document.querySelectorAll('input[name="role"]').forEach(function (r) {
    r.addEventListener('change', function () {
      var sf = document.getElementById('seller-fields');
      if (sf) sf.style.display = r.value === 'seller' ? 'block' : 'none';
    });
  });

  /* ── SCROLL REVEAL ── */
  var cards = document.querySelectorAll('.card');
  var others = document.querySelectorAll(
    '.cart-item, .order-card, .stat-card, .profile-header, .auth-box, .form-container, .success-box'
  );

  // Карточки товаров — скрываем и назначаем задержку
  cards.forEach(function (el, i) {
    el.classList.add('fur-hidden', 'fur-d' + (i % 4));
  });
  // Остальные элементы — без каскадной задержки
  others.forEach(function (el) {
    el.classList.add('fur-hidden', 'fur-d0');
  });

  var allReveal = Array.prototype.slice.call(cards).concat(Array.prototype.slice.call(others));

  if (allReveal.length === 0) return;

  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('fur-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.05 });

    allReveal.forEach(function (el) { observer.observe(el); });
  } else {
    // Фоллбэк для старых браузеров
    allReveal.forEach(function (el) { el.classList.add('fur-visible'); });
  }

  /* ── ПЕРЕХОД МЕЖДУ СТРАНИЦАМИ — плавный fade body ── */
  // Страница появляется с fade-in
  document.body.style.opacity = '0';
  document.body.style.transition = 'opacity 0.25s ease';
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      document.body.style.opacity = '1';
    });
  });

  document.addEventListener('click', function (e) {
    var link = e.target.closest('a[href]');
    if (!link) return;
    var href = link.getAttribute('href');
    if (!href
      || href.charAt(0) === '#'
      || href.indexOf('javascript') === 0
      || href.indexOf('://') !== -1
      || href === '/toggle-theme'
      || href.indexOf('/set-lang') === 0
      || link.target === '_blank'
      || e.ctrlKey || e.metaKey || e.shiftKey
      || link.closest('form')
    ) return;

    e.preventDefault();
    var dest = href;
    document.body.style.opacity = '0';
    setTimeout(function () { window.location.href = dest; }, 220);
  });

  window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
      document.body.style.opacity = '0';
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { document.body.style.opacity = '1'; });
      });
    }
  });

});
