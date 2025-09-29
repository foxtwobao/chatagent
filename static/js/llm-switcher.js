/**
 * LLM提供商切换器
 */
class LLMSwitcher {
    constructor() {
        this.currentProvider = 'volcano'; // 默认使用火山引擎
        this.init();
    }

    init() {
        this.createSwitcherUI();
        this.loadSavedProvider();
    }

    createSwitcherUI() {
        // 创建切换器容器
        const switcherContainer = document.createElement('div');
        switcherContainer.className = 'llm-switcher-container';
        switcherContainer.innerHTML = `
            <div class="llm-switcher">
                <label for="llm-provider-select">LLM提供商:</label>
                <select id="llm-provider-select" class="llm-provider-select">
                    <option value="volcano">火山引擎</option>
                    <option value="feishu_aily">飞书Aily</option>
                </select>
                <span class="provider-status" id="provider-status">火山引擎</span>
            </div>
        `;

        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .llm-switcher-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                background: rgba(255, 255, 255, 0.95);
                padding: 10px 15px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                border: 1px solid #e0e0e0;
            }

            .llm-switcher {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 14px;
            }

            .llm-provider-select {
                padding: 5px 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                font-size: 14px;
                cursor: pointer;
            }

            .llm-provider-select:focus {
                outline: none;
                border-color: #007bff;
                box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
            }

            .provider-status {
                color: #28a745;
                font-weight: bold;
                font-size: 12px;
            }

            @media (max-width: 768px) {
                .llm-switcher-container {
                    position: relative;
                    top: auto;
                    right: auto;
                    margin: 10px;
                    width: calc(100% - 20px);
                }
            }
        `;

        // 添加到页面
        document.head.appendChild(style);
        document.body.appendChild(switcherContainer);

        // 绑定事件
        const select = document.getElementById('llm-provider-select');
        select.addEventListener('change', (e) => {
            this.switchProvider(e.target.value);
        });
    }

    loadSavedProvider() {
        // 从localStorage加载保存的提供商设置
        const savedProvider = localStorage.getItem('llm_provider');
        if (savedProvider && ['volcano', 'feishu_aily'].includes(savedProvider)) {
            this.currentProvider = savedProvider;
            document.getElementById('llm-provider-select').value = savedProvider;
            this.updateStatus();
        }
    }

    switchProvider(provider) {
        if (provider === this.currentProvider) {
            return;
        }

        this.currentProvider = provider;
        
        // 保存到localStorage
        localStorage.setItem('llm_provider', provider);
        
        // 更新状态显示
        this.updateStatus();
        
        // 通知服务器切换提供商
        this.notifyServerSwitch(provider);
        
        // 显示切换成功消息
        this.showSwitchMessage(provider);
    }

    updateStatus() {
        const statusElement = document.getElementById('provider-status');
        const providerNames = {
            'volcano': '火山引擎',
            'feishu_aily': '飞书Aily'
        };
        
        if (statusElement) {
            statusElement.textContent = providerNames[this.currentProvider] || this.currentProvider;
        }
    }

    async notifyServerSwitch(provider) {
        try {
            const response = await fetch('/api/switch-llm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    provider: provider
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log('LLM提供商切换成功:', result);
        } catch (error) {
            console.error('切换LLM提供商失败:', error);
            // 如果服务器切换失败，恢复之前的设置
            this.revertProvider();
        }
    }

    revertProvider() {
        // 恢复到之前的提供商设置
        const select = document.getElementById('llm-provider-select');
        const previousProvider = this.currentProvider === 'volcano' ? 'feishu_aily' : 'volcano';
        
        this.currentProvider = previousProvider;
        select.value = previousProvider;
        localStorage.setItem('llm_provider', previousProvider);
        this.updateStatus();
        
        this.showErrorMessage('切换失败，已恢复到之前的设置');
    }

    showSwitchMessage(provider) {
        const providerNames = {
            'volcano': '火山引擎',
            'feishu_aily': '飞书Aily'
        };
        
        this.showMessage(`已切换到 ${providerNames[provider]}`, 'success');
    }

    showErrorMessage(message) {
        this.showMessage(message, 'error');
    }

    showMessage(message, type = 'info') {
        // 创建消息提示
        const messageDiv = document.createElement('div');
        messageDiv.className = `llm-switch-message ${type}`;
        messageDiv.textContent = message;
        
        // 添加样式
        const messageStyle = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 1001;
            padding: 10px 15px;
            border-radius: 4px;
            color: white;
            font-size: 14px;
            max-width: 300px;
            word-wrap: break-word;
            animation: slideIn 0.3s ease-out;
        `;
        
        const bgColor = type === 'success' ? '#28a745' : 
                       type === 'error' ? '#dc3545' : '#007bff';
        
        messageDiv.style.cssText = messageStyle + `background-color: ${bgColor};`;
        
        // 添加动画样式
        if (!document.getElementById('message-animation-style')) {
            const animationStyle = document.createElement('style');
            animationStyle.id = 'message-animation-style';
            animationStyle.textContent = `
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
            `;
            document.head.appendChild(animationStyle);
        }
        
        document.body.appendChild(messageDiv);
        
        // 3秒后自动移除
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 3000);
    }

    getCurrentProvider() {
        return this.currentProvider;
    }
}

// 初始化LLM切换器
document.addEventListener('DOMContentLoaded', () => {
    window.llmSwitcher = new LLMSwitcher();
});