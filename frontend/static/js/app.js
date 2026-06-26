/**
 * AutoInsightDaily - Frontend JavaScript
 * Handles all UI interactions and API calls
 */

// ============================================
// State Management
// ============================================
const state = {
    headlines: [],
    summaries: [],
    images: [],
    stagingImages: [],
    settings: {},
    pipelineStatus: 'idle'
};

// ============================================
// DOM Elements
// ============================================
const elements = {
    sidebar: document.getElementById('sidebar'),
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText'),
    pipelineBadge: document.getElementById('pipelineBadge'),
    progressFill: document.getElementById('progressFill'),
    progressText: document.getElementById('progressText'),
    toastContainer: document.getElementById('toastContainer'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText'),
    aiStatus: document.getElementById('aiStatus'),
    pageTitle: document.getElementById('pageTitle')
};

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initWebSocket();
    loadInitialData();
    checkAIStatus();
    loadSettings();
});

// ============================================
// Navigation
// ============================================
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            showSection(section);
            
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

function showSection(sectionName) {
    const sections = document.querySelectorAll('.section');
    sections.forEach(s => s.classList.remove('active'));
    
    const targetSection = document.getElementById(`${sectionName}Section`);
    if (targetSection) {
        targetSection.classList.add('active');
        elements.pageTitle.textContent = sectionName.charAt(0).toUpperCase() + sectionName.slice(1);
    }
    
    // Load section-specific data
    if (sectionName === 'images') refreshImages();
    if (sectionName === 'post') refreshStaging();
    if (sectionName === 'settings') loadSettings();
}

function toggleSidebar() {
    elements.sidebar.classList.toggle('collapsed');
    elements.sidebar.classList.toggle('open');
}

function toggleTheme() {
    const body = document.body;
    const isDark = !body.hasAttribute('data-theme');
    body.setAttribute('data-theme', isDark ? 'light' : '');
    document.getElementById('themeIcon').className = isDark ? 'fas fa-sun' : 'fas fa-moon';
    localStorage.setItem('theme', isDark ? 'light' : 'dark');
}

// Load theme from localStorage
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'light') {
    document.body.setAttribute('data-theme', 'light');
    document.getElementById('themeIcon').className = 'fas fa-sun';
}

