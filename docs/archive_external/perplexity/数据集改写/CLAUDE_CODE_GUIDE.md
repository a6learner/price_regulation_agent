# Claude Code 任务指南：电商价格合规系统改进

> **给 Claude Code 的上下文说明**：这是一个电商价格合规分析系统的毕业设计项目，当前存在数据集质量问题和Agent架构缺陷，导致Baseline（99.35%）效果反而优于RAG和Agent。以下是经过详细诊断后的改进任务清单，请按优先级逐步执行。

---

## 📋 项目现状（必读背景）

### Architecture
```
方法1: Baseline (纯LLM) → Binary Acc 99.35%, Legal Basis 89.48%, Reasoning 93.00%
方法2: RAG (LLM + 检索增强) → Binary Acc 100%, Legal Basis 82.23% (-7.25%), Reasoning 92.45%
方法3: Agent (6节点工作流) → 开发中，效果待测
```

### Core Problems Diagnosed
1. **测试集同源污染**：753条数据100%由qwen-8b改写，Baseline也用qwen-8b推理 → 同源偏差导致分数虚高
2. **隐性答案泄露**：User Prompt中"经调查核实"段落直接包含调查结论，而非原始证据
3. **评估指标不合理**：Binary Accuracy已触顶99%+，关键词启发式的Legal Basis/Reasoning Score无法区分方法差异
4. **Agent代码架构缺陷**：IntentAnalyzer规则过严、Grader的coverage评分失效、Reflector几乎不触发
5. **违规类型标签混乱**："无违规"/"不违规"/"无"三种写法；"其他"类别占19.3%

### Constraints
- 使用讯飞星辰MaaS API（Qwen3-8B, Qwen3.5-397B, MiniMax-M2.5）
- Claude Code Pro plan，token有限，需要高效利用
- 项目目录: `price_regulation_agent/`
- 向量库: ChromaDB, 嵌入模型: BAAI/bge-small-zh-v1.5, 重排模型: BAAI/bge-reranker-v2-m3

---

## 🎯 Task 1: 构建黄金测试集（Golden Test Set）

### 目标
从700+份真实行政处罚PDF文书中，构建一个**不经过LLM改写的**测试集，作为独立的评估基准。

### Step 1.1: PDF文本提取 pipeline
```python
# 文件位置建议: scripts/extract_pdf_texts.py
# 依赖: pdfplumber (优先) 或 PyPDF2
# 输入: data/raw_penalties/ 目录下的PDF文件
# 输出: data/processed/extracted_texts.jsonl

# 每条输出格式:
{
    "doc_id": "penalty_001",
    "filename": "原始文件名.pdf",
    "full_text": "处罚决定书全文...",
    "extraction_quality": "good/partial/failed",  # 记录提取质量
    "page_count": 3,
    "char_count": 2500
}
```

**注意事项**：
- 部分PDF可能是扫描件（图片PDF），pdfplumber提取为空时标记为`failed`，后续可用OCR处理
- 先跑一轮提取，统计成功率，决定是否需要OCR补充
- 预期：700份中可能有600-650份能直接提取文本

### Step 1.2: 结构化信息提取（核心步骤）

从提取的全文中，用**规则 + 正则**提取结构化字段，尽量不依赖LLM（节省token）。

```python
# 文件位置建议: scripts/parse_penalty_docs.py
# 输入: data/processed/extracted_texts.jsonl
# 输出: data/processed/structured_cases.jsonl

# 目标提取字段:
{
    "doc_id": "penalty_001",
    "platform": "淘宝",           # 正则提取电商平台名
    "merchant_name": "某某公司",   # 当事人/被处罚人
    "product_type": "服装",        # 商品类型
    "violation_facts": "...",      # 违法事实段落（关键！）
    "price_info": {                # 价格相关数据
        "original_price": "899元",
        "actual_price": "299元",
        "discount_claimed": "5折"
    },
    "legal_basis_cited": ["《价格法》第十四条", "《明码标价和禁止价格欺诈规定》第十七条"],
    "penalty_amount": "5000元",
    "penalty_authority": "XX市市场监督管理局",
    "penalty_date": "2024-03-15",
    "is_violation": true,          # 处罚文书 → 必然为true
    "violation_type": "虚构原价",  # 需要人工或半自动标注
    "raw_text_length": 2500
}
```

