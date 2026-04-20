****

# CLAUDE_CODE_GUIDE_V2: P0/P1 Bug Fix & Evaluation Upgrade

> 代码审查后的修复任务指南
> 数据集: eval_dataset_v4_final.jsonl (780条 = 500违规 + 280合规)
> 日期: 2026年4月

------

## 修复优先级总览

| 优先级   | 任务                     | 文件                                        | 问题            |
| :------- | :----------------------- | :------------------------------------------ | :-------------- |
| **P0-1** | Eval脚本适配v4 schema    | 3个eval脚本 + evaluator                     | 会直接crash     |
| **P0-2** | Prompt违规类型更新       | prompt_template.py (baseline + rag + agent) | 类型不匹配      |
| **P0-3** | 法条检索F1评测实现       | 新建 legal_retrieval_evaluator.py           | 核心指标缺失    |
| **P1-1** | BM25中文分词修复         | retriever.py                                | BM25对中文无效  |
| **P1-2** | IntentAnalyzer关键词扩充 | intent_analyzer.py                          | 74%案例无法识别 |

------

## P0-1: Eval脚本适配v4 Schema

## 问题

v4数据集结构:

```
json{
  "id": "CASE_0001",
  "input": {"case_description": "...", "platform": "...", "goods_or_service": "..."},
  "ground_truth": {
    "is_violation": true,
    "violation_type": "不明码标价",
    "qualifying_articles": [{"law": "价格法", "article": "第十三条", "article_key": "价格法_十三"}],
    "penalty_articles": [...],
    "legal_analysis_reference": "...",
    "penalty_result": "..."
  }
}
```

旧脚本期望的结构:

```
json{
  "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "meta": {"case_id": "...", "is_violation": true, "violation_type": "..."}
}
```

## 修复方案: 创建 `src/evaluation/dataset_adapter.py`

```
python"""
数据集适配器 — 将 eval_dataset_v4 格式转换为各评测脚本期望的格式
同时提供直接读取v4字段的工具函数
"""
import json
from typing import List, Dict, Any, Optional
from pathlib import Path


class DatasetAdapter:
    """v4数据集适配器"""

    def __init__(self, eval_path: str):
        self.eval_path = eval_path
        self.cases = self._load_v4(eval_path)

    def _load_v4(self, path: str) -> List[Dict]:
        """加载v4格式数据集"""
        cases = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    cases.append(json.loads(line))
        return cases

    def to_legacy_format(self, limit: Optional[int] = None) -> List[Dict]:
        """
        转换为旧格式（兼容现有 BaselineEvaluator / RAGEvaluator / AgentCoordinator）

        旧格式:
        {
          "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "案例描述"}
          ],
          "meta": {
            "case_id": "CASE_0001",
            "is_violation": true,
            "violation_type": "不明码标价"
          }
        }
        """
        cases = self.cases[:limit] if limit else self.cases
        legacy = []
        for case in cases:
            gt = case['ground_truth']
            legacy.append({
                "messages": [
                    {"role": "system", "content": "你是一名价格合规分析专家。"},
                    {"role": "user", "content": case['input']['case_description']}
                ],
                "meta": {
                    "case_id": case['id'],
                    "is_violation": gt['is_violation'],
                    "violation_type": gt.get('violation_type') or '无违规',
                    # 新增字段（向后兼容，旧代码不读也不报错）
                    "qualifying_articles": gt.get('qualifying_articles', []),
                    "penalty_articles": gt.get('penalty_articles', []),
                    "platform": case['input'].get('platform'),
                    "source_type": case.get('source_type'),
                }
            })
        return legacy

    def get_ground_truth_map(self) -> Dict[str, Dict]:
        """
        构建 case_id → ground_truth 的映射
        供 GroundTruthExtractor 和 LegalRetrievalEvaluator 使用
        """
        gt_map = {}
        for case in self.cases:
            case_id = case['id']
            gt = case['ground_truth']
            gt_map[case_id] = {
                'is_violation': gt['is_violation'],
                'violation_type': gt.get('violation_type'),
                'qualifying_article_keys': [
                    a['article_key'] for a in gt.get('qualifying_articles', [])
                ],
                'qualifying_articles_full': gt.get('qualifying_articles', []),
                'penalty_article_keys': [
                    a['article_key'] for a in gt.get('penalty_articles', [])
                ],
            }
        return gt_map

    def get_case_by_id(self, case_id: str) -> Optional[Dict]:
        """根据ID获取单条case"""
        for case in self.cases:
            if case['id'] == case_id:
                return case
        return None

    def get_statistics(self) -> Dict:
        """数据集统计信息"""
        violations = [c for c in self.cases if c['ground_truth']['is_violation']]
        compliants = [c for c in self.cases if not c['ground_truth']['is_violation']]

        from collections import Counter
        vtype_dist = Counter(
            c['ground_truth'].get('violation_type', '?') for c in violations
        )
        qual_counts = [
            len(c['ground_truth'].get('qualifying_articles', []))
            for c in violations
        ]

        return {
            'total': len(self.cases),
            'violations': len(violations),
            'compliants': len(compliants),
            'violation_type_distribution': dict(vtype_dist.most_common()),
            'avg_qualifying_articles': sum(qual_counts) / len(qual_counts) if qual_counts else 0,
            'violations_with_qualifying_articles': sum(1 for q in qual_counts if q > 0),
        }
```

