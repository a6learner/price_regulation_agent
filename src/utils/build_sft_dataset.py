"""
将 CoT 样本（input/thought/output）转换为主流 SFT 训练格式（chat messages），并按比例切分训练 / 验证集。

用法示例（在项目根目录）::

    python -m src.utils.build_sft_dataset ^
        --source "data/training/sft_samples_expanded.jsonl" ^
        --train-out "data/training/train_chat_sft.jsonl" ^
        --val-out "data/validation/val_chat_sft.jsonl" ^
        --val-ratio 0.2
"""

import argparse
import json
import random
from pathlib import Path
from typing import List, Dict, Any


DEFAULT_SYSTEM_PROMPT = (
    "你是一名电商平台价格合规审查助手，熟悉《价格法》《明码标价和禁止价格欺诈规定》"
    "及相关配套规章。你需要根据给定的案件事实，做出法律分析并给出是否违规的结论和依据。"
)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """读取 JSONL 文件为列表。"""
    samples: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            samples.append(json.loads(line))
    return samples


def save_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    """保存列表为 JSONL 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for obj in rows:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def cot_to_chat(sample: Dict[str, Any], system_prompt: str) -> Dict[str, Any]:
    """
    将一条 CoT 样本转换为 chat 格式。

    期望输入样本格式::

        {
            "input": "...案件事实...",
            "thought": "...思维链分析...",
            "output": "...结论..."
        }

    输出格式::

        {
            "messages": [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }
    """
    user_content = sample.get("input", "").strip()
    thought = sample.get("thought", "").strip()
    output = sample.get("output", "").strip()

    # 将思维链与结论拼接成一个 assistant 回复，便于主流 SFT 框架直接使用
    assistant_content_parts: List[str] = []
    if thought:
        assistant_content_parts.append("分析：")
        assistant_content_parts.append(thought)
    if output:
        assistant_content_parts.append("")
        assistant_content_parts.append("结论：")
        assistant_content_parts.append(output)

    assistant_content = "\n".join(assistant_content_parts).strip()

    chat_obj: Dict[str, Any] = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ]
    }

    # 将原始样本的一些有用字段透传到 meta，便于后续分析（如果存在的话）
    meta_fields = ["case_id", "violation_type", "law_references"]
    meta: Dict[str, Any] = {}
    for key in meta_fields:
        if key in sample:
            meta[key] = sample[key]
    if meta:
        chat_obj["meta"] = meta

    return chat_obj


def build_dataset(
    source: Path,
    train_out: Path,
    val_out: Path,
    val_ratio: float,
    seed: int,
    system_prompt: str,
) -> None:
    """主流程：读取 CoT 样本 → 转 chat 格式 → 随机划分训练/验证集。"""
    samples = load_jsonl(source)
    if not samples:
        raise ValueError(f"源文件中没有有效样本: {source}")

    chat_samples = [cot_to_chat(s, system_prompt) for s in samples]

    random.seed(seed)
    random.shuffle(chat_samples)

    n_total = len(chat_samples)
    n_val = max(1, int(n_total * val_ratio))
    val_set = chat_samples[:n_val]
    train_set = chat_samples[n_val:]

    save_jsonl(train_out, train_set)
    save_jsonl(val_out, val_set)

    print(f"总样本数: {n_total}")
    print(f"训练集: {len(train_set)} 条 → {train_out}")
    print(f"验证集: {len(val_set)} 条 → {val_out}")


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    default_source = project_root / "data" / "training" / "sft_samples_expanded.jsonl"
    default_train_out = project_root / "data" / "training" / "train_chat_sft.jsonl"
    default_val_out = project_root / "data" / "validation" / "val_chat_sft.jsonl"

    parser = argparse.ArgumentParser(
        description="将 CoT 样本转换为 chat 格式的 SFT 训练/验证集"
    )
    parser.add_argument(
        "--source",
        type=str,
        default=str(default_source),
        help="源 CoT JSONL 文件路径（包含 input/thought/output 字段）",
    )
    parser.add_argument(
        "--train-out",
        type=str,
        default=str(default_train_out),
        help="训练集输出 JSONL 文件路径",
    )
    parser.add_argument(
        "--val-out",
        type=str,
        default=str(default_val_out),
        help="验证集输出 JSONL 文件路径",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="验证集占比（0-1 之间，默认 0.2）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子，确保可复现划分结果",
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        default=DEFAULT_SYSTEM_PROMPT,
        help="system 消息内容，可根据需要自定义",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_dataset(
        source=Path(args.source),
        train_out=Path(args.train_out),
        val_out=Path(args.val_out),
        val_ratio=float(args.val_ratio),
        seed=int(args.seed),
        system_prompt=args.system_prompt,
    )


if __name__ == "__main__":
    main()