// ============================================
// WebSocket for Real-time Updates
// ============================================
let ws = null;
// ponytail: debounce rapid updates to prevent UI lag
let wsUpdateTimer = null;

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/status`);
    
    ws.onmessage = (event) => {
        clearTimeout(wsUpdateTimer);
        wsUpdateTimer = setTimeout(() => {
            const data = JSON.parse(event.data);
            updatePipelineUI(data);
        }, 100); // batch updates every 100ms
    };
    
    ws.onclose = () => {
        setTimeout(initWebSocket, 3000);
    };
    
    ws.onerror = () => {
        console.log('WebSocket error, falling back to polling');
        startPolling();
    };
}

function startPolling() {
    setInterval(async () => {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            updatePipelineUI(data.pipeline);
        } catch (e) {
            console.error('Polling error:', e);
        }
    }, 2000);
}

function updatePipelineUI(data) {
    state.pipelineStatus = data.status;
    
    // Update status dot
    elements.statusDot.className = 'status-dot';
    if (data.status === 'running') elements.statusDot.classList.add('running');
    if (data.status === 'error') elements.statusDot.classList.add('error');
    
    // Update status text
    elements.statusText.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
    
    // Update badge
    elements.pipelineBadge.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
    elements.pipelineBadge.className = 'badge ' + data.status;
    
    // Update progress
    elements.progressFill.style.width = `${data.progress}%`;
    
    // ponytail: show image progress if available
    let progressMsg = data.message || data.current_step || 'Ready to start';
    if (data.images_total > 0 && data.current_step === 'Generating images') {
        progressMsg = `Generated ${data.images_completed}/${data.images_total} images`;
    }
    elements.progressText.textContent = progressMsg;
}

// ============================================
// API Calls
// ============================================
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API Error');
        }
        
        return await response.json();
    } catch (error) {
        showToast(error.message, 'error');
        throw error;
    }
}

// ============================================
// Headlines
// ============================================
async function fetchHeadlines() {
    const limit = document.getElementById('headlineLimit')?.value || 8;
    showLoading('Fetching headlines...');
    
    try {
        const data = await apiCall(`/api/headlines/fetch?limit=${limit}`, { method: 'POST' });
        state.headlines = data.headlines;
        renderHeadlines();
        showToast(`Fetched ${data.count} headlines`, 'success');
        document.getElementById('headlineCount').textContent = data.count;
        refreshActivity();  // Auto-refresh activity log
    } catch (e) {
        console.error(e);
    } finally {
        hideLoading();
    }
}

function renderHeadlines() {
    const container = document.getElementById('headlinesContainer');
    
    if (state.headlines.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-newspaper"></i>
                <h3>No headlines fetched</h3>
                <p>Click "Fetch Headlines" to get started</p>
            </div>
        `;
        document.getElementById('newsFooter').style.display = 'none';
        return;
    }
    
    container.innerHTML = state.headlines.map((h, i) => `
        <div class="headline-card ${h.selected ? '' : 'deselected'}" data-index="${i}">
            <div class="headline-checkbox ${h.selected ? 'checked' : ''}" onclick="toggleHeadline(${i})">
                ${h.selected ? '<i class="fas fa-check"></i>' : ''}
            </div>
            <div class="headline-content">
                <span class="headline-source">${h.source}</span>
                <h4 class="headline-title">${h.title}</h4>
                <div class="headline-actions">
                    <a href="${h.link}" target="_blank" class="btn btn-sm btn-secondary">
                        <i class="fas fa-external-link-alt"></i> View
                    </a>
                </div>
            </div>
        </div>
    `).join('');
    
    document.getElementById('newsFooter').style.display = 'flex';
}

async function toggleHeadline(index) {
    try {
        await apiCall(`/api/headlines/${index}/toggle`, { method: 'PUT' });
        state.headlines[index].selected = !state.headlines[index].selected;
        renderHeadlines();
    } catch (e) {
        console.error(e);
    }
}

function selectAllHeadlines(selected) {
    state.headlines.forEach((h, i) => {
        if (h.selected !== selected) {
            toggleHeadline(i);
        }
    });
}

// ============================================
// Summarization
// ============================================
async function summarizeAll() {
    showLoading('Summarizing headlines...');
    
    try {
        const data = await apiCall('/api/summarize/batch', { method: 'POST' });
        state.summaries = data.summaries;
        renderSummaries();
        showToast(`Summarized ${data.count} headlines`, 'success');
        refreshActivity();  // Auto-refresh activity log
        showSection('ai');
        
        // Update nav
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        document.querySelector('[data-section="ai"]').classList.add('active');
    } catch (e) {
        console.error(e);
    } finally {
        hideLoading();
    }
}