## 修改3个eval脚本的数据加载部分

在每个 `run_*_eval.py` 中，替换数据加载逻辑:

```
python# === 替换原来的 load_eval_data / load_eval_cases 调用 ===

from src.evaluation.dataset_adapter import DatasetAdapter

# 加载v4数据集并转换
adapter = DatasetAdapter(args.eval_path)  # 或 args.eval_data
eval_cases = adapter.to_legacy_format(limit=args.limit)
gt_map = adapter.get_ground_truth_map()

# 打印统计
stats = adapter.get_statistics()
print(f"数据集: {stats['total']} 条 ({stats['violations']} 违规 + {stats['compliants']} 合规)")
print(f"有定性法条的违规案例: {stats['violations_with_qualifying_articles']}/{stats['violations']}")
```

**具体修改位置**:

1. `run_baseline_eval.py` 第331行: 替换 `evaluator.load_eval_data(args.eval_path, limit=args.limit)`
2. `run_rag_eval.py` 第101行: 替换 `evaluator.load_eval_data(args.eval_data, limit=args.limit)`
3. `run_agent_eval.py` 第348行: 替换 `load_eval_cases(args.eval_data, args.limit)`

同时更新默认 `--eval-path` / `--eval-data` 参数值:

```
python# 旧:
default='data/eval/eval_159.jsonl'
# 新:
default='data/eval/eval_dataset_v4_final.jsonl'
```

## GroundTruthExtractor 适配

当前 `GroundTruthExtractor` 也需要适配v4格式。最简单的方式是让它接受 `gt_map`:

```
python# 在 ground_truth_extractor.py 中添加:

class GroundTruthExtractor:
    def __init__(self, eval_data_path: str = None, gt_map: dict = None):
        self.ground_truths = {}
        if gt_map:
            # 直接使用v4的ground truth map
            self.ground_truths = gt_map
        elif eval_data_path:
            self.build_ground_truth_dict()

    def build_ground_truth_dict(self):
        """兼容旧格式的构建方法"""
        # ... 保留原有逻辑 ...
        pass

    def get_ground_truth(self, case_id: str):
        """获取单条case的ground truth"""
        gt = self.ground_truths.get(case_id)
        if not gt:
            return None

        # 兼容新旧两种格式
        if 'qualifying_article_keys' in gt:
            # v4格式
            return {
                'ground_truth_laws': gt['qualifying_article_keys'],
                'is_violation': gt['is_violation'],
                'violation_type': gt.get('violation_type'),
            }
        else:
            # 旧格式
            return gt
```

在3个eval脚本中改为:

```
python
gt_extractor = GroundTruthExtractor(gt_map=gt_map)
```

## 成功标准

```
text✅ python run_baseline_eval.py --eval-path data/eval/eval_dataset_v4_final.jsonl --limit 5 不报错
✅ python run_rag_eval.py --eval-data data/eval/eval_dataset_v4_final.jsonl --limit 5 不报错
✅ python run_agent_eval.py --eval-data data/eval/eval_dataset_v4_final.jsonl --limit 5 不报错
✅ 每条result中包含 case_id, ground_truth, prediction 字段
```

------

## P0-2: Prompt违规类型更新

## 问题

当前prompt中的违规类型 (prompt_template.py 第27-33行):

```
text
虚构原价 / 价格误导 / 虚假折扣 / 要素缺失 / 其他 / 无违规
```

v4数据集中的实际分布:

