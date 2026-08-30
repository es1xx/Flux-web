/**
 * Flux — theme, language, likes, infinite scroll, pill toasts
 */

document.addEventListener('DOMContentLoaded', function () {
    initializeBootstrapComponents();
    setupDjangoMessageToasts();
    setupLikeButtons();
    setupCommentToggles();
    setupThemeControls();
    setupLanguageControls();
    setupLogoutConfirmFromDrawer();
    setupInfiniteScroll();
});

function setupLogoutConfirmFromDrawer() {
    const modalEl = document.getElementById('logoutConfirmModal');
    const drawerEl = document.getElementById('fluxDrawer');
    if (!modalEl) return;

    document.querySelectorAll('[data-open-logout-modal]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const showModal = function () {
                bootstrap.Modal.getOrCreateInstance(modalEl).show();
            };

            if (drawerEl && drawerEl.classList.contains('show')) {
                drawerEl.addEventListener('hidden.bs.offcanvas', showModal, { once: true });
                bootstrap.Offcanvas.getOrCreateInstance(drawerEl).hide();
            } else {
                showModal();
            }
        });
    });
}

function initializeBootstrapComponents() {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el);
    });
    document.querySelectorAll('[data-bs-toggle="popover"]').forEach(function (el) {
        new bootstrap.Popover(el);
    });
}

/* --------------------------------------------
   Toast notifications
   -------------------------------------------- */

function normalizeToastType(type) {
    const t = String(type || 'info').toLowerCase();
    if (t === 'danger' || t === 'error') return 'error';
    if (t === 'success') return 'success';
    if (t === 'warning') return 'warning';
    return 'info';
}

function toastIconClass(type) {
    if (type === 'success') return 'bi-check-circle-fill';
    if (type === 'error') return 'bi-x-circle-fill';
    if (type === 'warning') return 'bi-exclamation-triangle-fill';
    return 'bi-info-circle-fill';
}

function getToastStack() {
    let stack = document.getElementById('fluxToastStack');
    if (!stack) {
        stack = document.createElement('div');
        stack.id = 'fluxToastStack';
        stack.className = 'flux-toast-stack';
        stack.setAttribute('aria-live', 'polite');
        document.body.appendChild(stack);
    }
    return stack;
}

function dismissToast(toast, immediate) {
    if (!toast || toast.dataset.leaving === '1') return;
    toast.dataset.leaving = '1';

    if (immediate) {
        toast.remove();
        return;
    }

    toast.classList.add('is-leaving');
    window.setTimeout(function () {
        if (toast.parentNode) toast.remove();
    }, 320);
}

/**
 * Global helper: showToast('Saved!', 'success')
 * Types: success | error | warning | info
 */
function showToast(message, type) {
    const text = String(message || '').trim();
    if (!text) return null;

    const kind = normalizeToastType(type);
    const toast = document.createElement('div');
    toast.className = 'flux-toast flux-toast--' + kind;
    toast.setAttribute('role', 'status');
    toast.innerHTML =
        '<span class="flux-toast-icon" aria-hidden="true"><i class="bi ' +
        toastIconClass(kind) +
        '"></i></span>' +
        '<span class="flux-toast-text"></span>' +
        '<button type="button" class="flux-toast-close" aria-label="Dismiss">' +
        '<i class="bi bi-x" aria-hidden="true"></i></button>';

    toast.querySelector('.flux-toast-text').textContent = text;
    toast.querySelector('.flux-toast-close').addEventListener('click', function () {
        dismissToast(toast);
    });

    getToastStack().appendChild(toast);

    const timer = window.setTimeout(function () {
        dismissToast(toast);
    }, 3500);
    toast.dataset.timer = String(timer);

    return toast;
}

function setupDjangoMessageToasts() {
    const source = document.getElementById('fluxDjangoMessages');
    if (!source) return;

    source.querySelectorAll('[data-toast-message]').forEach(function (el) {
        const message = el.getAttribute('data-toast-message');
        const type = el.getAttribute('data-toast-type') || 'info';
        if (message) showToast(message, type);
    });
    source.remove();
}

/** @deprecated Use showToast — kept for existing call sites */
function showNotification(message, type) {
    const mapped =
        type === 'danger' ? 'error' :
        type === 'secondary' ? 'info' :
        type || 'info';
    showToast(message, mapped);
}