**提取策略**（按可靠性排序）：
1. `violation_facts`: 匹配"经查"/"查明"/"违法事实"后到"以上事实"/"证据"前的段落
2. `legal_basis_cited`: 正则匹配`《...》第...条`模式
3. `platform`: 关键词匹配['淘宝','天猫','京东','拼多多','美团','抖音','小红书','携程','快手']
4. `penalty_amount`: 正则匹配"罚款...元"/"处...元罚款"
5. `violation_type`: **这是最难的部分**，建议先用规则初步分类，再人工复核

**violation_type 规则分类器**（初步版本）：
```python
def classify_violation(facts_text, legal_basis):
    """基于违法事实和法律依据的规则分类器"""
    # 虚构原价：关键词 + 法律依据
    if any(kw in facts_text for kw in ['原价', '划线价']) and \
       any(kw in facts_text for kw in ['从未', '无交易', '未成交', '虚构', '不存在']):
        return '虚构原价'

    # 虚假折扣：折扣计算不实
    if any(kw in facts_text for kw in ['折扣', '打折', '优惠']) and \
       any(kw in facts_text for kw in ['不实', '虚假', '实际', '并非']):
        return '虚假折扣'

    # 价格误导：信息完整但误导性表述
    if any(kw in facts_text for kw in ['误导', '宣传', '不符', '混淆', '误解']):
        return '价格误导'

    # 要素缺失：缺少必要信息
    if any(kw in facts_text for kw in ['未标', '未明', '缺少', '缺失', '未注明', '未标注']):
        return '要素缺失'

    # 无法确定 → 标记为待人工审核
    return '待审核'
```

### Step 1.3: 构造测试集query格式

**关键改进**：将处罚文书的违法事实段落**重新组织**为query，但**不包含调查结论**，只包含客观事实描述。

```python
# 文件位置建议: scripts/build_golden_testset.py

def build_query_from_penalty(structured_case):
    """
    从处罚文书构造测试query

    核心原则：
    1. 保留客观价格数据（标价、折扣、实际售价等数字）
    2. 保留经营行为描述（在哪个平台、卖什么、怎么标价）
    3. 【删除】调查结论性表述（"无法提供凭证"→改为"请核实是否有交易记录"）
    4. 【删除】定性判断词汇（"虚假"/"虚构"/"欺诈"等）
    """
    # 输出格式（与现有eval格式兼容）:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query_text}
        ],
        "meta": {
            "case_id": f"golden_{structured_case['doc_id']}",
            "is_violation": True,  # 处罚文书=违规
            "violation_type": structured_case['violation_type'],
            "platform": structured_case['platform'],
            "complexity": "real_case",  # 标记为真实案例
            "source": "penalty_document",
            "rewritten": False,  # 关键：标记为未经LLM改写
            "legal_basis_ground_truth": structured_case['legal_basis_cited']
        }
    }
```

### Step 1.4: 补充合规样本

处罚文书全是违规案例，需要补充合规（无违规）样本以构成完整测试集。

**策略**：
1. **从现有数据集中保留合规样本**：现有753条中有259条合规样本，筛选质量较好的保留（去除标签为"无"的14条，保留"无违规"标签的）
2. **人工构造合规样本**（可选）：基于真实场景写合规案例（无需LLM改写）
3. **目标比例**：违规:合规 ≈ 2:1（与真实场景的分布一致）

### 最终测试集目标规模

| 来源 | 预计数量 | 说明 |
|------|----------|------|
| 真实处罚文书（违规） | 300-400条 | 从700份PDF中提取（扣除提取失败和质量差的） |
| 保留现有合规样本 | 150-200条 | 从现有数据集筛选质量好的合规案例 |
| **合计** | **450-600条** | 足够导师认可的规模 |

---

## 🎯 Task 2: 修复评估指标体系

