# 🎮 CBT情绪日记游戏 - 设计风格指南

## 📋 项目概述

**项目名称**: CBT情绪日记游戏
**目标用户**: 青少年（13-18岁）
**核心理念**: 将认知行为疗法（CBT）与二次元游戏风格结合，让情绪管理变得有趣、可爱、充满活力

---

## 🎨 设计风格定位

### 核心关键词
- **二次元游戏风格** (Anime Game Style)
- **可爱活泼** (Cute & Lively)
- **治愈系** (Healing)
- **年轻化** (Youthful)
- **互动性强** (Interactive)

### 设计理念
> 打破传统心理健康应用的严肃形象，用色彩、动画和游戏化元素，让青少年在轻松愉快的氛围中管理情绪、记录心情。

---

## 🌈 色彩系统

### 主色调 (Primary Colors)
```css
/* 核心色彩 - 明亮活泼的二次元风格 */
--primary-pink: #FF6B9D;          /* 樱花粉 - 主色调 */
--primary-blue: #4ECDC4;          /* 青色 - 科技感 */
--primary-purple: #A78BFA;        /* 薰衣草紫 - 梦幻感 */
--primary-yellow: #FFC107;        /* 明黄色 - 活力 */
--primary-orange: #FF9800;        /* 橙色 - 温暖 */
```

**使用场景**:
- 樱花粉：主要CTA按钮、重要标题、情绪相关元素
- 青色：次要按钮、链接、科技类功能
- 薰衣草紫：标签、徽章、游戏元素
- 明黄/橙色：警告、提示、高亮

### 辅助色 (Accent Colors)
```css
/* 柔和的辅助色调 */
--accent-pink: #FFB6C1;           /* 浅粉 */
--accent-blue: #89F0E7;           /* 浅青 */
--accent-purple: #D4BBFF;         /* 浅紫 */
--accent-green: #7FE5A8;          /* 薄荷绿 */
--accent-yellow: #FFE082;         /* 浅黄 */
```

**使用场景**: 背景色、卡片背景、hover状态、装饰元素

### 渐变色 (Gradients)
```css
/* 游戏化渐变效果 */
--gradient-sunset: linear-gradient(135deg, #FF6B9D 0%, #FFC107 50%, #FF9800 100%);
--gradient-ocean: linear-gradient(135deg, #4ECDC4 0%, #A78BFA 100%);
--gradient-candy: linear-gradient(135deg, #FFB6C1 0%, #89F0E7 50%, #D4BBFF 100%);
--gradient-game: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
--gradient-sky: linear-gradient(180deg, #87CEEB 0%, #E0F6FF 100%);
```

**使用场景**: Hero区域、按钮、卡片、分割线

### 背景色系统
```css
--bg-main: #FFF5F8;               /* 淡粉白 - 主背景 */
--bg-secondary: #F0F9FF;          /* 淡蓝白 - 次级背景 */
--bg-card: #FFFFFF;               /* 纯白 - 卡片背景 */
```

### 文字色系统
```css
--text-primary: #2D3748;          /* 主文字 */
--text-secondary: #718096;        /* 次要文字 */
--text-light: #A0AEC0;            /* 辅助文字 */
```

---

## 🎭 UI组件风格

### 1. 按钮设计

**主要按钮** (Primary Button)
```css
.btn-primary {
    background: var(--gradient-sunset);
    color: white;
    border: none;
    border-radius: 25px;  /* 圆润的边角 */
    padding: 12px 32px;
    font-weight: 600;
    box-shadow: 0 8px 20px rgba(255, 107, 157, 0.3);
    transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

.btn-primary:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 30px rgba(255, 107, 157, 0.4);
}
```

**特点**:
- ✨ 使用渐变色增加视觉吸引力
- 🎈 圆润的圆角 (25px+)
- 💫 hover时有浮动效果
- 🌟 柔和的阴影营造立体感

**次要按钮** (Secondary Button)
```css
.btn-secondary {
    background: white;
    color: var(--primary-purple);
    border: 2px solid var(--primary-purple);
    border-radius: 25px;
    /* 其他属性同上 */
}
```

