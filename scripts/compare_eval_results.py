"""
对比 Baseline / RAG / Agent 的评测结果。

路径规则（简写）:
  仅写运行文件夹名时，自动解析为:
    results/baseline/<name>  /  results/rag/<name>  /  results/agent/<name>
  仍支持原先相对项目根或绝对路径的写法。

无参数运行:
  依次列出 results 下 baseline / rag / agent 的可用运行目录，通过序号选择（0=跳过），
  至少选两路；再输入输出文件名，保存到 results/compare/<文件名>.md

示例:
  cd price_regulation_agent

  python scripts/compare_eval_results.py
  python scripts/compare_eval_results.py --name my_comparison

  python scripts/compare_eval_results.py \\
    --baseline improved_baseline_full_eval-780__04-18 \\
    --rag improved_rag_full_eval-780__04-18 \\
    --agent improved_agent_full_eval-780__04-19 \\
    --name eval_780

  python scripts/compare_eval_results.py --list baseline
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.baseline.evaluator import BaselineEvaluator


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _has_path_separator(s: str) -> bool:
    return "/" in s or "\\" in s


def valid_run_dirs(method: str) -> List[Path]:
    """含完整结果文件的运行子目录，新在前。"""
    root = _project_root() / "results" / method
    if not root.is_dir():
        return []
    out: List[Path] = []
    for d in sorted(root.iterdir(), key=lambda p: p.name, reverse=True):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if method == "baseline":
            files = [m for m in d.glob("*_results.json") if "progress" not in m.name.lower()]
            if files:
                out.append(d)
        elif (d / "results.json").exists():
            out.append(d)
    return out


def resolve_user_path(raw: str, method: str) -> Path:
    """
    将用户输入解析为「运行目录」或「结果 JSON 文件」路径。
    - 短名: 仅目录名 -> results/<method>/<目录名>
    - 含路径分隔符: 相对项目根或绝对路径
    - .json 文件: 直接指向该文件
    """
    root = _project_root()
    raw = raw.strip().strip('"').strip("'")
    if not raw:
        raise ValueError("路径为空")

    # 绝对路径
    p = Path(raw)
    if p.is_absolute():
        if not p.exists():
            raise FileNotFoundError(f"路径不存在: {raw}")
        return p.resolve()

    # 显式 .json
    if raw.lower().endswith(".json"):
        candidates: List[Path] = []
        if Path(raw).is_absolute():
            candidates.append(Path(raw).resolve())
        elif _has_path_separator(raw):
            candidates.append((root / raw).resolve())
        else:
            candidates.append((root / raw).resolve())
        candidates.append(Path(raw).resolve())
        for cand in candidates:
            if cand.is_file():
                return cand.resolve()
        raise FileNotFoundError(f"未找到文件: {raw}")

    # 含子路径 -> 相对项目根
    if _has_path_separator(raw):
        cand = (root / raw).resolve()
        if cand.exists():
            return cand
        raise FileNotFoundError(f"路径不存在: {root / raw}")

    # 短目录名 -> results/<method>/<name>
    cand = (root / "results" / method / raw).resolve()
    if cand.is_dir():
        return cand
    # 不区分大小写匹配
    base = root / "results" / method
    if base.is_dir():
        low = raw.lower()
        for d in base.iterdir():
            if d.is_dir() and d.name.lower() == low:
                return d.resolve()
    raise FileNotFoundError(
        f"未找到运行目录: results/{method}/{raw}\n"
        f"可用目录: python scripts/compare_eval_results.py --list {method}"
    )


def resolve_result_file(
    raw: Optional[str],
    method: str,
    model_key: Optional[str],
) -> Optional[Path]:
    """将用户输入解析为具体结果 JSON 路径。method: baseline | rag | agent"""
    if not raw:
        return None
    path = resolve_user_path(raw, method)

    if path.is_file():
        return path

    if not path.is_dir():
        raise FileNotFoundError(f"路径不存在: {raw}")

    if method == "baseline":
        if model_key:
            candidate = path / f"{model_key}_results.json"
            if candidate.exists():
                return candidate
        matches = sorted(path.glob("*_results.json"))
        matches = [m for m in matches if "progress" not in m.name.lower()]
        if not matches:
            raise FileNotFoundError(f"目录中未找到 *_results.json: {path}")
        if len(matches) == 1:
            return matches[0]
        default = path / "qwen-8b_results.json"
        if default.exists():
            return default
        names = [m.name for m in matches]
        raise ValueError(
            f"目录中有多个结果文件，请用 --model 指定，例如 --model qwen-8b。"
            f" 当前: {names}"
        )

    if method in ("rag", "agent"):
        p = path / "results.json"
        if p.exists():
            return p
        raise FileNotFoundError(f"目录中未找到 results.json: {path}")

    raise ValueError(f"未知 method: {method}")


def load_baseline_or_rag(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"期望列表格式结果文件: {path}")
    return data


def _normalize_agent_row(r: Dict[str, Any]) -> Dict[str, Any]:
    perf = r.get("performance") or {}
    pred = r.get("prediction")
    if not isinstance(pred, dict):
        pred = {
            "is_violation": r.get("is_violation"),
            "has_risk_flag": r.get("has_risk_flag", False),
        }
    else:
        if "has_risk_flag" not in pred:
            pred = {**pred, "has_risk_flag": pred.get("has_risk_flag", False)}
    return {
        "case_id": r.get("case_id", ""),
        "success": r.get("success", False),
        "metrics": {
            "is_correct": r.get("match", False),
            "type_correct": r.get("type_correct", False),
        },
        "ground_truth": r.get("ground_truth", {}),
        "prediction": pred,
        "quality_metrics": r.get("quality_metrics", {}),
        "performance": {
            "response_time": float(perf.get("response_time", 0) or 0),
            "input_tokens": int(perf.get("input_tokens", 0) or 0),
            "output_tokens": int(perf.get("output_tokens", 0) or 0),
        },
    }


def parse_agent_file(
    path: Path,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    读取 Agent 的 results.json：逐条结果 + 顶层 metadata / metrics（评测脚本汇总）。
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("results")
    if not isinstance(rows, list):
        raise ValueError(f"Agent 结果缺少 results 列表: {path}")
    normalized = [_normalize_agent_row(r) for r in rows]
    meta = data.get("metadata")
    if meta is not None and not isinstance(meta, dict):
        meta = None
    fmetrics = data.get("metrics")
    if fmetrics is not None and not isinstance(fmetrics, dict):
        fmetrics = None
    return normalized, meta, fmetrics


def load_agent(path: Path) -> List[Dict[str, Any]]:
    rows, _, _ = parse_agent_file(path)
    return rows


def load_for_method(path: Path, method: str) -> List[Dict[str, Any]]:
    if method == "agent":
        return load_agent(path)
    return load_baseline_or_rag(path)


def format_agent_file_metrics(
    metadata: Optional[Dict[str, Any]],
    file_metrics: Optional[Dict[str, Any]],
) -> str:
    """将 Agent results.json 顶层的 metadata / metrics 格式化为 Markdown。"""
    header = "## Agent 专项指标（results.json 顶层汇总）"
    intro = (
        "以下字段由 `run_agent_eval.py` 在写出 `results.json` 时汇总，与上表中共用的 "
        "`BaselineEvaluator.calculate_metrics` 口径并存；**validation / reflection / advanced_* "
        "等仅 Agent 流水线具备。**"
    )

    if not metadata and not file_metrics:
        return (
            f"{header}\n\n"
            f"{intro}\n\n"
            "*本结果文件中未包含顶层 `metadata` / `metrics`，无法展示 Agent 脚本汇总。*\n"
        )

    lines: List[str] = [header, "", intro, ""]

    if metadata:
        lines.append("### metadata")
        for key in ("timestamp", "method", "total_cases"):
            if key in metadata:
                lines.append(f"- **{key}**: {metadata[key]}")
        lines.append("")

    if not file_metrics:
        lines.append("### metrics")
        lines.append("*（文件中无顶层 `metrics` 字段）*")
        return "\n".join(lines) + "\n"

    lines.append("### metrics（顶层标量）")

    def fmt_scalar(name: str, v: Any) -> str:
        if isinstance(v, bool):
            return str(v)
        if isinstance(v, (int, float)):
            if name in (
                "error_rate",
                "accuracy",
                "violation_type_accuracy",
                "validation_passed_rate",
                "reflection_triggered_rate",
            ):
                fv = float(v)
                return f"{fv:.6f}（{fv * 100:.2f}%）"
            if isinstance(v, float):
                return f"{v:.4f}"
            return str(v)
        return str(v)

    flat_order = (
        "total",
        "successful",
        "error_rate",
        "accuracy",
        "violation_type_accuracy",
        "validation_passed_rate",
        "reflection_triggered_rate",
    )
    for key in flat_order:
        if key in file_metrics:
            lines.append(f"- **{key}**: {fmt_scalar(key, file_metrics[key])}")

    for key in sorted(file_metrics.keys()):
        if key in flat_order or key in ("quality_metrics", "advanced_metrics_summary", "performance"):
            continue
        lines.append(f"- **{key}**: {file_metrics[key]}")

    qm = file_metrics.get("quality_metrics")
    if isinstance(qm, dict) and qm:
        lines.append("")
        lines.append("### metrics.quality_metrics")
        for k in sorted(qm.keys()):
            lines.append(f"- **{k}**: {qm[k]}")

    adv = file_metrics.get("advanced_metrics_summary")
    if isinstance(adv, dict) and adv:
        lines.append("")
        lines.append("### metrics.advanced_metrics_summary")
        for k in sorted(adv.keys()):
            v = adv[k]
            if isinstance(v, (int, float)):
                lines.append(f"- **{k}**: {float(v):.4f}")
            else:
                lines.append(f"- **{k}**: {v}")

    perf = file_metrics.get("performance")
    if isinstance(perf, dict) and perf:
        lines.append("")
        lines.append("### metrics.performance")
        for k in sorted(perf.keys()):
            lines.append(f"- **{k}**: {perf[k]}")

    return "\n".join(lines) + "\n"


def dedup_by_case_id_last(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        cid = r.get("case_id", "")
        by_id[cid] = r
    return [by_id[k] for k in sorted(by_id.keys())]


def agreement_patterns(
    loaded: Dict[str, Tuple[str, List[Dict[str, Any]]]],
) -> Optional[str]:
    if len(loaded) < 2:
        return None

    def ok_success_metrics(row: Dict[str, Any]) -> bool:
        if not row.get("success"):
            return False
        return bool(row.get("metrics", {}).get("is_correct"))

    sets = {}
    for key, (_, rows) in loaded.items():
        d = {}
        for row in rows:
            d[row.get("case_id", "")] = row
        sets[key] = d

    keys = list(sets.keys())
    common = set.intersection(*(set(sets[k].keys()) for k in keys))
    common.discard("")
    if not common:
        return None

    pat = Counter()
    for cid in sorted(common):
        tpl = tuple(ok_success_metrics(sets[k][cid]) for k in keys)
        pat[tpl] += 1

    labels = {"baseline": "B", "rag": "R", "agent": "A"}
    header = "".join(labels.get(k, k[0].upper()) for k in keys)

    lines = [
        f"（仅在各方法均出现的 `case_id` 上统计，共 {len(common)} 条；成功且二分类正确为 True）",
        f"模式 ({header}_ok): 条数",
    ]
    for tpl, cnt in sorted(pat.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"  {tpl}: {cnt}")
    return "\n".join(lines)


def metrics_for_rows(rows: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    ev = BaselineEvaluator()
    m = ev.calculate_metrics(rows)
    m["_label"] = label
    m["_unique_case_ids"] = len({r.get("case_id") for r in rows if r.get("case_id")})
    m["_rows"] = len(rows)
    return m


def format_metrics_table(metrics_list: List[Dict[str, Any]]) -> str:
    rows = []
    for m in metrics_list:
        rows.append(
            {
                "方法": m.get("_label", ""),
                "记录数": m.get("_rows"),
                "唯一case数": m.get("_unique_case_ids"),
                "成功": m.get("success_cases"),
                "失败": m.get("failed_cases"),
                "Accuracy": f"{m.get('accuracy', 0):.2%}",
                "Type Acc": f"{m.get('type_accuracy', 0):.2%}",
                "F1": f"{m.get('f1_score', 0):.2%}",
                "法律依据均分": f"{m.get('quality_metrics', {}).get('avg_legal_basis_score', 0):.4f}",
                "推理均分": f"{m.get('quality_metrics', {}).get('avg_reasoning_score', 0):.4f}",
                "平均耗时s": m.get("performance", {}).get("avg_response_time"),
            }
        )
    headers = list(rows[0].keys()) if rows else []
    lines = [" | ".join(headers), " | ".join("---" for _ in headers)]
    for row in rows:
        lines.append(" | ".join(str(row[h]) for h in headers))
    return "\n".join(lines)


def list_method_runs(method: str, limit: int) -> None:
    root = _project_root() / "results" / method
    if not root.is_dir():
        print(f"[错误] 目录不存在: {root}")
        sys.exit(1)
    dirs = valid_run_dirs(method)[:limit]
    print(f"{method} 运行目录（新在前，最多 {limit} 个）:\n")
    if not dirs:
        print("  (无)")
        return
    for d in dirs:
        print(f"  {d.relative_to(_project_root())}")


def _interactive_pick_dir(method: str, title_zh: str) -> Optional[Path]:
    dirs = valid_run_dirs(method)
    print(f"\n=== {title_zh} — results/{method}/ ===")
    if not dirs:
        print("  (无可用运行目录，输入 0 跳过)")
        return None
    for i, d in enumerate(dirs, 1):
        print(f"  [{i}] {d.name}")
    print("  [0] 跳过（不参与对比）")
    while True:
        try:
            s = input("请选择序号: ").strip()
        except EOFError:
            return None
        if not s:
            continue
        if not re.match(r"^\d+$", s):
            print("请输入非负整数。")
            continue
        n = int(s)
        if n == 0:
            return None
        if 1 <= n <= len(dirs):
            return dirs[n - 1]
        print(f"请输入 0～{len(dirs)}。")


def interactive_collect_specs(
    existing: List[Tuple[str, str, str]],
) -> List[Tuple[str, str, str]]:
    """
    交互补全 specs。existing 为 CLI 已解析的 (method, 目录名, label)。
    无 CLI 时依次提示 baseline / rag / agent；不足两路则报错退出。
    仅有一路 CLI 时，对未指定的 method 继续提示直到凑满两路。
    """
    if not sys.stdin.isatty():
        print("[错误] 非交互环境无法逐项选择，请至少传入两路 --baseline / --rag / --agent（可用短目录名）。")
        sys.exit(1)

    order = (
        ("baseline", "Baseline", "Baseline"),
        ("rag", "RAG", "RAG"),
        ("agent", "Agent", "Agent"),
    )
    specs = list(existing)
    have = {m for m, _, _ in specs}

    if not specs:
        print("未指定结果路径：进入交互模式（序号选 results/<方法>/ 下文件夹；短目录名即文件夹名）。")
        for method, zh, label in order:
            p = _interactive_pick_dir(method, zh)
            if p is not None:
                specs.append((method, p.name, label))
                have.add(method)
        if len(specs) < 2:
            print("[错误] 至少选择两路结果（非跳过）。")
            sys.exit(1)
        return specs

    if len(specs) >= 2:
        return specs

    print("当前不足两路，请继续选择。")
    for method, zh, label in order:
        if method in have:
            continue
        p = _interactive_pick_dir(method, zh)
        if p is not None:
            specs.append((method, p.name, label))
            have.add(method)
        if len(specs) >= 2:
            break

    if len(specs) < 2:
        print("[错误] 至少再选一路结果。")
        sys.exit(1)
    return specs


def normalize_compare_output_name(name: str) -> Path:
    """文件名 -> results/compare 下的 .md 路径。"""
    name = name.strip()
    if not name:
        name = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    if not name.lower().endswith(".md"):
        name = name + ".md"
    safe = re.sub(r'[<>:"/\\|?*]', "_", name)
    out_dir = _project_root() / "results" / "compare"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / safe


def run_compare(
    specs: List[Tuple[str, str, str]],
    model_key: Optional[str],
) -> Tuple[str, Dict[str, Tuple[str, Path, List[Dict[str, Any]]]]]:
    resolved: Dict[str, Tuple[str, Path, List[Dict[str, Any]]]] = {}
    agent_meta: Optional[Dict[str, Any]] = None
    agent_file_metrics: Optional[Dict[str, Any]] = None

    for method, raw, label in specs:
        p = resolve_result_file(raw, method, model_key)
        if p is None:
            continue
        if method == "agent":
            rows, agent_meta, agent_file_metrics = parse_agent_file(p)
        else:
            rows = load_for_method(p, method)
        resolved[method] = (label, p, rows)

    if len(resolved) < 2:
        raise ValueError("至少需要两路有效结果")

    out_lines: List[str] = []
    out_lines.append("# 评测结果对比\n")
    metrics_list: List[Dict[str, Any]] = []
    for method, (label, path, rows) in resolved.items():
        out_lines.append(f"## {label}\n")
        out_lines.append(f"- 文件: `{path.relative_to(_project_root())}`\n")
        m = metrics_for_rows(rows, label)
        metrics_list.append(m)
        m_dedup = metrics_for_rows(dedup_by_case_id_last(rows), f"{label}(唯一case)")
        metrics_list.append(m_dedup)

    out_lines.append("## 指标汇总（与 BaselineEvaluator.calculate_metrics 一致：准确率分母为成功样本）\n")
    out_lines.append(
        format_metrics_table([x for x in metrics_list if "(唯一case)" not in str(x.get("_label", ""))])
    )
    out_lines.append("\n")
    out_lines.append("### 去重后（每个 case_id 只保留最后一条）\n")
    out_lines.append(
        format_metrics_table([x for x in metrics_list if "(唯一case)" in str(x.get("_label", ""))])
    )
    out_lines.append("\n")

    if "agent" in resolved:
        agent_section = format_agent_file_metrics(agent_meta, agent_file_metrics)
        if agent_section.strip():
            out_lines.append(agent_section)

    agr = agreement_patterns({k: (v[0], v[2]) for k, v in resolved.items()})
    if agr:
        out_lines.append("## 多路一致模式（成功且二分类正确）\n")
        out_lines.append(agr + "\n")

    text = "\n".join(out_lines)
    return text, resolved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="对比 Baseline / RAG / Agent 评测结果；短名=results/<方法>/<目录名>；无参时交互选择。"
    )
    parser.add_argument(
        "--baseline",
        type=str,
        default=None,
        help="Baseline：运行目录短名、或 results/... 相对路径、或 *_results.json",
    )
    parser.add_argument("--rag", type=str, default=None, help="RAG：运行目录短名或路径或 results.json")
    parser.add_argument("--agent", type=str, default=None, help="Agent：运行目录短名或路径或 results.json")
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Baseline 目录下多模型时指定 key（如 qwen-8b）",
    )
    parser.add_argument(
        "--name",
        "-n",
        type=str,
        default=None,
        help="保存到 results/compare/<文件名>.md（只需文件名；默认 .md）",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="可选：完整输出路径（覆盖 --name 的默认目录）",
    )
    parser.add_argument(
        "--list",
        type=str,
        choices=["baseline", "rag", "agent"],
        default=None,
        help="列出该方法下含结果文件的运行子目录并退出",
    )
    parser.add_argument(
        "--list-limit",
        type=int,
        default=50,
        help="与 --list 配合，最多列出多少个目录（默认 50）",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="只打印到终端，不写入文件（即使给了 --name）",
    )
    args = parser.parse_args()

    if args.list:
        list_method_runs(args.list, args.list_limit)
        return

    cli_any = bool(args.baseline or args.rag or args.agent)

    specs: List[Tuple[str, str, str]] = []
    if args.baseline:
        specs.append(("baseline", args.baseline, "Baseline"))
    if args.rag:
        specs.append(("rag", args.rag, "RAG"))
    if args.agent:
        specs.append(("agent", args.agent, "Agent"))

    if len(specs) < 2:
        specs = interactive_collect_specs(specs)

    text, _resolved = run_compare(specs, args.model)
    print(text)

    out_path: Optional[Path] = None
    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = _project_root() / out_path
    elif args.name and not args.no_save:
        out_path = normalize_compare_output_name(args.name)
    elif not cli_any and not args.no_save and sys.stdin.isatty():
        try:
            fn = input("\n输出文件名（仅文件名，保存到 results/compare/，回车默认带时间戳）: ").strip()
        except EOFError:
            fn = ""
        out_path = normalize_compare_output_name(fn)

    if out_path and not args.no_save:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"\n已写入: {out_path.relative_to(_project_root())}")


if __name__ == "__main__":
    main()