### Step 2.1: 实现新指标计算

```python
# 文件位置建议: src/evaluation/advanced_metrics.py

from sklearn.metrics import (
    f1_score, precision_score, recall_score,
    classification_report, confusion_matrix
)
import numpy as np

class AdvancedMetrics:
    """改进的评估指标体系"""

    # === 核心指标1: Macro-F1 (多分类) ===
    @staticmethod
    def compute_macro_f1(y_true_types, y_pred_types):
        """
        对6种违规类型（含"无违规"）计算macro-F1

        Args:
            y_true_types: ground truth violation types list
            y_pred_types: predicted violation types list

        Returns:
            dict with macro_f1, per_class_f1, classification_report
        """
        # 标签归一化：统一合规标签
        label_map = {'不违规': '无违规', '无': '无违规', '合规': '无违规'}
        y_true_norm = [label_map.get(y, y) for y in y_true_types]
        y_pred_norm = [label_map.get(y, y) for y in y_pred_types]

        labels = ['虚构原价', '虚假折扣', '价格误导', '要素缺失', '其他', '无违规']

        macro_f1 = f1_score(y_true_norm, y_pred_norm, labels=labels, average='macro', zero_division=0)
        per_class = classification_report(y_true_norm, y_pred_norm, labels=labels, output_dict=True, zero_division=0)

        return {
            'macro_f1': round(macro_f1, 4),
            'per_class_f1': {label: round(per_class[label]['f1-score'], 4) for label in labels if label in per_class},
            'full_report': classification_report(y_true_norm, y_pred_norm, labels=labels, zero_division=0)
        }

    # === 核心指标2: 违规类型准确率 (Type Accuracy) ===
    @staticmethod
    def compute_type_accuracy(y_true_types, y_pred_types, is_violation_mask):
        """
        仅对is_violation=True的样本，计算violation_type的准确率

        这个指标反映模型"不仅判断对错，还能判断是哪种违规"的能力
        """
        correct = 0
        total = 0
        for true_t, pred_t, is_viol in zip(y_true_types, y_pred_types, is_violation_mask):
            if is_viol:  # 只算违规案例
                total += 1
                # 归一化后比较
                true_norm = true_t if true_t not in ['不违规', '无', '合规'] else '无违规'
                pred_norm = pred_t if pred_t not in ['不违规', '无', '合规'] else '无违规'
                if true_norm == pred_norm:
                    correct += 1
        return round(correct / total, 4) if total > 0 else 0.0

    # === 核心指标3: 法律条款引用准确率 ===
    @staticmethod
    def compute_legal_citation_accuracy(ground_truth_laws, predicted_laws):
        """
        基于ground truth法律条款（从处罚文书提取）计算引用准确率

        比关键词启发式更准确：直接对比模型引用的法条与处罚文书中的法条
        """
        precision_scores = []
        recall_scores = []

        for gt, pred in zip(ground_truth_laws, predicted_laws):
            gt_set = set(gt) if gt else set()
            pred_set = set(pred) if pred else set()

            if pred_set:
                precision = len(gt_set & pred_set) / len(pred_set)
            else:
                precision = 0.0

            if gt_set:
                recall = len(gt_set & pred_set) / len(gt_set)
            else:
                recall = 1.0 if not pred_set else 0.0

            precision_scores.append(precision)
            recall_scores.append(recall)

        avg_precision = np.mean(precision_scores)
        avg_recall = np.mean(recall_scores)
        f1 = 2 * avg_precision * avg_recall / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0

        return {
            'citation_precision': round(avg_precision, 4),
            'citation_recall': round(avg_recall, 4),
            'citation_f1': round(f1, 4)
        }

    # === 核心指标4: 错误不对称成本 ===
    @staticmethod
    def compute_weighted_accuracy(y_true, y_pred, fn_weight=3.0, fp_weight=1.0):
        """
        加权准确率：漏判违规(FN)的成本是误判合规(FP)的3倍

        在法律合规场景中，漏掉真正的违规比误报合规严重得多
        """
        tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
        tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
        fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)

        weighted = (tp + tn) / (tp + tn + fn_weight * fn + fp_weight * fp)
        return {
            'weighted_accuracy': round(weighted, 4),
            'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
            'fn_weight': fn_weight, 'fp_weight': fp_weight
        }
```