### 2. 卡片设计

**标准卡片**
```css
.card {
    background: white;
    border-radius: 20px;  /* 大圆角 */
    padding: 2rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    border: none;
    transition: all 0.3s ease;
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
```

**特点**:
- 📦 大圆角 (20px+)
- 🎯 无边框，使用阴影
- 🌊 hover时上浮效果
- ✨ 柔和的阴影

### 3. 表单元素

**输入框**
```css
.form-control {
    border: 2px solid #e5e7eb;
    border-radius: 15px;
    padding: 12px 20px;
    font-size: 1rem;
    transition: all 0.3s ease;
}

.form-control:focus {
    outline: none;
    border-color: var(--primary-purple);
    box-shadow: 0 0 0 4px rgba(167, 139, 250, 0.1);
}
```

**特点**:
- 🎨 圆润边角
- 💜 focus时紫色边框+光晕
- 📏 舒适的内边距

### 4. 标签/徽章

**情绪标签**
```css
.emotion-tag {
    display: inline-block;
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    color: #92400e;
    padding: 0.5rem 1rem;
    border-radius: 20px;  /* 胶囊形状 */
    font-size: 0.9rem;
    font-weight: 500;
}
```

**特点**:
- 🏷️ 胶囊形状 (完全圆角)
- 🌈 使用渐变背景
- 🎯 柔和的对比色文字

---

## ✨ 动画效果系统

### 1. 核心动画

**浮动动画** (用于装饰元素)
```css
@keyframes floatEmoji {
    0%, 100% {
        transform: translateY(0) rotate(0deg);
    }
    25% {
        transform: translateY(-20px) rotate(5deg);
    }
    75% {
        transform: translateY(-10px) rotate(-5deg);
    }
}

.floating-emoji {
    animation: floatEmoji 6s ease-in-out infinite;
}
```

**心跳动画** (用于重要元素)
```css
@keyframes heartbeat {
    0%, 100% {
        transform: scale(1);
    }
    10%, 30% {
        transform: scale(1.05);
    }
    20%, 40% {
        transform: scale(1);
    }
}
```

**闪烁动画** (用于提示)
```css
@keyframes twinkle {
    0%, 100% {
        opacity: 1;
        transform: scale(1);
    }
    50% {
        opacity: 0.7;
        transform: scale(1.1);
    }
}
```

**脉冲动画** (用于CTA按钮)
```css
@keyframes pulse {
    0%, 100% {
        transform: scale(1);
        box-shadow: var(--shadow-cute);
    }
    50% {
        transform: scale(1.05);
        box-shadow: 0 15px 40px rgba(255, 107, 157, 0.5);
    }
}

.pulse-animation {
    animation: pulse 2s ease-in-out infinite;
}
```

### 2. 交互动画原则

- ⚡ **速度**: 0.3s-0.5s (不宜过快或过慢)
- 🎯 **缓动**: 使用 `cubic-bezier` 创造弹性效果
- 🌊 **自然**: 模拟真实物理运动
- ✨ **细节**: 多维度变化 (位置+缩放+阴影)

---

## 🎮 游戏化元素

### 1. 情绪角色系统

**主角色 - 情绪小精灵**
```html
<div class="character-card main-character">
    <div class="character-avatar">
        <div class="avatar-circle">
            <i class="fas fa-heart" style="font-size: 4rem; color: #FF6B9D;"></i>
        </div>
        <div class="character-sparkle sparkle-1">✨</div>
        <div class="character-sparkle sparkle-2">⭐</div>
        <div class="character-sparkle sparkle-3">💫</div>
    </div>
    <h3 class="character-name">情绪小精灵</h3>
    <p class="character-desc">你的情绪管理伙伴</p>
</div>
```

**迷你情绪角色** (6种基础情绪)
- 😊 开心
- 😢 悲伤
- 😠 愤怒
- 😰 焦虑
- 😌 平静
- 😲 惊讶

**特点**:
- 🎭 使用Emoji作为角色表情
- ✨ 周围有闪烁的装饰元素
- 🎪 hover时有放大+旋转效果
- 💬 显示工具提示

### 2. 装饰元素

