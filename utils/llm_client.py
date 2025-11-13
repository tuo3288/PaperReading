"""
LLM调用封装 - 兼容OpenAI API格式
"""

from openai import OpenAI
from typing import Dict, List, Optional
import logging
import time


class LLMClient:
    """LLM客户端 - 封装OpenAI兼容的API调用"""

    def __init__(self, config: Dict):
        """
        初始化LLM客户端

        Args:
            config: 配置字典，包含api配置和models配置
        """
        self.config = config
        api_config = config.get('api', {})

        # 构建OpenAI客户端参数
        client_kwargs = {
            'api_key': api_config.get('api_key', 'your-api-key')
        }

        # 如果有base_url，添加它
        base_url = api_config.get('base_url')
        if base_url:
            client_kwargs['base_url'] = base_url

        # 如果有timeout，添加它（以秒为单位）
        timeout = api_config.get('timeout', 120)
        if timeout:
            client_kwargs['timeout'] = timeout

        self.client = OpenAI(**client_kwargs)

        self.models = config.get('models', {})
        self.max_retries = api_config.get('max_retries', 3)  # 从配置读取重试次数
        self.logger = logging.getLogger(__name__)

    def call_analyzer(self, prompt: str, temperature: float = 0.3) -> str:
        """
        调用分析者模型（强模型，用于深度分析）

        Args:
            prompt: 输入prompt
            temperature: 温度参数（默认0.3，更确定性）

        Returns:
            str: 模型输出
        """
        model = self.models.get('analyzer', 'gpt-4')
        return self._call_llm(model, prompt, temperature)

    def call_reviewer(self, prompt: str, temperature: float = 0.1) -> str:
        """
        调用审核者模型（快速模型，用于核实和判断）

        Args:
            prompt: 输入prompt
            temperature: 温度参数（默认0.1，更保守）

        Returns:
            str: 模型输出
        """
        model = self.models.get('reviewer', 'gpt-3.5-turbo')
        return self._call_llm(model, prompt, temperature)

    def _call_llm(self, model: str, prompt: str, temperature: float, max_retries: int = None) -> str:
        """
        实际调用LLM，带自动重试机制

        Args:
            model: 模型名称
            prompt: 输入prompt
            temperature: 温度参数
            max_retries: 最大重试次数（默认使用配置中的值）

        Returns:
            str: 模型输出
        """
        if max_retries is None:
            max_retries = self.max_retries

        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = min(2 ** attempt, 10)  # 指数退避，最多等10秒
                    self.logger.warning(f"Retrying after {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)

                self.logger.info(f"Calling LLM: {model}, temperature: {temperature} (Attempt {attempt + 1}/{max_retries})")
                self.logger.debug(f"Prompt length: {len(prompt)} characters")

                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=4000  # 足够长的输出
                )

                # 检查 response.choices 是否为空
                if not response.choices:
                    error_msg = f"API returned empty choices. Response: {response.model_dump_json()}"
                    self.logger.warning(error_msg)
                    last_error = ValueError(error_msg)
                    continue  # 重试

                # 检查 message.content 是否为 None
                output = response.choices[0].message.content
                if output is None:
                    error_msg = f"API returned None content. Finish reason: {response.choices[0].finish_reason}"
                    self.logger.warning(error_msg)
                    last_error = ValueError(error_msg)
                    continue  # 重试

                # 成功获取响应
                self.logger.info(f"✅ LLM response received, length: {len(output)} characters")
                return output

            except Exception as e:
                last_error = e
                self.logger.warning(f"❌ Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt == max_retries - 1:
                    # 最后一次尝试也失败了
                    self.logger.error(f"All {max_retries} attempts failed")
                    break

        # 所有重试都失败了
        self.logger.error(f"LLM call failed after {max_retries} attempts")
        if last_error:
            raise last_error
        else:
            raise RuntimeError(f"LLM call failed after {max_retries} attempts with unknown error")

    def call_with_retry(self, agent_type: str, prompt: str, max_retries: int = 3) -> str:
        """
        带重试的调用

        Args:
            agent_type: 'analyzer' or 'reviewer'
            prompt: 输入prompt
            max_retries: 最大重试次数

        Returns:
            str: 模型输出
        """
        for attempt in range(max_retries):
            try:
                if agent_type == 'analyzer':
                    return self.call_analyzer(prompt)
                elif agent_type == 'reviewer':
                    return self.call_reviewer(prompt)
                else:
                    raise ValueError(f"Unknown agent type: {agent_type}")
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise

        return ""