```
text不明码标价:     228 (45.6%)   ← prompt里根本没有
政府定价违规:   120 (24.0%)   ← prompt里根本没有
标价外加价:      73 (14.6%)   ← prompt里根本没有
误导性价格标示:  49 (9.8%)
虚假价格比较:     5 (1.0%)
变相提高价格:     6 (1.2%)
虚假折扣:         2 (0.4%)
不履行价格承诺:   1 (0.2%)
哄抬价格:         1 (0.2%)
未识别:          15 (3.0%)
```

84% 的案例的违规类型在prompt中找不到对应选项。

## 修复方案

需要修改 **3个地方** 的违规类型定义:

## 1. `src/baseline/prompt_template.py` — Baseline的system prompt

````
pythonSYSTEM_PROMPT = """你是一名价格合规分析专家，熟悉《中华人民共和国价格法》、《明码标价和禁止价格欺诈规定》、《价格违法行为行政处罚规定》等相关法律法规。你的任务是根据给定的案例事实，分析经营行为是否存在价格违法行为，并提供专业的法律依据和结论。

请严格按照以下JSON格式输出你的分析结果：

```json
{
  "is_violation": true/false,
  "violation_type": "违规类型",
  "confidence": 0.0-1.0,
  "reasoning": "详细的分析依据和法律推理过程",
  "legal_basis": "相关法律条文（请引用具体条款号）",
  "cited_articles": [
    {"law": "法律名称", "article": "第X条第X项"}
  ]
}
```

**违规类型说明**（必须从以下类型中选择一个）：
- **不明码标价**：未按规定标明价格、标价签不规范、缺少品名/计价单位/规格等必要信息
- **政府定价违规**：超出政府指导价/政府定价浮动范围、不执行政府定价
- **标价外加价**：在标价之外额外收取未标明的费用
- **误导性价格标示**：虚构原价、虚假折扣、虚假价格比较、利用虚假或使人误解的价格手段
- **变相提高价格**：抬高等级、以次充好、短斤少两等方式变相提价
- **哄抬价格**：捏造散布涨价信息、囤积居奇推高价格
- **其他价格违法**：不属于以上类型的其他价格违法行为
- **无违规**：合规经营，不存在价格违法行为

**注意事项**：
1. 如果是合规案例，violation_type设置为"无违规"
2. legal_basis需要引用具体的法律条款号（如"《价格法》第十三条第一款"）
3. cited_articles列出所有引用的法条，每条包含law和article字段
4. 不要引用你不确定的法条，宁可少引不要错引

请确保输出是有效的JSON格式。"""
````

## 2. `src/rag/prompt_template.py` — RAG的system prompt

将 `RAG_SYSTEM_PROMPT` 中的违规类型说明替换为与上面相同的内容。同时增加 `cited_articles` 字段到输出格式中。

## 3. `src/agents/reasoning_engine.py` — Agent的system prompt

将 `_build_system_prompt` 方法中（约第82-99行）的违规类型分类替换为:

```
python# 替换原来的 "**违规类型分类**" 部分:

"""
**违规类型分类**（必须从以下类型中选择一个）：
- **不明码标价**：未按规定标明价格、标价签不规范、缺少品名/计价单位/规格等必要信息
- **政府定价违规**：超出政府指导价/政府定价浮动范围、不执行政府定价
- **标价外加价**：在标价之外额外收取未标明的费用
- **误导性价格标示**：虚构原价、虚假折扣、虚假价格比较、利用虚假或使人误解的价格手段
- **变相提高价格**：抬高等级、以次充好、短斤少两等方式变相提价
- **哄抬价格**：捏造散布涨价信息、囤积居奇推高价格
- **其他价格违法**：不属于以上类型的其他价格违法行为
- **无违规**：合规经营，不存在价格违法行为

**判断示例**：
1. "超市货架上7瓶洗手液未标明价格" → 不明码标价
2. "停车场收费超出政府指导价标准" → 政府定价违规
3. "收取未标明的50元包装费" → 标价外加价
4. "标注原价1680元但从未以此价格销售" → 误导性价格标示
5. "注水肉冒充正常肉销售" → 变相提高价格
"""
```

同时更新 Agent 的 JSON 输出格式:

```
json{
  "reasoning_chain": ["步骤1: ...", "步骤2: ...", ...],
  "is_violation": true/false,
  "violation_type": "必须是上述类型之一",
  "legal_basis": "《法律名称》第X条",
  "cited_articles": [
    {"law": "价格法", "article": "第十三条"}
  ],
  "confidence": 0.0-1.0
}
```

## 4. 响应解析器也需要更新

在 `ResponseParser.compare_prediction_with_truth` 中，如果使用 smart matching，需要更新类型映射:

