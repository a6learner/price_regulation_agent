---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 304402204b8558e64976daec4489555c8206f1b24ff03f7e9c565bbb13b17bf0e898646a02200481f0460076ec0f1552066209961cb26d2a7b6352f8f1077039e5710fe05d77
    ReservedCode2: 30440220438da8fc5b3aabb6ed71489bb11c7b1a9010494ce30c5089107c9261e55afeac022021e0ae57cf58fe2dc8b0c6e63c505adeb52dc46920bd30967abc1fc635d0792e
---

# MiniMax 开发环境集成指南

## 🎯 集成方案概览

基于您在 AutoDL 环境中的开发需求，这里提供三种 MiniMax 集成方案，您可以根据实际情况选择最适合的方案。

## 📋 方案一：Web API 集成（推荐）

### 1. 部署 MiniMax 代理服务

```python
# minimax_proxy.py - 在您的 AutoDL 环境中部署
import os
import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MinimaxRequest(BaseModel):
    prompt: str
    model: str = "abab6.5s-chat"
    max_tokens: int = 2000
    temperature: float = 0.1

class MinimaxResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None

class MinimaxProxy:
    """MiniMax API 代理服务"""
    
    def __init__(self):
        self.base_url = "https://api.minimax.chat/v1"
        self.api_key = os.getenv("MINIMAX_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 MINIMAX_API_KEY 环境变量")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def chat_completion(self, request: MinimaxRequest) -> MinimaxResponse:
        """调用 MiniMax Chat API"""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": request.model,
                    "messages": [
                        {"role": "user", "content": request.prompt}
                    ],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature
                }
                
                response = await client.post(
                    f"{self.base_url}/text/chatcompletion_v2",
                    headers=self.headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return MinimaxResponse(
                        success=True,
                        content=result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                        usage=result.get("usage", {})
                    )
                else:
                    error_msg = f"API调用失败: {response.status_code}"
                    logger.error(error_msg)
                    return MinimaxResponse(success=False, error=error_msg)
                    
        except Exception as e:
            error_msg = f"调用异常: {str(e)}"
            logger.error(error_msg)
            return MinimaxResponse(success=False, error=error_msg)

# 创建 FastAPI 应用
app = FastAPI(title="MiniMax 开发代理", version="1.0.0")

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 MiniMax 代理
minimax_proxy = MinimaxProxy()

@app.post("/chat", response_model=MinimaxResponse)
async def chat_with_minimax(request: MinimaxRequest):
    """Chat 端点"""
    return await minimax_proxy.chat_completion(request)

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "minimax-proxy"}

@app.post("/analyze_code")
async def analyze_code(request: MinimaxRequest):
    """代码分析专用端点"""
    prompt = f"""
    你是一个专业的代码审查助手。请分析以下代码：

    {request.prompt}

    请从以下角度进行分析：
    1. 代码质量和最佳实践
    2. 潜在的性能问题
    3. 安全性考虑
    4. 改进建议
    5. 可能的 bug 或异常情况

    请提供详细的分析和具体的改进建议。
    """
    
    analysis_request = MinimaxRequest(
        prompt=prompt,
        model=request.model,
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )
    
    return await minimax_proxy.chat_completion(analysis_request)

@app.post("/debug_error")
async def debug_error(request: MinimaxRequest):
    """错误调试专用端点"""
    prompt = f"""
    你是一个专业的调试助手。请帮助分析以下错误和代码：

    错误信息：
    {request.prompt}

    请提供：
    1. 错误原因分析
    2. 修复方案
    3. 预防措施
    4. 相关的最佳实践

    请提供详细的调试步骤和解决方案。
    """
    
    debug_request = MinimaxRequest(
        prompt=prompt,
        model=request.model,
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )
    
    return await minimax_proxy.chat_completion(debug_request)

@app.post("/optimize_performance")
async def optimize_performance(request: MinimaxRequest):
    """性能优化专用端点"""
    prompt = f"""
    你是一个性能优化专家。请分析以下代码的性能问题：

    {request.prompt}

    请提供：
    1. 性能瓶颈分析
    2. 具体的优化建议
    3. 优化后的代码示例
    4. 预期性能提升

    请提供可执行的优化方案。
    """
    
    optimization_request = MinimaxRequest(
        prompt=prompt,
        model=request.model,
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )
    
    return await minimax_proxy.chat_completion(optimization_request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. 在开发代码中调用

```python
# 在您的项目中集成
import httpx
import asyncio
from typing import Dict, Any, Optional