### Step 2.2: 修改评估脚本

在现有的 `run_baseline_eval.py`, `run_rag_eval.py`, `run_agent_eval.py` 中集成新指标：

```python
# 在每个eval脚本的结果汇总部分添加:
from src.evaluation.advanced_metrics import AdvancedMetrics

metrics = AdvancedMetrics()
results['macro_f1'] = metrics.compute_macro_f1(y_true_types, y_pred_types)
results['type_accuracy'] = metrics.compute_type_accuracy(y_true_types, y_pred_types, is_violation_mask)
results['weighted_accuracy'] = metrics.compute_weighted_accuracy(y_true_binary, y_pred_binary)

# 如果使用golden test set（有ground truth法律依据）:
if has_ground_truth_laws:
    results['citation_metrics'] = metrics.compute_legal_citation_accuracy(gt_laws, pred_laws)
```

---

## 🎯 Task 3: 修复Agent代码（按子任务分解）

### Step 3.1: 修复 IntentAnalyzer

**问题**：当前规则过于严格，需要同时匹配两组关键词才能识别违规类型，导致70%+样本返回"需进一步分析"。

**修复方案**：放宽规则，改用单层关键词 + 权重打分。

```python
# 文件: src/agents/intent_analyzer.py
# 修改 _detect_violation_types 方法

def _detect_violation_types(self, query):
    """改进版：单层关键词 + 权重打分，不再要求双重匹配"""
    scores = {
        '虚构原价': 0,
        '虚假折扣': 0,
        '价格误导': 0,
        '要素缺失': 0
    }

    # 虚构原价信号词（任一命中即加分）
    for kw in ['原价', '划线价', '从未成交', '无交易记录', '虚构', '无销售记录', '不存在']:
        if kw in query:
            scores['虚构原价'] += 1

    # 虚假折扣信号词
    for kw in ['折扣', '打折', '优惠', '促销', '活动价', '特价', '限时', '减价']:
        if kw in query:
            scores['虚假折扣'] += 0.5
    for kw in ['虚假', '不实', '实际', '并非', '其实', '真实售价']:
        if kw in query:
            scores['虚假折扣'] += 1

    # 价格误导信号词
    for kw in ['宣传', '标注', '展示', '不符', '误导', '实际价格', '差异', '混淆']:
        if kw in query:
            scores['价格误导'] += 1

    # 要素缺失信号词
    for kw in ['未标', '未说明', '未明示', '缺失', '缺少', '未注明', '未标注',
               '运费', '税费', '附加费', '计算基准']:
        if kw in query:
            scores['要素缺失'] += 1

    # 按分数排序，返回top hints（至少返回一个）
    sorted_types = sorted(scores.items(), key=lambda x: -x[1])
    hints = [t for t, s in sorted_types if s > 0]

    if not hints:
        # 即使没有匹配，也返回最可能的类型（基于价格相关词汇）
        if any(kw in query for kw in ['价格', '价', '元', '费用']):
            hints = ['需进一步分析']
        else:
            hints = ['需进一步分析']

    return hints[:3]
```

### Step 3.2: 修复 Grader

**问题**：Coverage评分依赖低质量关键词，反而引入噪声。

**修复方案**：删除Coverage维度，简化评分。

