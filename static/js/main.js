/**
 * InsightBot Main JavaScript
 * Handles Theme, Sidebar, and Localization
 */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
});

function setTheme(theme) {
    let activeTheme = theme;
    if (theme === 'system') {
        activeTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    if (activeTheme === 'dark') {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
    
    updateThemeIcon(activeTheme);
}

function initTheme() {
    const themeBtn = document.getElementById('theme-toggle');
    const sidebarThemeBtn = document.getElementById('sidebar-theme-toggle');
    
    const currentTheme = localStorage.getItem('theme') || 'dark';
    setTheme(currentTheme);
    
    const toggleAction = () => {
        let theme = document.documentElement.getAttribute('data-theme') || 'dark';
        let newTheme = theme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme);
    };
    
    if (themeBtn) themeBtn.addEventListener('click', toggleAction);
    if (sidebarThemeBtn) sidebarThemeBtn.addEventListener('click', toggleAction);
}

function updateThemeIcon(theme) {
    const icons = document.querySelectorAll('#theme-toggle i, #sidebar-theme-toggle i');
    icons.forEach(icon => {
        if (theme === 'dark') {
            icon.className = 'fas fa-sun';
        } else {
            icon.className = 'fas fa-moon';
        }
    });
}

function initSidebar() {
    const mobileToggle = document.getElementById('mobile-menu-btn');
    const sidebar = document.querySelector('.app-sidebar');
    
    if (mobileToggle && sidebar) {
        mobileToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 1024 && 
                !sidebar.contains(e.target) && 
                !mobileToggle.contains(e.target) && 
                sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
            }
        });
    }
}

// Minimal Toast System
function showToast(message, type = 'info') {
    // Check if toast container exists
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed; bottom:20px; right:20px; z-index:9999; display:flex; flex-direction:column; gap:10px;';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `alert alert-${type}`;
    toast.style.cssText = 'margin:0; box-shadow:0 4px 6px rgba(0,0,0,0.1); animation:fadeIn 0.3s ease-out;';
    toast.innerHTML = `<i class="fas fa-info-circle"></i> <span>${message}</span>`;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