/* --------------------------------------------
   Theme / language
   -------------------------------------------- */

function getTheme() {
    return document.documentElement.getAttribute('data-theme') || 'dark';
}

function setTheme(theme) {
    const next = theme === 'light' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('flux-theme', next); } catch (e) { /* ignore */ }
    syncThemeControls(next);
}

function syncThemeControls(theme) {
    const isLight = theme === 'light';
    document.querySelectorAll('.theme-switch-input').forEach(function (input) {
        input.checked = isLight;
    });
}

function setupThemeControls() {
    syncThemeControls(getTheme());
    document.querySelectorAll('.theme-toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            setTheme(getTheme() === 'dark' ? 'light' : 'dark');
        });
    });
    document.querySelectorAll('.theme-switch-input').forEach(function (input) {
        input.addEventListener('change', function () {
            setTheme(input.checked ? 'light' : 'dark');
        });
    });
}

function getLang() {
    const attr = document.documentElement.getAttribute('data-lang')
        || document.documentElement.getAttribute('lang')
        || 'en';
    return attr === 'uk' ? 'uk' : 'en';
}

function languagePrefixedUrl(lang) {
    const next = lang === 'uk' ? 'uk' : 'en';
    const path = window.location.pathname;
    const search = window.location.search || '';
    const hash = window.location.hash || '';
    let newPath;

    if (/^\/(uk|en)(\/|$)/.test(path)) {
        newPath = path.replace(/^\/(uk|en)(?=\/|$)/, '/' + next);
    } else if (path === '/') {
        newPath = '/' + next + '/';
    } else {
        newPath = '/' + next + path;
    }

    return newPath + search + hash;
}

function setLang(lang) {
    const next = lang === 'uk' ? 'uk' : 'en';
    if (next === getLang()) {
        syncLangButtons(next);
        return;
    }
    window.location.href = languagePrefixedUrl(next);
}

function syncLangButtons(lang) {
    document.querySelectorAll('.lang-btn').forEach(function (btn) {
        btn.classList.toggle('active', btn.getAttribute('data-lang') === lang);
    });
}

function setupLanguageControls() {
    syncLangButtons(getLang());
    document.querySelectorAll('.lang-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            setLang(btn.getAttribute('data-lang'));
        });
    });
}

/* --------------------------------------------
   Comments / likes
   -------------------------------------------- */

function setupCommentToggles(root) {
    const scope = root || document;
    scope.querySelectorAll('.comment-toggle').forEach(function (btn) {
        if (btn.dataset.bound === '1') return;
        btn.dataset.bound = '1';
        btn.addEventListener('click', function () {
            const target = document.querySelector(btn.getAttribute('data-target'));
            if (!target) return;
            const open = target.hasAttribute('hidden');
            if (open) {
                target.removeAttribute('hidden');
                btn.setAttribute('aria-expanded', 'true');
            } else {
                target.setAttribute('hidden', '');
                btn.setAttribute('aria-expanded', 'false');
            }
        });
    });
}

function setupLikeButtons(root) {
    const scope = root || document;
    scope.querySelectorAll('.like-btn').forEach(function (button) {
        if (button.dataset.bound === '1') return;
        button.dataset.bound = '1';

        button.addEventListener('click', async function (e) {
            e.preventDefault();
            e.stopPropagation();

            if (button.dataset.loading === '1') return;

            const postId = button.getAttribute('data-post-id');
            const likeUrl = button.getAttribute('data-like-url');
            if (!postId || !likeUrl) return;

            const csrfToken = getCsrfToken();
            if (!csrfToken) {
                showToast('Session expired. Please refresh and try again.', 'error');
                return;
            }

            button.dataset.loading = '1';
            button.disabled = true;

            try {
                const response = await fetch(likeUrl, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json',
                        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    },
                    body: '',
                });

                if (response.status === 401 || response.status === 403) {
                    window.location.href = languagePrefixedUrl(getLang()).replace(/\/[^/]*$/, '/login/');
                    return;
                }
                if (response.redirected && response.url.indexOf('/login') !== -1) {
                    window.location.href = response.url;
                    return;
                }
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }

                const contentType = response.headers.get('content-type') || '';
                if (contentType.indexOf('application/json') === -1) {
                    throw new Error('Unexpected response');
                }

                const data = await response.json();
                updateLikeButton(button, postId, data);
            } catch (error) {
                console.error('Like error:', error);
                showToast('Error updating like. Please try again.', 'error');
            } finally {
                button.dataset.loading = '0';
                button.disabled = false;
            }
        });
    });
}