class MinimaxClient:
    """MiniMax 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def chat(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """发送聊天请求"""
        payload = {
            "prompt": prompt,
            "model": "abab6.5s-chat",
            **kwargs
        }
        
        response = await self.client.post(f"{self.base_url}/chat", json=payload)
        return response.json()
    
    async def analyze_code(self, code: str) -> Dict[str, Any]:
        """分析代码"""
        response = await self.client.post(
            f"{self.base_url}/analyze_code", 
            json={"prompt": code}
        )
        return response.json()
    
    async def debug_error(self, error_info: str) -> Dict[str, Any]:
        """调试错误"""
        response = await self.client.post(
            f"{self.base_url}/debug_error",
            json={"prompt": error_info}
        )
        return response.json()
    
    async def optimize_code(self, code: str) -> Dict[str, Any]:
        """优化代码性能"""
        response = await self.client.post(
            f"{self.base_url}/optimize_performance",
            json={"prompt": code}
        )
        return response.json()

# 使用示例
async def main():
    # 初始化客户端
    client = MinimaxClient()
    
    # 代码分析示例
    code_to_analyze = """
    def process_price_data(price_list):
        result = []
        for price in price_list:
            if price > 0:
                result.append(price * 1.1)
        return result
    """
    
    analysis = await client.analyze_code(code_to_analyze)
    print("代码分析结果:")
    print(analysis['content'])
    
    # 错误调试示例
    error_info = """
    Traceback (most recent call last):
      File "main.py", line 15, in <module>
        result = agent.analyze(query)
      File "/src/agents/coordinator.py", line 89, in analyze
        result = self.graph.invoke(initial_state)
      AttributeError: 'NoneType' object has no attribute 'invoke'
    """
    
    debug_result = await client.debug_error(error_info)
    print("\n调试建议:")
    print(debug_result['content'])

if __name__ == "__main__":
    asyncio.run(main())
```

## 📋 方案二：SDK 直接集成

### 安装和配置
```bash
# 安装 MiniMax SDK
pip install minimax-api

# 或者使用 HTTP 请求
pip install httpx aiohttp
```

### SDK 集成示例
```python
# minimax_sdk.py
import os
from typing import Dict, Any, Optional
import httpx

class MinimaxSDK:
    """MiniMax Python SDK 包装器"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.minimax.chat/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """同步聊天完成"""
        with httpx.Client(timeout=60) as client:
            payload = {
                "model": "abab6.5s-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 2000),
                "temperature": kwargs.get("temperature", 0.1)
            }
            
            response = client.post(
                f"{self.base_url}/text/chatcompletion_v2",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"API调用失败: {response.status_code}")
    
    async def chat_completion_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """异步聊天完成"""
        async with httpx.AsyncClient(timeout=60) as client:
            payload = {
                "model": "abab6.5s-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 2000),
                "temperature": kwargs.get("temperature", 0.1)
            }
            
            response = await client.post(
                f"{self.base_url}/text/chatcompletion_v2",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"API调用失败: {response.status_code}")

# 在您的项目中直接使用
def analyze_intent_with_minimax(query: str) -> str:
    """使用 MiniMax 分析意图"""
    client = MinimaxSDK(os.getenv("MINIMAX_API_KEY"))
    
    prompt = f"""
    请分析以下价格监管查询的意图：
    
    查询：{query}
    
    请输出JSON格式的结果：
    {{
        "task_type": "任务类型",
        "priority": "优先级", 
        "violation_type": "违规类型",
        "analysis_depth": "分析深度"
    }}
    """
    
    result = client.chat_completion(prompt)
    return result['choices'][0]['message']['content']
```

## 📋 方案三：CLI 工具集成

### 创建命令行工具
```python
# minimax_cli.py
import click
import asyncio
import json
from minimax_sdk import MinimaxSDK

@click.group()
def cli():
    """MiniMax 开发助手 CLI 工具"""
    pass

@cli.command()
@click.option('--api-key', help='MiniMax API Key')
@click.argument('prompt')
def chat(api_key, prompt):
    """通用聊天命令"""
    client = MinimaxSDK(api_key or os.getenv("MINIMAX_API_KEY"))
    result = client.chat_completion(prompt)
    click.echo(result['choices'][0]['message']['content'])

@cli.command()
@click.option('--api-key', help='MiniMax API Key')
@click.argument('file_path', type=click.Path(exists=True))
def analyze_code(api_key, file_path):
    """分析代码文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    prompt = f"""
    请分析以下代码的质量、性能和潜在问题：
    
    ```{code}```
    
    请提供详细的分析报告。
    """
    
    client = MinimaxSDK(api_key or os.getenv("MINIMAX_API_KEY"))
    result = client.chat_completion(prompt)
    click.echo(result['choices'][0]['message']['content'])

