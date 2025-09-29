#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek v3.1模型配置文件
在这里配置您的火山引擎API密钥
"""

# 从 .env 加载环境变量（如果存在）
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import os

# 火山引擎API配置（支持环境变量覆盖）
VOLCANO_ACCESS_KEY = os.getenv("VOLCANO_ACCESS_KEY", "YOUR_VOLCANO_ACCESS_KEY")

# 语音合成配置（支持环境变量覆盖）
VOICE_APP_ID = os.getenv("VOICE_APP_ID", "YOUR_VOICE_APP_ID")
VOICE_ACCESS_TOKEN = os.getenv("VOICE_ACCESS_TOKEN", "YOUR_VOICE_ACCESS_TOKEN")
# 语音参数（可调节，支持环境变量覆盖）
TTS_SPEECH_RATE = int(os.getenv("TTS_SPEECH_RATE", "0"))
TTS_VOICE_TYPE = os.getenv("TTS_VOICE_TYPE", "S_dQcSOODF1")  # 陈耀忠音色ID
TTS_RESOURCE_ID = os.getenv("TTS_RESOURCE_ID", "volc.megatts.default")  # 声音复刻2.0资源ID

# ASR语音识别配置 - 大模型录音文件识别API
ASR_APP_ID = os.getenv("ASR_APP_ID", "")
ASR_ACCESS_TOKEN = os.getenv("ASR_ACCESS_TOKEN", "")
ASR_SUBMIT_URL = os.getenv("ASR_SUBMIT_URL", "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit")
ASR_QUERY_URL = os.getenv("ASR_QUERY_URL", "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query")
ASR_RESOURCE_ID = os.getenv("ASR_RESOURCE_ID", "volc.bigasr.auc")
ASR_MODEL_NAME = os.getenv("ASR_MODEL_NAME", "bigmodel")
ASR_MODEL_VERSION = os.getenv("ASR_MODEL_VERSION", "400")  # 400模型性能更好
ASR_SAMPLE_RATE = int(os.getenv("ASR_SAMPLE_RATE", "16000"))
ASR_LANGUAGE = os.getenv("ASR_LANGUAGE", "")
ASR_MAX_DURATION = int(os.getenv("ASR_MAX_DURATION", "60"))
ASR_ENABLE_ITN = os.getenv("ASR_ENABLE_ITN", "true").lower() == "true"
ASR_ENABLE_PUNC = os.getenv("ASR_ENABLE_PUNC", "false").lower() == "true"
ASR_ENABLE_DDC = os.getenv("ASR_ENABLE_DDC", "false").lower() == "true"
# 公网音频访问基地址（可选）：例如 https://your.domain 或 http://public-ip:port
ASR_PUBLIC_BASE_URL = os.getenv("ASR_PUBLIC_BASE_URL", "")
# 是否保留上传的音频文件（默认不保留）
ASR_KEEP_UPLOADS = os.getenv("ASR_KEEP_UPLOADS", "false").lower() == "true"

# 飞书Aily配置（支持环境变量覆盖）
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "YOUR_FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "YOUR_FEISHU_APP_SECRET")
SKILL_APP_ID = os.getenv("SKILL_APP_ID", "YOUR_SKILL_APP_ID")
SKILL_ID = os.getenv("SKILL_ID", "YOUR_SKILL_ID")

# 飞书Aily流式输出配置（保持原有默认值，可用环境变量覆盖）
FEISHU_OPEN_API_BASE = os.getenv("FEISHU_OPEN_API_BASE", "https://open.feishu.cn")
FEISHU_POLLING_INTERVAL = float(os.getenv("FEISHU_POLLING_INTERVAL", "0.3"))
FEISHU_MAX_POLLING_TIME = int(os.getenv("FEISHU_MAX_POLLING_TIME", "60"))

# 服务器配置（支持环境变量覆盖）
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8001"))

# DeepSeek模型配置
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v3-1-terminus1")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")

# 默认参数配置
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "2048"))

# LLM提供商配置
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "feishu_aily")

# 调试模式
DEBUG = os.getenv("DEBUG", "true").lower() == "true"