```python
# 文件: src/agents/grader.py

class Grader:
    def __init__(self,
                 relevance_weight=0.9,    # 几乎完全依赖检索相关性
                 freshness_weight=0.1,    # 时效性作为微调
                 min_score=0.4):          # 降低阈值，更宽容
        self.relevance_weight = relevance_weight
        self.freshness_weight = freshness_weight
        # 删除 coverage_weight
        self.min_score = min_score

    def _score_doc(self, doc, keywords):
        """简化评分：只用relevance + freshness"""
        metadata = doc.get('metadata', {})

        # Relevance: 直接使用rerank_score或distance
        relevance = doc.get('rerank_score', max(0, 1 - doc.get('distance', 0.5)))

        # Freshness
        year = metadata.get('year', 2020)
        freshness = 1.0 if year >= 2024 else (0.8 if year >= 2020 else 0.6)

        final_score = self.relevance_weight * relevance + self.freshness_weight * freshness

        doc['relevance_score'] = round(relevance, 3)
        doc['freshness_score'] = round(freshness, 3)
        doc['final_score'] = round(final_score, 3)
        doc['grade'] = 'high' if final_score >= 0.7 else ('medium' if final_score >= 0.4 else 'low')

        return doc

    def _filter_docs(self, docs, min_keep=1):
        """改为 min_keep=1，允许更激进地过滤"""
        filtered = [d for d in docs if d['final_score'] >= self.min_score]
        if len(filtered) < min_keep and len(docs) >= min_keep:
            filtered = docs[:min_keep]
        return filtered
```

### Step 3.3: 修复 ReasoningEngine

**问题**：JSON解析失败无fallback，temperature过高。

```python
# 文件: src/agents/reasoning_engine.py
# 修改 _parse_response 方法

def _parse_response(self, text):
    """改进版：多级fallback解析"""
    # Level 1: 标准JSON提取
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            if 'is_violation' in result:
                return result
        except json.JSONDecodeError:
            pass

    # Level 2: 直接尝试解析全文为JSON
    try:
        result = json.loads(text)
        if 'is_violation' in result:
            return result
    except json.JSONDecodeError:
        pass

    # Level 3: 正则 fallback（从自然语言中提取关键字段）
    result = {
        'reasoning_chain': [],
        'is_violation': None,
        'violation_type': '未知',
        'legal_basis': '',
        'confidence': 0.5
    }

    # 提取 is_violation
    if re.search(r'(违规|存在.*问题|构成.*违法)', text):
        result['is_violation'] = True
    elif re.search(r'(不违规|合规|不存在.*问题|符合)', text):
        result['is_violation'] = False

    # 提取 violation_type
    type_patterns = {
        '虚构原价': r'虚构原价|虚构.*原价|原价.*虚构',
        '虚假折扣': r'虚假折扣|折扣.*虚假|虚假.*优惠',
        '价格误导': r'价格误导|误导.*消费者|误导性',
        '要素缺失': r'要素缺失|缺少.*标注|未.*标明',
    }
    for vtype, pattern in type_patterns.items():
        if re.search(pattern, text):
            result['violation_type'] = vtype
            break

    # 提取 legal_basis
    law_refs = re.findall(r'《[^》]+》[第\d]+条', text)
    if law_refs:
        result['legal_basis'] = '；'.join(law_refs[:3])

    # 提取 reasoning_chain（按句号分割取前5句）
    sentences = [s.strip() for s in re.split(r'[。\n]', text) if len(s.strip()) > 10]
    result['reasoning_chain'] = sentences[:5]

    return result
```

**同时修改模型调用参数**（在model_config.yaml中）：
```yaml
# configs/model_config.yaml 修改建议
models:
  qwen-8b:
    model_id: "xop3qwen8b"
    name: "Qwen3-8B"
    max_tokens: 2048
    temperature: 0.15    # 从0.7降到0.15，合规判断需要确定性
    top_p: 0.85          # 从0.9降到0.85
    lora_id: "0"
```

### Step 3.4: 修复 Reflector

**问题**：Critical条件太窄，几乎不触发重推理。

