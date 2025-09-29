#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书Aily流式输出客户端
基于飞书Aily对话API实现流式输出效果
"""

import requests
import json
import time
import logging
from typing import Generator, Optional, Dict, Any
from config import *

logger = logging.getLogger(__name__)

class FeishuAilyStreamingClient:
    """飞书Aily流式输出客户端"""
    
    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.skill_app_id = SKILL_APP_ID
        self.skill_id = SKILL_ID
        self.base_url = FEISHU_OPEN_API_BASE
        self.polling_interval = FEISHU_POLLING_INTERVAL
        self.max_polling_time = FEISHU_MAX_POLLING_TIME
        
        self._tenant_access_token = None
        self._token_expires_at = 0
        
    def _get_tenant_access_token(self) -> str:
        """获取tenant access token"""
        current_time = time.time()
        
        # 如果token还未过期，直接返回
        if self._tenant_access_token and current_time < self._token_expires_at:
            return self._tenant_access_token
            
        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        headers = {
            'Content-Type': 'application/json; charset=utf-8'
        }
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                self._tenant_access_token = result['tenant_access_token']
                # 设置过期时间（提前5分钟刷新）
                expires_in = result.get('expire', 7200)
                self._token_expires_at = current_time + expires_in - 300
                
                logger.info("成功获取飞书tenant access token")
                return self._tenant_access_token
            else:
                raise Exception(f"获取token失败: {result}")
                
        except Exception as e:
            logger.error(f"获取飞书tenant access token失败: {e}")
            raise
    
    def _make_api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[Any, Any]:
        """发起API请求"""
        token = self._get_tenant_access_token()
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=30)
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') != 0:
                raise Exception(f"API请求失败: {result}")
                
            return result.get('data', {})
            
        except Exception as e:
            logger.error(f"API请求失败 {method} {endpoint}: {e}")
            raise
    
    def _create_session(self) -> str:
        """创建会话"""
        endpoint = f"/open-apis/aily/v1/sessions"
        data = {
            "app_id": self.skill_app_id
        }
        
        result = self._make_api_request('POST', endpoint, data)
        session_data = result.get('session', {})
        session_id = session_data.get('id')
        
        if not session_id:
            raise Exception("创建会话失败，未获取到session_id")
            
        logger.info(f"创建飞书Aily会话成功: {session_id}")
        return session_id
    
    def _create_message(self, session_id: str, content: str) -> str:
        """创建用户消息"""
        endpoint = f"/open-apis/aily/v1/sessions/{session_id}/messages"
        import uuid
        data = {
            "content": content,
            "message_type": "text",
            "content_type": "TEXT",  # 使用大写的TEXT
            "idempotent_id": str(uuid.uuid4())
        }
        
        result = self._make_api_request('POST', endpoint, data)
        message_data = result.get('message', {})
        message_id = message_data.get('id')
        
        if not message_id:
            raise Exception("创建消息失败，未获取到message_id")
            
        logger.info(f"创建用户消息成功: {message_id}")
        return message_id
    
    def _create_run(self, session_id: str) -> str:
        """触发Bot执行"""
        endpoint = f"/open-apis/aily/v1/sessions/{session_id}/runs"
        data = {
            "app_id": self.skill_app_id,  # 使用app_id而不是skill_id
            "skill_id": self.skill_id  # 指定技能ID可以节省技能选择时间
        }
        
        result = self._make_api_request('POST', endpoint, data)
        run_data = result.get('run', {})
        run_id = run_data.get('id')
        
        if not run_id:
            raise Exception("创建运行失败，未获取到run_id")
            
        logger.info(f"创建Bot运行成功: {run_id}")
        return run_id
    
    def _get_run_status(self, session_id: str, run_id: str) -> Dict[str, Any]:
        """获取运行状态"""
        endpoint = f"/open-apis/aily/v1/sessions/{session_id}/runs/{run_id}"
        return self._make_api_request('GET', endpoint)
    
    def _list_messages(self, session_id: str, with_partial: bool = True) -> Dict[str, Any]:
        """获取消息列表"""
        endpoint = f"/open-apis/aily/v1/sessions/{session_id}/messages"
        if with_partial:
            endpoint += "?with_partial_message=true"
        
        return self._make_api_request('GET', endpoint)
    
    def chat_completion_stream(self, message: str, **kwargs) -> Generator[str, None, None]:
        """流式聊天完成接口"""
        try:
            logger.info(f"开始飞书Aily流式对话: {message}")
            
            # 1. 创建会话
            session_id = self._create_session()
            
            # 2. 创建用户消息
            user_message_id = self._create_message(session_id, message)
            
            # 3. 触发Bot执行
            run_id = self._create_run(session_id)
            
            # 4. 轮询获取流式输出
            start_time = time.time()
            last_content = ""
            
            while time.time() - start_time < self.max_polling_time:
                try:
                    # 获取运行状态
                    run_status = self._get_run_status(session_id, run_id)
                    status = run_status.get('run', {}).get('status', '')
                    
                    # 获取消息列表（包含部分消息）
                    messages_data = self._list_messages(session_id, with_partial=True)
                    messages = messages_data.get('messages', [])
                    
                    # 查找Bot的回复消息
                    bot_message = None
                    for msg in messages:
                        sender = msg.get('sender', {})
                        if (sender.get('sender_type') == 'ASSISTANT' and 
                            msg.get('id') != user_message_id):
                            bot_message = msg
                            break
                    
                    if bot_message:
                        current_content = bot_message.get('content', '')
                        
                        # 如果内容有更新，输出新增部分
                        if len(current_content) > len(last_content):
                            new_content = current_content[len(last_content):]
                            logger.debug(f"飞书Aily新增内容: {new_content}")
                            yield new_content
                            last_content = current_content
                        
                        # 如果消息状态已完成且内容不再变化，提前结束
                        elif (bot_message.get('status') == 'COMPLETED' and 
                              current_content and 
                              len(current_content) == len(last_content)):
                            logger.info("飞书Aily消息已完成且内容稳定，提前结束")
                            break
                    
                    # 检查是否完成 - 修复状态判断（使用大写）
                    if status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                        logger.info(f"飞书Aily对话完成，状态: {status}")
                        break
                    
                    # 额外检查：如果Bot消息已完成且内容不再变化，也应该结束
                    if (bot_message and 
                        bot_message.get('status') == 'COMPLETED' and 
                        len(current_content) == len(last_content) and 
                        current_content):  # 确保有内容
                        logger.info("飞书Aily Bot消息已完成且内容稳定，结束轮询")
                        break
                        
                except Exception as e:
                    logger.error(f"轮询过程中出错: {e}")
                    # 继续轮询，不中断
                
                # 等待下次轮询
                time.sleep(self.polling_interval)
            
            logger.info("飞书Aily流式对话结束")
            
        except Exception as e:
            logger.error(f"飞书Aily流式对话失败: {e}")
            yield f"对话出现错误: {str(e)}"
    
    def chat_completion(self, message: str, **kwargs) -> str:
        """非流式聊天完成接口"""
        try:
            logger.info(f"开始飞书Aily非流式对话: {message}")
            
            # 收集所有流式输出
            full_response = ""
            for chunk in self.chat_completion_stream(message, **kwargs):
                full_response += chunk
            
            return full_response
            
        except Exception as e:
            logger.error(f"飞书Aily非流式对话失败: {e}")
            return f"对话出现错误: {str(e)}"
    
    # 兼容性方法
    def chat_stream(self, message: str, **kwargs):
        """兼容旧接口的流式方法"""
        return self.chat_completion_stream(message, **kwargs)