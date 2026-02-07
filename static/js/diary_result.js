// 日记分析结果页面 JavaScript - 统一API版本
// 使用单一的 /api/analysis/{id}/unified-analyze 端点

(function() {
    'use strict';

    // 从URL获取日记ID
    const getDiaryIdFromURL = () => {
        const pathMatch = window.location.pathname.match(/\/diary\/(\d+)\/result/);
        return pathMatch ? parseInt(pathMatch[1]) : null;
    };

    const diaryId = getDiaryIdFromURL();

    if (!diaryId) {
        console.error('[结果页] 无法从URL获取日记ID');
        showError('页面参数错误，请返回重试');
        return;
    }

    console.log('[结果页] 日记ID:', diaryId);

    // DOM元素
    const aiAnalysisContent = document.getElementById('aiAnalysisContent');
    const scoresLoading = document.getElementById('scoresLoading');
    const scoresContent = document.getElementById('scoresContent');
    const scoresError = document.getElementById('scoresError');

    // 显示加载状态
    function showLoading() {
        if (aiAnalysisContent) {
            aiAnalysisContent.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                    <p class="mt-3 text-muted">正在分析你的日记...</p>
                </div>
            `;
        }
    }

    // 检查探险会话状态（只检查，不触发创建，避免重复调用AI）
    // 探险会话已经在日记创建时后台预生成了
    async function checkAdventureStatus() {
        const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
        if (!token) return;

        try {
            console.log('[预检查] 检查探险会话状态...');
            // 使用GET方法只检查状态，不触发创建
            const response = await fetch(`${window.location.origin}/api/adventure/session/${diaryId}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.status === 'generating') {
                    console.log('[预检查] 探险正在后台生成中...');
                } else if (data.status === 'pending' || data.status === 'in_progress') {
                    console.log('[预检查] 探险会话已准备:', data.scene_name || '未知场景');
                }
            } else if (response.status === 404) {
                console.log('[预检查] 探险会话尚未创建');
            }
        } catch (error) {
            console.warn('[预检查] 检查探险状态失败:', error.message);
        }
    }

    // 统一分析函数 - 使用新的unified-analyze端点
    async function loadUnifiedAnalysis() {
        console.log('[统一分析] 开始调用API');
        showLoading();

        const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
        if (!token) {
            showAnalysisError('请先登录后再查看分析结果');
            return;
        }

        // 后台检查探险状态（不触发创建，探险已在日记提交时预生成）
        checkAdventureStatus();

        try {
            const response = await fetch(`${window.location.origin}/api/analysis/${diaryId}/unified-analyze`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '分析失败');
            }

            const result = await response.json();
            console.log('[统一分析] 分析成功:', result);

            // 显示所有结果
            displayUserMessage(result.user_message, result.already_analyzed);
            displayScores(result);
            displayRewards(result.rewards, result.game_state);
            displayCBTInsights(result.cbt_insights);
            displayHighlights(result.highlights);

            // 如果升级了，显示庆祝动画
            if (result.rewards && result.rewards.level_up) {
                showLevelUpCelebration(result.rewards.new_level);
            }

        } catch (error) {
            console.error('[统一分析] 分析失败:', error);
            showAnalysisError(error.message || '分析失败，请稍后重试');
        }
    }

    // 显示用户消息（CBT分析）
    function displayUserMessage(message, alreadyAnalyzed) {
        if (!aiAnalysisContent) return;

        let html = '';

        if (alreadyAnalyzed) {
            html += `
                <div class="alert alert-info mb-3">
                    <i class="fas fa-info-circle me-2"></i>
                    该日记已分析过，以下是保存的分析结果
                </div>
            `;
        }

        if (message) {
            // 将换行转换为HTML换行
            const formattedMessage = message.replace(/\n/g, '<br>');
            html += `<p class="ai-text">${formattedMessage}</p>`;
        } else {
            html += `<p class="text-muted">暂无分析内容</p>`;
        }

        aiAnalysisContent.innerHTML = html;
    }

    // 显示分数变化
    function displayScores(result) {
        if (!scoresLoading || !scoresContent) return;

        scoresLoading.classList.add('d-none');
        scoresContent.classList.remove('d-none');

        const { new_scores, score_changes, previous_scores } = result;
        const reasoning = result.reasoning || {};

        // 心理健康值
        animateScore(
            'mentalHealth',
            new_scores.mental_health_score,
            score_changes.mental_health_change,
            reasoning.mental_health_reason
        );

        // 压力水平
        animateScore(
            'stressLevel',
            new_scores.stress_level,
            score_changes.stress_level_change,
            reasoning.stress_level_reason
        );

        // 成长潜力
        animateScore(
            'growthPotential',
            new_scores.growth_potential,
            score_changes.growth_potential_change,
            reasoning.growth_potential_reason
        );
    }

    // 显示奖励信息
    function displayRewards(rewards, gameState) {
        const rewardsSection = document.getElementById('rewardsSection');
        if (!rewardsSection || !rewards) return;

        rewardsSection.classList.remove('d-none');

        // 金币奖励
        const coinsEarned = document.getElementById('coinsEarned');
        if (coinsEarned) {
            coinsEarned.textContent = `+${rewards.coins_earned}`;
            // 添加动画类
            coinsEarned.classList.add('reward-animate');
        }

        // 总金币
        const totalCoins = document.getElementById('totalCoins');
        if (totalCoins && gameState) {
            totalCoins.textContent = gameState.coins;
        }

        // 当前等级
        const currentLevel = document.getElementById('currentLevel');
        if (currentLevel && gameState) {
            currentLevel.textContent = `Lv.${gameState.level}`;
        }

        // 日记数量
        const diaryCount = document.getElementById('diaryCount');
        if (diaryCount && gameState) {
            diaryCount.textContent = gameState.total_diaries;
        }

        // 下一级进度
        const nextLevelProgress = document.getElementById('nextLevelProgress');
        if (nextLevelProgress && gameState) {
            nextLevelProgress.textContent = `距离 Lv.${gameState.level + 1} 还需 ${gameState.diaries_to_next_level} 篇日记`;
        }

        // 奖励原因
        const bonusReason = document.getElementById('bonusReason');
        if (bonusReason && rewards.bonus_reason) {
            bonusReason.textContent = rewards.bonus_reason;
        }
    }

    // 显示CBT洞察
    function displayCBTInsights(cbtInsights) {
        const cbtSection = document.getElementById('cbtInsightsSection');
        if (!cbtSection || !cbtInsights) return;

        const hasContent = (cbtInsights.cognitive_distortions && cbtInsights.cognitive_distortions.length > 0) ||
                          (cbtInsights.recommendations && cbtInsights.recommendations.length > 0);

        if (!hasContent) return;

        cbtSection.classList.remove('d-none');

        // 认知扭曲
        const distortionsList = document.getElementById('distortionsList');
        if (distortionsList && cbtInsights.cognitive_distortions && cbtInsights.cognitive_distortions.length > 0) {
            distortionsList.innerHTML = cbtInsights.cognitive_distortions.map(d => `
                <div class="distortion-item mb-2">
                    <span class="badge bg-warning text-dark me-2">${d.type}</span>
                    <span class="text-muted">${d.description || ''}</span>
                </div>
            `).join('');
        }

        // 建议
        const recommendationsList = document.getElementById('recommendationsList');
        if (recommendationsList && cbtInsights.recommendations && cbtInsights.recommendations.length > 0) {
            recommendationsList.innerHTML = cbtInsights.recommendations.map(r => `
                <li><i class="fas fa-lightbulb text-warning me-2"></i>${r}</li>
            `).join('');
        }
    }

    // 显示积极亮点
    function displayHighlights(highlights) {
        const highlightsSection = document.getElementById('highlightsSection');
        const highlightsList = document.getElementById('highlightsList');

        if (!highlightsSection || !highlightsList || !highlights || highlights.length === 0) return;

        highlightsList.innerHTML = highlights.map(h => `
            <li><i class="fas fa-star text-success me-2"></i>${h}</li>
        `).join('');

        highlightsSection.classList.remove('d-none');
    }

    // 升级庆祝动画
    function showLevelUpCelebration(newLevel) {
        const modal = document.getElementById('levelUpModal');
        if (!modal) {
            // 动态创建模态框
            const modalHtml = `
                <div class="modal fade" id="levelUpModal" tabindex="-1">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content text-center">
                            <div class="modal-body py-5">
                                <div class="level-up-icon mb-3">🎉</div>
                                <h2 class="mb-3">恭喜升级！</h2>
                                <p class="lead">你已达到 <strong>Lv.${newLevel}</strong></p>
                                <p class="text-muted">继续写日记，解锁更多功能！</p>
                                <button type="button" class="btn btn-primary btn-lg mt-3" data-bs-dismiss="modal">
                                    太棒了！
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }

        // 显示模态框
        const levelUpModal = new bootstrap.Modal(document.getElementById('levelUpModal'));
        levelUpModal.show();
    }

    // 动画显示单个数值
    function animateScore(prefix, finalValue, change, reason) {
        const valueElement = document.getElementById(`${prefix}Value`);
        const changeElement = document.getElementById(`${prefix}Change`);
        const progressElement = document.getElementById(`${prefix}Progress`);
        const reasonElement = document.getElementById(`${prefix}Reason`);

        if (!valueElement) return;

        // 数值动画
        const startValue = parseInt(valueElement.textContent) || 50;
        const duration = 1500;
        const startTime = Date.now();

        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // 使用缓动函数
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            const currentValue = Math.round(startValue + (finalValue - startValue) * easeProgress);

            valueElement.textContent = currentValue;

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        animate();

        // 变化值显示
        if (changeElement) {
            const changeText = change >= 0 ? `+${change}` : `${change}`;
            changeElement.textContent = changeText;
            changeElement.className = `score-change ${change >= 0 ? 'positive' : 'negative'}`;
        }

        // 进度条动画
        if (progressElement) {
            setTimeout(() => {
                progressElement.style.width = `${finalValue}%`;
            }, 100);
        }

        // 原因显示
        if (reasonElement && reason) {
            reasonElement.textContent = reason;
        }
    }

    // 显示分析错误
    function showAnalysisError(message) {
        if (aiAnalysisContent) {
            aiAnalysisContent.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    ${message}
                </div>
            `;
        }

        if (scoresLoading) scoresLoading.classList.add('d-none');
        if (scoresError) {
            scoresError.classList.remove('d-none');
            const errorText = document.getElementById('errorText');
            if (errorText) errorText.textContent = message;
        }
    }

    // 显示通用错误
    function showError(message) {
        document.body.innerHTML = `
            <div class="container py-5 text-center">
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    ${message}
                </div>
                <a href="/diary" class="btn btn-primary mt-3">返回日记列表</a>
            </div>
        `;
    }

    // 页面初始化
    function init() {
        console.log('[结果页] 页面初始化');

        // 检查登录状态
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            console.error('[结果页] 用户未登录');
            window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
            return;
        }

        // 更新用户显示
        const usernameElement = document.getElementById('username');
        if (usernameElement && window.authManager.user) {
            usernameElement.textContent = window.authManager.user.username;
        }

        // 使用统一API加载分析
        loadUnifiedAnalysis();
    }

    // 等待DOM加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