```python
# 文件: src/agents/reflector.py
# 修改 _heuristic_validation 方法

def _heuristic_validation(self, reasoning_result, graded_docs):
    """改进版：更多验证维度"""
    issues = []

    # === 验证1: 法律依据检查（保留原有逻辑但增强） ===
    legal_basis = reasoning_result.get('legal_basis', '')
    reasoning_chain = reasoning_result.get('reasoning_chain', [])
    chain_text = ' '.join(reasoning_chain) if reasoning_chain else ''

    if not legal_basis and not re.search(r'《[^》]+》', chain_text):
        issues.append({
            "type": "missing_legal_basis",
            "severity": "critical",  # 升级为critical！完全没有法律依据应该重推理
            "description": "未引用任何法律条文",
            "suggestion": "请引用《价格法》《明码标价和禁止价格欺诈规定》等相关法律"
        })

    # === 验证2: 推理链完整性 ===
    if not reasoning_chain or len(reasoning_chain) < 3:
        issues.append({
            "type": "incomplete_reasoning",
            "severity": "critical",  # 升级为critical！推理链过短说明推理可能失败
            "description": f"推理链过短（{len(reasoning_chain)}步，需至少3步）",
            "suggestion": "请按照5步推理模板完整输出"
        })

    # === 验证3: is_violation 与 violation_type 一致性 ===
    is_violation = reasoning_result.get('is_violation')
    violation_type = reasoning_result.get('violation_type', '')

    if is_violation and violation_type in ['无违规', '合规', 'None', '', '未知']:
        issues.append({
            "type": "logic_inconsistency",
            "severity": "critical",
            "description": f"判定违规但violation_type='{violation_type}'",
            "suggestion": "请明确指定违规类型"
        })

    if not is_violation and violation_type not in ['无违规', '合规', 'None', '', '未知']:
        issues.append({
            "type": "logic_inconsistency",
            "severity": "critical",
            "description": f"判定不违规但violation_type='{violation_type}'",
            "suggestion": "若不违规，violation_type应为'无违规'"
        })

    # === 验证4 [新增]: 违规类型与推理链的一致性 ===
    if is_violation and violation_type and violation_type not in ['未知', '其他']:
        type_keywords = {
            '虚构原价': ['原价', '划线价', '从未', '虚构'],
            '虚假折扣': ['折扣', '打折', '优惠', '虚假'],
            '价格误导': ['误导', '宣传', '不符'],
            '要素缺失': ['未标', '缺少', '缺失', '未明']
        }
        expected_kws = type_keywords.get(violation_type, [])
        if expected_kws and not any(kw in chain_text for kw in expected_kws):
            issues.append({
                "type": "type_reasoning_mismatch",
                "severity": "warning",
                "description": f"违规类型'{violation_type}'但推理链中未提及相关关键词",
                "suggestion": f"推理链应明确分析与'{violation_type}'相关的事实"
            })

    # === 验证5 [新增]: 置信度合理性 ===
    confidence = reasoning_result.get('confidence', 0)
    if confidence < 0.3 and is_violation is not None:
        issues.append({
            "type": "low_confidence",
            "severity": "warning",
            "description": f"置信度过低({confidence:.2f})，判断可能不可靠",
            "suggestion": "请重新审视证据是否充分"
        })

    return issues
```

### Step 3.5: 简化Agent架构（可选，如果效果仍不好）

如果修复后效果仍不理想，考虑简化为3节点架构：

```python
# 可选方案: src/agents/simple_agent_coordinator.py

class SimpleAgentCoordinator:
    """精简版Agent：检索 → 推理 → 验证"""

    def __init__(self, config_path, db_path):
        self.retriever = HybridRetriever(db_path)
        self.reasoning_engine = ReasoningEngine(config_path)
        self.reflector = Reflector(config_path, max_reflection=1)

    def process(self, query):
        # Step 1: 直接检索（跳过IntentAnalyzer，使用固定TopK）
        retrieved = self.retriever.retrieve(
            query=query, laws_k=3, cases_k=5,
            distance_threshold=0.15, min_k=2
        )

        # Step 2: 简化Grading（只用rerank_score排序，不过滤）
        graded = {
            'graded_laws': sorted(retrieved.get('laws', []),
                                  key=lambda x: x.get('rerank_score', 0), reverse=True),
            'graded_cases': sorted(retrieved.get('cases', []),
                                   key=lambda x: x.get('rerank_score', 0), reverse=True)
        }

        # Step 3: 推理
        intent = {'reasoning_hints': [], 'complexity': 'medium'}
        reasoning_result = self.reasoning_engine.reason(query, graded, intent)

        if not reasoning_result.get('success'):
            return reasoning_result

        # Step 4: 反思验证
        final_result = self.reflector.reflect(reasoning_result, graded, query, intent)

        return final_result
```