**漂浮Emoji**
```html
<div class="floating-emoji" style="top: 10%; left: 5%; animation-delay: 0s;">😊</div>
<div class="floating-emoji" style="top: 20%; right: 10%; animation-delay: 0.5s;">💖</div>
```

**彩色泡泡**
```css
.bubble {
    position: absolute;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.8), rgba(167, 139, 250, 0.3));
    animation: bubbleFloat 15s ease-in-out infinite;
    opacity: 0.6;
}
```

**星星闪烁**
```css
.character-sparkle {
    position: absolute;
    font-size: 1.5rem;
    animation: twinkle 2s ease-in-out infinite;
}
```

### 3. 游戏化数据展示

**统计卡片**
```html
<div class="stat-item">
    <div class="stat-number">1000+</div>
    <div class="stat-label">用户加入</div>
</div>
```

**样式特点**:
- 📊 大字号数字 (2.5rem+)
- 🎨 使用渐变色
- ✨ 数字动态滚动效果
- 🏆 添加图标增强可读性

---

## 📱 响应式设计原则

### 断点系统
```css
/* Mobile First */
@media (min-width: 576px) { /* SM */ }
@media (min-width: 768px) { /* MD */ }
@media (min-width: 992px) { /* LG */ }
@media (min-width: 1200px) { /* XL */ }
```

### 移动端适配要点
- 📱 按钮最小高度 44px (易点击)
- 📏 字体最小 14px
- 🖼️ 图片全宽显示
- 📦 减少动画复杂度
- 🎯 简化导航结构

---

## 🎯 排版系统

### 字体选择
```css
body {
    font-family: 'Fredoka', 'Nunito', sans-serif;
}
```

**字体特点**:
- **Fredoka**: 可爱、圆润、游戏化
- **Nunito**: 现代、清晰、易读

### 字体大小层级
```css
h1 { font-size: 3rem; }      /* 48px - 页面主标题 */
h2 { font-size: 2.5rem; }    /* 40px - 区块标题 */
h3 { font-size: 2rem; }      /* 32px - 次级标题 */
h4 { font-size: 1.5rem; }    /* 24px - 小标题 */
p { font-size: 1rem; }       /* 16px - 正文 */
small { font-size: 0.875rem; } /* 14px - 辅助文字 */
```

### 行高
- 标题: 1.2
- 正文: 1.6-1.8
- 辅助文字: 1.5

---

## 🌟 特色UI模式

### 1. Hero区域设计

**结构**:
```
[装饰元素层] (漂浮emoji + 泡泡)
    ↓
[内容层] (标题 + 描述 + CTA)
    ↓
[角色展示层] (情绪小精灵 + 迷你角色)
```

**特点**:
- 🎨 多层次视觉效果
- ✨ 动态装饰元素
- 🎯 清晰的视觉层级
- 💫 交互式角色

### 2. 功能卡片网格

**布局**:
- 桌面: 3列网格
- 平板: 2列网格
- 手机: 1列堆叠

**样式**:
- 🎨 使用渐变色图标
- 📦 卡片hover效果
- 🎯 图标+标题+描述结构

### 3. 徽章/标签系统

**Badge Tag**:
```html
<div class="badge-tag">
    <i class="fas fa-gamepad me-2"></i>
    情绪管理 × 游戏冒险
</div>
```

**样式**:
```css
.badge-tag {
    display: inline-block;
    background: rgba(255, 255, 255, 0.2);
    border: 2px solid rgba(255, 255, 255, 0.3);
    backdrop-filter: blur(10px);
    border-radius: 30px;
    padding: 0.5rem 1.5rem;
    font-weight: 600;
}
```

---

## 🎨 设计实现示例

### 页面布局模板