```
python# 新旧类型映射（用于兼容旧数据或模型输出不精确时的模糊匹配）
TYPE_ALIASES = {
    '要素缺失': '不明码标价',
    '价格误导': '误导性价格标示',
    '虚构原价': '误导性价格标示',
    '虚假折扣': '误导性价格标示',
    '虚假宣传': '误导性价格标示',
    '价格欺诈': '误导性价格标示',
    '不执行政府定价': '政府定价违规',
    '超政府指导价': '政府定价违规',
    '合规': '无违规',
    '不违规': '无违规',
}
```

## 成功标准

```
text✅ Baseline/RAG/Agent 的 system prompt 中违规类型覆盖了 v4 数据集中 95%+ 的类型
✅ 模型输出的 violation_type 能与 ground truth 做精确匹配
✅ 新增了 cited_articles 输出字段，为法条F1评测提供数据
```

------

## P0-3: 法条检索 Precision/Recall/F1 评测实现

## 问题

当前评测只有 Binary Accuracy 和启发式 Legal Basis Quality。缺少基于 `qualifying_articles.article_key` 的精确法条检索评测。这是 Baseline vs RAG vs Agent 对比的核心区分度指标。

## 创建 `src/evaluation/legal_retrieval_evaluator.py`

```
python"""
法条检索评测器
基于 eval_dataset_v4 的 qualifying_articles.article_key 计算 Precision / Recall / F1

用法:
    evaluator = LegalRetrievalEvaluator(gt_map)
    # 对每条case的LLM输出提取predicted_keys
    predicted_keys = evaluator.extract_article_keys_from_output(llm_output_text)
    # 单条评分
    score = evaluator.evaluate_single(case_id, predicted_keys)
    # 批量评分
    batch_scores = evaluator.evaluate_batch(results_list)
"""

import re
import json
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict


class LegalRetrievalEvaluator:
    """法条检索评测器"""

    def __init__(self, gt_map: Dict[str, Dict]):
        """
        Args:
            gt_map: DatasetAdapter.get_ground_truth_map() 的输出
                    {case_id: {"qualifying_article_keys": [...], ...}}
        """
        self.gt_map = gt_map

        # 预处理: 标准化所有ground truth keys
        self.gt_keys_map = {}
        for case_id, gt in gt_map.items():
            raw_keys = gt.get('qualifying_article_keys', [])
            self.gt_keys_map[case_id] = self._normalize_keys(raw_keys)

    # ========================================================
    # 1. 从LLM输出中提取法条引用
    # ========================================================

    def extract_article_keys_from_output(self, output_text: str) -> List[str]:
        """
        从LLM的自然语言输出中提取法条引用，转换为标准化article_key

        支持两种输入:
        1. 结构化JSON中的 cited_articles 字段
        2. 自然语言中的 《法律名》第X条 模式
        """
        keys = set()

        # 方式1: 尝试从JSON中提取 cited_articles
        try:
            # 提取JSON块
            json_match = re.search(r'\{[^{}]*"cited_articles"[^{}]*\}', output_text, re.DOTALL)
            if not json_match:
                json_match = re.search(r'```json\s*(.*?)\s*```', output_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1) if '```' in json_match.group(0) else json_match.group(0)
                # 尝试修复不完整的JSON
                parsed = json.loads(json_str)
                for article in parsed.get('cited_articles', []):
                    law = article.get('law', '')
                    art = article.get('article', '')
                    key = self._law_article_to_key(law, art)
                    if key:
                        keys.add(key)
        except (json.JSONDecodeError, AttributeError):
            pass

        # 方式2: 正则提取 《法律名》第X条
        patterns = [
            # 《价格法》第十三条第一款
            r'《([^》]+)》\s*第([一二三四五六七八九十百零\d]+)条(?:\s*第([一二三四五六七八九十百零\d]+)(?:款|项))?',
            # 《明码标价和禁止价格欺诈规定》第十九条第三项
            r'《([^》]+)》\s*第([一二三四五六七八九十百零\d]+)条(?:\s*第([一二三四五六七八九十百零\d]+)(?:款|项))?',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, output_text):
                law_name = self._normalize_law_name(match.group(1))
                article = match.group(2)
                sub = match.group(3) if match.lastindex >= 3 and match.group(3) else None
                key = f"{law_name}_{article}"
                if sub:
                    key += f"_{sub}"
                keys.add(key)

        # 方式3: 从 legal_basis 字段直接提取（如果是结构化输出）
        try:
            parsed = json.loads(output_text) if output_text.strip().startswith('{') else None
            if parsed:
                lb = parsed.get('legal_basis', '')
                for pattern in patterns:
                    for match in re.finditer(pattern, lb):
                        law_name = self._normalize_law_name(match.group(1))
                        article = match.group(2)
                        sub = match.group(3) if match.lastindex >= 3 and match.group(3) else None
                        key = f"{law_name}_{article}"
                        if sub:
                            key += f"_{sub}"
                        keys.add(key)
        except (json.JSONDecodeError, AttributeError):
            pass

        return self._normalize_keys(list(keys))

    # ========================================================
    # 2. 单条评分
    # ========================================================

    def evaluate_single(
        self,
        case_id: str,
        predicted_keys: List[str],
        mode: str = 'both'
    ) -> Dict:
        """
        评估单条case的法条检索质量

        Args:
            case_id: 案例ID
            predicted_keys: 模型预测的法条key列表
            mode: 'strict' | 'relaxed' | 'both'

        Returns:
            dict: 包含 strict 和/或 relaxed 粒度的 P/R/F1
        """
        gt_keys = self.gt_keys_map.get(case_id, [])

        if not gt_keys:
            # 合规案例或无ground truth → 跳过法条评分
            return {
                'case_id': case_id,
                'skipped': True,
                'reason': 'no_qualifying_articles_in_ground_truth'
            }

        pred_normalized = self._normalize_keys(predicted_keys)
        gt_normalized = gt_keys  # 已在__init__中标准化

        result = {'case_id': case_id, 'skipped': False}

        if mode in ('strict', 'both'):
            result['strict'] = self._compute_prf(
                set(pred_normalized),
                set(gt_normalized)
            )

        if mode in ('relaxed', 'both'):
            # Relaxed: 只匹配到"法律名_条"级别，忽略款/项
            pred_relaxed = set(self._to_article_level(k) for k in pred_normalized)
            gt_relaxed = set(self._to_article_level(k) for k in gt_normalized)
            result['relaxed'] = self._compute_prf(pred_relaxed, gt_relaxed)

        result['predicted_keys'] = pred_normalized
        result['ground_truth_keys'] = gt_normalized

        return result

    # ========================================================
    # 3. 批量评分
    # ========================================================

    def evaluate_batch(self, results: List[Dict]) -> Dict:
        """
        批量评估所有case

        Args:
            results: 评测结果列表，每条需包含:
                     - 'case_id': str
                     - 'llm_response' 或 'raw_response' 或 'output': str (LLM原始输出)
                     或
                     - 'predicted_keys': List[str] (已提取的法条keys)

        Returns:
            dict: 宏平均 P/R/F1 + 每条详细评分
        """
        case_scores = []

        for result in results:
            case_id = result.get('case_id', '')

            # 获取predicted_keys
            if 'predicted_keys' in result:
                pred_keys = result['predicted_keys']
            else:
                # 从LLM输出中提取
                output_text = (
                    result.get('llm_response', '') or
                    result.get('raw_response', '') or
                    json.dumps(result.get('output', {}), ensure_ascii=False)
                )
                pred_keys = self.extract_article_keys_from_output(output_text)

            score = self.evaluate_single(case_id, pred_keys)
            case_scores.append(score)

        # 计算宏平均（只计算未跳过的case）
        evaluated = [s for s in case_scores if not s.get('skipped')]
        skipped = [s for s in case_scores if s.get('skipped')]

        summary = {
            'total_cases': len(results),
            'evaluated_cases': len(evaluated),
            'skipped_cases': len(skipped),
        }

        for mode in ('strict', 'relaxed'):
            scores = [s[mode] for s in evaluated if mode in s]
            if scores:
                summary[f'{mode}_macro_precision'] = round(
                    sum(s['precision'] for s in scores) / len(scores), 4
                )
                summary[f'{mode}_macro_recall'] = round(
                    sum(s['recall'] for s in scores) / len(scores), 4
                )
                summary[f'{mode}_macro_f1'] = round(
                    sum(s['f1'] for s in scores) / len(scores), 4
                )
                # 也计算micro（总体TP/FP/FN）
                total_tp = sum(s['tp'] for s in scores)
                total_fp = sum(s['fp'] for s in scores)
                total_fn = sum(s['fn'] for s in scores)
                micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
                micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
                micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0
                summary[f'{mode}_micro_precision'] = round(micro_p, 4)
                summary[f'{mode}_micro_recall'] = round(micro_r, 4)
                summary[f'{mode}_micro_f1'] = round(micro_f1, 4)

        summary['case_scores'] = case_scores

        return summary

    # ========================================================
    # 4. 内部辅助方法
    # ========================================================

    def _compute_prf(self, pred_set: Set[str], gt_set: Set[str]) -> Dict:
        """计算 Precision / Recall / F1"""
        tp = len(pred_set & gt_set)
        fp = len(pred_set - gt_set)
        fn = len(gt_set - pred_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1': round(f1, 4),
            'tp': tp,
            'fp': fp,
            'fn': fn,
        }

    def _normalize_law_name(self, name: str) -> str:
        """标准化法律名称"""
        name = name.replace('中华人民共和国', '')
        # 常见简称映射
        aliases = {
            '价格法': '价格法',
            '禁止价格欺诈行为规定': '禁止价格欺诈行为的规定',
            '禁止价格欺诈行为的规定': '禁止价格欺诈行为的规定',
            '明码标价和禁止价格欺诈规定': '明码标价和禁止价格欺诈规定',
            '价格违法行为行政处罚规定': '价格违法行为行政处罚规定',
            '电子商务法': '电子商务法',
            '消费者权益保护法': '消费者权益保护法',
        }
        return aliases.get(name, name)

    def _normalize_keys(self, keys: List[str]) -> List[str]:
        """标准化article_key列表"""
        normalized = []
        for key in keys:
            # 修复已知的格式问题
            key = key.replace('、', '_')  # "价格法_十三、二" → "价格法_十三_二"
            key = key.rstrip('_')          # "价格法_十三、" → "价格法_十三"
            key = key.rstrip('、')
            if key:
                normalized.append(key)
        return list(set(normalized))  # 去重

    def _to_article_level(self, key: str) -> str:
        """
        转换到条级别（忽略款/项）
        "价格法_十四_四" → "价格法_十四"
        "明码标价和禁止价格欺诈规定_十九_三" → "明码标价和禁止价格欺诈规定_十九"
        """
        parts = key.split('_')
        if len(parts) >= 3:
            # law_article_sub → law_article
            return '_'.join(parts[:2])
        return key


