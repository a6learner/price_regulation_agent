# Phase 2: 数据集构建 + 法条检索评测体系

> **给 Claude Code 的任务指南**
> 项目：价格合规智能分析系统（毕业论文）
> 日期：2026年4月
> 前序工作：Phase 1 已完成 791 份 PDF 扫描，输出 scan_results_v2.jsonl (787条)

---

## 战略目标 (Strategic Goal)

构建一个以**法条引用正确性**为核心评测维度的黄金测试集，使得 Baseline(纯LLM) / RAG(LLM+检索) / Agent(多节点工作流) 三种方案可以在**法条检索精度**上产生有区分度的对比。

**核心论点**：RAG/Agent 的价值不在于"判断对不对"（Baseline 已经 99%+），而在于"能否检索到正确的法律条文作为判断依据"。Baseline 靠参数记忆猜法条，RAG 靠检索召回法条 — 这才是有意义的对比维度。

---

## 当前数据状况 (Current Data Status)

```
scan_results_v2.jsonl: 787 条扫描结果
├── 有法条引用: 638 (81.1%)
│   ├── 有定性法条+处罚法条: 359
│   ├── 只有定性法条: 104
│   └── 只有处罚法条: 175
├── 无法条引用: 149 (18.9%)
├── 有violation_facts段: 450 (57.2%)
├── 有legal_analysis段: 397 (50.4%)
└── 最佳候选(定性法条+事实段): 300
```

**关键发现**：法条分两类，必须区分！
- **定性法条** (qualifying articles) = Agent 应该检索到的 = ground truth
  - 《价格法》第12条(政府定价)、第13条(明码标价)、第14条(不正当价格行为)
  - 《明码标价和禁止价格欺诈规定》各条
  - 《禁止价格欺诈行为的规定》各条
- **处罚法条** (penalty articles) = 量刑依据，不作为检索目标
  - 《价格法》第39-42条（罚则）
  - 《价格违法行为行政处罚规定》各条（处罚标准）

---

## Task 1: 数据集精细提取 (Dataset Extraction)

### 目标
从 scan_results_v2.jsonl 的 787 条中，提取出 450-600 条高质量样本，每条包含完整的结构化字段。

### 数据集 Schema

每条测试样本的目标格式 (`eval_dataset_v3.jsonl`):

```jsonc
{
  // === 元信息 ===
  "id": "CASE_001",                          // 唯一编号
  "source_pdf": "宝鸡市陈仓区_152号.pdf",      // 来源PDF文件名
  "region": "宝鸡市陈仓区",                    // 执法地区

  // === 输入（给Agent的prompt内容）===
  "input": {
    "case_description": "...",                // 案件事实描述（来自"经查"段）
    // ↑ 这是Agent看到的唯一输入，不能包含法律分析结论
    "platform": "拼多多",                      // 涉及平台（可选，辅助信息）
    "goods_or_service": "某品牌手机壳"          // 涉及商品/服务（可选）
  },

  // === Ground Truth（标准答案）===
  "ground_truth": {
    "is_violation": true,                     // 是否违规（二分类）

    "violation_type": "A1",                   // 违规类型编码（辅助，非核心）
    "violation_type_name": "虚构原价",          // 违规类型名称

    "qualifying_articles": [                  // ★ 核心：定性法条列表
      {
        "law": "价格法",
        "article": "第十四条第四项",
        "article_key": "价格法_十四_四",        // 标准化key，用于自动评分
        "description": "经营者利用虚假的或者使人误解的价格手段，诱骗消费者或其他经营者与其进行交易"
      },
      {
        "law": "明码标价和禁止价格欺诈规定",
        "article": "第十九条第三项",
        "article_key": "明码标价和禁止价格欺诈规定_十九_三",
        "description": "通过虚假折价、减价或者价格比较等方式销售商品或者提供服务"
      }
    ],

    "penalty_articles": [                     // 处罚法条（参考，不评分）
      {
        "law": "价格违法行为行政处罚规定",
        "article": "第七条",
        "article_key": "价格违法行为行政处罚规定_七"
      }
    ],

    "legal_analysis_reference": "...",        // 原文"本局认为"段（参考）
    "penalty_result": "罚款5000元"             // 处罚结果（参考）
  }
}
```

