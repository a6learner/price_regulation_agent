"""
模型注册表 - 管理所有可用的评估模型
支持灵活添加新模型，并统一管理模型配置
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml


class ModelRegistry:
    """模型注册表 - 管理所有可用模型的配置"""

    def __init__(self, config_path: str = "configs/model_config.yaml"):
        """
        初始化模型注册表

        Args:
            config_path: 模型配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.models = self._build_model_registry()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _build_model_registry(self) -> Dict[str, Dict[str, Any]]:
        """
        构建模型注册表

        Returns:
            模型注册表字典，key为模型key，value为模型配置
        """
        models = {}

        # 从配置文件中读取模型
        config_models = self.config.get('models', {})

        for model_key, model_config in config_models.items():
            models[model_key] = {
                'key': model_key,
                'name': model_config.get('name', model_key),
                'model_id': model_config.get('model_id'),
                'type': model_config.get('type', 'baseline'),  # baseline, rag, agent
                'config': model_config,
                'result_file': f'{model_key}_results.json'
            }

        return models

    def get_model(self, model_key: str) -> Optional[Dict[str, Any]]:
        """
        获取模型配置

        Args:
            model_key: 模型键名

        Returns:
            模型配置字典，如果不存在返回None
        """
        return self.models.get(model_key)

    def list_models(self) -> List[str]:
        """
        列出所有可用模型的key

        Returns:
            模型key列表
        """
        return list(self.models.keys())

    def list_models_by_type(self, model_type: str) -> List[str]:
        """
        按类型列出模型

        Args:
            model_type: 模型类型 (baseline, rag, agent)

        Returns:
            符合类型的模型key列表
        """
        return [
            key for key, config in self.models.items()
            if config.get('type') == model_type
        ]

    def get_result_path(self, model_key: str, results_dir: str = "results/baseline") -> Path:
        """
        获取模型结果文件路径

        Args:
            model_key: 模型键名
            results_dir: 结果目录

        Returns:
            结果文件路径
        """
        model = self.get_model(model_key)
        if not model:
            raise ValueError(f"模型不存在: {model_key}")

        return Path(results_dir) / model['result_file']

    def find_latest_result(self, model_key: str, results_dir: str = "results/baseline") -> Optional[Path]:
        """
        查找某模型最近一次运行的结果文件

        优先从新格式子文件夹中查找（按文件夹名倒序=最新时间戳优先），
        fallback 到旧格式的平铺文件。

        Returns:
            结果文件路径，不存在则返回 None
        """
        base = Path(results_dir)
        result_filename = f"{model_key}_results.json"

        # 新格式：results_dir/*/{ model_key}_results.json
        matches = sorted(base.glob(f"*/{result_filename}"), reverse=True)
        if matches:
            return matches[0]

        # 旧格式 fallback：results_dir/{model_key}_results.json
        old_path = base / result_filename
        if old_path.exists():
            return old_path

        return None

    def has_result(self, model_key: str, results_dir: str = "results/baseline") -> bool:
        """检查模型是否有已保存的评估结果"""
        return self.find_latest_result(model_key, results_dir) is not None

    def add_model(
        self,
        model_key: str,
        model_name: str,
        model_id: str,
        model_type: str = 'baseline',
        **kwargs
    ):
        """
        动态添加新模型到注册表

        Args:
            model_key: 模型键名
            model_name: 模型显示名称
            model_id: 模型ID
            model_type: 模型类型
            **kwargs: 其他配置参数
        """
        self.models[model_key] = {
            'key': model_key,
            'name': model_name,
            'model_id': model_id,
            'type': model_type,
            'config': kwargs,
            'result_file': f'{model_key}_results.json'
        }

    def print_registry(self):
        """打印所有注册的模型"""
        print("\n可用模型列表:")
        print("="*70)
        print(f"{'Key':<15} {'Name':<30} {'Type':<10} {'Has Result':<12}")
        print("-"*70)

        for key, model in self.models.items():
            has_result = "[有结果]" if self.has_result(key) else ""
            print(f"{key:<15} {model['name']:<30} {model['type']:<10} {has_result:<12}")

        print("="*70)


def main():
    """测试模型注册表"""
    registry = ModelRegistry()

    print("模型注册表测试")
    registry.print_registry()

    print(f"\nBaseline模型: {registry.list_models_by_type('baseline')}")
    print(f"所有模型: {registry.list_models()}")

    # 测试添加新模型
    registry.add_model(
        model_key='qwen7b',
        model_name='Qwen2.5-7B',
        model_id='qwen2.5-7b',
        model_type='baseline',
        max_tokens=2048
    )

    print("\n添加Qwen7B后:")
    registry.print_registry()


if __name__ == '__main__':
    main()
