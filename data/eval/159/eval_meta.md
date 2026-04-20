# 电商价格合规评估数据集统计报告

## 基本信息

- **生成日期**: 2026-03-10
- **数据文件**: eval_100.jsonl
- **总数据量**: 104条

## 数据分布统计

### 1. 违规判定分布

| 类型 | 数量 | 占比 |
|------|------|------|
| 违规案例 | 63条 | 60.6% |
| 合规案例 | 41条 | 39.4% |

### 2. 违规类型分布（违规案例内）

| 违规类型 | 数量 | 占比 |
|---------|------|------|
| 虚构原价 | 22条 | 34.9% |
| 价格误导 | 18条 | 28.6% |
| 虚假折扣 | 17条 | 27.0% |
| 要素缺失 | 5条 | 7.9% |
| 其他 | 1条 | 1.6% |

### 3. 平台分布

| 平台 | 数量 | 占比 |
|------|------|------|
| 淘宝 | 20条 | 19.2% |
| 京东 | 19条 | 18.3% |
| 拼多多 | 16条 | 15.4% |
| 美团 | 14条 | 13.5% |
| 天猫 | 13条 | 12.5% |
| 抖音 | 13条 | 12.5% |
| 其他 | 9条 | 8.7% |

### 4. 复杂度分布

| 复杂度 | 数量 | 占比 |
|--------|------|------|
| simple | 51条 | 49.0% |
| medium | 40条 | 38.5% |
| complex | 13条 | 12.5% |

### 5. 场景覆盖

数据集覆盖以下主要场景：
- 限时折扣、大促活动、秒杀活动
- 直播带货、优惠券促销、会员价
- 团购优惠、拼团活动、满减活动
- 新品上市、换季清仓、临期特卖
- 预售活动、服务定价、套餐定价
- 阶梯定价、跨店满减、社区团购
- 边界场景（价格波动、大幅折扣等）

## 数据质量说明

### 数据来源
- 基于真实电商处罚案例改编
- 参考《价格法》《明码标价和禁止价格欺诈规定》等法规
- 覆盖主流电商平台和常见违规场景

### 数据格式
- 采用OpenAI messages格式（system/user/assistant）
- 包含meta字段记录案例属性
- 支持直接用于模型评估

### 数据结构示例

```json
{
  "messages": [
    {"role": "system", "content": "系统提示词..."},
    {"role": "user", "content": "案例描述..."},
    {"role": "assistant", "content": "分析回复..."}
  ],
  "meta": {
    "case_id": "eval_001",
    "is_violation": true,
    "violation_type": "虚构原价",
    "platform": "淘宝",
    "scenario": "限时折扣",
    "complexity": "simple"
  }
}
```

### 文件列表

| 文件名 | 说明 |
|--------|------|
| eval_100.jsonl | 完整评估数据集（104条） |
| eval_meta.json | 数据集元信息（JSON格式） |
| eval_meta.md | 数据集统计报告（本文件） |

## 使用说明

```python
import json

# 读取数据
with open('eval_100.jsonl', 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f if line.strip()]

print(f"总数据量: {len(data)}条")

# 分类统计
violations = [d for d in data if d['meta']['is_violation']]
compliant = [d for d in data if not d['meta']['is_violation']]

print(f"违规案例: {len(violations)}条")
print(f"合规案例: {len(compliant)}条")

# 获取案例
for item in data:
    messages = item['messages']
    meta = item['meta']
    case_id = meta['case_id']
    is_violation = meta['is_violation']
    violation_type = meta['violation_type']
    # 进行评估...
```

## 评估指标建议

### 核心指标
1. **准确率 (Accuracy)**: 正确判断违规/不违规的比例
2. **精确率 (Precision)**: 判为违规的案例中真正违规的比例
3. **召回率 (Recall)**: 真正违规的案例中被正确识别的比例
4. **F1-Score**: 精确率和召回率的调和平均

### 分层评估
- 按复杂度分层：simple/medium/complex
- 按违规类型分层：虚构原价/虚假折扣/价格误导/要素缺失
- 按平台分层：淘宝/京东/拼多多/美团/抖音/天猫/其他

---

**数据集版本**: 1.0
**最后更新**: 2026-03-10
