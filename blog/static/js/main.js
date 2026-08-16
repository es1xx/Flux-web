/**
 * Flux — theme, language (URL prefixes), likes, feed interactions
 */

document.addEventListener('DOMContentLoaded', function () {
    initializeBootstrapComponents();
    setupMessageAutoDismiss();
    setupLikeButtons();
    setupCommentToggles();
    setupThemeControls();
    setupLanguageControls();
    setupLogoutConfirmFromDrawer();
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

function setupMessageAutoDismiss() {
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(function (alert) {
        setTimeout(function () {
            try {
                bootstrap.Alert.getOrCreateInstance(alert).close();
            } catch (e) { /* ignore */ }
        }, 5000);
    });
}

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

function setupCommentToggles() {
    document.querySelectorAll('.comment-toggle').forEach(function (btn) {
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

function setupLikeButtons() {
    document.querySelectorAll('.like-btn').forEach(function (button) {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            if (button.dataset.loading === '1') return;

            const postId = button.getAttribute('data-post-id');
            const likeUrl = button.getAttribute('data-like-url');
            if (!postId || !likeUrl) return;

            const csrfToken = getCsrfToken();
            if (!csrfToken) {
                showNotification('Session expired. Please refresh and try again.', 'danger');
                return;
            }

            button.dataset.loading = '1';
            button.disabled = true;

            fetch(likeUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                },
                body: '',
            })
                .then(function (response) {
                    if (response.status === 401 || response.status === 403) {
                        window.location.href = languagePrefixedUrl(getLang()).replace(/\/[^/]*$/, '/login/');
                        throw new Error('auth');
                    }
                    if (response.redirected && response.url.indexOf('/login') !== -1) {
                        window.location.href = response.url;
                        throw new Error('auth');
                    }
                    if (!response.ok) throw new Error('Network response was not ok');
                    const type = response.headers.get('content-type') || '';
                    if (type.indexOf('application/json') === -1) {
                        throw new Error('Unexpected response');
                    }
                    return response.json();
                })
                .then(function (data) {
                    updateLikeButton(button, postId, data);
                })
                .catch(function (error) {
                    if (error && error.message === 'auth') return;
                    console.error('Like error:', error);
                    showNotification('Error updating like. Please try again.', 'danger');
                })
                .finally(function () {
                    button.dataset.loading = '0';
                    button.disabled = false;
                });
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
    } else {
        icon.classList.add('bi-heart');
        icon.classList.remove('bi-heart-fill');
        button.classList.remove('liked');
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

function showNotification(message, type) {
    type = type || 'info';
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-' + type + ' alert-dismissible fade show';
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML =
        message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';

    const container = document.querySelector('.flux-main .flux-container')
        || document.querySelector('.flux-container')
        || document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        setTimeout(function () {
            try { bootstrap.Alert.getOrCreateInstance(alertDiv).close(); } catch (e) { /* ignore */ }
        }, 5000);
    }
}

window.blogApp = {
    getCsrfToken: getCsrfToken,
    showNotification: showNotification,
    setTheme: setTheme,
    setLang: setLang,
};
