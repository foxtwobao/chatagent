# ChatAgent 项目开发规范

本文档为 ChatAgent 智能对话助手项目提供完整的开发规范和指导，确保代码质量、项目可维护性和团队协作效率。

## 📋 目录

- [项目概述](#项目概述)
- [技术栈](#技术栈)
- [目录结构](#目录结构)
- [代码规范](#代码规范)
- [命名约定](#命名约定)
- [API开发规范](#api开发规范)
- [配置管理](#配置管理)
- [Git提交规范](#git提交规范)
- [部署规范](#部署规范)
- [第三方服务集成](#第三方服务集成)

## 🎯 项目概述

ChatAgent 是一个基于 Flask 的智能对话助手，集成了火山引擎 LLM、语音合成、语音识别和飞书 Aily 等多项 AI 服务。

### 核心功能
- 文本对话（支持流式输出）
- 语音识别（ASR）
- 语音合成（TTS）
- 文件上传处理
- 多 LLM 提供商支持

## 🛠️ 技术栈

### 后端技术
- **框架**: Flask 2.3.3
- **CORS**: Flask-CORS 4.0.0
- **HTTP客户端**: requests 2.31.0
- **环境变量**: python-dotenv 1.0.1
- **Python版本**: 3.11+

### 前端技术
- **HTML5**: 语义化标签
- **CSS3**: 现代样式和响应式设计
- **JavaScript**: ES6+ 语法
- **WebAPI**: MediaRecorder, Fetch API

### 部署技术
- **容器化**: Docker + Docker Compose
- **Web服务器**: Flask内置服务器（开发）/ Gunicorn（生产）

## 📁 目录结构

```
chatagent/
├── .trae/                          # Trae IDE 配置
│   └── rules/
│       └── project_rules.md        # 项目规范文档
├── static/                         # 静态资源
│   ├── css/
│   │   └── style.css              # 主样式文件
│   ├── js/
│   │   ├── app.js                 # 主前端逻辑
│   │   └── llm-switcher.js        # LLM切换组件
│   └── images/
│       └── user-avatar.svg        # 用户头像图标
├── resources/                      # 资源文件
│   └── yaozhong.jpg               # 音色展示图片
├── uploads/                        # 文件上传目录
├── app.py                         # Flask 主应用
├── config.py                      # 配置文件
├── feishu_aily_streaming_client.py # 飞书Aily客户端
├── index.html                     # 主页面
├── requirements.txt               # Python依赖
├── Dockerfile                     # Docker构建文件
├── docker-compose.yml             # Docker Compose配置
├── .env.example                   # 环境变量示例
├── .gitignore                     # Git忽略文件
└── README.md                      # 项目文档
```

### 目录组织原则
1. **静态资源分离**: CSS、JS、图片分别存放在 static/ 对应子目录
2. **配置集中管理**: 所有配置统一在 config.py 中管理
3. **模块化设计**: 不同功能的客户端独立文件
4. **资源隔离**: 上传文件、资源文件分别存放


## 🌐 API开发规范

### 1. 路由设计
- 使用 RESTful API 设计原则
- 统一的 URL 前缀 `/api`
- 明确的资源命名

```python
# 聊天相关
@app.route('/api/chat', methods=['POST'])          # 普通聊天
@app.route('/api/chat/stream', methods=['POST'])   # 流式聊天

# 语音相关
@app.route('/api/asr', methods=['POST'])           # 语音识别
@app.route('/api/tts', methods=['POST'])           # 语音合成

# 文件相关
@app.route('/api/upload', methods=['POST'])        # 文件上传
```

### 2. 请求响应格式
- 统一的 JSON 响应格式
- 明确的状态码使用
- 详细的错误信息

```python
# 成功响应
{
    "success": true,
    "data": {
        "message": "处理成功",
        "result": "..."
    }
}

# 错误响应
{
    "success": false,
    "error": {
        "code": "INVALID_PARAMETER",
        "message": "参数格式不正确",
        "details": "..."
    }
}
```

### 3. 错误处理
- 统一的错误处理装饰器
- 详细的错误日志记录
- 用户友好的错误信息

```python
@app.errorhandler(400)
def bad_request(error):
    """400错误处理"""
    logger.warning(f"Bad request: {error}")
    return jsonify({
        'success': false,
        'error': {
            'code': 'BAD_REQUEST',
            'message': '请求参数不正确'
        }
    }), 400
```

## ⚙️ 配置管理

### 1. 配置文件结构
- 所有配置集中在 `config.py`
- 支持环境变量覆盖
- 敏感信息使用环境变量

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# 火山引擎配置
VOLCANO_ACCESS_KEY = os.getenv("VOLCANO_ACCESS_KEY", "")

# 服务器配置
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8001"))

# 调试模式
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
```

### 2. 环境变量管理
- 使用 `.env` 文件管理本地环境变量
- 提供 `.env.example` 作为模板
- 生产环境直接设置环境变量

```bash
# .env.example
# 火山引擎配置
VOLCANO_ACCESS_KEY=your_volcano_access_key

# 语音合成配置
VOICE_APP_ID=your_voice_app_id
VOICE_ACCESS_TOKEN=your_voice_access_token

# 服务器配置
SERVER_HOST=127.0.0.1
SERVER_PORT=8001
DEBUG=true
```


## 🔌 第三方服务集成

### 1. LLM大模型使用火山引擎
- **文档**: https://www.volcengine.com/docs/82379/1494384
- **要求**: 使用流式响应，支持中文
- **默认模型**: deepseek-v3.1-terminus（可在config.py中修改）

### 2. 语音合成
- **文档**: 
  - https://www.volcengine.com/docs/6561/1257584
  - https://www.volcengine.com/docs/6561/1598757
- **音色**: 支持使用声音复刻音色
- **版本**: 必须使用V3版本接口以支持声音复刻
- **配置**: APP_ID 和 TOKEN 在 config.py 文件中配置

### 3. 语音识别
- **API**: 使用火山引擎大模型录音文件识别API
- **版本**: V3版本
- **配置**: ASR_APP_ID 和 ASR_ACCESS_TOKEN 在 config.py 中配置

### 4. 服务器配置
- **配置位置**: config.py 文件
- **默认端口**: 8001（可在config.py中修改）
- **主机地址**: 默认 127.0.0.1

---

## 📚 参考资源

- [Flask 官方文档](https://flask.palletsprojects.com/)
- [PEP 8 代码风格指南](https://pep8.org/)
- [火山引擎 API 文档](https://www.volcengine.com/docs/)
- [Docker 最佳实践](https://docs.docker.com/develop/dev-best-practices/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

**注意**: 本规范文档应随项目发展持续更新，确保与实际开发实践保持一致。

