#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能对话助手后端服务
集成火山引擎LLM和语音合成功能
"""

import uuid
import tempfile
import os
import json
import asyncio
import logging
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import requests
import base64
import hashlib
import hmac
import time
from urllib.parse import urlencode
from config import *
import config as settings
from feishu_aily_streaming_client import FeishuAilyStreamingClient
from werkzeug.exceptions import RequestEntityTooLarge

# 配置日志
logging.basicConfig(level=logging.DEBUG)  # 改为DEBUG级别以查看详细日志
logger = logging.getLogger(__name__)

# 文件上传配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 推断公共基地址，优先使用反向代理头，其次使用请求的url_root
def infer_public_base_url(req):
    try:
        proto = req.headers.get('X-Forwarded-Proto')
        host = req.headers.get('X-Forwarded-Host')
        port = req.headers.get('X-Forwarded-Port')
        if proto and host:
            if port and ':' not in host:
                host = f"{host}:{port}"
            base = f"{proto}://{host}"
            logger.debug(f"通过X-Forwarded头推断公共基地址: {base}")
            return base.rstrip('/')
    except Exception as e:
        logger.debug(f"通过X-Forwarded头推断失败: {e}")
    try:
        base = req.url_root
        logger.debug(f"通过request.url_root推断公共基地址: {base}")
        return base.rstrip('/')
    except Exception as e:
        logger.debug(f"通过request.url_root推断失败: {e}")
        return ''

class VolcanoLLMClient:
    """火山引擎LLM客户端"""
    
    def __init__(self):
        self.api_url = DEEPSEEK_API_URL
        self.access_key = VOLCANO_ACCESS_KEY
        self.model = DEEPSEEK_MODEL
    
    def chat_stream(self, message, temperature=DEFAULT_TEMPERATURE, max_tokens=DEFAULT_MAX_TOKENS):
        """流式聊天接口"""
        # 火山引擎API使用API Key认证方式
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_key}'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {
                    'role': 'system',
                    'content': '你是陈耀忠，长城物业的董事长'
                },
                {
                    'role': 'user',
                    'content': message
                }
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': True
        }
        
        try:
            logger.info(f"发送LLM请求到: {self.api_url}")
            logger.info(f"使用模型: {self.model}")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=30
            )
            logger.info(f"API响应状态码: {response.status_code}")
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"LLM请求失败: {e}")
            logger.error(f"响应内容: {response.text if 'response' in locals() else '无响应'}")
            raise

class VolcanoTTSClient:
    """火山引擎语音合成客户端 - V3版本支持声音复刻"""
    
    def __init__(self):
        self.app_id = VOICE_APP_ID
        self.access_token = VOICE_ACCESS_TOKEN
        self.voice_type = TTS_VOICE_TYPE  # 从环境变量读取音色ID
        # 使用V3版本API端点
        self.api_url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
    
    def synthesize(self, text):
        """语音合成 - V3版本"""
        headers = {
            'Content-Type': 'application/json',
            'X-Api-App-Id': self.app_id,
            'X-Api-Access-Key': self.access_token,
            'X-Api-Resource-Id': TTS_RESOURCE_ID,  # 从环境变量读取资源ID
            'X-Api-Request-Id': str(int(time.time() * 1000))
        }
        
        payload = {
            'user': {
                'uid': 'user_001'
            },
            'namespace': 'BidirectionalTTS',
            'req_params': {
                'text': text,
                'speaker': self.voice_type,  # 使用声音复刻音色ID
                'audio_params': {
                    'format': 'mp3',
                    'sample_rate': 24000,
                    'speech_rate': TTS_SPEECH_RATE,  # 从配置常量读取语速
                    'loudness_rate': 0  # 音量，取值范围[-50,100]
                }
            }
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30,
                stream=True  # 启用流式响应
            )
            response.raise_for_status()
            
            # 处理流式响应 - V3版本返回多个JSON对象
            audio_data_parts = []
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8').strip()
                    if not line_str:
                        continue
                        
                    try:
                        result = json.loads(line_str)
                        logger.debug(f"TTS流式响应: {result}")
                        
                        # 检查是否有音频数据
                        if result.get('data') and isinstance(result['data'], str):
                            # 收集base64音频数据
                            audio_data_parts.append(result['data'])
                            
                        # 检查是否完成
                        if result.get('code') == 20000000 and result.get('message') == 'OK':
                            logger.info("TTS流式响应完成")
                            break
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"TTS流式响应JSON解析失败: {e}, 行内容: {line_str}")
                        continue
            
            # 合并所有音频数据
            if audio_data_parts:
                # 将所有base64数据合并
                combined_audio_data = ''.join(audio_data_parts)
                logger.info(f"TTS音频数据合并完成，总长度: {len(combined_audio_data)}")
                return base64.b64decode(combined_audio_data)
            else:
                logger.error("TTS响应中未找到音频数据")
                return None
            
        except Exception as e:
            logger.error(f"TTS请求失败: {e}")
            return None

# 初始化客户端

class VolcanoASRClient:
    """火山引擎大模型录音文件识别客户端"""
    
    def __init__(self):
        # 统一与LLM/TTS相同的初始化风格，直接使用config.py中的常量
        self.app_id = ASR_APP_ID
        self.access_token = ASR_ACCESS_TOKEN
        self.submit_url = ASR_SUBMIT_URL
        self.query_url = ASR_QUERY_URL
        self.resource_id = ASR_RESOURCE_ID
        self.model_name = ASR_MODEL_NAME
        self.model_version = ASR_MODEL_VERSION
        self.sample_rate = ASR_SAMPLE_RATE
        self.language = ASR_LANGUAGE
        self.enable_itn = ASR_ENABLE_ITN
        self.enable_punc = ASR_ENABLE_PUNC
        self.enable_ddc = ASR_ENABLE_DDC

        # 关键配置校验
        missing = []
        if not self.app_id:
            missing.append('ASR_APP_ID')
        if not self.access_token:
            missing.append('ASR_ACCESS_TOKEN')
        if not self.submit_url:
            missing.append('ASR_SUBMIT_URL')
        if not self.query_url:
            missing.append('ASR_QUERY_URL')
        if missing:
            logger.error(f"ASR关键配置缺失: {missing}。请在 .env 或环境变量中设置这些值。")
            raise RuntimeError(f"缺少ASR配置: {', '.join(missing)}")
    
    def submit_task(self, audio_url):
        """提交ASR任务"""
        # 根据文件扩展名确定音频格式
        audio_format = 'wav'  # 默认wav
        if audio_url.endswith('.ogg'):
            audio_format = 'ogg'
        elif audio_url.endswith('.mp3'):
            audio_format = 'mp3'
        elif audio_url.endswith('.webm'):
            audio_format = 'webm'
        elif audio_url.endswith('.wav'):
            audio_format = 'wav'
        
        # 根据格式设置codec
        codec = 'pcm'  # wav默认使用pcm
        if audio_format == 'ogg':
            codec = 'opus'
        elif audio_format == 'mp3':
            codec = 'mp3'
        elif audio_format == 'webm':
            codec = 'opus'
        
        # 根据官方文档，需要在Header中设置认证信息
        headers = {
            'Content-Type': 'application/json',
            'X-Api-App-Key': self.app_id,
            'X-Api-Access-Key': self.access_token,
            'X-Api-Resource-Id': 'volc.bigasr.auc',
            'X-Api-Request-Id': str(uuid.uuid4()),
            'X-Api-Sequence': '-1'
        }
        # 严格按照官方示例的最小请求体构造
        payload = {
            'user': {
                'uid': 'chatagent_user'
            },
            'audio': {
                'format': audio_format,
                'url': audio_url
            },
            'request': {
                'model_name': self.model_name,
                'enable_itn': self.enable_itn
            }
        }
        
        try:
            logger.info(f"提交ASR任务到: {self.submit_url}")
            # 避免泄露密钥：对请求头中的敏感信息做掩码
            safe_headers = dict(headers)
            if 'X-Api-Access-Key' in safe_headers:
                safe_headers['X-Api-Access-Key'] = '***'
            if 'X-Api-App-Key' in safe_headers:
                safe_headers['X-Api-App-Key'] = '***'
            logger.debug(f"ASR请求头: {safe_headers}")
            logger.debug(f"ASR请求体: {payload}")
            
            response = requests.post(
                self.submit_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            # 详细日志：状态码、响应头、原始文本
            logger.debug(f"ASR提交HTTP状态: {response.status_code}")
            try:
                logger.debug(f"ASR提交响应头: {dict(response.headers)}")
            except Exception:
                logger.debug("ASR提交响应头记录失败")
            try:
                logger.debug(f"ASR提交响应文本: {response.text[:1000]}")
            except Exception:
                logger.debug("ASR提交响应文本记录失败")

            response.raise_for_status()

            # 优先按照文档通过响应头判断提交结果
            x_status = response.headers.get('X-Api-Status-Code') or response.headers.get('x-api-status-code')
            x_message = response.headers.get('X-Api-Message') or response.headers.get('x-api-message')
            x_logid = response.headers.get('X-Tt-Logid') or response.headers.get('x-tt-logid')
            logger.info(f"ASR提交响应头状态: X-Api-Status-Code={x_status}, X-Api-Message={x_message}, X-Tt-Logid={x_logid}")

            # 按照文档：X-Api-Status-Code=20000000且X-Api-Message=OK表示成功；响应体为空是正常情况
            request_id_str = headers.get('X-Api-Request-Id')
            if str(x_status) == '20000000' and (x_message is None or str(x_message).upper() == 'OK'):
                # 使用提交请求头中的X-Api-Request-Id作为任务标识进行后续查询（部分实现返回体为空）
                logger.info(f"ASR任务提交成功，使用请求ID作为任务标识: {request_id_str}")
                return {'success': True, 'task_id': request_id_str, 'request_id': request_id_str, 'logid': x_logid}

            # 若头部未表明成功，尝试解析JSON响应（兼容另一返回格式）
            try:
                result = response.json()
            except ValueError:
                logger.debug("ASR提交响应体为空或非JSON格式")
                result = {}
            logger.debug(f"ASR提交响应JSON(兼容解析): {result}")

            resp = result.get('resp', {})
            code = resp.get('code')
            if code == 1000 or code == '1000':
                task_id = resp.get('id')
                if task_id:
                    logger.info(f"ASR任务提交成功(JSON)，任务ID: {task_id}")
                    return {'success': True, 'task_id': task_id, 'request_id': request_id_str, 'logid': x_logid}

            # 失败路径：汇总头部与JSON的错误信息
            error_msg = x_message or resp.get('message', '提交任务失败')
            logger.error(f"ASR任务提交失败: header_status={x_status}, header_message={x_message}, json_code={code}, json_message={resp.get('message')}, logid={x_logid}")
            return {'success': False, 'error': f"状态码: {x_status}, 信息: {error_msg}", 'logid': x_logid}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ASR任务提交请求失败: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    logger.error(f"ASR API错误状态: {e.response.status_code}")
                    logger.error(f"ASR API错误响应头: {dict(e.response.headers)}")
                except Exception:
                    pass
                try:
                    error_detail = e.response.json()
                    logger.error(f"ASR API错误详情(JSON): {error_detail}")
                    return {'success': False, 'error': f'API错误: {error_detail}'}
                except Exception:
                    logger.error(f"ASR API错误响应文本: {e.response.text}")
                    return {'success': False, 'error': f'API错误: {e.response.text}'}
            return {'success': False, 'error': f'网络请求失败: {str(e)}'}
        except Exception as e:
            logger.error(f"ASR任务提交异常: {str(e)}")
            return {'success': False, 'error': f'提交任务异常: {str(e)}'}
    
    def query_result(self, task_id, request_id=None):
        """查询ASR任务结果"""
        # 根据官方文档，查询接口的URL
        query_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"
        
        # 根据官方文档，需要在Header中设置认证信息
        headers = {
            'Content-Type': 'application/json',
            'X-Api-App-Key': self.app_id,
            'X-Api-Access-Key': self.access_token,
            'X-Api-Resource-Id': self.resource_id,
            'X-Api-Request-Id': str(request_id) if request_id else str(uuid.uuid4()),
            'X-Api-Sequence': '-1'
        }
        
        # 根据官方文档的请求体格式
        payload = {
            'id': task_id
        }
        
        try:
            logger.info(f"查询ASR任务结果: {task_id}")
            # 安全日志：掩码敏感头
            safe_headers = dict(headers)
            if 'X-Api-Access-Key' in safe_headers:
                safe_headers['X-Api-Access-Key'] = '***'
            if 'X-Api-App-Key' in safe_headers:
                safe_headers['X-Api-App-Key'] = '***'
            logger.debug(f"ASR查询请求头: {safe_headers}")
            logger.debug(f"ASR查询请求体: {payload}")
            
            response = requests.post(
                query_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            logger.debug(f"ASR查询HTTP状态: {response.status_code}")
            try:
                logger.debug(f"ASR查询响应头: {dict(response.headers)}")
            except Exception:
                logger.debug("ASR查询响应头记录失败")
            try:
                logger.debug(f"ASR查询响应文本: {response.text[:1000]}")
            except Exception:
                logger.debug("ASR查询响应文本记录失败")

            # 先依据响应头的状态码判断处理流程
            x_status = response.headers.get('X-Api-Status-Code') or response.headers.get('x-api-status-code')
            x_message = response.headers.get('X-Api-Message') or response.headers.get('x-api-message')
            x_logid = response.headers.get('X-Tt-Logid') or response.headers.get('x-tt-logid')
            logger.info(f"ASR查询响应头状态: X-Api-Status-Code={x_status}, X-Api-Message={x_message}, X-Tt-Logid={x_logid}")

            # 处理中/队列中：继续轮询
            if str(x_status) in ('20000001', '20000002'):
                return {'success': True, 'status': 'processing', 'logid': x_logid}
            # 静音音频：无需继续查询，提示重新提交
            if str(x_status) == '20000003':
                return {'success': False, 'status': 'silent', 'error': '静音音频，请重新提交', 'logid': x_logid}
            # 参数错误：直接返回失败
            if x_status and str(x_status).startswith('450'):
                return {'success': False, 'error': x_message or '请求参数无效', 'logid': x_logid}
            # 服务内部错误或繁忙
            if x_status and str(x_status).startswith('550'):
                if str(x_status) == '55000031':
                    return {'success': False, 'status': 'busy', 'error': '服务器繁忙，请稍后重试', 'logid': x_logid}
                return {'success': False, 'error': x_message or '服务内部处理错误', 'logid': x_logid}

            response.raise_for_status()
            try:
                result = response.json()
            except ValueError:
                logger.error(f"ASR查询响应非JSON，原始文本: {response.text}")
                return {'success': False, 'error': '查询响应非JSON'}
            logger.debug(f"ASR查询响应JSON: {result}")
            # 兼容 v3 返回结构：顶层包含 result
            if isinstance(result, dict) and 'result' in result:
                res = result.get('result', {})
                text = res.get('text')
                if text:
                    return {'success': True, 'text': text, 'status': 'completed', 'logid': x_logid}
                utterances = res.get('utterances', [])
                if utterances:
                    joined = '\n'.join([u.get('text', '') for u in utterances if u.get('text')])
                    return {'success': True, 'text': joined, 'status': 'completed', 'logid': x_logid}
                # 头部已是成功，但正文无文本字段，返回空文本
                if str(x_status) == '20000000':
                    return {'success': True, 'text': '', 'status': 'completed', 'logid': x_logid}
            
            # 兼容旧版结构：顶层 resp.code == 1000
            resp = result.get('resp') if isinstance(result, dict) else None
            if isinstance(resp, dict):
                code = resp.get('code')
                if code == 1000 or code == "1000":
                    text = resp.get('text')
                    if text:
                        return {'success': True, 'text': text, 'status': 'completed', 'logid': x_logid}
                    utterances = resp.get('utterances', [])
                    if utterances:
                        joined = '\n'.join([u.get('text', '') for u in utterances if u.get('text')])
                        return {'success': True, 'text': joined, 'status': 'completed', 'logid': x_logid}
                    return {'success': True, 'text': '', 'status': 'completed', 'logid': x_logid}
                else:
                    error_msg = resp.get('message', '查询任务失败')
                    logger.error(f"ASR任务查询失败: code={code}, message={error_msg}")
                    return {'success': False, 'error': error_msg, 'logid': x_logid}
            
            # 兜底：如果头部成功但正文没有预期结构，返回空文本成功；否则视为无效格式
            if str(x_status) == '20000000':
                return {'success': True, 'text': '', 'status': 'completed', 'logid': x_logid}
            return {'success': False, 'error': '无效的查询响应格式', 'logid': x_logid}
        except requests.exceptions.RequestException as e:
            logger.error(f"ASR任务查询请求失败: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    logger.error(f"ASR查询错误状态: {e.response.status_code}")
                    logger.error(f"ASR查询错误响应头: {dict(e.response.headers)}")
                except Exception:
                    pass
                try:
                    error_detail = e.response.json()
                    logger.error(f"ASR查询错误详情(JSON): {error_detail}")
                    return {'success': False, 'error': f'API错误: {error_detail}'}
                except Exception:
                    logger.error(f"ASR查询错误响应文本: {e.response.text}")
                    return {'success': False, 'error': f'API错误: {e.response.text}'}
            return {'success': False, 'error': f'网络请求失败: {str(e)}'}
        except Exception as e:
            logger.error(f"ASR结果查询异常: {str(e)}")
            return {'success': False, 'error': f'查询结果异常: {str(e)}'}
    
    def recognize_with_polling(self, audio_url, max_wait_time=60, poll_interval=2):
        """提交任务并轮询获取结果"""
        # 提交任务
        submit_result = self.submit_task(audio_url)
        if not submit_result['success']:
            return submit_result
        
        task_id = submit_result['task_id']
        start_time = time.time()
        
        # 轮询查询结果
        while time.time() - start_time < max_wait_time:
            query_result = self.query_result(task_id, request_id=submit_result.get('request_id'))
            
            if not query_result['success']:
                return query_result
            
            if query_result.get('status') == 'completed':
                return query_result
            elif query_result.get('status') == 'processing':
                time.sleep(poll_interval)
                continue
            else:
                return {'success': False, 'error': '未知状态'}
        
        return {'success': False, 'error': '识别超时'}
    
    def recognize(self, audio_data):
        """兼容原有接口的识别方法 - 将音频数据保存为临时文件并上传"""
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # 这里需要将临时文件上传到可访问的URL
            # 由于大模型API需要音频URL，我们需要实现文件上传功能
            # 暂时返回错误，提示需要实现文件上传服务
            os.unlink(temp_file_path)  # 清理临时文件
            
            return {
                'success': False,
                'error': '大模型ASR需要音频文件URL，请实现文件上传服务或使用本地文件识别'
            }
            
        except Exception as e:
            logger.error(f"ASR识别异常: {str(e)}")
            return {'success': False, 'error': f'识别异常: {str(e)}'}

# 初始化客户端
if LLM_PROVIDER == "feishu_aily":
    llm_client = FeishuAilyStreamingClient()
    logger.info(f"使用飞书Aily流式LLM提供商")
else:
    llm_client = VolcanoLLMClient()
    logger.info(f"使用火山引擎LLM提供商")

tts_client = VolcanoTTSClient()
asr_client = VolcanoASRClient()

@app.route('/')
def index():
    """主页"""
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """静态文件服务"""
    return send_from_directory('static', filename)

@app.route('/resources/<path:filename>')
def resource_files(filename):
    """资源文件服务"""
    return send_from_directory('resources', filename)

@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天接口"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': '消息不能为空'}), 400
        
        # 检查是否需要流式响应
        stream = data.get('stream', False)
        
        if stream:
            return Response(
                generate_stream_response(message),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # 非流式响应（备用）
            if isinstance(llm_client, FeishuAilyStreamingClient):
                # 飞书Aily非流式响应
                response = llm_client.chat_completion(message)
                return jsonify({'response': response})
            else:
                # 火山引擎非流式响应
                response = llm_client.chat_stream(message)
                full_response = ""
                
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data_obj = json.loads(data_str)
                                if 'choices' in data_obj and data_obj['choices']:
                                    delta = data_obj['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    full_response += content
                            except json.JSONDecodeError:
                                continue
                
                return jsonify({'response': full_response})
            
    except Exception as e:
        logger.error(f"聊天接口错误: {e}")
        return jsonify({'error': '服务器内部错误'}), 500

def generate_stream_response(message):
    """生成流式响应"""
    try:
        logger.info(f"开始生成流式响应，消息: {message}")
        
        # 根据当前LLM客户端类型处理不同的响应格式
        if isinstance(llm_client, FeishuAilyStreamingClient):
            # 飞书Aily返回生成器
            response_generator = llm_client.chat_completion_stream(message)
            full_response = ""
            
            for chunk in response_generator:
                if chunk:
                    logger.debug(f"飞书Aily响应块: {chunk}")
                    full_response += chunk
                    
                    # 构造SSE格式的响应
                    sse_data = {
                        'choices': [{
                            'delta': {
                                'content': chunk
                            }
                        }]
                    }
                    yield f'data: {json.dumps(sse_data, ensure_ascii=False)}\n\n'
            
            logger.info(f"飞书Aily流式响应完成，完整内容: {full_response}")
            yield 'data: [DONE]\n\n'
            
        else:
            # 火山引擎返回requests.Response对象
            response = llm_client.chat_stream(message)
            full_response = ""  # 用于收集完整响应
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    logger.debug(f"收到响应行: {line}")
                    
                    # 处理火山引擎API的响应格式
                    if line.startswith('data: '):
                        data_content = line[6:].strip()  # 移除 'data: ' 前缀
                        logger.debug(f"处理数据: {data_content}")
                        
                        if data_content == '[DONE]':
                            logger.info(f"流式响应完成，完整内容: {full_response}")
                            yield 'data: [DONE]\n\n'
                            break
                        
                        try:
                            data = json.loads(data_content)
                            # 提取内容并累积到完整响应中
                            if 'choices' in data and len(data['choices']) > 0:
                                choice = data['choices'][0]
                                if 'delta' in choice and 'content' in choice['delta']:
                                    content = choice['delta']['content']
                                    if content:
                                        full_response += content
                        except json.JSONDecodeError:
                            pass
                        
                        # 直接转发数据
                        yield f'data: {data_content}\n\n'
                    elif line.strip():
                        # 如果不是标准SSE格式，尝试解析为JSON
                        try:
                            json.loads(line)
                            logger.debug(f"发送非SSE格式数据: {line}")
                            yield f'data: {line}\n\n'
                        except json.JSONDecodeError:
                            logger.debug(f"跳过非JSON行: {line}")
                            continue
                        
            # 确保发送结束信号
            yield 'data: [DONE]\n\n'
            logger.info("火山引擎流式响应完成")
        
    except Exception as e:
        logger.error(f"流式响应错误: {e}")
        error_data = {
            'error': {
                'message': '生成响应时出现错误',
                'type': 'server_error'
            }
        }
        yield f'data: {json.dumps(error_data, ensure_ascii=False)}\n\n'
        yield 'data: [DONE]\n\n'

@app.route('/api/switch-llm', methods=['POST'])
def switch_llm():
    """切换LLM提供商接口"""
    try:
        data = request.get_json()
        provider = data.get('provider', '').strip()
        
        if provider not in ['volcano', 'feishu_aily']:
            return jsonify({'error': '不支持的LLM提供商'}), 400
        
        global llm_client
        
        # 切换LLM客户端
        if provider == 'feishu_aily':
            llm_client = FeishuAilyStreamingClient()
            logger.info("已切换到飞书Aily流式LLM提供商")
        else:
            llm_client = VolcanoLLMClient()
            logger.info("已切换到火山引擎LLM提供商")
        
        return jsonify({
            'success': True,
            'provider': provider,
            'message': f'已成功切换到{provider}提供商'
        })
        
    except Exception as e:
        logger.error(f"切换LLM提供商错误: {e}")
        return jsonify({'error': '服务器内部错误'}), 500

@app.route('/api/stt', methods=['POST'])
def speech_to_text():
    """语音转文字接口 - 支持大模型ASR"""
    try:
        # 诊断上传请求的内容类型与字段情况
        logger.debug(f"STT请求 content_type={request.content_type}")
        try:
            logger.debug(f"STT请求 files.keys={list(request.files.keys())}")
        except Exception as _e:
            logger.debug(f"STT请求 files.keys 记录失败: {_e}")
        # 检查是否有文件上传
        if 'audio' not in request.files:
            logger.warning(f"未找到音频文件，content_type={request.content_type}, files.keys={list(request.files.keys()) if hasattr(request, 'files') else 'N/A'}")
            return jsonify({'error': '未找到音频文件'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            logger.warning("上传音频文件名为空")
            return jsonify({'error': '未选择文件'}), 400
        
        # 检查文件类型
        if not allowed_file(file.filename):
            logger.warning(f"不支持的音频格式: {file.filename}")
            return jsonify({'error': '不支持的音频格式'}), 400
        
        # 保存上传的文件
        filename = secure_filename(file.filename)
        timestamp = str(int(time.time()))
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        logger.info(f"上传音频已保存: {file_path} 大小={os.path.getsize(file_path)} 字段名='audio' 原文件名='{secure_filename(file.filename)}'")
        
        try:
            # 构建音频文件URL (需要可公网访问)
            public_base = settings.ASR_PUBLIC_BASE_URL.strip() if hasattr(settings, 'ASR_PUBLIC_BASE_URL') else ''
            if public_base:
                # 确保不重复斜杠
                if public_base.endswith('/'):
                    public_base = public_base[:-1]
                logger.info(f"使用配置的ASR_PUBLIC_BASE_URL: {public_base}")
            else:
                # 动态从用户访问的URL推断公共基地址
                public_base = infer_public_base_url(request)
                if public_base:
                    logger.info(f"自动推断ASR公共基地址: {public_base}")
                    if ('127.0.0.1' in public_base) or ('localhost' in public_base) or public_base.startswith('http://0.0.0.0'):
                        logger.warning("自动推断的公共基地址是本地地址，外部ASR服务可能无法访问。建议在 .env 中设置 ASR_PUBLIC_BASE_URL 为可公网访问的域名或IP:端口。")
                else:
                    # 无法推断则回退到本地地址
                    public_base = f"http://127.0.0.1:{SERVER_PORT}"
                    logger.warning("无法从请求推断公共基地址，回退使用本地地址。外部ASR服务可能无法访问 http://127.0.0.1。请在 .env 中设置 ASR_PUBLIC_BASE_URL 为可公网访问的域名或IP:端口。")
            audio_url = f"{public_base}/uploads/{filename}"
            logger.info(f"构建的音频URL: {audio_url}")
            
            # 使用大模型ASR进行识别
            result = asr_client.recognize_with_polling(audio_url)
            
            # 清理临时文件
            if not ASR_KEEP_UPLOADS:
                try:
                    os.unlink(file_path)
                    logger.debug(f"已删除上传临时文件: {file_path}")
                except Exception as del_err:
                    logger.warning(f"删除上传临时文件失败: {del_err}")
            else:
                logger.info(f"保留上传文件以便调试: {file_path}")
            
            if result and result.get('success'):
                return jsonify({
                    'success': True,
                    'text': result.get('text', ''),
                    'confidence': result.get('confidence', 0),
                    'language': result.get('language', 'auto'),
                    'duration': result.get('duration', 0)
                })
            else:
                err = result.get('error') if result else '识别失败'
                logger.error(f"ASR识别失败: {err}")
                return jsonify({'success': False, 'error': err}), 500
        except Exception as e:
            logger.error(f"处理上传音频时异常: {e}")
            return jsonify({'error': f'处理失败: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"语音转文字接口异常: {e}")
        return jsonify({'error': f'接口异常: {str(e)}'}), 500

# 提供上传文件的访问路由
@app.route('/uploads/')
def uploads_index():
    return jsonify({'success': True, 'message': 'uploads index ok'})
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """提供上传文件的访问"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """语音合成接口"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': '文本不能为空'}), 400
        
        # 限制文本长度
        if len(text) > 1000:
            text = text[:1000]
        
        # 调用语音合成
        audio_data = tts_client.synthesize(text)
        
        if audio_data:
            return Response(
                audio_data,
                mimetype='audio/mpeg',
                headers={
                    'Content-Disposition': 'attachment; filename="speech.mp3"',
                    'Cache-Control': 'no-cache'
                }
            )
        else:
            return jsonify({'error': '语音合成失败'}), 500
            
    except Exception as e:
        logger.error(f"语音合成接口错误: {e}")
        return jsonify({'error': '服务器内部错误'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': int(time.time()),
        'version': '1.0.0'
    })

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({'error': '接口不存在'}), 404

@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({'error': '文件过大，超过5MB限制'}), 413

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({'error': '服务器内部错误'}), 500

if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('static/images', exist_ok=True)
    
    logger.info(f"启动服务器，地址: http://{SERVER_HOST}:{SERVER_PORT}")
    logger.info(f"使用模型: {DEEPSEEK_MODEL}")
    logger.info(f"语音合成音色: {tts_client.voice_type}")
    
    app.run(
        host=SERVER_HOST,
        port=SERVER_PORT,
        debug=DEBUG,
        threaded=True
    )