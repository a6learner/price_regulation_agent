"""
RAG 检索消融（子集）：对比四种法规检索配置，其余与正式 RAG 一致（cases_k=0、同一 prompt）。

- semantic_only: 仅 Chroma 向量，无 BM25、无 CrossEncoder
- bm25_only:     仅 BM25，无向量、无 CrossEncoder
- rrf:           向量 + BM25（RRF），无 CrossEncoder
- rrf_rerank:    向量 + BM25 + CrossEncoder（与当前默认管线一致）

用法（在项目根 price_regulation_agent 下）::

    python scripts/rag/run_rag_ablation.py --limit 154 --model qwen-8b --note ablation_154

说明:
- 使用数据集前 N 条（默认 154），与全量 780 分布可能略有偏差，论文中应写明。
- 指标使用 BaselineEvaluator.calculate_metrics（与 Baseline/RAG 列表结果结构一致）。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.evaluation.dataset_adapter import DatasetAdapter
from src.evaluation.ground_truth_extractor import GroundTruthExtractor
from src.rag.evaluator import RAGEvaluator
from src.rag.retriever import HybridRetriever


def collect_required_note(cli_note: str | None) -> str:
    if cli_note and cli_note.strip():
        return cli_note.strip()
    if sys.stdin.isatty():
        while True:
            note = input("本次运行说明（必填）: ").strip()
            if note:
                return note
            print("备注不能为空，请重新输入。")
    print("[错误] 必须提供 --note（当前为非交互环境，无法输入备注）")
    sys.exit(1)


def create_run_dir(base_dir: str, note: str) -> Path:
    slug = re.sub(r'[\\/:*?"<>|]+', '', note)
    slug = re.sub(r'\s+', '_', slug).strip('._')
    slug = re.sub(r'[^0-9A-Za-z_\-\u4e00-\u9fff]+', '', slug) or "ablation"
    date_tag = datetime.now().strftime("%m-%d")
    base_name = f"rag_ablation_{slug}__{date_tag}"
    run_path = Path(base_dir) / base_name
    suffix = 2
    while run_path.exists():
        run_path = Path(base_dir) / f"{base_name}__v{suffix}"
        suffix += 1
    run_path.mkdir(parents=True, exist_ok=True)
    return run_path


def build_retrievers(db_path: str):
    # bm25_only 放最前：不触发 HF 下载向量/重排模型，网络差时至少能跑完该变体
    return {
        "bm25_only": HybridRetriever(db_path, use_reranker=False, use_bm25=True, use_semantic=False),
        "semantic_only": HybridRetriever(db_path, use_reranker=False, use_bm25=False, use_semantic=True),
        "rrf": HybridRetriever(db_path, use_reranker=False, use_bm25=True, use_semantic=True),
        "rrf_rerank": HybridRetriever(db_path, use_reranker=True, use_bm25=True, use_semantic=True),
    }


def parse_args():
    p = argparse.ArgumentParser(description="RAG 检索消融（子集）")
    p.add_argument("--eval-data", default="data/eval/eval_dataset_v4_final.jsonl", help="评测 jsonl")
    p.add_argument("--limit", type=int, default=154, help="取前 N 条（默认 154）")
    p.add_argument("--model", default="qwen-8b", help="生成模型 key（model_config.yaml）")
    p.add_argument("--db-path", default="data/rag/chroma_db", help="Chroma 目录")
    p.add_argument("--note", default=None, help="运行备注（必填，非 TTY 时）")
    return p.parse_args()


def main():
    args = parse_args()
    note = collect_required_note(args.note)
    run_dir = create_run_dir("results/rag", note)
    print(f"输出目录: {run_dir}")

    adapter = DatasetAdapter(args.eval_data)
    eval_cases = adapter.to_legacy_format(limit=args.limit)
    gt_map = adapter.get_ground_truth_map()
    stats = adapter.get_statistics()

    run_info = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": "rag_ablation",
        "eval_data": args.eval_data,
        "limit": args.limit,
        "eval_cases": len(eval_cases),
        "dataset_stats_full_file": stats,
        "model": args.model,
        "variants": ["bm25_only", "semantic_only", "rrf", "rrf_rerank"],
        "note": note,
    }
    (run_dir / "run_info.json").write_text(
        json.dumps(run_info, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    retrievers = build_retrievers(args.db_path)
    summary = {"variants": {}}

    for name, retriever in retrievers.items():
        print(f"\n{'=' * 60}\n变体: {name}\n{'=' * 60}")
        ev = RAGEvaluator(db_path=args.db_path, retriever=retriever)
        ev.output_config["results_dir"] = str(run_dir)
        results = ev.evaluate_batch(eval_cases, model_key=args.model, save_progress=False)
        metrics = ev.calculate_metrics(results)
        summary["variants"][name] = {
            "accuracy": metrics.get("accuracy"),
            "f1_score": metrics.get("f1_score"),
            "precision": metrics.get("precision"),
            "recall": metrics.get("recall"),
            "type_accuracy": metrics.get("type_accuracy"),
            "success_cases": metrics.get("success_cases"),
            "avg_response_time": metrics.get("performance", {}).get("avg_response_time"),
        }
        out_path = run_dir / f"results_{name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"已写: {out_path}")

    (run_dir / "ablation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown 表（便于贴论文）
    lines = [
        "# RAG 检索消融汇总\n",
        f"- 数据: `{args.eval_data}` 前 **{args.limit}** 条\n",
        f"- 模型: `{args.model}`\n",
        f"- 输出目录: `{run_dir}`\n",
        "\n| 变体 | Accuracy | F1 | Type Acc | 平均耗时s |\n",
        "|---|---:|---:|---:|---:|\n",
    ]
    for name in ["bm25_only", "semantic_only", "rrf", "rrf_rerank"]:
        m = summary["variants"][name]
        lines.append(
            f"| {name} | {m.get('accuracy', 0):.4f} | {m.get('f1_score', 0):.4f} | "
            f"{m.get('type_accuracy', 0):.4f} | {m.get('avg_response_time', 0)} |\n"
        )
    (run_dir / "ablation_summary.md").write_text("".join(lines), encoding="utf-8")
    print(f"\n汇总: {run_dir / 'ablation_summary.md'}")


if __name__ == "__main__":
    main()
