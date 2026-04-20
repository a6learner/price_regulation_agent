"""本地向量/重排模型路径：优先环境变量，其次项目内 models/，最后 HuggingFace Hub ID。"""
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_st_model(env_var: str, hub_id: str, local_dirname: str) -> str:
    """
    Args:
        env_var: 环境变量名，若已设置则直接使用（可为绝对路径或相对 cwd 的路径）
        hub_id: 默认从 Hub 加载的模型 ID
        local_dirname: 在 <项目根>/models/ 下的子目录名
    """
    override = os.environ.get(env_var)
    if override:
        return override.strip()
    local = _PROJECT_ROOT / "models" / local_dirname
    if local.is_dir():
        return str(local)
    return hub_id