function updateLikeButton(button, postId, data) {
    const likesCountElement =
        document.getElementById('likes-count-' + postId) ||
        button.querySelector('.likes-count');
    const icon = button.querySelector('i');

    if (likesCountElement) {
        likesCountElement.textContent = data.likes_count;
    }

    if (!icon) return;

    if (data.liked) {
        icon.classList.remove('bi-heart');
        icon.classList.add('bi-heart-fill');
        button.classList.add('liked');
        button.setAttribute('aria-pressed', 'true');
    } else {
        icon.classList.add('bi-heart');
        icon.classList.remove('bi-heart-fill');
        button.classList.remove('liked');
        button.setAttribute('aria-pressed', 'false');
    }
}

function getCsrfToken() {
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (input && input.value) return input.value;

    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;

    return getCookie('csrftoken');
}

function getCookie(name) {
    if (!document.cookie) return null;
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + '=') {
            return decodeURIComponent(cookie.substring(name.length + 1));
        }
    }
    return null;
}

/* --------------------------------------------
   Infinite scroll
   -------------------------------------------- */

function setupInfiniteScroll() {
    const grid = document.getElementById('fluxFeedGrid');
    const sentinel = document.getElementById('fluxFeedSentinel');
    const loader = document.getElementById('fluxFeedLoader');
    if (!grid || !sentinel || grid.getAttribute('data-infinite-scroll') !== 'true') return;

    let nextPage = parseInt(grid.getAttribute('data-next-page') || '', 10);
    let hasNext = grid.getAttribute('data-has-next') === 'true';
    let loading = false;

    if (!hasNext || !nextPage) {
        sentinel.remove();
        if (loader) loader.hidden = true;
        return;
    }

    function buildPageUrl(page) {
        const url = new URL(window.location.href);
        url.searchParams.set('page', String(page));
        return url.pathname + url.search;
    }

    function setLoading(isLoading) {
        loading = isLoading;
        if (!loader) return;
        loader.hidden = !isLoading;
        loader.setAttribute('aria-hidden', isLoading ? 'false' : 'true');
    }

    function stopObserving(observer) {
        if (observer) observer.disconnect();
        if (sentinel.parentNode) sentinel.remove();
        setLoading(false);
    }

    function loadNextPage(observer) {
        if (loading || !hasNext || !nextPage) return;
        setLoading(true);

        fetch(buildPageUrl(nextPage), {
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
            },
        })
            .then(function (response) {
                if (!response.ok) throw new Error('Failed to load more posts');
                return response.json();
            })
            .then(function (data) {
                const html = (data && data.html) || '';
                if (html) {
                    const wrap = document.createElement('div');
                    wrap.innerHTML = html;
                    const fragment = document.createDocumentFragment();
                    while (wrap.firstChild) {
                        fragment.appendChild(wrap.firstChild);
                    }
                    grid.appendChild(fragment);
                    setupLikeButtons(grid);
                    setupCommentToggles(grid);
                }

                hasNext = !!(data && data.has_next);
                nextPage = data && data.next_page ? parseInt(data.next_page, 10) : null;
                grid.setAttribute('data-has-next', hasNext ? 'true' : 'false');
                grid.setAttribute('data-next-page', nextPage || '');

                if (!hasNext) {
                    stopObserving(observer);
                }
            })
            .catch(function (err) {
                console.error('Infinite scroll error:', err);
                showToast('Could not load more posts.', 'error');
            })
            .finally(function () {
                if (hasNext) setLoading(false);
            });
    }

    const observer = new IntersectionObserver(
        function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) loadNextPage(observer);
            });
        },
        { root: null, rootMargin: '240px 0px', threshold: 0 }
    );

    observer.observe(sentinel);
}

window.showToast = showToast;
window.blogApp = {
    getCsrfToken: getCsrfToken,
    showNotification: showNotification,
    showToast: showToast,
    setTheme: setTheme,
    setLang: setLang,
};
