# 智能对话助手 (ChatAgent)

一个集成了火山引擎大模型、语音识别、语音合成和飞书Aily的多模态智能对话系统。支持语音输入、文本对话、语音合成播放等功能，提供完整的人机交互体验。
本项目为实现AI IDE编码用途，使用trae + Claude-4-Sonnect/GPT5

## 🌟 功能特性

- **多模态交互**：支持文本输入、语音输入和语音输出
- **智能对话**：集成火山引擎DeepSeek大模型和飞书Aily
- **语音识别**：基于火山引擎ASR大模型，支持高精度语音转文字
- **语音合成**：使用火山引擎TTS，支持声音复刻和情感表达
- **流式响应**：支持实时流式对话，提升用户体验
- **动态UI**：包含思考动画、语音波形等交互效果

## 📋 系统要求

- Python 3.8+
- 现代浏览器（支持Web Audio API）
- 火山引擎账号
- 飞书开发者账号（可选）

## 🔑 前置条件 - API密钥申请

### 1. 火山引擎API密钥申请

#### 1.1 注册火山引擎账号
1. 访问 [火山引擎官网](https://www.volcengine.com/)
2. 注册并完成实名认证
3. 登录控制台

#### 1.2 申请大模型API密钥
1. 进入 [豆包大模型页面](https://www.volcengine.com/product/doubao/)
2. 点击右下角【推理】按钮
3. 选择DeepSeek模型（如deepseek-v3-1-terminus）
4. 点击【确认接入】创建接入点
5. 在接入点列表中点击【API调用】获取API密钥

#### 1.3 申请语音合成服务
1. 访问 [豆包语音页面](https://www.volcengine.com/product/voice-tech)
2. 申请语音合成服务，获取APP_ID和ACCESS_TOKEN
3. 如需声音复刻功能，申请相应服务并获取音色ID

#### 1.4 申请语音识别服务
1. 在火山引擎控制台申请语音识别服务
2. 获取ASR相关的APP_ID和ACCESS_TOKEN
3. 配置大模型录音文件识别API权限

### 2. 飞书Aily API申请（可选）

#### 2.1 创建飞书应用
1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 登录并进入开发者后台
3. 创建企业自建应用

#### 2.2 获取应用凭证
1. 在应用详情页面，点击【凭证与基础信息】
2. 获取App ID和App Secret
3. 配置相应的API权限

#### 2.3 配置Aily技能
1. 在飞书Aily平台创建技能
2. 获取SKILL_APP_ID和SKILL_ID

## ⚙️ 配置说明

### 环境变量配置

创建 `.env` 文件或直接修改 `config.py`：

```bash
# 火山引擎大模型配置
VOLCANO_ACCESS_KEY=your_volcano_access_key
DEEPSEEK_MODEL=deepseek-v3-1-terminus
DEEPSEEK_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions

# 语音合成配置
VOICE_APP_ID=your_voice_app_id
VOICE_ACCESS_TOKEN=your_voice_access_token
TTS_SPEECH_RATE=0
TTS_VOICE_TYPE=your_voice_type 音色ID，支持自定义音色
TTS_RESOURCE_ID=volc.megatts.default

# 语音识别配置
ASR_APP_ID=your_asr_app_id
ASR_ACCESS_TOKEN=your_asr_access_token
ASR_SUBMIT_URL=https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit
ASR_QUERY_URL=https://openspeech.bytedance.com/api/v3/auc/bigmodel/query
ASR_RESOURCE_ID=volc.bigasr.auc
ASR_MODEL_NAME=bigmodel
ASR_MODEL_VERSION=400
ASR_SAMPLE_RATE=16000
ASR_LANGUAGE=
ASR_MAX_DURATION=60
ASR_ENABLE_ITN=true
ASR_ENABLE_PUNC=false
ASR_ENABLE_DDC=false
ASR_PUBLIC_BASE_URL=
ASR_KEEP_UPLOADS=false

# 飞书Aily配置（可选）
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
SKILL_APP_ID=your_skill_app_id
SKILL_ID=your_skill_id
FEISHU_OPEN_API_BASE=https://open.feishu.cn
FEISHU_POLLING_INTERVAL=0.5
FEISHU_MAX_POLLING_TIME=60

# 服务器配置
SERVER_HOST=127.0.0.1
SERVER_PORT=8001

# 模型参数
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=2048
LLM_PROVIDER=feishu_aily

# 调试模式
DEBUG=true
```

### 详细参数说明

#### 火山引擎配置
- `VOLCANO_ACCESS_KEY`: 火山引擎API密钥
- `DEEPSEEK_MODEL`: 使用的大模型名称
- `DEEPSEEK_API_URL`: 大模型API接口地址

#### 语音合成配置
- `VOICE_APP_ID`: 语音合成应用ID
- `VOICE_ACCESS_TOKEN`: 语音合成访问令牌
- `TTS_SPEECH_RATE`: 语音合成语速调节（-500到500）
- `TTS_VOICE_TYPE`: 语音合成音色ID
- `TTS_RESOURCE_ID`: 语音合成资源ID（默认：volc.megatts.default 声音复刻2.0）

#### 语音识别配置
- `ASR_APP_ID`: 语音识别应用ID
- `ASR_ACCESS_TOKEN`: 语音识别访问令牌
- `ASR_SUBMIT_URL`: 语音识别提交接口
- `ASR_QUERY_URL`: 语音识别查询接口
- `ASR_RESOURCE_ID`: 资源ID
- `ASR_MODEL_NAME`: 模型名称
- `ASR_MODEL_VERSION`: 模型版本（400性能更好）
- `ASR_SAMPLE_RATE`: 采样率（16000Hz）
- `ASR_LANGUAGE`: 语言设置（空为自动检测）
- `ASR_MAX_DURATION`: 最大录音时长（秒）
- `ASR_ENABLE_ITN`: 启用逆文本标准化
- `ASR_ENABLE_PUNC`: 启用标点符号
- `ASR_ENABLE_DDC`: 启用数字转换
- `ASR_PUBLIC_BASE_URL`: 公网音频访问基地址
- `ASR_KEEP_UPLOADS`: 是否保留上传的音频文件

#### 飞书Aily配置
- `FEISHU_APP_ID`: 飞书应用ID
- `FEISHU_APP_SECRET`: 飞书应用密钥
- `SKILL_APP_ID`: 技能应用ID
- `SKILL_ID`: 技能ID
- `FEISHU_OPEN_API_BASE`: 飞书开放平台基地址
- `FEISHU_POLLING_INTERVAL`: 轮询间隔（秒）
- `FEISHU_MAX_POLLING_TIME`: 最大轮询时间（秒）

#### 服务器配置
- `SERVER_HOST`: 服务器监听地址
- `SERVER_PORT`: 服务器端口

#### 模型参数
- `DEFAULT_TEMPERATURE`: 模型温度参数（0-1）
- `DEFAULT_MAX_TOKENS`: 最大生成令牌数
- `LLM_PROVIDER`: LLM提供商（feishu_aily或volcano）

## 🚀 部署指南

### 方式一：直接部署

#### 1. 克隆项目
```bash
git clone <repository-url>
cd chatagent
```

#### 2. 创建虚拟环境
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

#### 3. 安装依赖
```bash
pip install -r requirements.txt
```

#### 4. 配置环境变量
```bash
# 复制配置文件
cp config.py.example config.py

# 编辑配置文件，填入你的API密钥
# 或者创建 .env 文件
```

#### 5. 启动服务
```bash
python app.py
```

#### 6. 访问应用
打开浏览器访问：`http://localhost:8001`

### 方式二：Docker部署

#### 1. 构建镜像
```bash
# 克隆项目
git clone <repository-url>
cd chatagent

# 构建Docker镜像
docker build -t chatagent .
```

#### 2. 运行容器
```bash
# 使用环境变量运行
docker run -d \
  --name chatagent-app \
  -p 8001:8001 \
  -e VOLCANO_ACCESS_KEY=your_key \
  -e VOICE_APP_ID=your_app_id \
  -e VOICE_ACCESS_TOKEN=your_token \
  chatagent

# 或使用配置文件挂载
docker run -d \
  --name chatagent-app \
  -p 8001:8001 \
  -v $(pwd)/config.py:/app/config.py:ro \
  chatagent
```

#### 3. 使用Docker Compose
```bash
# 编辑docker-compose.yml中的环境变量
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 4. 健康检查
```bash
# 检查容器状态
docker ps

# 查看应用日志
docker logs chatagent-app

# 测试服务
curl http://localhost:8001/
```

## 📁 项目结构

```
chatagent/
├── app.py                      # 主应用文件
├── config.py                   # 配置文件
├── feishu_aily_streaming_client.py  # 飞书Aily流式客户端
├── requirements.txt            # Python依赖
├── Dockerfile                  # Docker构建文件
├── docker-compose.yml          # Docker Compose配置
├── .env.example               # 环境变量示例
├── uploads/                   # 音频文件上传目录
├── static/                    # 静态资源
│   ├── css/
│   │   └── style.css         # 样式文件
│   └── js/
│       └── app.js            # 前端JavaScript
├── templates/                 # HTML模板
│   └── index.html            # 主页面
└── README.md                 # 项目文档
```

## 🔧 API接口

### 聊天接口
- `POST /api/chat` - 文本聊天
- `POST /api/chat/stream` - 流式聊天

### 语音接口
- `POST /api/asr` - 语音识别
- `POST /api/tts` - 语音合成

### 文件接口
- `POST /api/upload` - 文件上传
- `GET /uploads/<filename>` - 文件访问

## 🐛 故障排除

### 常见问题

1. **API密钥错误**
   - 检查config.py中的密钥配置
   - 确认密钥有效期和权限

2. **语音功能异常**
   - 检查浏览器麦克风权限
   - 确认音频格式支持

3. **Docker部署问题**
   - 检查端口占用：`netstat -an | grep 8001`
   - 查看容器日志：`docker logs chatagent-app`

4. **网络连接问题**
   - 检查防火墙设置
   - 确认API接口可访问性

### 调试模式

启用调试模式获取详细日志：
```bash
export DEBUG=true
python app.py
```

## 📄 许可证

本项目采用 MIT 许可证。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目。

## 📞 支持

如有问题，请通过以下方式联系：
- 提交GitHub Issue
- 查看火山引擎官方文档
- 参考飞书开放平台文档

---

**注意**：使用本项目前请确保已获得相应的API服务授权，并遵守相关服务条款。