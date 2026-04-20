# 评测结果对比

## Baseline

- 文件: `results\baseline\improved_baseline_full_eval-780__04-18\qwen-8b_results.json`

## RAG

- 文件: `results\rag\improved_rag_full_eval-780__04-18\results.json`

## Agent

- 文件: `results\agent\improved_agent_full_eval-780__04-19\results.json`

## 指标汇总（与 BaselineEvaluator.calculate_metrics 一致：准确率分母为成功样本）

方法 | 记录数 | 唯一case数 | 成功 | 失败 | Accuracy | Type Acc | F1 | 法律依据均分 | 推理均分 | 平均耗时s
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
Baseline | 780 | 718 | 779 | 1 | 89.35% | 73.68% | 91.47% | 0.8411 | 0.8415 | 7.02
RAG | 780 | 718 | 778 | 2 | 89.85% | 74.94% | 92.01% | 0.7321 | 0.8685 | 7.77
Agent | 780 | 718 | 776 | 4 | 86.98% | 71.52% | 89.79% | 0.7035 | 0.8931 | 37.62


### 去重后（每个 case_id 只保留最后一条）

方法 | 记录数 | 唯一case数 | 成功 | 失败 | Accuracy | Type Acc | F1 | 法律依据均分 | 推理均分 | 平均耗时s
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
Baseline(唯一case) | 718 | 718 | 717 | 1 | 88.84% | 72.52% | 90.65% | 0.8421 | 0.8407 | 7.08
RAG(唯一case) | 718 | 718 | 716 | 2 | 89.39% | 73.88% | 91.28% | 0.7297 | 0.8687 | 7.82
Agent(唯一case) | 718 | 718 | 714 | 4 | 86.13% | 70.03% | 88.63% | 0.7032 | 0.8952 | 38.93


## Agent 专项指标（results.json 顶层汇总）

以下字段由 `run_agent_eval.py` 在写出 `results.json` 时汇总，与上表中共用的 `BaselineEvaluator.calculate_metrics` 口径并存；**validation / reflection / advanced_* 等仅 Agent 流水线具备。**

### metadata
- **timestamp**: 2026-04-19 09:36:19
- **method**: Agent (5-node workflow)
- **total_cases**: 780

### metrics（顶层标量）
- **total**: 780
- **successful**: 776
- **error_rate**: 0.005128（0.51%）
- **accuracy**: 0.869845（86.98%）
- **violation_type_accuracy**: 0.729730（72.97%）
- **validation_passed_rate**: 0.953608（95.36%）
- **reflection_triggered_rate**: 0.046392（4.64%）

### metrics.quality_metrics
- **avg_legal_basis_score**: 0.7034793814432989
- **avg_reasoning_score**: 0.8931056701030927

### metrics.advanced_metrics_summary
- **evidence_chain_avg**: 0.4700
- **explainability_avg**: 0.3370
- **legal_citation_avg**: 0.1590
- **overall_avg**: 0.3380
- **remediation_avg**: 0.4030
- **structured_output_avg**: 0.3200

### metrics.performance
- **avg_response_time**: 37.62

## 多路一致模式（成功且二分类正确）

（仅在各方法均出现的 `case_id` 上统计，共 718 条；成功且二分类正确为 True）
模式 (BRA_ok): 条数
  (True, True, True): 590
  (False, False, False): 50
  (True, True, False): 35
  (False, False, True): 16
  (True, False, False): 10
  (False, True, False): 8
  (False, True, True): 7
  (True, False, True): 2
