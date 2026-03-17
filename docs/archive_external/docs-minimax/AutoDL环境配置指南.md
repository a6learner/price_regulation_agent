---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 304502200557c61417fd34f80d8b1a2f70d912a3d1fc8ee46a92dc38ddc73e7c92254825022100db8756ea6df130a2ee3c155d83630cfb03e04c7910282786efb00ce2733cd4ee
    ReservedCode2: 304502206134a6a725ccc91155ef436c699de224aaa5ed7c7640b2d7c04dd0fc09ba5c0b022100aeb24c600e3ac6d9cf81c903df0cc2ab25d0fe1c0b1398be5c2a7182d28bde41
---

# AutoDL 环境配置指南

## 🎯 目标配置
- **GPU**: RTX 4090 (24GB) × 1
- **CPU**: 16核以上
- **内存**: 64GB+
- **存储**: 500GB SSD
- **系统**: Ubuntu 20.04/22.04

## 🚀 快速部署步骤

### 1. AutoDL实例创建
```bash
# 登录 https://www.autodl.com/
# 创建实例时选择：
# - 镜像：PyTorch 2.0.0 (CUDA 11.8)
# - GPU：RTX 4090
# - 资源配置：24GB显存版本
```

### 2. 基础环境安装
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python 3.9+
sudo apt install python3.9 python3.9-pip python3.9-dev -y

# 创建虚拟环境
python3.9 -m venv price_regulation_env
source price_regulation_env/bin/activate

# 升级pip
pip install --upgrade pip
```

### 3. 核心依赖安装
```bash
# 安装PyTorch (CUDA 11.8兼容)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 安装AI开发核心库
pip install transformers==4.35.0
pip install langchain==0.0.340
pip install langgraph==0.0.46
pip install llama-factory==0.6.2
pip install chromadb==0.4.18
pip install sentence-transformers==2.2.2
pip install accelerate==0.24.1

# 安装数据处理库
pip install pandas==2.1.3
pip install numpy==1.24.3
pip install scikit-learn==1.3.2
pip install jieba==0.42.1

# 安装爬虫相关
pip install requests==2.31.0
pip install beautifulsoup4==4.12.2
pip install selenium==4.15.2
pip install playwright==1.40.0

# 安装数据库
pip install neo4j==5.15.0
pip install pymongo==4.6.0

# 安装Web开发
pip install fastapi==0.104.1
pip install uvicorn==0.24.0
pip install streamlit==1.28.2

# 安装监控和日志
pip install wandb==0.16.0
pip install tensorboard==2.15.1
```

### 4. Neo4j 部署
```bash
# 下载Neo4j社区版
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable 5.0' | sudo tee -a /etc/apt/sources.list.d/neo4j.list

sudo apt update
sudo apt install neo4j=5.15.0

# 启动Neo4j
sudo systemctl enable neo4j
sudo systemctl start neo4j

# 设置初始密码（默认用户名neo4j）
neo4j-admin dbms set-initial-password your_secure_password

# 验证部署
curl http://localhost:7474
```

### 5. 项目目录结构创建
```bash
mkdir -p price_regulation_agent/{src,data,models,tests,docs,config}
cd price_regulation_agent

# 创建主要目录
mkdir -p src/{agents,data_processing,knowledge_base,model_training,api,utils}
mkdir -p data/{raw,processed,training,validation,evaluation}
mkdir -p models/{base,finetuned,embeddings}
mkdir -p config/{database,model,agent}
mkdir -p tests/{unit,integration,e2e}
mkdir -p docs/{api,architecture,user_guide}

# 初始化Git仓库
git init
echo "price_regulation_agent/" > .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "models/" >> .gitignore
echo ".env" >> .gitignore
```

## 🔧 环境验证脚本
```bash
# 创建 environment_check.py
cat > environment_check.py << 'EOF'
import torch
import transformers
import langchain
import chromadb
import neo4j
import sys

def check_environment():
    """检查所有关键组件是否正确安装"""
    print("=== 环境检查 ===")
    
    # 检查PyTorch和CUDA
    print(f"PyTorch版本: {torch.__version__}")
    print(f"CUDA是否可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA版本: {torch.version.cuda}")
        print(f"GPU数量: {torch.cuda.device_count()}")
        print(f"GPU名称: {torch.cuda.get_device_name(0)}")
    
    # 检查其他库
    libraries = {
        "transformers": transformers.__version__,
        "langchain": langchain.__version__,
        "chromadb": chromadb.__version__
    }
    
    for lib, version in libraries.items():
        print(f"{lib}: {version}")
    
    # 检查磁盘空间
    import os
    total, used, free = os.statvfs('/').f_frsize * os.statvfs('/').f_blocks, \
                       os.statvfs('/').f_frsize * os.statvfs('/').f_bavail, \
                       os.statvfs('/').f_frsize * os.statvfs('/').f_bfree
    print(f"磁盘使用情况: {used // (1024**3):.1f}GB / {total // (1024**3):.1f}GB")
    
    print("=== 检查完成 ===")

if __name__ == "__main__":
    check_environment()
EOF

# 运行验证
python environment_check.py
```

## 🌐 网络配置确认
```bash
# 测试关键网站访问
echo "测试GitHub访问..."
curl -I https://github.com

echo "测试Hugging Face访问..."
curl -I https://huggingface.co

echo "测试PyPI访问..."
curl -I https://pypi.org

echo "测试国内镜像访问..."
curl -I https://mirrors.aliyun.com/pypi/simple
```

## 📝 配置注意事项
1. **内存优化**: 如果内存不足，可以适当调整批处理大小
2. **存储管理**: 定期清理临时文件和模型缓存
3. **网络代理**: 如果网络较慢，建议配置国内镜像源
4. **版本兼容性**: 确保CUDA版本与PyTorch版本匹配

## 🔄 快速重置脚本
```bash
# 创建 reset_environment.sh
cat > reset_environment.sh << 'EOF'
#!/bin/bash
echo "正在重置环境..."

# 停止相关服务
sudo systemctl stop neo4j

# 清理Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# 清理模型缓存
rm -rf ~/.cache/huggingface/
rm -rf ~/.cache/torch/
rm -rf ~/.cache/chroma/

# 重新激活环境
source price_regulation_env/bin/activate

echo "环境重置完成！"
EOF

chmod +x reset_environment.sh
```