### 执行步骤

#### Step 1.1: 筛选高质量候选

```python
# 筛选标准（按优先级）:
# Tier 1 (最佳): 有定性法条 + 有violation_facts段 → ~300条
# Tier 2 (良好): 有任何法条 + 有violation_facts段 → ~390条
# Tier 3 (可用): 有任何法条 + text_length > 500 → ~637条
#
# 目标: 先处理 Tier 1 + Tier 2，预计得到 350-450 条
# 如果不够，再从 Tier 3 中用 LLM 补充提取
```

从 `scan_results_v2.jsonl` 中筛选:
1. 读取所有 787 条记录
2. 按上述 Tier 分级
3. 输出 `candidates_tier1.jsonl` 和 `candidates_tier2.jsonl`

#### Step 1.2: 区分定性法条 vs 处罚法条

这是最关键的一步。scan_results_v2 中的 `citation_keys` 混在一起，需要拆分。

```python
# 定性法条前缀（Agent应该检索到的）
QUALIFYING_PREFIXES = [
    '价格法_十二',        # 政府定价
    '价格法_十三',        # 明码标价义务
    '价格法_十四',        # 不正当价格行为
    '明码标价和禁止价格欺诈规定_',
    '禁止价格欺诈行为的规定_',
    '电子商务法_',
    '消费者权益保护法_',
    '反不正当竞争法_',
]

# 处罚法条前缀（量刑依据，不评分）
PENALTY_PREFIXES = [
    '价格法_三十',        # 法律责任章节
    '价格法_四十',
    '价格违法行为行政处罚规定_',  # 整部都是处罚标准
]
```

对每条记录，将 `citation_keys` 拆分为 `qualifying_articles` 和 `penalty_articles`。

**注意**：`价格违法行为行政处罚规定` 比较特殊 — 它的第4-8条既定义了违法行为类型，又规定了处罚标准。处理方式：
- 第4条(串通操纵)、第5条(哄抬价格)、第6条(囤积居奇)、第7条(价格欺诈)、第8条(变相提价) → **同时归入定性和处罚**
- 第9条(不执行政府定价)、第10条、第11条、第13条 → **只归入处罚**
- 第16条、第21条 → 从轻/减轻情节，**只归入处罚**

```python
# 处罚规定中兼具定性功能的条款
DUAL_PURPOSE_ARTICLES = [
    '价格违法行为行政处罚规定_四',
    '价格违法行为行政处罚规定_五',
    '价格违法行为行政处罚规定_六',
    '价格违法行为行政处罚规定_七',
    '价格违法行为行政处罚规定_八',
]
```

#### Step 1.3: 构建 case_description（去除答案泄露）

**极其重要**：`case_description` 只能包含事实描述，不能包含法律结论。

```python
# 来源：violation_facts_preview（"经查"段）
# 必须删除的内容：
LEAKAGE_PATTERNS = [
    r'违反了《.*?》',          # 法律引用
    r'构成.*?违法行为',         # 定性结论
    r'本局认为.*',             # 法律分析
    r'依据.*?规定',            # 处罚依据
    r'属于.*?价格(?:欺诈|违法)',  # 分类标签
]

# 正确的 case_description 示例:
# "当事人在拼多多平台开设网店销售手机壳。经查，其在商品首页标示价格为
#  9.9元，但消费者点击进入详情页后实际标价为19.9元，付款页面结算价格
#  为19.9元。2023年1月至6月期间，该商品共销售1234单。"
#
# 错误的 case_description（有泄露）:
# "当事人...构成价格欺诈违法行为，违反了《价格法》第十四条..."
```

处理流程：
1. 取 `violation_facts_preview` 作为原始文本
2. 用正则删除上述泄露模式
3. 如果删除后文本过短 (< 80字)，回退到全文提取，重新定位"经查"到"以上事实"之间的段落
4. 输出 clean 后的 `case_description`

#### Step 1.4: 用 LLM 补充结构化（Stage 2）

对 Tier 1 + Tier 2 中仍有缺失字段的案例，用讯飞星辰 API 补充:

```
需要LLM补充的字段（仅当规则提取失败时）:
- platform（涉及平台）
- goods_or_service（涉及商品/服务）
- violation_type（违规类型编码，参照 violation_taxonomy.md）

不需要LLM的字段（规则提取即可）:
- qualifying_articles（来自 citation_keys 拆分）
- penalty_articles（同上）
- is_violation（处罚文书 = 全部为 true，合规样本另行构建）
- case_description（来自 violation_facts，去泄露后直接用原文）
```

**绝对禁止**: 用 LLM 改写 case_description 或 legal_analysis_reference。这些字段必须保留原文，否则引入同源污染。

#### Step 1.5: 构建合规样本（无违规案例）

当前 787 条全部是违规案例（来自处罚文书），需要补充合规样本。

**方法（改进版）**：不用 LLM 凭空生成，而是从违规案例中构造"修正版":

```python
# 策略：选取事实清晰的违规案例，将其违规要素去除，构造合规版本
#
# 示例:
# 原案例（违规）: "当事人在拼多多标示手机壳售价9.9元，详情页为19.9元"
# 合规版本: "当事人在拼多多平台销售手机壳，首页标示价格9.9元，
#           详情页与付款页面价格均为9.9元，价格标示一致"
#
# 这里可以用 LLM 辅助生成合规版本，但：
# 1. 必须标注 "synthetic": true
# 2. 不计入法条检索评分（因为合规案例没有应引用的法条）
# 3. 只用于二分类评测（is_violation = false）
#
# 建议数量：~100条（占总数据集15-20%）
# 从每种违规类型中各选10-15条作为模板
```

### 输出

- `eval_dataset_v3.jsonl` — 完整数据集 (450-600条 + ~100条合规)
- `dataset_statistics.json` — 数据集统计报告
- `extraction_log.jsonl` — 提取过程日志（记录每条的处理方式和质量分数）

### 成功标准

```
✅ 总样本数 ≥ 500
✅ 违规样本中有 qualifying_articles 的比例 ≥ 90%
✅ case_description 泄露率 < 3%（含判定词的比例）
✅ 合规样本占比 15-20%
✅ 没有任何字段经过 LLM 改写（case_description 和 legal_analysis 保留原文）
```

---

## Task 2: 法条知识库构建 (Legal Knowledge Base)

### 目标
构建一个结构化的法条知识库，供 RAG 系统检索。这个知识库的质量直接决定 RAG 的上限。

### 知识库结构

```jsonc
// legal_knowledge_base.jsonl — 每条一个法条chunk
{
  "chunk_id": "price_law_art14_sub4",
  "law_name": "中华人民共和国价格法",
  "law_short": "价格法",
  "article": "第十四条",
  "sub_article": "第四项",
  "article_key": "价格法_十四_四",           // 与数据集的 article_key 对齐
  "full_text": "经营者不得利用虚假的或者使人误解的价格手段，诱骗消费者或者其他经营者与其进行交易。",
  "context": "第十四条 经营者不得有下列不正当价格行为：...",  // 上下文（整条）
  "tags": ["价格欺诈", "虚假价格", "误导性标价"],          // 语义标签
  "typical_scenarios": ["虚构原价", "虚假折扣", "低价诱骗高价结算"]  // 典型适用场景
}
```

### 需要收录的法律法规

按优先级排列:

| 优先级 | 法律法规 | 条文数(约) | 说明 |
|--------|---------|-----------|------|
| P0 | 《中华人民共和国价格法》 | ~48条 | 核心法律 |
| P0 | 《价格违法行为行政处罚规定》 | ~21条 | 处罚标准 |
| P0 | 《明码标价和禁止价格欺诈规定》(2022) | ~25条 | 新规，电商相关 |
| P1 | 《禁止价格欺诈行为的规定》 | ~15条 | 旧规但仍适用 |
| P1 | 《规范促销行为暂行规定》 | ~30条 | 促销价格规范 |
| P2 | 《电子商务法》(价格相关条款) | ~5条 | 电商平台义务 |
| P2 | 《消费者权益保护法》(价格相关条款) | ~3条 | 消费者权益 |

### 执行步骤

