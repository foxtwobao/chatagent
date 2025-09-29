class ChatApp {
    constructor() {
        this.initElements();
        this.initEventListeners();
        this.initMediaRecorder();
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recordingTimer = null;
        this.maxRecordingTime = 60000; // 60秒
        this.currentAudio = null;
        // 交互状态
        this.isVoicePressing = false;
        this.isCancelIntent = false;
        this.pressStartY = null;
        this.cancelThreshold = 60; // 上滑超过60px视为取消
        this.isCancelledRecording = false;
        // 动画定时器
        this.recognitionAnimationTimer = null;
        this.thinkingAnimationTimer = null; // 新增思考动画定时器
        // 检测内置浏览器环境
        this.isInAppBrowser = this.detectInAppBrowser();
    }

    // 检测是否在微信、飞书、钉钉等内置浏览器中
    detectInAppBrowser() {
        const userAgent = navigator.userAgent.toLowerCase();
        return userAgent.includes('micromessenger') || // 微信
               userAgent.includes('lark') ||           // 飞书
               userAgent.includes('dingtalk') ||       // 钉钉
               userAgent.includes('aliapp') ||         // 支付宝
               userAgent.includes('qq/') ||            // QQ
               userAgent.includes('weibo');            // 微博
    }

    initElements() {
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.voiceBtn = document.getElementById('voiceBtn');
        this.chatHistory = document.getElementById('chatHistory');
        this.voiceIndicator = document.getElementById('voiceIndicator');
        this.stopRecording = document.getElementById('stopRecording');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.quoteText = document.getElementById('quoteText');
        this.recordingTime = document.getElementById('recordingTime');
    }

    initEventListeners() {
        // 发送按钮点击事件
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // 输入框回车事件
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 语音按钮事件（改为长按交互：按下开始录音，松开发送，上滑取消）
        this.voiceBtn.addEventListener('click', (e) => { e.preventDefault(); /* 使用长按手势进行录音 */ });
        // 触摸事件
        this.voiceBtn.addEventListener('touchstart', (e) => this.handleVoiceTouchStart(e), { passive: false });
        this.voiceBtn.addEventListener('touchmove', (e) => this.handleVoiceTouchMove(e), { passive: false });
        this.voiceBtn.addEventListener('touchend', (e) => this.handleVoiceTouchEnd(e));
        this.voiceBtn.addEventListener('touchcancel', (e) => this.handleVoiceTouchCancel(e));
        // 鼠标事件
        this.voiceBtn.addEventListener('mousedown', (e) => this.handleVoiceMouseDown(e));
        // 全局监听鼠标移动与松开用于“上滑取消”判断
        document.addEventListener('mousemove', (e) => this.handleVoiceMouseMove(e));
        document.addEventListener('mouseup', (e) => this.handleVoiceMouseUp(e));

        // 停止按钮仍保留
        this.stopRecording.addEventListener('click', () => this.stopVoiceRecording());

        // 输入框内容变化事件
        this.messageInput.addEventListener('input', () => {
            this.updateSendButton();
        });
    }

    async initMediaRecorder() {
        try {
            // 检查浏览器支持
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                console.warn('浏览器不支持录音功能');
                this.voiceBtn.style.display = 'none';
                this.showError('您的浏览器不支持录音功能，请使用Chrome、Firefox或Edge浏览器');
                return;
            }

            if (!window.MediaRecorder) {
                console.warn('浏览器不支持MediaRecorder');
                this.voiceBtn.style.display = 'none';
                this.showError('您的浏览器版本过低，请升级浏览器以使用录音功能');
                return;
            }

            // 检查权限状态
            if (navigator.permissions) {
                try {
                    const permission = await navigator.permissions.query({ name: 'microphone' });
                    console.log('麦克风权限状态:', permission.state);
                    
                    if (permission.state === 'denied') {
                        this.showPermissionDeniedMessage();
                        return;
                    }
                } catch (e) {
                    console.log('无法查询权限状态:', e);
                }
            }

            // 获取麦克风权限
            console.log('正在请求麦克风权限...');
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                } 
            });
            
            // 创建MediaRecorder实例（仅在支持wav/mp3/ogg时设置mimeType）
            const supportedType = this.getSupportedMimeType();
            const options = {};
            if (supportedType) {
                options.mimeType = supportedType;
            }
            try {
                this.mediaRecorder = new MediaRecorder(stream, options);
            } catch (e) {
                console.warn('无法创建MediaRecorder，错误:', e);
                this.voiceBtn.style.display = 'none';
                this.showFileUploadOption();
                this.showError('当前浏览器不支持录音为 WAV/MP3/OGG 格式，请使用文件上传方式');
                return;
            }

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                if (this.isCancelledRecording) {
                    console.log('录音被取消，跳过语音识别与发送');
                    this.isCancelledRecording = false; // 重置取消标记
                    this.audioChunks = []; // 清空已采集数据，避免误触发
                    this.showLoading(false); // 确保不显示“思考中”提示
                    return;
                }
                this.processRecording();
            };

            this.mediaRecorder.onerror = (event) => {
                console.error('录音错误:', event.error);
                this.showError('录音过程中发生错误，请重试');
                this.resetRecordingState();
            };

            // 保存stream引用以便后续使用
            this.audioStream = stream;
            console.log('录音功能初始化成功');
            
        } catch (error) {
            console.error('初始化录音功能失败:', error);
            this.handlePermissionError(error);
        }
    }

    handlePermissionError(error) {
        console.log('权限错误详情:', error.name, error.message);
        
        if (error.name === 'NotAllowedError') {
            this.showPermissionDeniedMessage();
        } else if (error.name === 'NotFoundError') {
            this.showError('未检测到麦克风设备，请检查您的麦克风是否正常连接');
            this.voiceBtn.style.display = 'none';
        } else if (error.name === 'NotReadableError') {
            this.showError('麦克风被其他应用占用，请关闭其他使用麦克风的应用后重试');
            this.voiceBtn.style.display = 'none';
        } else if (error.name === 'OverconstrainedError') {
            this.showError('麦克风不支持所需的音频格式，请尝试使用其他麦克风');
            this.voiceBtn.style.display = 'none';
        } else {
            this.showError(`录音功能初始化失败: ${error.message || '未知错误'}`);
            this.voiceBtn.style.display = 'none';
        }
    }

    showPermissionDeniedMessage() {
        const isHttps = location.protocol === 'https:';
        const isLocalhost = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
        
        let message = '麦克风权限被拒绝。';
        
        if (!isHttps && !isLocalhost) {
            message += '请使用HTTPS协议访问本站，或在浏览器地址栏点击"不安全"按钮允许麦克风权限。';
        } else {
            message += '请点击地址栏的麦克风图标，选择"允许"，然后刷新页面。';
        }
        
        // 添加重试按钮和文件上传选项
        this.showErrorWithOptions(message, [
            {
                text: '重试',
                action: () => {
                    this.initMediaRecorder();
                }
            },
            {
                text: '上传音频文件',
                action: () => {
                    this.showFileUploadOption();
                }
            }
        ]);
        
        // 暂时隐藏录音按钮
        this.voiceBtn.style.display = 'none';
    }

    showErrorWithOptions(message, options) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message-with-options';
        
        const optionsHtml = options.map((option, index) => 
            `<button class="option-btn" data-index="${index}">${option.text}</button>`
        ).join('');
        
        errorDiv.innerHTML = `
            <div class="error-content">
                <span class="error-text">${message}</span>
                <div class="error-options">
                    ${optionsHtml}
                </div>
            </div>
        `;
        
        // 添加事件监听器
        errorDiv.addEventListener('click', (e) => {
            if (e.target.classList.contains('option-btn')) {
                const index = parseInt(e.target.dataset.index);
                errorDiv.remove();
                options[index].action();
            }
        });
        
        // 移除之前的错误消息
        const existingError = document.querySelector('.error-message-with-options');
        if (existingError) {
            existingError.remove();
        }
        
        document.body.appendChild(errorDiv);
        
        // 10秒后自动移除
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 15000);
    }

    showFileUploadOption() {
        // 创建文件输入元素
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'audio/*,.wav,.mp3,.ogg';
        fileInput.style.display = 'none';
        
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleFileUpload(file);
            }
            document.body.removeChild(fileInput);
        });
        
        document.body.appendChild(fileInput);
        fileInput.click();
    }

    async handleFileUpload(file) {
        // 检查文件大小 (5MB限制)
        if (file.size > 5 * 1024 * 1024) {
            this.showError('文件大小超过5MB限制，请选择较小的音频文件');
            return;
        }
        
        // 检查文件类型
        const allowedTypes = ['audio/wav', 'audio/mp3', 'audio/ogg'];
        if (!allowedTypes.includes(file.type) && !file.name.match(/\.(wav|mp3|ogg)$/i)) {
            this.showError('不支持的音频格式，请选择 WAV、MP3、或 OGG 格式的文件');
            return;
        }
        
        try {
            this.showLoading(true);
            
            const formData = new FormData();
            formData.append('audio', file);
            
            const response = await fetch('/api/stt', {
                method: 'POST',
                body: formData
            });
            
            // 停止动画
            clearInterval(animateDots);
            
            const result = await response.json();
            
            if (result.success && result.text) {
                // 更新识别结果到占位消息
                if (messageText) {
                    messageText.textContent = result.text;
                }
                
                // 将识别结果填入输入框并直接发送，不重复添加用户消息
                this.messageInput.value = result.text;
                this.updateSendButton();
                console.log('语音识别成功:', result.text);
                
                // 直接发送消息到后端，不再调用sendMessage()以避免重复添加用户消息
                const message = result.text;
                
                // 清空输入框
                this.messageInput.value = '';
                this.updateSendButton();
                
                // 在输出区域先展示占位提示
                const placeholderEl = this.addMessage('耀忠思考中...', 'assistant', false);
                
                try {
                    // 发送消息到后端
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            message: message,
                            stream: true
                        })
                    });
        
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
        
                    // 使用占位消息进行流式替换
                    await this.handleStreamResponse(response, placeholderEl);
        
                } catch (error) {
                    console.error('发送消息失败:', error);
                    this.showError('发送消息失败，请重试');
                }
            } else {
                this.showError(result.error || '语音识别失败，请重试');
            }
        } catch (error) {
            console.error('文件上传失败:', error);
            this.showError('文件上传失败，请检查网络连接后重试');
        } finally {
            this.showLoading(false);
        }
    }

    showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.innerHTML = `
            <div class="success-content">
                <span class="success-text">${message}</span>
            </div>
        `;
        
        document.body.appendChild(successDiv);
        
        // 3秒后自动移除
        setTimeout(() => {
            if (successDiv.parentElement) {
                successDiv.remove();
            }
        }, 3000);
    }

    getSupportedMimeType() {
        // 火山引擎ASR支持的格式：raw / wav / mp3 / ogg
        // 这里仅选择浏览器常见且被API支持的容器格式
        const types = [
            'audio/ogg',
            'audio/wav',
            'audio/mp3'
        ];
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                return type;
            }
        }
        // 如果上述格式均不支持，则提示用户使用文件上传
        return '';
    }

    toggleVoiceRecording() {
        if (!this.mediaRecorder) {
            this.showError('录音功能不可用');
            return;
        }

        if (this.isRecording) {
            this.stopVoiceRecording();
        } else {
            this.startVoiceRecording();
        }
    }

    startVoiceRecording() {
        try {
            if (this.mediaRecorder.state === 'inactive') {
                this.isCancelledRecording = false; // 新录音会话重置取消状态
                this.audioChunks = [];
                this.isRecording = true;
                this.recordingStartTime = Date.now();
                
                // 更新UI状态
                this.voiceBtn.classList.add('recording');
                if (this.voiceIndicator) this.voiceIndicator.classList.add('active');
                
                // 开始录音
                this.mediaRecorder.start();
                
                // 开始时间显示更新
                this.updateRecordingTime();
                
                // 设置60秒自动停止
                this.recordingTimer = setTimeout(() => {
                    if (this.isRecording) {
                        this.stopVoiceRecording();
                        this.showError('录音时间已达60秒上限，已自动停止');
                    }
                }, this.maxRecordingTime);
                
                console.log('开始录音');
            }
        } catch (error) {
            console.error('启动录音失败:', error);
            this.showError('启动录音失败');
            this.resetRecordingState();
        }
    }

    updateRecordingTime() {
        if (!this.isRecording) return;
        
        const elapsed = Date.now() - this.recordingStartTime;
        const seconds = Math.floor(elapsed / 1000);
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        
        const timeString = `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
        if (this.recordingTime) {
            this.recordingTime.textContent = timeString;
        }
        
        // 继续更新时间
        if (this.isRecording) {
            setTimeout(() => this.updateRecordingTime(), 100);
        }
    }

    resetRecordingState() {
        this.isRecording = false;
        this.voiceBtn.classList.remove('recording');
        if (this.voiceIndicator) this.voiceIndicator.classList.remove('active');
        
        if (this.recordingTimer) {
            clearTimeout(this.recordingTimer);
            this.recordingTimer = null;
        }
        
        // 重置时间显示
        if (this.recordingTime) {
            this.recordingTime.textContent = '00:00';
        }
    }

    // 语音长按交互：触摸事件（类内方法）
    handleVoiceTouchStart(e) {
        e.preventDefault();
        if (!this.mediaRecorder) return;
        this.isVoicePressing = true;
        this.isCancelIntent = false;
        const touch = e.touches[0];
        this.pressStartY = touch.clientY;
        this.updateRecordingStatus('按住说话，上滑取消');
        this.startVoiceRecording();
    }

    handleVoiceTouchMove(e) {
        if (!this.isVoicePressing) return;
        const touch = e.touches[0];
        const deltaY = this.pressStartY - touch.clientY; // 上滑为正
        if (deltaY > this.cancelThreshold) {
            if (!this.isCancelIntent) {
                this.isCancelIntent = true;
                this.updateRecordingStatus('松开手指，取消发送');
                if (this.voiceIndicator) this.voiceIndicator.classList.add('cancel');
            }
        } else {
            if (this.isCancelIntent) {
                this.isCancelIntent = false;
                this.updateRecordingStatus('按住说话，上滑取消');
                if (this.voiceIndicator) this.voiceIndicator.classList.remove('cancel');
            }
        }
        e.preventDefault();
    }

    handleVoiceTouchEnd(e) {
        if (!this.isVoicePressing) return;
        e.preventDefault();
        this.isVoicePressing = false;
        if (this.isCancelIntent) {
            this.updateRecordingStatus('已取消');
            this.cancelCurrentRecording();
            if (this.voiceIndicator) this.voiceIndicator.classList.remove('cancel');
            this.pressStartY = null;
        } else {
            this.updateRecordingStatus('发送中...');
            this.stopVoiceRecording();
        }
        if (this.voiceIndicator) this.voiceIndicator.classList.remove('cancel');
        this.pressStartY = null;
    }

    handleVoiceTouchCancel(e) {
        if (!this.isVoicePressing) return;
        e.preventDefault();
        this.isVoicePressing = false;
        this.updateRecordingStatus('已取消');
        this.cancelCurrentRecording();
        if (this.voiceIndicator) this.voiceIndicator.classList.remove('cancel');
        this.pressStartY = null;
    }

    // 语音长按交互：鼠标事件（桌面模拟，类内方法）
    handleVoiceMouseDown(e) {
        if (e.button !== 0) return; // 左键
        if (!this.mediaRecorder) return;
        this.isVoicePressing = true;
        this.isCancelIntent = false;
        this.pressStartY = e.clientY;
        this.updateRecordingStatus('按住说话，上滑取消');
        this.startVoiceRecording();
    }

    handleVoiceMouseMove(e) {
        if (!this.isVoicePressing) return;
        const deltaY = this.pressStartY - e.clientY;
        if (deltaY > this.cancelThreshold) {
            if (!this.isCancelIntent) {
                this.isCancelIntent = true;
                this.updateRecordingStatus('松开鼠标，取消发送');
                if (this.voiceIndicator) this.voiceIndicator.classList.add('cancel');
            }
        } else {
            if (this.isCancelIntent) {
                this.isCancelIntent = false;
                this.updateRecordingStatus('按住说话，上滑取消');
                if (this.voiceIndicator) this.voiceIndicator.classList.remove('cancel');
            }
        }
    }

    handleVoiceMouseUp(e) {
        if (!this.isVoicePressing) return;
        this.isVoicePressing = false;
        if (this.isCancelIntent) {
            this.updateRecordingStatus('已取消');
            this.cancelCurrentRecording();
        } else {
            this.updateRecordingStatus('发送中...');
            this.stopVoiceRecording();
        }
        if (this.voiceIndicator) this.voiceIndicator.classList.remove('cancel');
        this.pressStartY = null;
    }

    cancelCurrentRecording() {
        try {
            this.isCancelledRecording = true; // 标记为取消，onstop将跳过处理
            if (this.mediaRecorder && this.isRecording) {
                // 停止但不触发发送
                this.mediaRecorder.stop();
            }
        } catch (err) {
            console.warn('取消录音时发生错误', err);
        }
        // 重置状态与UI
        this.resetRecordingState();
        // 清空已采集的片段，避免误发
        this.audioChunks = [];
        // 给出明确提示
        this.showError('已取消发送');
    }

    updateRecordingStatus(text) {
        const statusEl = document.querySelector('.recording-status');
        if (statusEl) statusEl.textContent = text;
        // 确保指示器可见
        if (this.voiceIndicator) this.voiceIndicator.classList.add('active');
    }

    stopVoiceRecording() {
        if (this.mediaRecorder && this.isRecording) {
            try {
                this.isCancelledRecording = false; // 正常停止，允许后续处理
                this.mediaRecorder.stop();
                this.resetRecordingState();
                console.log('停止录音');
            } catch (error) {
                console.error('停止录音失败:', error);
                this.resetRecordingState();
            }
        }
    }

    async processRecording() {
        if (this.audioChunks.length === 0) {
            this.showError('录音数据为空');
            return;
        }

        try {
            // 创建音频Blob
            const audioBlob = new Blob(this.audioChunks, { 
                type: this.getSupportedMimeType() 
            });
            
            console.log('录音文件大小:', (audioBlob.size / 1024).toFixed(2), 'KB');
            
            // 检查文件大小（5MB限制）
            if (audioBlob.size > 5 * 1024 * 1024) {
                this.showError('录音文件过大，请缩短录音时间');
                return;
            }

            // 添加语音识别中的提示消息
            const recognitionPlaceholder = this.addMessage('语音识别中', 'user');
            const messageText = recognitionPlaceholder.querySelector('.message-text');
            
            // 清除可能存在的旧定时器
            if (this.recognitionAnimationTimer) {
                clearInterval(this.recognitionAnimationTimer);
            }
            
            // 添加动态省略号
            let dots = 0;
            this.recognitionAnimationTimer = setInterval(() => {
                if (messageText) {
                    dots = (dots + 1) % 4;
                    messageText.textContent = '语音识别中' + '.'.repeat(dots);
                }
            }, 500);
            
            // 发送到后端进行语音识别
            const formData = new FormData();
            // 根据实际录音格式设置文件名
            const mimeType = this.getSupportedMimeType();
            let fileName = 'recording.wav';  // 默认wav
            if (mimeType && mimeType.includes('ogg')) {
                fileName = 'recording.ogg';
            } else if (mimeType && mimeType.includes('mp3')) {
                fileName = 'recording.mp3';
            }
            formData.append('audio', audioBlob, fileName);
            
            const response = await fetch('/api/stt', {
                method: 'POST',
                body: formData
            });
            
            // 停止动画
            if (this.recognitionAnimationTimer) {
                clearInterval(this.recognitionAnimationTimer);
                this.recognitionAnimationTimer = null;
            }
            
            const result = await response.json();
            
            if (result.success && result.text) {
                // 更新识别结果到占位消息
                if (messageText) {
                    messageText.textContent = result.text;
                }
                
                // 将识别结果填入输入框并直接发送，不重复添加用户消息
                this.messageInput.value = result.text;
                this.updateSendButton();
                console.log('语音识别成功:', result.text);
                
                // 直接发送消息到后端，不再调用sendMessage()以避免重复添加用户消息
                const message = result.text;
                
                // 清空输入框
                this.messageInput.value = '';
                this.updateSendButton();
                
                // 在输出区域先展示占位提示
                const placeholderEl = this.addMessage('耀忠思考中...', 'assistant', false);
                
                try {
                    // 发送消息到后端
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            message: message,
                            stream: true
                        })
                    });
        
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
        
                    // 使用占位消息进行流式替换
                    await this.handleStreamResponse(response, placeholderEl);
        
                } catch (error) {
                    console.error('发送消息失败:', error);
                    this.showError('发送消息失败，请重试');
                }
            } else {
                // 移除占位消息
                if (recognitionPlaceholder && recognitionPlaceholder.parentNode) {
                    recognitionPlaceholder.parentNode.removeChild(recognitionPlaceholder);
                }
                this.showError(result.error || '语音识别失败');
            }
            
        } catch (error) {
            // 确保在出错时也停止动画
            if (this.recognitionAnimationTimer) {
                clearInterval(this.recognitionAnimationTimer);
                this.recognitionAnimationTimer = null;
            }
            console.error('处理录音失败:', error);
            this.showError('语音识别失败，请重试');
        } finally {
            // 最后确保动画被停止
            if (this.recognitionAnimationTimer) {
                clearInterval(this.recognitionAnimationTimer);
                this.recognitionAnimationTimer = null;
            }
            this.audioChunks = [];
        }
    }

    updateSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendBtn.disabled = !hasText;
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;
    
        // 清空输入框
        this.messageInput.value = '';
        this.updateSendButton();
    
        // 添加用户消息到聊天历史
        this.addMessage(message, 'user');
    
        // 在输出区域先展示占位提示
        const placeholderEl = this.addMessage('耀忠思考中...', 'assistant', false);
    
        try {
            // 发送消息到后端
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    stream: true
                })
            });
    
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
    
            // 使用占位消息进行流式替换
            await this.handleStreamResponse(response, placeholderEl);
    
        } catch (error) {
            console.error('发送消息失败:', error);
            this.showError('发送消息失败，请重试');
        }
    }

    async handleStreamResponse(response, placeholderElement) {
        // 停止思考动画
        if (this.thinkingAnimationTimer) {
            clearInterval(this.thinkingAnimationTimer);
            this.thinkingAnimationTimer = null;
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullContent = '';
        
        // 获取或创建消息文本元素
        let messageTextElement = placeholderElement.querySelector('.message-text');
        if (!messageTextElement) {
            messageTextElement = document.createElement('div');
            messageTextElement.className = 'message-text';
            const contentDiv = placeholderElement.querySelector('.message-content');
            contentDiv.innerHTML = ''; // 清空占位内容
            contentDiv.appendChild(messageTextElement);
        }
        
        try {
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) {
                    console.log('流式响应完成');
                    // 流式响应完成后调用语音合成
                    if (fullContent.trim()) {
                        console.log('开始语音合成，文本长度:', fullContent.length);
                        await this.requestTTS(fullContent, placeholderElement);
                    }
                    break;
                }
                
                // 解码数据
                buffer += decoder.decode(value, { stream: true });
                
                // 处理可能的多个数据块
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // 保留最后一个不完整的行
                
                for (const line of lines) {
                    if (line.trim() === '') continue;
                    
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            console.log('收到结束标记');
                            // 收到结束标记后也调用语音合成
                            if (fullContent.trim()) {
                                console.log('开始语音合成，文本长度:', fullContent.length);
                                await this.requestTTS(fullContent, placeholderElement);
                            }
                            return;
                        }
                        
                        try {
                            const parsed = JSON.parse(data);
                            let content = '';
                            
                            // 处理不同的数据格式
                            if (parsed.content) {
                                // 直接content格式
                                content = parsed.content;
                            } else if (parsed.choices && parsed.choices[0] && parsed.choices[0].delta && parsed.choices[0].delta.content) {
                                // OpenAI格式 (飞书Aily使用的格式)
                                content = parsed.choices[0].delta.content;
                            }
                            
                            if (content) {
                                fullContent += content;
                                messageTextElement.textContent = fullContent;
                                this.scrollToBottom();
                            }
                        } catch (e) {
                            console.warn('解析JSON失败:', e, '数据:', data);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('处理流式响应时出错:', error);
            messageTextElement.textContent = '响应处理出错，请重试';
        }
    }

    async requestTTS(text, messageElement) {
        try {
            const response = await fetch('/api/tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text
                })
            });

            if (response.ok) {
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                
                // 根据浏览器环境选择不同的UI
                if (this.isInAppBrowser) {
                    this.addWeChatStyleVoiceMessage(messageElement, audioUrl, text);
                } else {
                    this.addAudioButton(messageElement, audioUrl);
                    
                    // 自动播放语音
                    const audioBtn = messageElement.querySelector('.audio-btn');
                    if (audioBtn) {
                        // 延迟一小段时间确保按钮已添加
                        setTimeout(() => {
                            this.playAudio(audioUrl, audioBtn);
                        }, 100);
                    }
                }
            }
        } catch (error) {
            console.error('语音合成失败:', error);
        }
    }

    // 添加微信风格的语音消息
    addWeChatStyleVoiceMessage(messageElement, audioUrl, text) {
        const messageContent = messageElement.querySelector('.message-content');
        const messageText = messageElement.querySelector('.message-text');
        
        // 创建语音消息容器
        const voiceContainer = document.createElement('div');
        voiceContainer.className = 'wechat-voice-message';
        
        // 创建语音播放区域
        const voicePlayArea = document.createElement('div');
        voicePlayArea.className = 'voice-play-area';
        
        // 语音图标
        const voiceIcon = document.createElement('div');
        voiceIcon.className = 'voice-icon';
        voiceIcon.innerHTML = '🔊';
        
        // 语音时长（估算）
        const duration = Math.ceil(text.length / 10); // 简单估算，每10个字符1秒
        const durationText = document.createElement('span');
        durationText.className = 'voice-duration';
        durationText.textContent = `${duration}"`;
        
        voicePlayArea.appendChild(voiceIcon);
        voicePlayArea.appendChild(durationText);
        
        // 文字内容
        const textContent = document.createElement('div');
        textContent.className = 'voice-text-content';
        textContent.textContent = text;
        
        voiceContainer.appendChild(voicePlayArea);
        voiceContainer.appendChild(textContent);
        
        // 添加点击播放事件
        voicePlayArea.addEventListener('click', () => {
            this.playWeChatVoice(audioUrl, voiceIcon);
        });
        
        // 替换原有内容
        messageContent.innerHTML = '';
        messageContent.appendChild(voiceContainer);
    }

    // 播放微信风格语音
    playWeChatVoice(audioUrl, iconElement) {
        // 停止当前播放的音频
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
            // 重置所有语音图标
            document.querySelectorAll('.voice-icon').forEach(icon => {
                icon.innerHTML = '🔊';
                icon.classList.remove('playing');
            });
        }

        const audio = new Audio(audioUrl);
        this.currentAudio = audio;
        
        // 更新图标为播放状态
        iconElement.innerHTML = '🔉';
        iconElement.classList.add('playing');
        
        audio.play();
        
        audio.onended = () => {
            iconElement.innerHTML = '🔊';
            iconElement.classList.remove('playing');
            this.currentAudio = null;
        };
        
        audio.onerror = () => {
            iconElement.innerHTML = '🔊';
            iconElement.classList.remove('playing');
            this.currentAudio = null;
            this.showError('音频播放失败');
        };
    }

    addAudioButton(messageElement, audioUrl) {
        const audioBtn = document.createElement('button');
        audioBtn.className = 'audio-btn';
        audioBtn.innerHTML = '<i class="fas fa-play"></i>';
        audioBtn.title = '播放语音';
        
        audioBtn.addEventListener('click', () => {
            this.playAudio(audioUrl, audioBtn);
        });
        
        const messageContent = messageElement.querySelector('.message-content');
        messageContent.appendChild(audioBtn);
    }

    playAudio(audioUrl, button) {
        // 停止当前播放的音频
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
            // 重置所有播放按钮
            document.querySelectorAll('.audio-btn').forEach(btn => {
                btn.innerHTML = '<i class="fas fa-play"></i>';
                btn.classList.remove('playing');
            });
        }

        const audio = new Audio(audioUrl);
        this.currentAudio = audio;
        
        button.innerHTML = '<i class="fas fa-pause"></i>';
        button.classList.add('playing');
        
        audio.play();
        
        audio.onended = () => {
            button.innerHTML = '<i class="fas fa-play"></i>';
            button.classList.remove('playing');
            this.currentAudio = null;
        };
        
        audio.onerror = () => {
            button.innerHTML = '<i class="fas fa-play"></i>';
            button.classList.remove('playing');
            this.currentAudio = null;
            this.showError('音频播放失败');
        };
    }

    addMessage(text, sender, isTyping = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const avatarImg = document.createElement('img');
        avatarImg.className = 'message-avatar';
        avatarImg.src = sender === 'user' ? 'static/images/user-avatar.svg' : 'resources/yaozhong.jpg';
        avatarImg.alt = sender === 'user' ? '用户头像' : '耀忠头像';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (isTyping) {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'typing-indicator';
            typingDiv.innerHTML = `
                <span>正在思考...</span>
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            `;
            contentDiv.appendChild(typingDiv);
            
            // 短暂延迟后移除打字指示器，但保留文本容器
            setTimeout(() => {
                const typingIndicator = contentDiv.querySelector('.typing-indicator');
                if (typingIndicator) {
                    typingIndicator.remove();
                }
            }, 500); // 减少延迟时间
        } else {
            const textDiv = document.createElement('div');
            textDiv.className = 'message-text';
            textDiv.textContent = text;
            contentDiv.appendChild(textDiv);
            
            // 如果是"耀忠思考中"消息，添加动态省略号动画
            if (text === '耀忠思考中...') {
                // 清除可能存在的旧定时器
                if (this.thinkingAnimationTimer) {
                    clearInterval(this.thinkingAnimationTimer);
                }
                
                // 添加动态省略号
                let dots = 0;
                this.thinkingAnimationTimer = setInterval(() => {
                    if (textDiv) {
                        dots = (dots + 1) % 4;
                        textDiv.textContent = '耀忠思考中' + '.'.repeat(dots);
                    }
                }, 500);
            }
        }
        
        messageDiv.appendChild(avatarImg);
        messageDiv.appendChild(contentDiv);
        
        this.chatHistory.appendChild(messageDiv);
        this.scrollToBottom();
        
        return messageDiv;
    }

    showLoading(show) {
        if (!this.loadingIndicator) return;
        if (show) {
            this.loadingIndicator.classList.add('active');
        } else {
            this.loadingIndicator.classList.remove('active');
        }
    }

    showError(message) {
        // 创建错误提示
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #ff4757;
            color: white;
            padding: 1rem 2rem;
            border-radius: 10px;
            z-index: 1001;
            box-shadow: 0 4px 15px rgba(255, 71, 87, 0.3);
        `;
        
        document.body.appendChild(errorDiv);
        
        // 3秒后自动移除
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 3000);
    }

    scrollToBottom() {
        this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
    }

    // 初始化欢迎消息
    initWelcomeMessage() {
        const welcomeText = "您好！我是陈耀忠，很高兴与您对话。您可以通过文字或语音向我提问，我会尽力为您答疑解惑。";
        this.addMessage(welcomeText, 'assistant');
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    const app = new ChatApp();
    
    // 添加欢迎消息
    setTimeout(() => {
        app.initWelcomeMessage();
    }, 1000);
});

// 处理页面可见性变化，暂停音频播放
document.addEventListener('visibilitychange', () => {
    if (document.hidden && window.chatApp && window.chatApp.currentAudio) {
        window.chatApp.currentAudio.pause();
    }
});

// 全局错误处理
window.addEventListener('error', (event) => {
    console.error('全局错误:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('未处理的Promise拒绝:', event.reason);
});