function renderSummaries() {
    const container = document.getElementById('summariesContainer');
    
    if (state.summaries.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-align-left"></i>
                <h3>No summaries yet</h3>
                <p>Fetch and summarize headlines first</p>
            </div>
        `;
        document.getElementById('aiFooter').style.display = 'none';
        return;
    }
    
    container.innerHTML = state.summaries.map((s, i) => `
        <div class="summary-card">
            <div class="summary-header">
                <span class="summary-index">${i + 1}</span>
            </div>
            <div class="summary-original">
                <strong>Original:</strong> ${s.original_title}
            </div>
            <p class="summary-text">${s.summary}</p>
            ${s.hashtag ? `<span class="summary-hashtag">${s.hashtag}</span>` : ''}
        </div>
    `).join('');
    
    document.getElementById('aiFooter').style.display = 'flex';
}

// ============================================
// Image Generation
// ============================================
// ponytail: poll for new images during generation
let imageRefreshInterval = null;

async function generateImages() {
    if (state.summaries.length === 0) {
        showToast('Please summarize headlines first', 'warning');
        return;
    }
    
    try {
        const data = await apiCall('/api/images/generate', { method: 'POST' });
        
        if (data.status === 'started') {
            // ponytail: hide loading immediately, show progress via toast + polling
            showToast(`Generating ${data.total} images...`, 'info');
            showSection('images');
            
            // Update nav
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            document.querySelector('[data-section="images"]').classList.add('active');
            
            // Poll for new images every 2 seconds
            imageRefreshInterval = setInterval(async () => {
                await refreshImages();
                // Stop polling when generation completes
                if (state.pipelineStatus === 'idle' || state.pipelineStatus === 'error') {
                    clearInterval(imageRefreshInterval);
                    imageRefreshInterval = null;
                    showToast('Image generation complete!', 'success');
                }
            }, 2000);
            
            refreshActivity();
        }
    } catch (e) {
        console.error(e);
        showToast('Failed to start generation', 'error');
    }
}

async function refreshImages() {
    try {
        const data = await apiCall('/api/images');
        state.images = data.images;
        renderImages();
        document.getElementById('imageCount').textContent = data.images.length;
    } catch (e) {
        console.error(e);
    }
}

function renderImages() {
    const container = document.getElementById('imagesGrid');
    
    if (state.images.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-image"></i>
                <h3>No images generated</h3>
                <p>Complete the summarization step first</p>
            </div>
        `;
        document.getElementById('imagesFooter').style.display = 'none';
        return;
    }
    
    // ponytail: add selected flag if missing
    state.images.forEach(img => { if (img.selected === undefined) img.selected = true; });
    
    container.innerHTML = state.images.map((img, i) => `
        <div class="image-card ${img.selected ? '' : 'unselected'}" data-index="${i}">
            <div class="image-checkbox">
                <input type="checkbox" ${img.selected ? 'checked' : ''} onchange="toggleImage(${i})">
            </div>
            <div class="image-preview" onclick="openImageModal('${img.path}')">
                <img src="${img.path}" alt="${img.name}" loading="lazy">
            </div>
            <div class="image-info">
                <p class="image-name">${img.name}</p>
                <p class="image-size">${formatBytes(img.size)}</p>
            </div>
        </div>
    `).join('');
    
    document.getElementById('imagesFooter').style.display = 'flex';
}

function toggleImage(index) {
    state.images[index].selected = !state.images[index].selected;
    renderImages();
}

function openImageModal(src) {
    const modal = document.getElementById('imageModal');
    const img = document.getElementById('modalImage');
    img.src = src;
    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('imageModal').classList.remove('active');
}

// Close modal on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// ============================================
// Staging & Upload
// ============================================
async function uploadToStaging() {
    const selected = state.images.filter(img => img.selected);
    if (selected.length === 0) {
        showToast('No images selected', 'warning');
        return;
    }
    
    showLoading(`Uploading ${selected.length} images...`);
    
    try {
        // ponytail: backend already uploads all from dir, so just call it
        const data = await apiCall('/api/staging/upload', { method: 'POST' });
        showToast(`Uploaded ${data.count} images`, 'success');
        refreshActivity();
        await refreshStaging();
        showSection('post');
        
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        document.querySelector('[data-section="post"]').classList.add('active');
    } catch (e) {
        console.error(e);
    } finally {
        hideLoading();
    }
}

async function refreshStaging() {
    try {
        const data = await apiCall('/api/staging/images');
        state.stagingImages = data.images || [];
        renderStagingInfo();
        renderCarouselPreview();
    } catch (e) {
        console.error(e);
    }
}