1. 从国家法律法规数据库 (https://flk.npc.gov.cn/) 获取法律全文
2. 按条/款/项拆分为独立 chunk
3. 每个 chunk 生成 `article_key`（格式与数据集对齐）
4. 用 LLM 为每个 chunk 生成 `tags` 和 `typical_scenarios`（辅助检索）
5. 输出 `legal_knowledge_base.jsonl`

### 成功标准

```
✅ 覆盖数据集中出现的所有 article_key（0 遗漏）
✅ 每个 chunk 有完整的 full_text + context
✅ article_key 格式与 eval_dataset_v3 完全一致
```

---

## Task 3: 评测框架实现 (Evaluation Framework)

### 核心评测维度

```
维度1: 二分类准确性 (Binary Classification)
  - 指标: Accuracy, Macro-F1, Precision, Recall
  - ground truth: is_violation (true/false)
  - 用于: 验证基本判断能力

维度2: ★ 法条检索准确性 (Legal Article Retrieval) ← 最重要
  - 指标: Precision, Recall, F1 (set-level)
  - ground truth: qualifying_articles[].article_key
  - 用于: 对比 Baseline vs RAG vs Agent 的核心区分度

维度3: 推理质量 (Reasoning Quality)
  - 指标: GPT/人工评分 1-5 (可选，后期做)
  - 用于: 辅助说明
```

### 维度2 详细设计：法条检索 Precision / Recall / F1

```python
def evaluate_legal_retrieval(predicted_keys: List[str], ground_truth_keys: List[str]):
    """
    评估单条case的法条检索质量
    
    predicted_keys: Agent/RAG/Baseline 输出中引用的法条 article_key 列表
    ground_truth_keys: 数据集中的 qualifying_articles[].article_key 列表
    
    支持两种粒度:
    - strict: article_key 完全匹配（如 "价格法_十四_四"）
    - relaxed: 只匹配到条级别（如 "价格法_十四" 匹配 "价格法_十四_四"）
    """
    pred_set = set(predicted_keys)
    gt_set = set(ground_truth_keys)
    
    # Strict matching
    strict_tp = len(pred_set & gt_set)
    strict_precision = strict_tp / len(pred_set) if pred_set else 0
    strict_recall = strict_tp / len(gt_set) if gt_set else 0
    strict_f1 = 2 * strict_precision * strict_recall / (strict_precision + strict_recall) \
                if (strict_precision + strict_recall) > 0 else 0
    
    # Relaxed matching (条级别)
    pred_article_level = set(k.rsplit('_', 1)[0] if k.count('_') > 1 else k for k in pred_set)
    gt_article_level = set(k.rsplit('_', 1)[0] if k.count('_') > 1 else k for k in gt_set)
    relaxed_tp = len(pred_article_level & gt_article_level)
    relaxed_precision = relaxed_tp / len(pred_article_level) if pred_article_level else 0
    relaxed_recall = relaxed_tp / len(gt_article_level) if gt_article_level else 0
    relaxed_f1 = 2 * relaxed_precision * relaxed_recall / (relaxed_precision + relaxed_recall) \
                 if (relaxed_precision + relaxed_recall) > 0 else 0
    
    return {
        "strict": {"precision": strict_precision, "recall": strict_recall, "f1": strict_f1},
        "relaxed": {"precision": relaxed_precision, "recall": relaxed_recall, "f1": relaxed_f1},
    }


def evaluate_dataset(results: List[Dict], dataset: List[Dict]):
    """
    整个数据集的宏平均评估
    
    results[i] = {"predicted_keys": [...], "predicted_violation": bool, "reasoning": "..."}
    dataset[i] = 一条eval_dataset_v3记录
    """
    all_strict_p, all_strict_r, all_strict_f1 = [], [], []
    all_relaxed_p, all_relaxed_r, all_relaxed_f1 = [], [], []
    binary_correct = 0
    
    # 只对违规样本评估法条检索（合规样本无ground truth法条）
    violation_cases = [(r, d) for r, d in zip(results, dataset) 
                       if d["ground_truth"]["is_violation"]]
    
    for result, case in violation_cases:
        gt_keys = [a["article_key"] for a in case["ground_truth"]["qualifying_articles"]]
        pred_keys = result["predicted_keys"]
        
        scores = evaluate_legal_retrieval(pred_keys, gt_keys)
        all_strict_p.append(scores["strict"]["precision"])
        all_strict_r.append(scores["strict"]["recall"])
        all_strict_f1.append(scores["strict"]["f1"])
        all_relaxed_p.append(scores["relaxed"]["precision"])
        all_relaxed_r.append(scores["relaxed"]["recall"])
        all_relaxed_f1.append(scores["relaxed"]["f1"])
    
    # 二分类全量评估
    for result, case in zip(results, dataset):
        if result["predicted_violation"] == case["ground_truth"]["is_violation"]:
            binary_correct += 1
    
    n = len(violation_cases)
    return {
        "binary_accuracy": binary_correct / len(dataset),
        "legal_retrieval_strict": {
            "macro_precision": sum(all_strict_p) / n,
            "macro_recall": sum(all_strict_r) / n,
            "macro_f1": sum(all_strict_f1) / n,
        },
        "legal_retrieval_relaxed": {
            "macro_precision": sum(all_relaxed_p) / n,
            "macro_recall": sum(all_relaxed_r) / n,
            "macro_f1": sum(all_relaxed_f1) / n,
        },
        "total_cases": len(dataset),
        "violation_cases_evaluated": n,
    }
```

### 预期结果模式（论文中的故事线）

```
                     Binary Acc   Legal-Strict-F1   Legal-Relaxed-F1
Baseline (Qwen3-8B)    95-99%       30-50%             45-65%
RAG (Qwen3-8B+检索)    95-99%       55-75%             70-85%
Agent (6节点工作流)     95-99%       60-80%             75-90%
```

**论点**: Binary Accuracy 三者差距很小（都很高），但法条检索F1是拉开差距的关键维度：
- Baseline 只靠参数记忆，很容易引错条款（如把第13条和第14条搞混）
- RAG 通过检索能找到正确法条，但可能检索噪声导致多引或引错
- Agent 通过意图分析→精准检索→反思验证，能进一步提高精度

这个故事可以直接写进论文的实验分析章节。

### Baseline / RAG / Agent 输出格式标准化

三种方法的输出必须统一格式，才能用同一套评测函数:

```jsonc
// 每种方法对每条case的输出
{
  "case_id": "CASE_001",
  "method": "baseline",  // "baseline" | "rag" | "agent"
  "predicted_violation": true,
  "predicted_keys": ["价格法_十四_四", "明码标价和禁止价格欺诈规定_十九"],
  "reasoning": "当事人标注的原价无真实交易记录，构成虚构原价...",
  "raw_output": "..."  // LLM原始输出（debug用）
}
```

**关键**: 需要从 LLM 的自然语言输出中提取 `predicted_keys`。方法:

```python
# 方案1（推荐）: Prompt 要求 LLM 以结构化格式输出
EVAL_PROMPT = """请分析以下价格合规案例...

请严格按以下JSON格式输出:
{
  "is_violation": true/false,
  "cited_laws": [
    {"law": "价格法", "article": "第十四条第四项"},
    ...
  ],
  "reasoning": "..."
}"""

# 方案2（兜底）: 从自然语言输出中用正则提取法条
# 复用 violation_type_discovery.py 中的 LawCitationExtractor
```

### 执行步骤

1. 实现 `eval_framework.py`，包含上述 `evaluate_legal_retrieval` 和 `evaluate_dataset`
2. 实现 `run_baseline.py` — 纯 LLM 推理（不检索）
3. 实现 `run_rag.py` — LLM + 法条知识库检索
4. 实现 `run_agent.py` — 现有 Agent 工作流
5. 实现 `compare_results.py` — 对比三种方法、生成结果表格和图表

### 成功标准

```
✅ 三种方法的输出格式一致
✅ 评测函数支持 strict 和 relaxed 两种粒度
✅ 能生成论文可用的对比表格
✅ Baseline 的 Legal-F1 显著低于 RAG（这是核心论点）
```

---

## Task 4: Agent 代码修复 (Agent Code Fixes)

在评测之前，需要修复已知的 Agent 代码问题（Phase 1 诊断的）:

### 4.1 IntentAnalyzer 过度分流

```python
# 问题: 当前 IntentAnalyzer 70%+ 输出"需进一步分析"，导致大量case被踢到fallback
# 修复: 简化意图分类，只区分 3 类:
#   - "price_violation_analysis" (价格合规分析) → 主流程
#   - "general_legal_query" (一般法律咨询) → 简单回答
#   - "unclear" (不清楚) → 要求补充信息
# 对于评测数据集，所有case都应走 "price_violation_analysis"
```

### 4.2 Grader 评分逻辑

```python
# 问题: coverage_score 依赖关键词硬匹配，不适合评估法条引用
# 修复: 改为基于 article_key 的匹配:
#   1. 从 Agent 输出中提取引用的法条（用正则）
#   2. 与知识库中的法条做匹配
#   3. 计算覆盖率
```

### 4.3 Reflector 触发条件

```python
# 问题: 反思几乎从不触发
# 修复: 当 Grader 发现以下情况时触发反思:
#   - Agent 输出为"违规"但未引用任何法条
#   - Agent 引用了互相矛盾的法条（如同时引用第13条明码标价和第14条价格欺诈）
#   - Agent 引用的法条与检测到的违规类型不匹配
```

### 优先级

Agent 修复可以和 Task 1-3 并行。但评测必须在 Task 1 + Task 2 + Task 3 完成后才能跑。

---

## 执行顺序总结

```
Phase 2 Timeline:

Week 1: Task 1 (数据集提取)
  ├── Step 1.1: 筛选候选 (1h)
  ├── Step 1.2: 拆分法条类型 (2h)
  ├── Step 1.3: 构建case_description + 去泄露 (3h)
  ├── Step 1.4: LLM补充结构化 (2h, 需API)
  └── Step 1.5: 构建合规样本 (2h, 需API)

Week 1: Task 2 (法条知识库) — 可与Task 1并行
  ├── 下载法律全文 (1h)
  ├── 拆分chunk + 生成article_key (2h)
  └── 生成tags和scenarios (1h, 需API)

Week 2: Task 3 (评测框架)
  ├── 实现eval_framework.py (2h)
  ├── 实现run_baseline.py (2h)
  ├── 调整run_rag.py (3h, 需对接法条知识库)
  └── 实现compare_results.py (1h)

Week 2: Task 4 (Agent修复) — 可与Task 3并行
  ├── IntentAnalyzer简化 (1h)
  ├── Grader逻辑重写 (2h)
  └── Reflector触发条件 (1h)

Week 3: 跑评测 + 分析结果 + 写论文实验章节
```

---

## 关键文件清单

| 文件 | 说明 | 依赖 |
|------|------|------|
| `scan_results_v2.jsonl` | Phase 1 扫描结果 (787条) | 已有 |
| `violation_taxonomy.md` | 违规类型分类体系 | 已有 |
| `violation_type_discovery.py` | PDF扫描脚本 (v2) | 已有 |
| `eval_dataset_v3.jsonl` | **新建** - 黄金测试集 | Task 1 输出 |
| `legal_knowledge_base.jsonl` | **新建** - 法条知识库 | Task 2 输出 |
| `eval_framework.py` | **新建** - 评测函数 | Task 3 输出 |
| `run_baseline.py` | **新建** - Baseline推理 | Task 3 输出 |
| `run_rag.py` | **修改** - RAG推理(对接新知识库) | Task 3 输出 |
| `run_agent.py` | **修改** - Agent推理 | Task 4 输出 |
| `compare_results.py` | **新建** - 结果对比 | Task 3 输出 |

---

## 重要注意事项 (Critical Notes)

### ❌ 绝对不做的事
1. **不改写原文** — case_description 和 legal_analysis_reference 必须是处罚文书原文
2. **不用 LLM 生成 ground truth 法条** — ground truth 来自 PDF 中已提取的 citation_keys
3. **不在 case_description 中泄露答案** — 不能包含法律分析结论和法条引用
4. **不用 qwen-8b 做任何改写** — 这会重蹈同源污染的覆辙

### ✅ 必须做的事
1. **区分定性法条和处罚法条** — 只用定性法条作为检索评测的 ground truth
2. **保留 article_key 格式一致性** — 数据集、知识库、评测函数三方统一
3. **记录每条case的处理日志** — 方便回溯和质量审核
4. **先跑小批量验证** — 每个 Task 先用 20 条做 pilot test，确认无误再全量跑