def print_evaluation_summary(summary: Dict, method_name: str = ""):
    """打印评测结果摘要"""
    print(f"\n{'='*60}")
    print(f"法条检索评测结果 {f'({method_name})' if method_name else ''}")
    print(f"{'='*60}")
    print(f"总案例: {summary['total_cases']}")
    print(f"评测案例(有ground truth法条): {summary['evaluated_cases']}")
    print(f"跳过(合规/无法条): {summary['skipped_cases']}")

    for mode in ('strict', 'relaxed'):
        macro_f1 = summary.get(f'{mode}_macro_f1', 0)
        micro_f1 = summary.get(f'{mode}_micro_f1', 0)
        if macro_f1 or micro_f1:
            print(f"\n  [{mode.upper()}]")
            print(f"    Macro  P={summary.get(f'{mode}_macro_precision',0):.2%}  "
                  f"R={summary.get(f'{mode}_macro_recall',0):.2%}  "
                  f"F1={macro_f1:.2%}")
            print(f"    Micro  P={summary.get(f'{mode}_micro_precision',0):.2%}  "
                  f"R={summary.get(f'{mode}_micro_recall',0):.2%}  "
                  f"F1={micro_f1:.2%}")
    print(f"{'='*60}")
```

## 集成到3个eval脚本中

在每个eval脚本的评测完成后，追加法条F1计算:

```
python# === 在所有case评测完成后，追加以下代码 ===