@cli.command()
@click.option('--api-key', help='MiniMax API Key')
@click.argument('error_info')
def debug(api_key, error_info):
    """调试错误信息"""
    prompt = f"""
    请分析以下错误并提供解决方案：
    
    错误信息：
    {error_info}
    """
    
    client = MinimaxSDK(api_key or os.getenv("MINIMAX_API_KEY"))
    result = client.chat_completion(prompt)
    click.echo(result['choices'][0]['message']['content'])

if __name__ == '__main__':
    cli()
```

## 🔧 部署和使用指南

### 1. 在 AutoDL 环境中部署
```bash
# 1. 上传代理服务代码到 AutoDL
scp minimax_proxy.py user@autodl-server:/home/price_regulation_agent/

# 2. 设置 API Key
export MINIMAX_API_KEY="your_api_key_here"

# 3. 启动服务
python minimax_proxy.py

# 4. 后台运行
nohup python minimax_proxy.py > minimax.log 2>&1 &
```

### 2. 在 IDE 中集成
```python
# 在 VSCode/IDE 中创建代码片段
# minimax_helper.py
class MinimaxHelper:
    """开发助手类"""
    
    @staticmethod
    async def quick_review(code: str) -> str:
        """快速代码审查"""
        prompt = f"""
        请快速审查以下代码，指出关键问题：
        
        {code}
        
        请简要说明发现的问题和建议。
        """
        client = MinimaxClient()
        result = await client.chat(prompt)
        return result['content']
    
    @staticmethod
    def explain_error(error_msg: str) -> str:
        """解释错误"""
        client = MinimaxClient()
        # 这里使用同步调用
        result = client.chat(f"请解释以下错误：{error_msg}")
        return result['content']
    
    @staticmethod
    def suggest_improvement(code: str) -> str:
        """建议改进"""
        client = MinimaxClient()
        result = client.chat(f"请建议以下代码的改进：{code}")
        return result['content']

# 使用示例
# 在调试代码时
if __name__ == "__main__":
    code = """
    def process_data(data):
        result = []
        for item in data:
            if item['price'] > 100:
                result.append(item)
        return result
    """
    
    # 快速审查
    review = MinimaxHelper.quick_review(code)
    print("代码审查结果:", review)
```

### 3. Jupyter Notebook 集成
```python
# 在 Jupyter 中使用
# 单元格 1: 配置
from minimax_client import MinimaxClient
import asyncio

client = MinimaxClient("http://your-autodl-server:8000")

# 单元格 2: 代码分析
async def analyze_my_code():
    code = """
    # 您的代码
    def my_function():
        pass
    """
    
    result = await client.analyze_code(code)
    print("分析结果:")
    display(Markdown(result['content']))

# 单元格 3: 运行分析
await analyze_my_code()
```

## 🎯 针对毕设项目的具体应用

### 1. 数据采集阶段
```python
# 使用 MiniMax 帮助分析爬虫代码
async def improve_crawler():
    crawler_code = open('crawler.py').read()
    
    prompt = f"""
    请分析以下爬虫代码，指出潜在的问题和改进建议：
    
    {crawler_code}
    
    特别关注：
    1. 反爬虫策略
    2. 数据质量
    3. 错误处理
    4. 性能优化
    """
    
    result = await client.chat(prompt)
    print(result['content'])
```

### 2. 智能体开发阶段
```python
# 分析智能体架构
async def review_agent_logic():
    agent_code = open('src/agents/coordinator.py').read()
    
    prompt = f"""
    请审查以下智能体协调器代码的架构设计：
    
    {agent_code}
    
    评估点：
    1. 架构合理性
    2. 错误处理
    3. 扩展性
    4. 性能考虑
    """
    
    result = await client.chat(prompt)
    print(result['content'])
```

### 3. 调试和优化
```python
# 错误调试助手
def debug_minimax_assisted(error_traceback):
    """使用 MiniMax 辅助调试"""
    prompt = f"""
    以下是智能体系统运行时的错误跟踪：
    
    {error_traceback}
    
    请提供：
    1. 错误根因分析
    2. 修复步骤
    3. 预防措施
    4. 相关代码改进建议
    """
    
    result = client.chat(prompt)
    return result['content']
```

## 📊 使用建议

1. **API Key 安全**: 使用环境变量存储 API Key
2. **请求频率**: 合理控制 API 调用频率，避免超出限制
3. **缓存机制**: 对于相同的分析请求，可以添加缓存
4. **错误处理**: 在生产环境中添加完善的错误处理
5. **成本控制**: 监控 API 使用量，避免不必要的费用

通过这种集成方式，您可以在整个毕设开发过程中随时获得 MiniMax 的智能辅助，大大提高开发效率！