"""
数据预处理脚本
将三个方法的结果文件合并为一个JSON，供看板使用
"""
import json
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
OUTPUT_DIR = Path(__file__).parent / "data"


def load_eval_dataset():
    """加载eval数据集，获取原始案例描述（适配v4格式）"""
    eval_path = DATA_DIR / "eval" / "eval_dataset_v4_final.jsonl"
    cases = {}
    with open(eval_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            case_id = data.get("id", "")
            gt = data.get("ground_truth", {})
            inp = data.get("input", {})
            cases[case_id] = {
                "case_description": inp.get("case_description", ""),
                "meta": {
                    "case_id": case_id,
                    "is_violation": gt.get("is_violation", False),
                    "violation_type": gt.get("violation_type", ""),
                    "platform": inp.get("platform", ""),
                    "scenario": "",
                    "complexity": "",
                    "region": data.get("region", ""),
                }
            }
    return cases


def load_baseline_results():
    """加载Baseline结果"""
    path = RESULTS_DIR / "baseline" / "20260418_021531" / "qwen-8b_results.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    results = {}
    for item in data:
        case_id = item.get("case_id", "")
        results[case_id] = {
            "success": item.get("success", False),
            "llm_response": item.get("llm_response", ""),
            "prediction": item.get("prediction", {}),
            "is_correct": item.get("metrics", {}).get("is_correct", False),
            "type_correct": item.get("metrics", {}).get("type_correct", False),
            "match_details": item.get("metrics", {}).get("match_details", {}),
            "quality_metrics": item.get("quality_metrics", {}),
            "performance": item.get("performance", {})
        }
    return results


def load_rag_results():
    """加载RAG结果"""
    path = RESULTS_DIR / "rag" / "20260418_021628" / "results.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    results = {}
    for item in data:
        case_id = item.get("case_id", "")
        results[case_id] = {
            "success": item.get("success", False),
            "llm_response": item.get("llm_response", ""),
            "prediction": item.get("prediction", {}),
            "is_correct": item.get("metrics", {}).get("is_correct", False),
            "type_correct": item.get("metrics", {}).get("type_correct", False),
            "match_details": item.get("metrics", {}).get("match_details", {}),
            "quality_metrics": item.get("quality_metrics", {}),
            "retrieval_info": item.get("retrieval_info", {}),
            "performance": item.get("performance", {})
        }
    return results


def load_agent_results():
    """加载Agent结果"""
    path = RESULTS_DIR / "agent" / "20260418_113740" / "results.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    results_list = data.get("results", [])
    results = {}
    for item in results_list:
        case_id = item.get("case_id", "")
        results[case_id] = {
            "success": item.get("success", False),
            "reasoning_chain": item.get("reasoning_chain", []),
            "prediction": {
                "is_violation": item.get("is_violation"),
                "violation_type": item.get("violation_type", ""),
                "confidence": item.get("confidence", 0),
                "legal_basis": item.get("legal_basis", ""),
                "reasoning": "\n".join(item.get("reasoning_chain", []))
            },
            "is_correct": item.get("match", False),
            "type_correct": item.get("type_correct", False),
            "match_details": item.get("match_details", {}),
            "quality_metrics": item.get("quality_metrics", {}),
            "remediation": item.get("remediation", {}),
            "reflection_count": item.get("reflection_count", 0),
            "performance": item.get("performance", {})
        }
    return results


def merge_data():
    """合并所有数据"""
    print("加载eval数据集...")
    eval_cases = load_eval_dataset()

    print("加载Baseline结果...")
    baseline = load_baseline_results()

    print("加载RAG结果...")
    rag = load_rag_results()

    print("加载Agent结果...")
    agent = load_agent_results()

    # 合并数据
    merged = []
    violation_types = set()

    for case_id in sorted(eval_cases.keys()):
        eval_data = eval_cases.get(case_id, {})
        meta = eval_data.get("meta", {})

        # 记录违规类型
        vtype = meta.get("violation_type", "")
        if vtype:
            violation_types.add(vtype)

        case_data = {
            "case_id": case_id,
            "case_description": eval_data.get("case_description", ""),
            "ground_truth": {
                "is_violation": meta.get("is_violation", False),
                "violation_type": meta.get("violation_type", ""),
                "platform": meta.get("platform", ""),
                "scenario": meta.get("scenario", ""),
                "complexity": meta.get("complexity", "")
            },
            "baseline": baseline.get(case_id, {"success": False}),
            "rag": rag.get(case_id, {"success": False}),
            "agent": agent.get(case_id, {"success": False})
        }
        merged.append(case_data)

    # 构建索引信息
    index = {
        "total": len(merged),
        "violation_types": sorted(list(violation_types)),
        "filters": {
            "error_types": [
                {"value": "all", "label": "全部"},
                {"value": "baseline_error", "label": "Baseline错误"},
                {"value": "rag_error", "label": "RAG错误"},
                {"value": "agent_error", "label": "Agent错误"},
                {"value": "inconsistent", "label": "三者不一致"}
            ],
            "violation_types": [{"value": "all", "label": "全部"}] +
                [{"value": vt, "label": vt} for vt in sorted(violation_types)]
        }
    }

    output = {
        "index": index,
        "cases": merged
    }

    # 保存
    output_path = OUTPUT_DIR / "merged.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"数据合并完成，共 {len(merged)} 条案例")
    print(f"违规类型: {sorted(violation_types)}")
    print(f"输出文件: {output_path}")
    return output_path


if __name__ == "__main__":
    merge_data()
