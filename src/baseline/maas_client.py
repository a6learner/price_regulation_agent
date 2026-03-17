"""
讯飞星辰MaaS平台API客户端
支持多模型切换和调用
"""

import requests
import time
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path
import json


class MaaSClient:
    """讯飞星辰MaaS平台API客户端"""

    def __init__(self, config_path: str = "configs/model_config.yaml"):
        """
        初始化客户端

        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.api_config = self.config['api']
        self.models_config = self.config['models']

        # 统计信息
        self.total_requests = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_errors = 0

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _build_headers(self, lora_id: str = "0") -> Dict[str, str]:
        """构建请求头，支持微调模型"""
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_config["api_key"]}',
            'lora_id': lora_id
        }

    def _build_messages(self, system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
        """构建消息列表"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        model_key: str
    ) -> Dict[str, Any]:
        """
        构建请求负载

        Args:
            messages: 消息列表
            model_key: 模型键名 ('qwen' 或 'minimax')

        Returns:
            请求负载字典
        """
        model_config = self.models_config[model_key]

        payload = {
            "model": model_config['model_id'],
            "messages": messages,
            "max_tokens": model_config.get('max_tokens', 2048),
            "temperature": model_config.get('temperature', 0.7),
            "top_p": model_config.get('top_p', 0.9),
        }

        return payload

    def call_model(
        self,
        system_prompt: str,
        user_prompt: str,
        model_key: str = 'qwen',
        retry: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        调用MaaS平台模型

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            model_key: 模型键名 ('qwen' 或 'minimax')
            retry: 是否启用重试

        Returns:
            API响应字典，失败返回None
        """
        messages = self._build_messages(system_prompt, user_prompt)
        payload = self._build_payload(messages, model_key)

        # 从模型配置读取 lora_id，默认为 "0"
        model_config = self.models_config[model_key]
        lora_id = model_config.get('lora_id', '0')
        headers = self._build_headers(lora_id)

        max_retries = self.api_config['retry_times'] if retry else 1
        retry_delay = self.api_config['retry_delay']

        # 构建完整的API endpoint
        # 讯飞星辰MaaS遵循OpenAI兼容格式
        api_url = self.api_config['base_url']
        if not api_url.endswith('/chat/completions'):
            # 如果base_url没有包含endpoint，添加标准endpoint
            api_url = api_url.rstrip('/') + '/chat/completions'

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.api_config['timeout']
                )

                if response.status_code == 200:
                    try:
                        result = response.json()

                        # 更新统计信息
                        self.total_requests += 1
                        if 'usage' in result:
                            self.total_input_tokens += result['usage'].get('prompt_tokens', 0)
                            self.total_output_tokens += result['usage'].get('completion_tokens', 0)

                        return result
                    except json.JSONDecodeError as e:
                        print(f"JSON解析异常: {e}")
                        print(f"响应状态码: {response.status_code}")
                        print(f"响应内容 (前500字符): {response.text[:500]}")
                        print(f"完整响应内容: {response.text}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay * (attempt + 1))
                else:
                    print(f"API请求失败 (状态码: {response.status_code})")
                    print(f"响应内容: {response.text}")

                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))  # 指数退避

            except requests.exceptions.Timeout:
                print(f"请求超时 (尝试 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))

            except requests.exceptions.RequestException as e:
                print(f"请求异常: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))

        # 所有重试都失败
        self.total_errors += 1
        return None

    def extract_response_text(self, api_response: Dict[str, Any]) -> Optional[str]:
        """
        从API响应中提取文本内容

        Args:
            api_response: API响应字典

        Returns:
            提取的文本内容，失败返回None
        """
        try:
            # 根据讯飞API的实际响应格式调整
            # 通常格式: response['choices'][0]['message']['content']
            if 'choices' in api_response and len(api_response['choices']) > 0:
                return api_response['choices'][0]['message']['content']
            else:
                print(f"无法从响应中提取内容: {api_response}")
                return None
        except (KeyError, IndexError) as e:
            print(f"解析响应时出错: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取调用统计信息"""
        return {
            'total_requests': self.total_requests,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'total_errors': self.total_errors
        }

    def reset_statistics(self):
        """重置统计信息"""
        self.total_requests = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_errors = 0