```html
<!-- 标准页面结构 -->
<body>
    <!-- 导航栏 - 游戏风格 -->
    <nav class="navbar navbar-expand-lg sticky-top">
        <!-- 使用渐变背景或半透明背景 -->
    </nav>

    <!-- Hero区域（首页） -->
    <section class="hero-section">
        <!-- 装饰元素 -->
        <div class="floating-emoji">...</div>
        <div class="bubble">...</div>

        <!-- 主内容 -->
        <div class="container">
            <h1 class="hero-title">
                主标题<br>
                <span class="gradient-text">重点文字</span>
            </h1>
            <p class="hero-subtitle">副标题</p>
            <div class="hero-actions">
                <button class="btn btn-primary pulse-animation">主要CTA</button>
                <button class="btn btn-secondary">次要操作</button>
            </div>
        </div>

        <!-- 角色展示 -->
        <div class="character-showcase">...</div>
    </section>

    <!-- 功能区域 -->
    <section class="features-section">
        <div class="container">
            <div class="row">
                <div class="col-md-4">
                    <div class="feature-card">
                        <div class="feature-icon">🎮</div>
                        <h3>功能标题</h3>
                        <p>功能描述</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- 页脚 -->
    <footer class="footer">
        <!-- 渐变背景 + 简洁信息 -->
    </footer>
</body>
```

---

## 📝 设计清单

在设计新页面时，确保包含以下元素：

### 必备元素 ✅
- [ ] 使用二次元色彩系统（粉、青、紫）
- [ ] 圆润的边角（20px+）
- [ ] 柔和的阴影效果
- [ ] Hover交互动画
- [ ] 可爱的字体 (Fredoka/Nunito)
- [ ] 渐变色应用
- [ ] Emoji或图标装饰

### 加分元素 ⭐
- [ ] 漂浮装饰元素
- [ ] 脉冲/闪烁动画
- [ ] 游戏化角色
- [ ] 彩色泡泡背景
- [ ] 数据可视化
- [ ] 动态加载效果
- [ ] 成就/徽章系统

### 禁忌 ❌
- ❌ 尖锐的直角
- ❌ 纯黑色（使用深灰）
- ❌ 单调的纯色背景
- ❌ 过于严肃的图标
- ❌ 缺乏动画的静态页面
- ❌ 过小的点击区域
- ❌ 低对比度文字

---

## 🎯 使用指南

### 为新页面应用此设计风格

**步骤1**: 确定页面类型
- 信息展示页？→ 使用卡片网格布局
- 表单页面？→ 添加可爱的表单样式
- 数据页面？→ 游戏化数据可视化

**步骤2**: 选择主色调
- 情绪相关 → 樱花粉 + 渐变
- 数据/统计 → 青色 + 紫色
- 游戏功能 → 彩虹渐变

**步骤3**: 添加装饰元素
- 顶部：漂浮emoji (2-4个)
- 背景：彩色泡泡 (3-5个)
- 重点区域：星星闪烁

**步骤4**: 实现动画
- 按钮：hover上浮 + 阴影
- 卡片：hover放大
- 重要CTA：脉冲动画
- 装饰元素：漂浮动画

**步骤5**: 优化细节
- 检查圆角（最小15px）
- 添加过渡动画（0.3s）
- 确保响应式布局
- 测试交互反馈

---

## 🔗 参考资源

### CSS变量引用
```css
/* 在你的CSS文件中直接使用这些变量 */
.my-element {
    background: var(--primary-pink);
    box-shadow: var(--shadow-cute);
    border-radius: var(--radius-md);
}
```

### 组件库
所有样式定义在：`/static/css/style.css`

### 图标系统
使用 Font Awesome 6.4.0：
- 情绪：heart, smile, frown, etc.
- 功能：gamepad, book, chart, etc.
- UI：plus, edit, trash, etc.

---

## 💡 设计原则总结

1. **可爱优先**: 使用圆角、渐变、emoji让界面更友好
2. **动画增强**: 适度的动画让交互更生动
3. **色彩鲜明**: 大胆使用明亮的色彩吸引注意
4. **游戏化**: 将功能转化为游戏元素（角色、徽章、成就）
5. **青少年导向**: 符合目标用户审美，避免过于幼稚或成熟
6. **情绪为核心**: 设计始终围绕情绪主题展开

---

**最后更新**: 2025-11-15
**设计版本**: v1.0
**适用范围**: CBT情绪日记游戏全站

---

💖 让我们一起创造一个温暖、有趣、治愈的情绪管理空间！