---

## 🎯 Task 4: 统一评估流程

### Step 4.1: 创建统一对比脚本

```python
# 文件位置建议: scripts/run_comparison.py
# 功能: 在同一数据集上运行3种方法，生成统一对比报告

"""
使用方式:
python scripts/run_comparison.py \
    --eval-data data/eval/golden_testset.jsonl \
    --methods baseline,rag,agent \
    --model qwen-8b \
    --output results/comparison_report.md
"""
```

### Step 4.2: 对比报告模板

输出报告应包含：

```markdown
# 三方法对比报告

## 1. Binary Classification
| Method | Accuracy | Precision | Recall | F1 | Weighted Acc (FN×3) |
|--------|----------|-----------|--------|-----|---------------------|

## 2. Violation Type Classification (Macro-F1)
| Method | Macro-F1 | 虚构原价 | 虚假折扣 | 价格误导 | 要素缺失 | 其他 | 无违规 |
|--------|----------|----------|----------|----------|----------|------|--------|

## 3. Type Accuracy (violation cases only)
| Method | Type Accuracy |
|--------|---------------|

## 4. Legal Citation Quality
| Method | Citation Precision | Citation Recall | Citation F1 |
|--------|-------------------|-----------------|-------------|

## 5. Cost Analysis
| Method | Avg Response Time | Avg Tokens | API Calls per Query |
|--------|-------------------|------------|---------------------|

## 6. Error Analysis
### 6.1 Per-violation-type error rates
### 6.2 Confusion matrix
### 6.3 Sample error cases (top 10 most confident wrong predictions)
```

---

## ⚠️ 执行顺序建议

```
Task 1 (数据集) ─────────────────────────────────→ 产出黄金测试集
                                                      ↓
Task 2 (评估指标) ────→ 产出新指标模块 ──────────→ 接入评估流程
                                                      ↓
Task 3.1-3.4 (Agent修复) ──→ 产出修复后Agent ──→ 重新评估
                                                      ↓
Task 4 (统一对比) ─────────────────────────────────→ 最终对比报告
```

**建议分多次会话给 Claude Code**：
- Session 1: Task 1 (PDF提取 + 结构化)
- Session 2: Task 1 (构造测试集query) + Task 2 (评估指标)
- Session 3: Task 3 (Agent修复，一次给完所有修改)
- Session 4: Task 4 (统一评估)

这样每次的token消耗可控，且每个session有明确的输入/输出。

---

## 📎 附录：关键文件路径参考

```
price_regulation_agent/
├── configs/model_config.yaml        # 模型配置（修改temperature）
├── data/
│   ├── eval/
│   │   ├── eval_159.jsonl           # 原始测试集
│   │   ├── eval_754.jsonl           # 扩展测试集
│   │   └── golden_testset.jsonl     # 【新建】黄金测试集
│   ├── raw_penalties/               # 【新建】放入700+份PDF
│   └── processed/
│       ├── extracted_texts.jsonl    # 【新建】PDF提取文本
│       └── structured_cases.jsonl   # 【新建】结构化案例
├── src/
│   ├── agents/
│   │   ├── intent_analyzer.py       # 【修改】放宽规则
│   │   ├── grader.py                # 【修改】删除coverage
│   │   ├── reasoning_engine.py      # 【修改】JSON fallback + temperature
│   │   ├── reflector.py             # 【修改】增加验证维度
│   │   └── agent_coordinator.py     # 可选修改
│   └── evaluation/
│       └── advanced_metrics.py      # 【新建】新指标模块
├── scripts/
│   ├── extract_pdf_texts.py         # 【新建】PDF提取
│   ├── parse_penalty_docs.py        # 【新建】结构化解析
│   ├── build_golden_testset.py      # 【新建】构建测试集
│   └── run_comparison.py            # 【新建】统一对比
└── results/
    └── comparison_report.md         # 【新建】对比报告
```
