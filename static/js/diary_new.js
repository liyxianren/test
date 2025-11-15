// 日记新建页面 - 步骤式引导
(function() {
    'use strict';

    // 全局状态
    const state = {
        currentStep: 1,
        selectedEmotions: [],
        triggerEvent: '',
        intensity: 5,
        intensityEmoji: '😟',
        diaryContent: '',
        uploadedImages: [],
        diaryId: null
    };

    // DOM元素
    const elements = {
        // 步骤卡片
        stepCards: document.querySelectorAll('.step-card'),
        stepItems: document.querySelectorAll('.step-item'),

        // 步骤1：情绪选择
        emotionButtons: document.querySelectorAll('.emotion-btn-game'),
        selectedEmotionsPreview: document.getElementById('selectedEmotionsPreview'),
        selectedEmotionTags: document.getElementById('selectedEmotionTags'),
        nextStep1: document.getElementById('nextStep1'),

        // 步骤2：触发事件
        triggerEventInput: document.getElementById('triggerEvent'),
        charCount: document.getElementById('charCount'),
        templateButtons: document.querySelectorAll('.btn-template'),
        prevStep2: document.getElementById('prevStep2'),
        nextStep2: document.getElementById('nextStep2'),

        // 步骤3：情绪强度
        emojiSelectors: document.querySelectorAll('.emoji-selector'),
        emojiProgress: document.getElementById('emojiProgress'),
        intensityLabel: document.getElementById('intensityLabel'),
        intensityValue: document.getElementById('intensityValue'),
        prevStep3: document.getElementById('prevStep3'),
        nextStep3: document.getElementById('nextStep3'),

        // 步骤4：日记编写
        diarySummary: document.getElementById('diarySummary'),
        summaryEmotions: document.getElementById('summaryEmotions'),
        summaryIntensity: document.getElementById('summaryIntensity'),
        diaryContentInput: document.getElementById('diaryContent'),
        wordCount: document.getElementById('wordCount'),
        uploadImageBtn: document.getElementById('uploadImageBtn'),
        imageInput: document.getElementById('imageInput'),
        imagePreviewGrid: document.getElementById('imagePreviewGrid'),
        prevStep4: document.getElementById('prevStep4'),
        saveDiary: document.getElementById('saveDiary'),

        // AI助手
        aiPanel: document.getElementById('aiPanel'),
        aiPanelContent: document.getElementById('aiPanelContent'),
        aiDrawerMobile: document.getElementById('aiDrawerMobile'),
        drawerContent: document.getElementById('drawerContent'),
        closeDrawer: document.getElementById('closeDrawer')
    };

    // 初始化
    function init() {
        bindEventListeners();
        updateAuthUI();
        setDefaultIntensity();
        validateStep2();
    }

    // 绑定事件监听器
    function bindEventListeners() {
        // 步骤1：情绪选择
        elements.emotionButtons.forEach(btn => {
            btn.addEventListener('click', handleEmotionSelect);
        });
        elements.nextStep1.addEventListener('click', () => goToStep(2));

        // 步骤2：触发事件
        elements.triggerEventInput.addEventListener('input', handleTriggerEventInput);
        elements.templateButtons.forEach(btn => {
            btn.addEventListener('click', handleTemplateSelect);
        });
        elements.prevStep2.addEventListener('click', () => goToStep(1));
        elements.nextStep2.addEventListener('click', () => goToStep(3));

        // 步骤3：情绪强度
        elements.emojiSelectors.forEach(btn => {
            btn.addEventListener('click', handleIntensitySelect);
        });
        elements.prevStep3.addEventListener('click', () => goToStep(2));
        elements.nextStep3.addEventListener('click', () => goToStep(4));

        // 步骤4：日记编写
        elements.diaryContentInput.addEventListener('input', handleDiaryContentInput);
        elements.uploadImageBtn.addEventListener('click', () => elements.imageInput.click());
        elements.imageInput.addEventListener('change', handleImageUpload);
        elements.prevStep4.addEventListener('click', () => goToStep(3));
        elements.saveDiary.addEventListener('click', handleSaveDiary);

        // AI助手
        if (elements.closeDrawer) {
            elements.closeDrawer.addEventListener('click', () => {
                elements.aiDrawerMobile.style.display = 'none';
            });
        }

        // 退出登录
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', logout);
        }
    }

    // ==================== 步骤1：情绪选择 ====================
    function handleEmotionSelect(e) {
        const btn = e.currentTarget;
        const emotion = btn.dataset.emotion;
        const emoji = btn.dataset.emoji;

        if (btn.classList.contains('selected')) {
            // 取消选择
            btn.classList.remove('selected');
            state.selectedEmotions = state.selectedEmotions.filter(e => e.name !== emotion);
        } else {
            // 添加选择
            btn.classList.add('selected');
            state.selectedEmotions.push({ name: emotion, emoji: emoji });
        }

        updateEmotionPreview();
        validateStep1();
    }

    function updateEmotionPreview() {
        if (state.selectedEmotions.length > 0) {
            elements.selectedEmotionsPreview.style.display = 'block';
            elements.selectedEmotionTags.innerHTML = state.selectedEmotions.map(e =>
                `<span class="emotion-tag-selected">${e.emoji} ${e.name}</span>`
            ).join('');
        } else {
            elements.selectedEmotionsPreview.style.display = 'none';
        }
    }

    function validateStep1() {
        elements.nextStep1.disabled = state.selectedEmotions.length === 0;
    }

    // ==================== 步骤2：触发事件 ====================
    function handleTriggerEventInput(e) {
        const text = e.target.value;
        state.triggerEvent = text;
        elements.charCount.textContent = text.length;
        validateStep2();
    }

    function handleTemplateSelect(e) {
        const template = e.currentTarget.dataset.template;
        elements.triggerEventInput.value = template;
        state.triggerEvent = template;
        elements.charCount.textContent = template.length;
        validateStep2();
    }

    function validateStep2() {
        elements.nextStep2.disabled = false;
    }

    // ==================== 步骤3：情绪强度 ====================
    function setDefaultIntensity() {
        // 默认选择中等强度（5/10）
        selectIntensity(5);
    }

    function handleIntensitySelect(e) {
        const intensity = parseInt(e.currentTarget.dataset.intensity);
        selectIntensity(intensity);
    }

    function selectIntensity(intensity) {
        state.intensity = intensity;

        // 更新选中状态
        elements.emojiSelectors.forEach((btn, index) => {
            if (index + 1 === intensity) {
                btn.classList.add('selected');
                state.intensityEmoji = btn.textContent.trim();
            } else {
                btn.classList.remove('selected');
            }
        });

        // 更新进度条
        const percentage = ((intensity - 1) / 9) * 100;
        elements.emojiProgress.style.width = percentage + '%';

        // 更新颜色（绿色→黄色→红色渐变）
        let color;
        if (intensity <= 3) {
            color = '#10b981'; // 绿色
        } else if (intensity <= 7) {
            color = '#f59e0b'; // 黄色
        } else {
            color = '#ef4444'; // 红色
        }
        elements.emojiProgress.style.background = color;

        // 更新标签
        const label = elements.emojiSelectors[intensity - 1].dataset.label;
        elements.intensityLabel.textContent = label;
        elements.intensityValue.textContent = intensity;
    }

    // ==================== 步骤4：日记编写 ====================
    function handleDiaryContentInput(e) {
        const text = e.target.value;
        state.diaryContent = text;

        // 统计字数（中文算1个字，英文单词算1个字）
        const chineseChars = text.match(/[\u4e00-\u9fa5]/g) || [];
        const words = text.match(/[a-zA-Z]+/g) || [];
        const wordCount = chineseChars.length + words.length;

        elements.wordCount.textContent = wordCount;
    }

    async function handleImageUpload(e) {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        elements.imagePreviewGrid.style.display = 'grid';

        for (let file of files) {
            // 验证文件大小（最大5MB）
            if (file.size > 5 * 1024 * 1024) {
                showMessage('图片大小不能超过5MB', 'error');
                continue;
            }

            const formData = new FormData();
            formData.append('image', file);

            try {
                const response = await apiClient.post('/upload/image', formData);
                const imageUrl = response?.data?.image_url || response?.data?.url;

                if (imageUrl) {
                    state.uploadedImages.push(imageUrl);
                    addImagePreview(imageUrl);
                } else {
                    showMessage('图片上传失败', 'error');
                }
            } catch (error) {
                console.error('图片上传失败:', error);
                showMessage('图片上传失败', 'error');
            }
        }
    }

    function addImagePreview(imageUrl) {
        const preview = document.createElement('div');
        preview.className = 'image-preview-item';
        preview.innerHTML = `
            <img src="${imageUrl}" alt="预览">
            <button class="btn-remove-image" data-url="${imageUrl}">
                <i class="fas fa-times"></i>
            </button>
        `;

        preview.querySelector('.btn-remove-image').addEventListener('click', function() {
            state.uploadedImages = state.uploadedImages.filter(url => url !== imageUrl);
            preview.remove();
            if (state.uploadedImages.length === 0) {
                elements.imagePreviewGrid.style.display = 'none';
            }
        });

        elements.imagePreviewGrid.appendChild(preview);
    }


    async function handleSaveDiary() {
        if (!state.diaryContent.trim()) {
            showMessage('请先写点什么吧', 'error');
            return;
        }

        // 显示loading
        elements.saveDiary.disabled = true;
        elements.saveDiary.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>保存中...';

        try {
            // 1. 保存日记
            const diaryData = {
                content: state.diaryContent,
                emotion_tags: state.selectedEmotions.map(e => e.name),
                emotion_score: {
                    intensity: state.intensity,
                    emoji: state.intensityEmoji,
                    label: elements.emojiSelectors[state.intensity - 1].dataset.label
                },
                trigger_event: state.triggerEvent,
                images: state.uploadedImages
            };

            const saveResponse = await apiClient.post('/diary', diaryData);

            if (saveResponse.data && saveResponse.data.diary) {
                state.diaryId = saveResponse.data.diary.id;
                showMessage('日记保存成功！', 'success');

                // 2. 调用AI分析
                await analyzeWithAI(state.diaryId);
            }
        } catch (error) {
            console.error('保存日记失败:', error);
            showMessage(error.response?.data?.message || '保存失败，请重试', 'error');
        } finally {
            // 恢复按钮
            elements.saveDiary.disabled = false;
            elements.saveDiary.innerHTML = '<i class="fas fa-save me-2"></i>保存日记';
        }
    }

    async function analyzeWithAI(diaryId) {
        // 显示AI面板
        showAIPanel();

        try {
            const response = await apiClient.post(`/diary/${diaryId}/ai-analyze`, {
                emotions: state.selectedEmotions.map(e => e.name),
                trigger_event: state.triggerEvent,
                intensity: state.intensity,
                content: state.diaryContent
            });

            if (response.data && response.data.analysis) {
                displayAIAnalysis(response.data.analysis);
            }
        } catch (error) {
            console.error('AI分析失败:', error);
            displayAIError();
        }
    }

    function showAIPanel() {
        // 桌面端
        if (elements.aiPanel) {
            elements.aiPanel.style.display = 'block';
        }

        // 移动端
        if (elements.aiDrawerMobile && window.innerWidth < 992) {
            elements.aiDrawerMobile.style.display = 'block';
            // 添加滑入动画
            setTimeout(() => {
                elements.aiDrawerMobile.classList.add('show');
            }, 10);
        }
    }

    function displayAIAnalysis(analysis) {
        // 保存游戏数值到sessionStorage，供游戏页面使用
        if (analysis.game_values) {
            sessionStorage.setItem('latest_game_values', JSON.stringify(analysis.game_values));
            sessionStorage.setItem('latest_diary_id', state.diaryId);
        }

        // 保存情绪分析数据
        if (analysis.emotion_analysis) {
            sessionStorage.setItem('latest_emotion_analysis', JSON.stringify(analysis.emotion_analysis));
        }

        const html = `
            <div class="ai-analysis-result">
                ${analysis.user_message ? `
                <div class="analysis-section">
                    <h5><i class="fas fa-comment-dots me-2"></i>AI情绪分析师的话</h5>
                    <div class="user-message-box">
                        <p style="white-space: pre-wrap; line-height: 1.8;">${analysis.user_message}</p>
                    </div>
                    ${analysis.game_values ? `
                    <div class="game-tip mt-3" style="padding: 1rem; background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%); border-radius: 10px; border-left: 4px solid #667eea;">
                        <p style="margin: 0; color: #374151; font-size: 0.9rem;">
                            <i class="fas fa-gamepad me-2" style="color: #667eea;"></i>
                            你的情绪数据已转化为游戏数值，点击下方"进入游戏"查看详情
                        </p>
                    </div>
                    ` : ''}
                </div>
                ` : ''}

                ${analysis.cognitive_distortions && analysis.cognitive_distortions.length > 0 ? `
                <div class="analysis-section">
                    <h5><i class="fas fa-brain me-2"></i>识别到的认知扭曲</h5>
                    <div class="distortion-list">
                        ${analysis.cognitive_distortions.map(d => `
                            <div class="distortion-item">
                                <span class="distortion-badge">${d.type}</span>
                                <p class="distortion-desc">${d.description}</p>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}

                ${analysis.challenges && analysis.challenges.length > 0 ? `
                <div class="analysis-section">
                    <h5><i class="fas fa-tasks me-2"></i>CBT挑战任务</h5>
                    <div class="challenges-list">
                        ${analysis.challenges.map((c, idx) => `
                            <div class="challenge-item">
                                <div class="challenge-header">
                                    <span class="challenge-number">#${idx + 1}</span>
                                    <span class="challenge-title">${c.title}</span>
                                    <span class="challenge-reward">+${c.reward_coins || 50}💰</span>
                                </div>
                                <p class="challenge-desc">${c.description}</p>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}

                <div class="analysis-actions mt-4">
                    <a href="/diary" class="btn btn-outline">
                        <i class="fas fa-list me-2"></i>查看所有日记
                    </a>
                    <a href="/game" class="btn btn-primary">
                        <i class="fas fa-gamepad me-2"></i>进入游戏
                    </a>
                    <button class="btn btn-secondary" onclick="location.reload()">
                        <i class="fas fa-plus me-2"></i>写新日记
                    </button>
                </div>
            </div>
        `;

        // 更新桌面端和移动端内容
        if (elements.aiPanelContent) {
            elements.aiPanelContent.innerHTML = html;
        }
        if (elements.drawerContent) {
            elements.drawerContent.innerHTML = html;
        }
    }

    function displayAIError() {
        const html = `
            <div class="ai-error">
                <div class="error-icon">😕</div>
                <h5>AI分析暂时不可用</h5>
                <p>你的日记已经保存成功，但AI分析服务暂时无法连接。</p>
                <div class="mt-4">
                    <a href="/diary" class="btn btn-outline">
                        <i class="fas fa-list me-2"></i>查看所有日记
                    </a>
                    <button class="btn btn-primary" onclick="location.reload()">
                        <i class="fas fa-plus me-2"></i>写新日记
                    </button>
                </div>
            </div>
        `;

        if (elements.aiPanelContent) {
            elements.aiPanelContent.innerHTML = html;
        }
        if (elements.drawerContent) {
            elements.drawerContent.innerHTML = html;
        }
    }

    // ==================== 步骤导航 ====================
    function goToStep(step) {
        // 隐藏所有卡片
        elements.stepCards.forEach(card => {
            card.classList.remove('active');
        });

        // 更新步骤指示器
        elements.stepItems.forEach((item, index) => {
            if (index < step) {
                item.classList.add('completed');
                item.classList.remove('active');
            } else if (index === step - 1) {
                item.classList.add('active');
                item.classList.remove('completed');
            } else {
                item.classList.remove('active', 'completed');
            }
        });

        // 显示当前步骤卡片
        const currentCard = document.getElementById(`step${step}Card`);
        if (currentCard) {
            currentCard.classList.add('active');

            // 滚动到顶部
            window.scrollTo({ top: 0, behavior: 'smooth' });

            // 如果是步骤4，更新摘要
            if (step === 4) {
                updateDiarySummary();
            }
        }

        state.currentStep = step;
    }

    function updateDiarySummary() {
        // 更新情绪摘要
        elements.summaryEmotions.innerHTML = state.selectedEmotions.map(e =>
            `<span class="emotion-tag-summary">${e.emoji} ${e.name}</span>`
        ).join('');

        // 更新强度摘要
        elements.summaryIntensity.innerHTML = `
            <span class="intensity-emoji">${state.intensityEmoji}</span>
            <span class="intensity-text">${state.intensity}/10 (${elements.emojiSelectors[state.intensity - 1].dataset.label})</span>
        `;
    }

    // ==================== 辅助函数 ====================
    function updateAuthUI() {
        const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
        const userData = localStorage.getItem('user') || sessionStorage.getItem('user');

        if (!token || !userData) {
            // 未登录，跳转到登录页
            window.location.href = '/login';
            return;
        }

        try {
            const user = JSON.parse(userData);
            const usernameElement = document.getElementById('username');
            if (usernameElement) {
                usernameElement.textContent = user.username;
            }
        } catch (error) {
            console.error('Failed to parse user data:', error);
            window.location.href = '/login';
        }
    }

    function logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('user');
        window.location.href = '/';
    }

    function showMessage(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
        alertDiv.style.zIndex = '9999';

        const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle';
        alertDiv.innerHTML = `
            <i class="fas fa-${icon} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alertDiv);

        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }

    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
