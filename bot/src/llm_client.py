import os
import json
from typing import Dict, List, Optional
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        pass


class ZhipuAIClient(BaseLLMClient):
    def __init__(self, api_key: str):
        try:
            from zhipuai import ZhipuAI
            self.client = ZhipuAI(api_key=api_key)
            self.model = "glm-4"
        except ImportError:
            raise ImportError("请安装智谱AI SDK: pip install zhipuai")
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content


class QwenClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "qwen-turbo"):
        try:
            import dashscope
            dashscope.api_key = api_key
            self.dashscope = dashscope
            self.model = model
        except ImportError:
            raise ImportError("请安装通义千问SDK: pip install dashscope")
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        from dashscope import Generation
        response = Generation.call(
            model=self.model,
            messages=messages,
            temperature=temperature,
            result_format='message',
        )
        if response.status_code == 200:
            return response.output.choices[0].message.content
        else:
            raise Exception(f"API调用失败: {response.message}")


class ErnieClient(BaseLLMClient):
    def __init__(self, api_key: str, secret_key: str):
        try:
            import qianfan
            self.client = qianfan.ChatCompletion()
            self.api_key = api_key
            self.secret_key = secret_key
            os.environ["QIANFAN_AK"] = api_key
            os.environ["QIANFAN_SK"] = secret_key
        except ImportError:
            raise ImportError("请安装千帆SDK: pip install qianfan")
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        response = self.client.do(
            messages=messages,
            temperature=temperature,
            model="ERNIE-Bot-4"
        )
        return response["result"]


class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=45.0)
            self.model = model
        except ImportError:
            raise ImportError("请安装OpenAI SDK: pip install openai")
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content


class DeepSeekClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com",
                timeout=45.0,
            )
            self.model = model
        except ImportError:
            raise ImportError("请安装OpenAI SDK: pip install openai")
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=800,
        )
        return response.choices[0].message.content


class LLMClientFactory:
    @staticmethod
    def create_client(provider: str, **kwargs) -> BaseLLMClient:
        providers = {
            'zhipu': ZhipuAIClient,
            'qwen': QwenClient,
            'ernie': ErnieClient,
            'openai': OpenAIClient,
            'deepseek': DeepSeekClient,
        }
        
        if provider not in providers:
            raise ValueError(f"不支持的提供商: {provider}. 支持的提供商: {list(providers.keys())}")
        
        return providers[provider](**kwargs)
