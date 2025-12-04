// CBT情绪日记游戏 - 主JavaScript文件

// API基础URL
const API_BASE_URL = window.location.origin + '/api';

// 通用工具函数
function showAlert(message, type = 'info', container = null) {
    const alertContainer = container || document.getElementById('alertContainer');
    if (!alertContainer) {
        console.warn('Alert container not found');
        return;
    }

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show animate-fade-in-up`;
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    alertContainer.innerHTML = '';
    alertContainer.appendChild(alertDiv);

    // 自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function showLoading(element, show = true) {
    if (!element) return;

    if (show) {
        element.dataset.originalText = element.innerHTML;
        element.innerHTML = '<span class="loading me-2"></span>处理中...';
        element.disabled = true;
    } else {
        element.innerHTML = element.dataset.originalText || element.textContent;
        element.disabled = false;
        delete element.dataset.originalText;
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 认证管理器
class AuthManager {
    constructor() {
        this.token = null;
        this.user = null;
        this.init();
    }

    init() {
        this.loadAuthData();
        this.updateUI();
    }

    loadAuthData() {
        // 优先从localStorage获取（记住我功能）
        this.token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
        const userData = localStorage.getItem('user') || sessionStorage.getItem('user');

        if (userData) {
            try {
                this.user = JSON.parse(userData);
            } catch (error) {
                console.error('Failed to parse user data:', error);
                this.clearAuthData();
            }
        }
    }

    saveAuthData(token, user, rememberMe = false) {
        this.token = token;
        this.user = user;

        const storage = rememberMe ? localStorage : sessionStorage;
        const otherStorage = rememberMe ? sessionStorage : localStorage;

        storage.setItem('access_token', token);
        storage.setItem('user', JSON.stringify(user));

        // 清除另一个存储中的数据
        otherStorage.removeItem('access_token');
        otherStorage.removeItem('user');
    }

    clearAuthData() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('user');
    }

    isAuthenticated() {
        return !!(this.token && this.user);
    }

    async validateToken() {
        if (!this.token) return false;

        try {
            const response = await fetch(`${API_BASE_URL}/auth/profile`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.user = data.user;
                return true;
            } else {
                this.clearAuthData();
                return false;
            }
        } catch (error) {
            console.error('Token validation failed:', error);
            this.clearAuthData();
            return false;
        }
    }

    updateUI() {
        // 兼容两种导航栏ID写法（auth-guest/authGuest 与 auth-user/authUser）
        const guestSections = document.querySelectorAll('#auth-guest, #authGuest');
        const userSections = document.querySelectorAll('#auth-user, #authUser');
        const usernameSpans = document.querySelectorAll(
            '#auth-guest #username, #authGuest #username, #auth-user #username, #authUser #username'
        );
        const loginLinks = document.querySelectorAll('.login-link');
        const registerLinks = document.querySelectorAll('.register-link');

        if (this.isAuthenticated()) {
            guestSections.forEach(el => el.classList.add('d-none'));
            userSections.forEach(el => el.classList.remove('d-none'));
            usernameSpans.forEach(el => {
                el.textContent = this.user.username;
            });

            loginLinks.forEach(link => {
                link.style.display = 'none';
            });
            registerLinks.forEach(link => {
                link.style.display = 'none';
            });
        } else {
            guestSections.forEach(el => el.classList.remove('d-none'));
            userSections.forEach(el => el.classList.add('d-none'));

            loginLinks.forEach(link => {
                link.style.display = 'block';
            });
            registerLinks.forEach(link => {
                link.style.display = 'block';
            });
        }
    }

    async login(username, password, rememberMe = false) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                this.saveAuthData(data.access_token, data.user, rememberMe);
                this.updateUI();
                return { success: true, data };
            } else {
                return { success: false, error: data.error || '登录失败' };
            }
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: '网络错误，请重试' };
        }
    }

    async register(username, email, password, rememberMe = false) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, email, password })
            });

            const data = await response.json();

            if (response.ok) {
                this.saveAuthData(data.access_token, data.user, rememberMe);
                this.updateUI();
                return { success: true, data };
            } else {
                return { success: false, error: data.error || '注册失败' };
            }
        } catch (error) {
            console.error('Registration error:', error);
            return { success: false, error: '网络错误，请重试' };
        }
    }

    logout() {
        this.clearAuthData();
        this.updateUI();
        showAlert('已退出登录', 'info');

        setTimeout(() => {
            window.location.href = '/';
        }, 1000);
    }

    async getCurrentUser() {
        if (!this.isAuthenticated()) return null;

        if (await this.validateToken()) {
            return this.user;
        }
        return null;
    }
}

// API客户端
class APIClient {
    constructor(authManager = null) {
        this.baseURL = API_BASE_URL;
        this.authManager = authManager;
    }

    getAuthManager() {
        return this.authManager || window.authManager;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = new Headers(options.headers || {});

        const authManager = this.getAuthManager();
        if (authManager?.token && !headers.has('Authorization')) {
            headers.set('Authorization', `Bearer ${authManager.token}`);
        }

        const body = options.body;
        const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
        if (!isFormData && body && !headers.has('Content-Type')) {
            headers.set('Content-Type', 'application/json');
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers,
                body: isFormData || typeof body === 'string' || body == null
                    ? body
                    : JSON.stringify(body)
            });

            const contentType = response.headers.get('Content-Type') || '';
            let data = null;
            if (contentType.includes('application/json')) {
                data = await response.json();
            } else if (response.status !== 204) {
                const textData = await response.text();
                data = textData || null;
            }

            if (response.status === 401) {
                authManager?.logout();
            }

            if (!response.ok) {
                const error = new Error(data?.error || data?.message || 'Request failed');
                error.response = { status: response.status, data };
                throw error;
            }

            return {
                status: response.status,
                ok: response.ok,
                data,
                headers: response.headers
            };
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request(url, { method: 'GET' });
    }

    async post(endpoint, data = {}, options = {}) {
        const isFormData = typeof FormData !== 'undefined' && data instanceof FormData;
        const headers = { ...(options.headers || {}) };

        if (isFormData) {
            Object.keys(headers).forEach(key => {
                if (key.toLowerCase() === 'content-type') {
                    delete headers[key];
                }
            });
        }

        return this.request(endpoint, {
            ...options,
            method: 'POST',
            body: data,
            headers
        });
    }

    async put(endpoint, data = {}, options = {}) {
        const headers = { ...(options.headers || {}) };
        return this.request(endpoint, {
            ...options,
            method: 'PUT',
            body: data,
            headers
        });
    }

    async delete(endpoint, options = {}) {
        return this.request(endpoint, { method: 'DELETE', ...options });
    }
}

// 表单验证工具
class FormValidator {
    constructor(form) {
        this.form = form;
        this.rules = {};
        this.errors = {};
    }

    addRule(fieldName, validator, message) {
        if (!this.rules[fieldName]) {
            this.rules[fieldName] = [];
        }
        this.rules[fieldName].push({ validator, message });
    }

    validate() {
        this.errors = {};
        let isValid = true;

        Object.keys(this.rules).forEach(fieldName => {
            const field = this.form.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            const value = field.value.trim();
            this.rules[fieldName].forEach(rule => {
                if (!rule.validator(value)) {
                    this.errors[fieldName] = rule.message;
                    isValid = false;
                }
            });

            // 更新UI
            this.updateFieldUI(field, this.errors[fieldName]);
        });

        return isValid;
    }

    updateFieldUI(field, error) {
        const feedbackElement = field.parentNode.querySelector('.invalid-feedback');

        if (error) {
            field.classList.add('is-invalid');
            if (feedbackElement) {
                feedbackElement.textContent = error;
            }
        } else {
            field.classList.remove('is-invalid');
            if (feedbackElement) {
                feedbackElement.textContent = '';
            }
        }
    }

    getErrors() {
        return this.errors;
    }

    hasErrors() {
        return Object.keys(this.errors).length > 0;
    }
}

// 常用验证器
const Validators = {
    required: (value) => value.length > 0,
    minLength: (min) => (value) => value.length >= min,
    maxLength: (max) => (value) => value.length <= max,
    email: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
    password: (value) => value.length >= 6,
    sameAs: (fieldName) => (value, formData) => value === formData[fieldName]
};

// 主题切换管理
class ThemeManager {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.bindEvents();
    }

    bindEvents() {
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    toggleTheme() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.currentTheme);
        localStorage.setItem('theme', this.currentTheme);
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);

        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            const icon = themeToggle.querySelector('i');
            icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
        }
    }
}

// 页面路由管理
class Router {
    constructor() {
        this.routes = new Map();
        this.currentPath = window.location.pathname;
        this.init();
    }

    init() {
        window.addEventListener('popstate', () => {
            this.handleRoute();
        });

        this.handleRoute();
    }

    addRoute(path, handler) {
        this.routes.set(path, handler);
    }

    navigate(path, title = '') {
        window.history.pushState({}, title, path);
        this.handleRoute();
    }

    handleRoute() {
        this.currentPath = window.location.pathname;

        for (const [path, handler] of this.routes) {
            if (this.matchPath(path, this.currentPath)) {
                handler();
                return;
            }
        }
    }

    matchPath(routePath, currentPath) {
        // 简单的路径匹配，可以扩展为支持参数
        return routePath === currentPath;
    }
}

// 全局初始化
let authManager, apiClient, themeManager, router;

document.addEventListener('DOMContentLoaded', function() {
    // 初始化全局管理器
    authManager = new AuthManager();
    apiClient = new APIClient(authManager);
    themeManager = new ThemeManager();
    router = new Router();

    // 暴露到全局
    window.authManager = authManager;
    window.apiClient = apiClient;
    window.themeManager = themeManager;
    window.router = router;
    window.showAlert = showAlert;
    window.showLoading = showLoading;
    window.formatDate = formatDate;
    window.FormValidator = FormValidator;
    window.Validators = Validators;

    console.log('CBT情绪日记游戏已加载完成');

    // 添加全局事件监听
    bindGlobalEvents();
});

function bindGlobalEvents() {
    // 退出登录按钮
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => authManager.logout());
    }

    // 表单清除错误状态
    document.querySelectorAll('.form-control').forEach(input => {
        input.addEventListener('input', function() {
            this.classList.remove('is-invalid');
        });
    });

    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            // 跳过空的href
            if (!href || href === '#') {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// 导出类供其他模块使用（移除ES6 export语法，直接赋值到window对象）
window.AuthManager = AuthManager;
window.APIClient = APIClient;
window.FormValidator = FormValidator;
window.Validators = Validators;
window.ThemeManager = ThemeManager;
window.Router = Router;
