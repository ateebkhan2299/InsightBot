/**
 * InsightBot — Core Client Utilities
 * Theme management, Toast Notifications & UI Helpers
 */

// ── Theme Management ──────────────────────────────────────────────────────────

function initTheme() {
    const saved = localStorage.getItem('insightbot-theme') || 'light';
    applyTheme(saved);
}

function applyTheme(theme) {
    let active = theme;
    if (theme === 'system') {
        active = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', active);
    document.documentElement.classList.toggle('dark', active === 'dark');
}

function setTheme(theme) {
    localStorage.setItem('insightbot-theme', theme);
    applyTheme(theme);
    if (typeof showToast === 'function') {
        showToast('Theme switched to ' + theme.toUpperCase(), 'success');
    }
}

// Auto-init theme on script load
initTheme();

// Listen for system theme changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const saved = localStorage.getItem('insightbot-theme');
    if (saved === 'system') applyTheme('system');
});


// ── Toast Notification System ─────────────────────────────────────────────────

function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');

    const isDark = document.documentElement.classList.contains('dark');
    const themes = {
        success: { bg: isDark ? '#064E3B' : '#ECFDF5', color: isDark ? '#6EE7B7' : '#065F46', border: isDark ? '#065F46' : '#A7F3D0', icon: 'fa-check-circle' },
        error:   { bg: isDark ? '#7F1D1D' : '#FEF2F2', color: isDark ? '#FCA5A5' : '#991B1B', border: isDark ? '#991B1B' : '#FECACA', icon: 'fa-times-circle' },
        warning: { bg: isDark ? '#78350F' : '#FFFBEB', color: isDark ? '#FCD34D' : '#92400E', border: isDark ? '#92400E' : '#FDE68A', icon: 'fa-exclamation-triangle' },
        info:    { bg: isDark ? '#1E1B4B' : '#EEF2FF', color: isDark ? '#A5B4FC' : '#3730A3', border: isDark ? '#3730A3' : '#C7D2FE', icon: 'fa-info-circle' }
    };

    const t = themes[type] || themes.info;

    toast.style.cssText = `background:${t.bg};color:${t.color};border:1px solid ${t.border};padding:10px 16px;border-radius:8px;font-size:13px;font-weight:500;box-shadow:0 4px 12px rgba(0,0,0,0.15);display:flex;align-items:center;gap:8px;pointer-events:auto;transition:all 0.25s ease;opacity:0;transform:translateY(8px);max-width:380px;`;
    toast.innerHTML = `<i class="fas ${t.icon}" style="flex-shrink:0;"></i> <span>${message}</span>`;

    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(8px)';
        setTimeout(() => toast.remove(), 250);
    }, 3500);
}


// ── Flash Message Auto-Display ─────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.flash-message').forEach(el => {
        const type = el.dataset.type || 'info';
        const msg = el.textContent.trim();
        if (msg) showToast(msg, type);
        setTimeout(() => el.remove(), 100);
    });
});


// ── Mobile Sidebar Toggle ─────────────────────────────────────────────────────

function toggleSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('hidden');
}


// ── Number Formatting ─────────────────────────────────────────────────────────

function formatNumber(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
    return n.toString();
}


// ── Copy to Clipboard ─────────────────────────────────────────────────────────

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard', 'success');
    }).catch(() => {
        showToast('Failed to copy', 'error');
    });
}