from src.evaluation.legal_retrieval_evaluator import LegalRetrievalEvaluator, print_evaluation_summary

# 初始化法条评测器
legal_evaluator = LegalRetrievalEvaluator(gt_map)

# 计算法条检索F1
legal_summary = legal_evaluator.evaluate_batch(results)
print_evaluation_summary(legal_summary, method_name="Baseline")  # 或 "RAG" / "Agent"

# 保存到结果文件中
# 在save_results时追加:
output_data['legal_retrieval_metrics'] = {
    k: v for k, v in legal_summary.items() if k != 'case_scores'
}
```

## 成功标准

```
text✅ 能从LLM输出中正确提取法条引用（正则 + JSON解析双通道）
✅ strict模式: article_key完全匹配（"价格法_十四_四"）
✅ relaxed模式: 条级别匹配（"价格法_十四" 匹配 "价格法_十四_四"）
✅ 输出包含 Macro P/R/F1 和 Micro P/R/F1
✅ 合规案例（无ground truth法条）自动跳过，不影响平均分
```

------

## P1-1: BM25中文分词修复

## 问题

`src/rag/retriever.py` 第21行:

```
python
self.laws_tokenized = [doc.split() for doc in self.laws_corpus]
```

`str.split()` 按空格分词，中文文本几乎没有空格，导致每个文档被当作一整个token。BM25完全失效。

## 修复

```
python# retriever.py