function renderStagingInfo() {
    const container = document.getElementById('stagingInfo');
    
    if (state.stagingImages.length === 0) {
        container.innerHTML = '<p>No images on staging server</p>';
        return;
    }
    
    container.innerHTML = `
        <p><strong>${state.stagingImages.length}</strong> images on staging server</p>
        <ul style="margin-top: 8px; padding-left: 20px; color: var(--text-secondary); font-size: 0.875rem;">
            ${state.stagingImages.map(img => `<li>${img.name}</li>`).join('')}
        </ul>
    `;
}

function renderCarouselPreview() {
    const container = document.getElementById('carouselPreview');
    
    if (state.stagingImages.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-images"></i>
                <p>Upload images to staging first</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = state.stagingImages.map(img => `
        <div class="carousel-image">
            <img src="${img.url}" alt="${img.name}" loading="lazy">
        </div>
    `).join('');
}

async function cleanupStaging() {
    if (!confirm('Are you sure you want to remove all images from staging?')) return;
    
    showLoading('Cleaning up staging...');
    
    try {
        await apiCall('/api/staging/cleanup', { method: 'DELETE' });
        showToast('Staging cleaned up', 'success');
        refreshActivity();  // Auto-refresh activity log
        await refreshStaging();
    } catch (e) {
        console.error(e);
    } finally {
        hideLoading();
    }
}

// ============================================
// Instagram Posting
// ============================================
async function postToInstagram() {
    if (state.stagingImages.length < 2) {
        showToast('Need at least 2 images for a carousel', 'warning');
        return;
    }
    
    if (!confirm('Post this carousel to Instagram?')) return;
    
    showLoading('Posting to Instagram...');
    
    try {
        const data = await apiCall('/api/instagram/post', { method: 'POST' });
        if (data.success) {
            showToast('Posted to Instagram successfully! 🎉', 'success');
            refreshActivity();  // Auto-refresh activity log
        } else {
            showToast('Post failed', 'error');
        }
    } catch (e) {
        console.error(e);
    } finally {
        hideLoading();
    }
}

async function checkInstagramConnection() {
    try {
        const data = await apiCall('/api/instagram/status');
        const container = document.getElementById('instagramStatus');
        const badge = document.getElementById('igConnectionStatus');
        
        if (data.connected) {
            container.innerHTML = `<p><i class="fas fa-check-circle" style="color: var(--success);"></i> Connected (ID: ${data.user_id})</p>`;
            if (badge) {
                badge.textContent = 'Connected';
                badge.className = 'status-badge connected';
            }
        } else {
            container.innerHTML = `<p><i class="fas fa-times-circle" style="color: var(--danger);"></i> Not connected</p>`;
            if (badge) {
                badge.textContent = 'Disconnected';
                badge.className = 'status-badge disconnected';
            }
        }
    } catch (e) {
        console.error(e);
    }
}

function testInstagramConnection() {
    checkInstagramConnection();
    showToast('Connection tested', 'info');
}

// ============================================
// Full Pipeline
// ============================================
async function runFullPipeline() {
    if (!confirm('Run the full pipeline? This will fetch, summarize, generate images, and post to Instagram.')) return;
    
    showLoading('Running full pipeline...');
    
    try {
        const limit = document.getElementById('headlineLimit')?.value || 8;
        const data = await apiCall(`/api/pipeline/run?headline_limit=${limit}`, { method: 'POST' });
        showToast('Pipeline completed successfully! 🎉', 'success');
        refreshActivity();  // Auto-refresh activity log
        refreshImages();
        refreshStaging();
    } catch (e) {
        console.error(e);
    } finally {
        hideLoading();
    }
}

// ============================================
// AI Status
// ============================================
async function checkAIStatus() {
    try {
        const data = await apiCall('/api/ai/status');
        const container = elements.aiStatus;
        
        if (data.status === 'connected') {
            const displayName = data.provider === 'ollama' ? 'Ollama (Local)' : 'OpenRouter (Cloud)';
            container.innerHTML = `<i class="fas fa-circle"></i><span>AI: ${displayName}</span>`;
            container.classList.add('connected');
            container.classList.remove('disconnected');
        } else {
            container.innerHTML = `<i class="fas fa-circle"></i><span>AI: Offline</span>`;
            container.classList.add('disconnected');
            container.classList.remove('connected');
        }
        
        // Update AI section
        const detail = document.getElementById('aiStatusDetail');
        if (detail) {
            const currentModels = data.current_models ? `
                <p><strong>Current Models:</strong></p>
                <ul>
                    <li>Summary: ${data.current_models.summary}</li>
                    <li>Image: ${data.current_models.image}</li>
                </ul>
            ` : '';
            
            detail.innerHTML = `
                <p><strong>Provider:</strong> ${data.provider}</p>
                <p><strong>Status:</strong> ${data.status}</p>
                ${currentModels}
                ${data.models?.length ? `<p><strong>Available Models:</strong> ${data.models.slice(0, 5).join(', ')}</p>` : ''}
            `;
        }
        
        // Update provider buttons
        document.getElementById('ollamaBtn')?.classList.toggle('active', data.provider === 'ollama');
        document.getElementById('openrouterBtn')?.classList.toggle('active', data.provider === 'openrouter');
    } catch (e) {
        console.error(e);
    }
}

async function setProvider(provider) {
    try {
        showLoading('Switching AI provider...');
        const response = await apiCall('/api/ai/provider', {
            method: 'POST',
            body: JSON.stringify({ provider })
        });
        
        if (response.success) {
            showToast(`Provider switched to ${provider}`, 'success');
            await checkAIStatus();  // Refresh status
        }
    } catch (e) {
        showToast(`Failed to switch provider: ${e.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// Settings
// ============================================
async function loadSettings() {
    try {
        const data = await apiCall('/api/settings');
        state.settings = data;
        
        // Update AI provider buttons in settings section
        document.getElementById('settingsOllamaBtn')?.classList.toggle('active', data.ai_provider === 'ollama');
        document.getElementById('settingsOpenrouterBtn')?.classList.toggle('active', data.ai_provider === 'openrouter');
        
        const imageDir = document.getElementById('imageDir');
        if (imageDir) imageDir.value = data.image_dir;
        
        const stagingUrl = document.getElementById('stagingUrl');
        if (stagingUrl) stagingUrl.value = data.staging_url;
        
        const summaryModel = document.getElementById('summaryModel');
        if (summaryModel && data.models) summaryModel.value = data.models.summary;
        
        const imageModel = document.getElementById('imageModel');
        if (imageModel && data.models) imageModel.value = data.models.image;
        
        const translationModel = document.getElementById('translationModel');
        if (translationModel && data.models) translationModel.value = data.models.translation;
        
        // Check Instagram connection
        checkInstagramConnection();
    } catch (e) {
        console.error(e);
    }
}

async function updateModel(modelType, modelName) {
    try {
        const currentProvider = state.settings.ai_provider || 'ollama';
        const models = {};
        models[modelType] = modelName;
        
        const response = await apiCall('/api/ai/provider', {
            method: 'POST',
            body: JSON.stringify({ 
                provider: currentProvider,
                models: models
            })
        });
        
        if (response.success) {
            showToast(`${modelType} model updated to ${modelName}`, 'success');
            await loadSettings();  // Refresh settings
        }
    } catch (e) {
        showToast(`Failed to update model: ${e.message}`, 'error');
    }
}

// ============================================
// Stats & Activity
// ============================================
async function loadInitialData() {
    try {
        const data = await apiCall('/api/status');
        
        // Update stats
        document.getElementById('totalTokens').textContent = 
            (data.stats.total_prompt_tokens + data.stats.total_completion_tokens).toLocaleString();
        document.getElementById('processingTime').textContent = 
            `${(data.stats.total_duration_ns / 1e9).toFixed(1)}s`;
        
        // Render activity
        renderActivity(data.activity);
        
        // Load images count
        refreshImages();
    } catch (e) {
        console.error(e);
    }
}

async function refreshActivity() {
    try {
        const data = await apiCall('/api/activity');
        renderActivity(data.activity);
    } catch (e) {
        console.error(e);
    }
}

function getStepIcon(step) {
    const icons = {
        'fetch': 'newspaper',
        'summarize': 'brain',
        'generate': 'image',
        'upload': 'cloud-upload-alt',
        'post': 'instagram',
        'pipeline': 'rocket',
        'cleanup': 'broom'
    };
    return icons[step] || 'circle';
}

function getStepColor(step) {
    const colors = {
        'fetch': '#3b82f6',      // blue
        'summarize': '#8b5cf6',  // purple
        'generate': '#ec4899',   // pink
        'upload': '#f59e0b',     // amber
        'post': '#e91e63',       // instagram pink
        'pipeline': '#10b981',   // green
        'cleanup': '#6b7280'     // gray
    };
    return colors[step] || '#6b7280';
}

function renderActivity(activity) {
    const container = document.getElementById('activityList');
    
    if (!activity || activity.length === 0) {
        container.innerHTML = `
            <div class="activity-empty">
                <i class="fas fa-inbox"></i>
                <p>No recent activity</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = activity.slice(0, 20).map(item => {
        const icon = getStepIcon(item.step);
        const color = getStepColor(item.step);
        const statusIcon = item.status === 'success' ? 'check' : item.status === 'running' ? 'spinner fa-spin' : 'times';
        const statusClass = item.status === 'running' ? 'running' : item.status;
        
        // Build details section
        let detailsHtml = '';
        if (item.details && Object.keys(item.details).length > 0) {
            const details = item.details;
            const detailItems = [];
            
            if (details.count !== undefined) detailItems.push(`<span class="detail-badge">📊 ${details.count} items</span>`);
            if (details.duration_seconds !== undefined) detailItems.push(`<span class="detail-badge">⏱️ ${details.duration_seconds}s</span>`);
            if (details.ai_provider) detailItems.push(`<span class="detail-badge">🤖 ${details.ai_provider}</span>`);
            if (details.sources) {
                const sourceNames = Object.keys(details.sources).slice(0, 3).join(', ');
                detailItems.push(`<span class="detail-badge">📰 ${sourceNames}</span>`);
            }
            if (details.hashtag) detailItems.push(`<span class="detail-badge">${details.hashtag}</span>`);
            if (details.file) detailItems.push(`<span class="detail-badge">📁 ${details.file}</span>`);
            if (details.error) detailItems.push(`<span class="detail-badge error">⚠️ ${details.error.substring(0, 50)}</span>`);
            
            if (detailItems.length > 0) {
                detailsHtml = `<div class="activity-details">${detailItems.join('')}</div>`;
            }
        }
        
        return `
            <div class="activity-item ${statusClass}">
                <div class="activity-icon" style="background: ${color}20; border-color: ${color}">
                    <i class="fas fa-${icon}" style="color: ${color}"></i>
                </div>
                <div class="activity-info">
                    <div class="activity-header">
                        <span class="activity-action">${item.action}</span>
                        <span class="activity-status ${statusClass}">
                            <i class="fas fa-${statusIcon}"></i>
                        </span>
                    </div>
                    ${detailsHtml}
                    <small class="activity-time">${formatTime(item.timestamp)}</small>
                </div>
            </div>
        `;
    }).join('');
}

// ============================================
// Utility Functions
// ============================================
function showLoading(text = 'Processing...') {
    elements.loadingText.textContent = text;
    elements.loadingOverlay.classList.add('active');
}

function hideLoading() {
    elements.loadingOverlay.classList.remove('active');
}

function showToast(message, type = 'info') {
    const icons = {
        success: 'check-circle',
        error: 'times-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${icons[type]}"></i>
        <span>${message}</span>
    `;
    
    elements.toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
    return date.toLocaleDateString();
}