import jieba

class HybridRetriever:
    def __init__(self, db_path="data/rag/chroma_db", use_reranker=True, use_bm25=True):
        # ... 其他初始化代码不变 ...

        # Build BM25 index for laws
        self.bm25 = None
        self.laws_corpus_ids = []
        if use_bm25:
            all_laws = self.db.laws_collection.get()
            if all_laws and all_laws['documents']:
                self.laws_corpus = all_laws['documents']
                self.laws_corpus_ids = all_laws['ids']
                # 修复: 使用jieba分词替代空格分割
                self.laws_tokenized = [list(jieba.cut(doc)) for doc in self.laws_corpus]
                self.bm25 = BM25Okapi(self.laws_tokenized)

    def retrieve(self, query, laws_k=3, cases_k=3,
                 distance_threshold=0.15, min_k=2, min_rerank_score=0.0):
        # ... 其他代码不变 ...

        # BM25 search (if enabled)
        bm25_law_ids = []
        if self.bm25:
            # 修复: 使用jieba分词
            tokenized_query = list(jieba.cut(query))
            bm25_scores = self.bm25.get_scores(tokenized_query)
            # ... 后续代码不变 ...
```

## 依赖

```
bash
pip install jieba
```

如果已安装 jieba，不需要额外操作。如果环境中没有 jieba:

```
bash# 如果 pip install jieba 不可用，也可以用 pkuseg 或直接用字级别分割作为fallback:
# self.laws_tokenized = [list(doc) for doc in self.laws_corpus]
# 字级别分割不如jieba但远好于空格分割
```

## 成功标准

```
text✅ pip install jieba 成功
✅ HybridRetriever 初始化时能正确分词
✅ BM25检索能返回合理结果（对"未明码标价"查询能检索到价格法第13条）
```

------

## P1-2: IntentAnalyzer关键词扩充

## 问题

当前只检测4种违规类型（虚构原价/虚假折扣/价格误导/要素缺失），但v4数据集中84%的案例类型不在此列。

## 修复

在 `intent_analyzer.py` 的 `_detect_violation_types` 方法中追加:

```
pythondef _detect_violation_types(self, query):
    """规则based检测违规类型"""
    hints = []

    # === 原有4种 ===

    # 虚构原价
    if any(kw in query for kw in ['原价', '从未成交', '无交易记录', '无销售记录', '虚构']):
        hints.append('误导性价格标示')

    # 虚假折扣
    if any(kw in query for kw in ['折扣', '打折', '优惠', '促销', '活动价', '限时', '特价']):
        if any(kw in query for kw in ['虚假', '误导', '不实', '欺骗']):
            hints.append('误导性价格标示')

    # 价格误导
    if any(kw in query for kw in ['宣传', '标注', '展示', '首页']) and \
       any(kw in query for kw in ['实际', '不符', '差异']):
        hints.append('误导性价格标示')

    # === 新增：覆盖v4中高频的类型 ===

    # 不明码标价 (45.6%)
    if any(kw in query for kw in [
        '未标明价格', '未明码标价', '标价签', '未标注', '未标示',
        '未按规定', '计价单位', '不标明', '没有标价', '未张贴',
        '价格标示', '价格公示', '明码标价'
    ]):
        hints.append('不明码标价')

    # 政府定价违规 (24.0%)
    if any(kw in query for kw in [
        '政府指导价', '政府定价', '超出.*?标准', '浮动幅度',
        '发改委', '物价局', '核定价格', '限价', '最高限价',
        '政府.*?价格', '超标准收费'
    ]):
        hints.append('政府定价违规')

    # 标价外加价 (14.6%)
    if any(kw in query for kw in [
        '额外收取', '加收', '另行收取', '标价之外', '多收',
        '反向抹零', '包装费', '服务费', '手续费', '工本费'
    ]):
        hints.append('标价外加价')

    # 变相提高价格 (1.2%)
    if any(kw in query for kw in [
        '以次充好', '短斤少两', '缺斤少两', '抬高等级',
        '掺杂掺假', '注水', '变相提价'
    ]):
        hints.append('变相提高价格')

    # 哄抬价格
    if any(kw in query for kw in [
        '哄抬', '囤积', '涨价信息', '大幅提价', '推高价格'
    ]):
        hints.append('哄抬价格')

    if not hints:
        hints.append('需进一步分析')

    return hints[:3]
```

同时更新 `_generate_hints` 方法:

```
pythondef _generate_hints(self, violation_hints, entities):
    """生成推理提示"""
    hints = []

    hint_map = {
        '误导性价格标示': '关注价格标注是否真实，原价是否有交易记录，折扣计算是否正确',
        '不明码标价': '检查是否按规定明码标价，标价签是否包含品名、计价单位、价格等要素',
        '政府定价违规': '核查收费标准是否在政府指导价/定价范围内',
        '标价外加价': '检查是否存在在标价之外额外收取未标明费用的情况',
        '变相提高价格': '检查是否存在抬高等级、以次充好等变相提价行为',
        '哄抬价格': '核查是否存在捏造散布涨价信息、囤积居奇等行为',
    }

    for vtype in violation_hints:
        if vtype in hint_map:
            hints.append(hint_map[vtype])

    if 'platform' in entities:
        hints.append(f"参考{entities['platform']}平台相关案例")

    return hints
```

## 成功标准

```
text✅ 对"超市7瓶洗手液未标明价格"能识别为"不明码标价"
✅ 对"停车场收费超出政府指导价"能识别为"政府定价违规"
✅ 未识别(需进一步分析)率从 ~74% 降到 <20%
```

------

## 验证流程

全部修改完成后，按以下顺序验证:

```
bash# Step 1: 单元测试 — DatasetAdapter
python -c "
from src.evaluation.dataset_adapter import DatasetAdapter
adapter = DatasetAdapter('data/eval/eval_dataset_v4_final.jsonl')
stats = adapter.get_statistics()
print(stats)
legacy = adapter.to_legacy_format(limit=3)
print(legacy[0].keys())
print(legacy[0]['meta'].keys())
print('DatasetAdapter OK')
"

# Step 2: 单元测试 — LegalRetrievalEvaluator
python -c "
from src.evaluation.dataset_adapter import DatasetAdapter
from src.evaluation.legal_retrieval_evaluator import LegalRetrievalEvaluator
adapter = DatasetAdapter('data/eval/eval_dataset_v4_final.jsonl')
gt_map = adapter.get_ground_truth_map()
evaluator = LegalRetrievalEvaluator(gt_map)
# 测试提取
test_text = '根据《价格法》第十三条和《明码标价和禁止价格欺诈规定》第五条'
keys = evaluator.extract_article_keys_from_output(test_text)
print(f'Extracted keys: {keys}')
# 测试评分
score = evaluator.evaluate_single('CASE_0001', keys)
print(f'Score: {score}')
print('LegalRetrievalEvaluator OK')
"

# Step 3: Pilot test — Baseline (5条)
python scripts/run_baseline_eval.py --models qwen --eval-path data/eval/eval_dataset_v4_final.jsonl --limit 5

# Step 4: Pilot test — RAG (5条)
python scripts/run_rag_eval.py --eval-data data/eval/eval_dataset_v4_final.jsonl --limit 5

# Step 5: Pilot test — Agent (5条)
python scripts/run_agent_eval.py --eval-data data/eval/eval_dataset_v4_final.jsonl --limit 5
```

每步必须通过才进入下一步。全部通过后再全量跑780条。

------

## 文件清单

| 操作     | 文件路径                                      | 说明             |
| :------- | :-------------------------------------------- | :--------------- |
| **新建** | `src/evaluation/dataset_adapter.py`           | v4数据集适配器   |
| **新建** | `src/evaluation/legal_retrieval_evaluator.py` | 法条F1评测器     |
| **修改** | `src/evaluation/ground_truth_extractor.py`    | 支持gt_map输入   |
| **修改** | `src/baseline/prompt_template.py`             | 更新违规类型分类 |
| **修改** | `src/rag/prompt_template.py`                  | 更新违规类型分类 |
| **修改** | `src/agents/reasoning_engine.py`              | 更新违规类型分类 |
| **修改** | `src/rag/retriever.py`                        | jieba分词修复    |
| **修改** | `src/agents/intent_analyzer.py`               | 关键词扩充       |
| **修改** | `scripts/run_baseline_eval.py`                | 适配v4 + 法条F1  |
| **修改** | `scripts/run_rag_eval.py`                     | 适配v4 + 法条F1  |
| **修改** | `scripts/run_agent_eval.py`                   | 适配v4 + 法条F1  |