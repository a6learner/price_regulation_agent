"""
合规样本生成脚本 (eval_dataset_v4_final.jsonl)

三源混合策略:
  Source A (120条): 违规案例修正版 -- 用 Qwen3.5-397B
  Source B (120条): 真实商业场景构造 -- 用 MiniMax-M2.5
  Source C (60条):  边界/Hard Negative -- 混用两个模型

用法:
  python scripts/generate_compliant_samples.py --source A [--limit 5]
  python scripts/generate_compliant_samples.py --source B [--limit 5]
  python scripts/generate_compliant_samples.py --source C [--limit 5]
  python scripts/generate_compliant_samples.py --merge
"""

import json
import random
import re
import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.baseline.maas_client import MaaSClient

# ── 路径常量 ──────────────────────────────────────────────────────────────────
EVAL_V3 = Path("data/eval/eval_dataset_v3_final.jsonl")
OUT_A    = Path("data/eval/compliant_source_a.jsonl")
OUT_B    = Path("data/eval/compliant_source_b.jsonl")
OUT_C    = Path("data/eval/compliant_source_c.jsonl")
OUT_V4   = Path("data/eval/eval_dataset_v4_final.jsonl")

# ── 采样配置 ──────────────────────────────────────────────────────────────────
SOURCE_A_QUOTA = {
    "不明码标价":     55,
    "政府定价违规":   28,
    "标价外加价":     17,
    "误导性价格标示": 12,
    "__other__":       8,   # 其余类型合并
}

# ── Source B 场景定义 ─────────────────────────────────────────────────────────
SOURCE_B_SCENARIOS = {
    "超市/便利店明码标价": [
        "社区便利店日用品标价检查",
        "大型超市生鲜区价格标示",
        "便利店饮料冷柜价格检查",
        "超市进口食品价格标示",
        "社区超市节日促销活动",
        "便利店预包装食品价格标示",
        "超市家电区价格标示",
        "便利店酒类商品价格标示",
        "超市婴幼儿用品价格标示",
        "便利店早餐食品价格标示",
    ],
    "餐饮业菜单定价": [
        "中餐厅堂食菜单价格明示",
        "快餐连锁店菜单公示",
        "奶茶店饮品价格标示",
        "火锅店食材明码标价",
        "外卖平台餐厅菜单定价",
        "烘焙店产品价格标示",
        "日料餐厅套餐定价",
        "自助餐厅收费标准公示",
        "咖啡馆饮品价格标示",
        "小吃摊档价格公示",
    ],
    "电商商品定价": [
        "淘宝店铺手机壳商品定价页面",
        "京东自营家电促销活动",
        "拼多多百亿补贴商品价格",
        "抖音直播间商品价格标示",
        "天猫旗舰店双11折扣活动",
        "京东图书品类满减活动",
        "淘宝店铺服饰类目定价",
        "唯品会品牌特卖价格标示",
        "小红书店铺美妆商品定价",
        "闲鱼二手商品定价",
    ],
    "停车场/交通收费": [
        "商场地下停车场收费标准公示",
        "路边咪表停车收费标准",
        "机场停车场收费标准公示",
        "医院停车场按政府指导价收费",
        "景区停车场收费公示",
        "住宅小区停车位收费标准",
        "高速公路收费站收费公示",
        "共享单车平台计费规则",
        "网约车平台计费标准公示",
        "公共交通换乘优惠说明",
    ],
    "医疗/药品定价": [
        "零售药店处方药价格标示",
        "连锁药店OTC药品价格展示",
        "诊所诊疗费用公示",
        "医疗美容机构项目收费公示",
        "体检机构套餐价格明示",
        "眼镜店镜片价格标示",
        "口腔诊所治疗收费公示",
        "中医馆针灸推拿收费标准",
        "药店保健品价格标示",
        "医院自费项目收费公示",
    ],
    "加油站油品定价": [
        "中石化加油站92号汽油定价",
        "中石油加油站95号汽油价格公示",
        "民营加油站油品价格标示",
        "高速公路服务区加油站收费",
        "加油站非油品商品价格标示",
        "LNG加气站燃气价格公示",
        "电动车充电桩收费标准公示",
        "加油站洗车服务收费",
        "加油站便利店商品价格标示",
        "柴油价格公示",
    ],
    "教育培训收费": [
        "K12辅导机构课程收费公示",
        "少儿编程培训机构收费标准",
        "成人职业技能培训收费",
        "艺术培训机构课时费公示",
        "体育培训机构课程价格",
        "语言培训机构收费标准",
        "在线教育平台课程定价",
        "幼儿园托班收费公示",
        "驾校培训收费标准",
        "考研培训机构收费说明",
    ],
    "物业/水电费收费": [
        "住宅小区物业费收取标准",
        "写字楼物业管理费公示",
        "居民用电阶梯电价说明",
        "居民用水计费标准公示",
        "天然气居民用气价格",
        "物业停车费收取标准",
        "小区公共设施维修费说明",
        "供暖费用计算标准公示",
        "电梯使用管理费收取",
        "垃圾处理费收费标准",
    ],
    "电商促销活动": [
        "天猫双11预售定金膨胀活动",
        "京东618全品类满减活动",
        "拼多多限时秒杀价格标示",
        "淘宝超级品牌日折扣",
        "抖音好物节商品折扣",
        "小红书品牌营销日活动",
        "唯品会限时闪购活动",
        "苏宁易购以旧换新补贴",
        "当当网图书满减促销",
        "网易严选年货节活动",
    ],
    "线下服务(美容/维修)": [
        "美容院护肤项目价格公示",
        "理发店男士剪发收费",
        "汽车4S店保养项目明码标价",
        "家电维修上门服务收费",
        "手机维修店屏幕更换价格",
        "干洗店衣物清洗收费标准",
        "健身房会员卡价格公示",
        "足疗按摩店项目价格",
        "装修公司报价项目明细",
        "宠物医院诊疗收费标准",
    ],
    "O2O平台定价(美团/大众点评)": [
        "美团外卖餐厅团购套餐价格",
        "大众点评优惠券使用规则",
        "美团酒店预订价格显示",
        "滴滴打车计费规则公示",
        "饿了么平台餐厅定价",
        "美团买菜生鲜价格标示",
        "携程酒店价格明示",
        "高德地图打车服务定价",
        "美团单车骑行收费说明",
        "口碑平台商家优惠活动",
    ],
    "房地产/租赁定价": [
        "新建商品房销售价格公示",
        "二手房中介费收取标准",
        "租房平台房源租金标示",
        "长租公寓收费标准公示",
        "商铺租金价格标示",
        "写字楼租赁价格明示",
        "停车位出售/出租价格公示",
        "房屋中介费收费规则",
        "短租民宿平台定价",
        "厂房租赁收费标准",
    ],
}

# ── Source C 边界场景定义 ─────────────────────────────────────────────────────
SOURCE_C_TYPES = {
    "C1_合法原价标注": {
        "desc": '合法使用"原价"标注（有真实交易记录）',
        "scenarios": [
            "电商平台宠物医疗套餐，标注原价1680元，折后188元，有历史成交记录",
            "美容院脱毛套餐，标注原价3800元，现价980元，有3个月内成交记录",
            "在线教育课程，标注原价2680元，限时特惠598元，历史销售记录可查",
            "健身房年卡，标注原价3600元，现价1280元，节前有以3600元销售的记录",
            "电商平台家用电器，标注原价5999元，活动价3299元，30日内有原价成交",
            "珠宝首饰，标注原价18800元，特惠价9800元，活动前30日有原价销售记录",
            "母婴用品，标注原价698元，促销价398元，上月有以698元成交的订单",
            "家具定制，标注原价12800元，现价8600元，历史订单记录中有原价成交",
            "户外运动装备，标注原价2980元，特价1680元，季末有原价销售记录",
            "汽车配件，标注原价1580元，活动价880元，近期有多笔原价成交",
        ],
    },
    "C2_合法价格差异": {
        "desc": "合法价格差异（不同规格/配置）",
        "scenarios": [
            "手机壳商品，首页展示基础款9.9元，详情页另有磁吸防摔款19.9元，属不同规格",
            "蛋糕店，6寸蛋糕138元，8寸蛋糕188元，同款不同尺寸规格",
            "电商平台床上四件套，标准版198元与高端版398元，面料与工艺不同",
            "软件订阅服务，月付版25元/月与年付版198元/年，费率不同但均已明示",
            "停车场，首小时8元/小时，超出后5元/小时，分段计费已在入口公示",
            "餐厅套餐，工作日午市68元，周末88元，节假日溢价已在菜单注明",
            "酒店客房，标准间358元与高级套间698元，房型配置不同价格不同",
            "汽车保养套餐，普通机油保养380元与全合成机油保养580元，品质不同",
            "网约车，经济型15元起步与商务型25元起步，车型服务等级不同",
            "健身课程，团操课50元/次与私教课280元/次，服务内容不同",
        ],
    },
    "C3_合法浮动定价": {
        "desc": "合法浮动定价（市场调节价，属正常波动）",
        "scenarios": [
            "蔬菜批发市场白菜价格因暴雨供应减少从1.2元涨至1.8元，属正常市场波动",
            "海鲜市场活虾因季节性因素从38元/斤涨至55元/斤，进货成本同步上涨",
            "鸡蛋零售商在禽流感疫情期间价格从4.8元/斤上调至6.2元/斤，进价同步涨",
            "花卉市场玫瑰在情人节前后从8元/支涨至25元/支，节后恢复正常价格",
            "建材市场木材价格因原材料成本上升从480元/立方米上涨至560元/立方米",
            "网约车在恶劣天气下动态调价，高峰系数1.5倍已在APP内明确告知用户",
            "酒店在春节黄金周期间价格从平时880元/晚调整为1680元/晚，属市场调节",
            "农贸市场猪肉价格随收购价波动，从22元/斤调整至28元/斤，成本同步变化",
            "物流公司在节假日旺季运费上浮20%，已在官网提前公告调价通知",
            "加油站附近民营停车场在展会期间从10元/次调整为15元/次，属市场调节价",
        ],
    },
    "C4_合法比较价格": {
        "desc": "合法使用比较价格（标注数据来源，价格有依据）",
        "scenarios": [
            "商品标注'市场参考价58元（数据来源：京东平台同款均价）'，实售39元，京东同款均价56-62元可查",
            "电商商家标注'线下门店价格128元'，线上售价89元，线下门店实际售价128元可核实",
            "护肤品标注'专柜价格680元（数据来源：品牌官网）'，特卖价338元，官网同款确为680元",
            "二手平台商品标注'全新官方售价：3299元'，二手售价1800元，官网当前售价3299元",
            "团购商品标注'到店消费价：388元/位'，团购价268元/位，门店菜单展示价确为388元",
            "建材商标注'其他品牌同规格参考价：85元/平方米（来源：市建材协会指导价）'，本店售价72元",
            "保险公司标注'行业平均保费：1580元（来源：监管部门行业数据）'，本款产品费率1280元",
            "电器商品标注'厂商建议零售价：2999元（见产品包装箱）'，实际售价2499元，包装确有标注",
            "餐厅标注'同类菜品市场均价：68元（来源：美食点评平台）'，本店售价52元，平台均价可查",
            "装修公司标注'同等工艺市场报价区间：280-320元/平方米（来源：行业协会）'，本公司报价260元",
        ],
    },
    "C5_促销规则执行正确": {
        "desc": "促销活动规则执行正确（描述复杂但实际执行一致）",
        "scenarios": [
            "满300减50活动，消费者实付298元时未享受优惠，与活动规则一致，无多收",
            "双11预售定金100元可抵300元，消费者支付尾款时系统正确扣除200元差价",
            "买一送一活动，赠品与促销页面标注的商品完全一致，无替换低价商品",
            "会员折扣9折活动，收银台实际按9折结算，与会员协议约定一致",
            "团购优惠券规则注明'每桌限用一张'，消费者到店使用时按规则执行无异议",
            "外卖平台满49元免配送费活动，消费者订单金额达标后系统自动免除配送费",
            "积分兑换活动，100积分兑换5元券，消费者实际使用时按约定折算无误",
            "限时闪购99元特价，活动页面标明限量200件，售完后商品恢复原价无后台调整",
            "老客专属8折券，系统验证消费者身份后正确应用折扣，新客无法使用",
            "拼团成功享受6折，拼团页面明确标注拼团价格，成团后按标注价格结算",
        ],
    },
    "C6_附加条件已明确标注": {
        "desc": "标价中有附加消费条件但已在显著位置清晰标注",
        "scenarios": [
            "餐厅标注'最低消费200元/桌'，在菜单封面及入口处均有醒目告示",
            "停车场标注'前30分钟免费，之后5元/小时'，入口处大字告示牌清晰可见",
            "酒店早餐标注'含早餐（限2位成人，额外加人需补差价48元/位）'，预订页面已注明",
            "电商商品标注'需购满3件享受此价格，不足3件恢复原价'，商品详情页显著位置标注",
            "美容院护理套餐标注'疗程价格，需购买完整疗程（10次）'，合同首页明确注明",
            "健身房年卡标注'含私教课2节（限本店使用，需提前预约）'，会员协议有清晰说明",
            "餐厅标注'服务费10%（含在账单中）'，菜单第一页有中英文提示",
            "外卖平台标注'配送费由距离决定，此价格为基础配送费（3公里内）'，下单页面注明",
            "汽车租赁标注'基础价格不含保险，全险需加收60元/天'，预订页面价格拆分明示",
            "软件服务标注'基础版199元/年，高级功能需额外购买插件包'，定价页面有功能对比表",
        ],
    },
}


# ── 质量检查 ──────────────────────────────────────────────────────────────────
JUDGMENT_WORDS = re.compile(r'合规|违规|不违法|未违反|符合规定|不构成违法|无违法行为|不构成|无违规')
LAW_CITATION    = re.compile(r'《.*?法》|《.*?规定》|《.*?条例》|第[一二三四五六七八九十百\d]+条')
PRICE_PATTERN   = re.compile(r'[\d,]+(?:\.\d+)?\s*元')
ENTITY_PATTERN  = re.compile(r'[\u4e00-\u9fa5]{2,}(?:店|市场|平台|公司|超市|药店|医院|学校|机构|中心|园|厅|馆|场|院|部|处)')


def quality_check(desc: str) -> tuple[bool, list[str]]:
    """返回 (passed, warnings列表)"""
    warnings = []
    if not (80 <= len(desc) <= 600):
        warnings.append(f"长度不合规: {len(desc)} 字符")
    if JUDGMENT_WORDS.search(desc):
        warnings.append(f"含判定词: {JUDGMENT_WORDS.search(desc).group()}")
    if LAW_CITATION.search(desc):
        warnings.append(f"含法条引用: {LAW_CITATION.search(desc).group()}")
    if not PRICE_PATTERN.search(desc):
        warnings.append("缺少具体价格数字")
    if not ENTITY_PATTERN.search(desc):
        warnings.append("缺少具体商业实体")
    return len(warnings) == 0, warnings


# ── 辅助工具 ──────────────────────────────────────────────────────────────────
def load_violations() -> list[dict]:
    with open(EVAL_V3, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def extract_regions(violations: list[dict]) -> list[str]:
    return [v["region"] for v in violations if v.get("region")]


def load_existing(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_record(path: Path, record: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def make_ground_truth():
    return {
        "is_violation": False,
        "violation_type": None,
        "qualifying_articles": [],
        "penalty_articles": [],
        "legal_analysis_reference": "",
        "penalty_result": "",
    }


def call_and_extract(client: MaaSClient, system_prompt: str, user_prompt: str, model_key: str) -> str | None:
    resp = client.call_model(system_prompt, user_prompt, model_key=model_key)
    if resp is None:
        return None
    return client.extract_response_text(resp)


# ── Source A ──────────────────────────────────────────────────────────────────
SYSTEM_A = "你是一位中国市场监管领域的合规专家。"

USER_A_TEMPLATE = """我会给你一段来自行政处罚决定书的违法事实描述。
请你将其修改为"合规版本"——即保留相同的商业场景（行业、商品/服务、平台），
但将违法要素修改为合规状态。

修改规则:
1. 保留: 当事人类型、行业、商品/服务类型、经营场所、时间段
2. 修改: 将违法行为改为合规行为（如"未标价"→"已按规定标价"）
3. 添加: 适当补充合规细节（如"标价签注明了品名、产地、规格、计价单位"）
4. 必须包含: 至少一处具体价格数字（如"XX元"），使描述更具体真实
5. 风格: 保持行政执法文书的客观叙事风格，不加入主观评价
6. 长度: 与原文相近（±30%）
7. 禁止: 不引用任何法律条文，不做法律分析结论
8. 禁止: 不使用"合规""违规""未违反""符合规定"等判定词

原文（违规）:
{desc}

违规类型: {vtype}

请输出修正后的合规版本（仅输出修正文本，不要其他说明）:"""


def generate_source_a(limit: int = None):
    violations = load_violations()
    regions = extract_regions(violations)

    # 分层采样
    buckets: dict[str, list] = {k: [] for k in SOURCE_A_QUOTA}
    other_types = set()
    for v in violations:
        vtype = v["ground_truth"].get("violation_type", "")
        if vtype in SOURCE_A_QUOTA:
            buckets[vtype].append(v)
        else:
            buckets["__other__"].append(v)
            other_types.add(vtype)

    sampled = []
    for key, quota in SOURCE_A_QUOTA.items():
        pool = buckets[key]
        n = min(quota, len(pool))
        sampled.extend(random.sample(pool, n))

    random.shuffle(sampled)
    if limit:
        sampled = sampled[:limit]

    existing = load_existing(OUT_A)
    existing_ids = {r["id"] for r in existing}
    start_idx = len(existing) + 1

    client = MaaSClient()
    passed = failed = skipped = 0

    print(f"[Source A] 目标: {len(sampled)} 条  已有: {len(existing)} 条")

    for i, case in enumerate(sampled):
        comp_id = f"COMP_A_{start_idx + i:03d}"
        if comp_id in existing_ids:
            skipped += 1
            continue

        desc = case["input"]["case_description"]
        vtype = case["ground_truth"].get("violation_type", "其他")
        user_prompt = USER_A_TEMPLATE.format(desc=desc, vtype=vtype)

        print(f"  [{i+1}/{len(sampled)}] {comp_id} ({vtype}) ...", end=" ", flush=True)
        text = call_and_extract(client, SYSTEM_A, user_prompt, model_key="qwen")

        if text is None:
            print("API失败，跳过")
            failed += 1
            continue

        text = text.strip()
        ok, warnings = quality_check(text)
        if not ok:
            print(f"质检失败: {warnings}")
            failed += 1
            continue

        record = {
            "id": comp_id,
            "source_pdf": None,
            "region": case.get("region") or random.choice(regions),
            "tier": 0,
            "source_type": "compliant_corrected",
            "input": {
                "case_description": text,
                "platform": case["input"].get("platform"),
                "goods_or_service": case["input"].get("goods_or_service"),
            },
            "ground_truth": make_ground_truth(),
        }
        append_record(OUT_A, record)
        passed += 1
        print(f"OK ({len(text)}字)")
        time.sleep(0.5)

    stats = client.get_statistics()
    print(f"\n[Source A] 完成: 通过{passed} / 失败{failed} / 跳过{skipped}")
    print(f"  Token使用: 输入{stats['total_input_tokens']} 输出{stats['total_output_tokens']}")


# ── Source B ──────────────────────────────────────────────────────────────────
SYSTEM_B = "你是一位中国市场监管领域的合规专家，同时也是一位有丰富执法经验的市场监管人员。"

USER_B_TEMPLATE = """请你撰写一段关于以下商业场景的事实描述，描述内容应体现该商户在价格方面的实际做法。

要求:
1. 风格: 模拟市场监管执法人员的日常检查记录，客观中性
2. 内容: 描述商户的定价/标价行为
3. 必须包含: 具体的商品/服务名称、具体价格数字、标价方式
4. 长度: 150-400字
5. 禁止: 不引用法律条文
6. 禁止: 不使用"合规""符合规定""未违反""不构成违法"等判定词

场景类别: {category}
具体场景: {scenario}
地区: {region}

请输出事实描述（仅输出描述文本）:"""


def generate_source_b(limit: int = None):
    violations = load_violations()
    regions = extract_regions(violations)

    # 展开所有场景
    all_tasks = []
    for cat, scenarios in SOURCE_B_SCENARIOS.items():
        for scenario in scenarios:
            all_tasks.append((cat, scenario))

    random.shuffle(all_tasks)
    if limit:
        all_tasks = all_tasks[:limit]

    existing = load_existing(OUT_B)
    existing_ids = {r["id"] for r in existing}
    start_idx = len(existing) + 1

    client = MaaSClient()
    passed = failed = skipped = 0

    print(f"[Source B] 目标: {len(all_tasks)} 条  已有: {len(existing)} 条")

    for i, (cat, scenario) in enumerate(all_tasks):
        comp_id = f"COMP_B_{start_idx + i:03d}"
        if comp_id in existing_ids:
            skipped += 1
            continue

        region = random.choice(regions)
        user_prompt = USER_B_TEMPLATE.format(category=cat, scenario=scenario, region=region)

        print(f"  [{i+1}/{len(all_tasks)}] {comp_id} [{cat}] {scenario[:20]}...", end=" ", flush=True)
        text = call_and_extract(client, SYSTEM_B, user_prompt, model_key="minimax")

        if text is None:
            print("API失败，跳过")
            failed += 1
            continue

        text = text.strip()
        ok, warnings = quality_check(text)
        if not ok:
            print(f"质检失败: {warnings}")
            failed += 1
            continue

        record = {
            "id": comp_id,
            "source_pdf": None,
            "region": region,
            "tier": 0,
            "source_type": "compliant_constructed",
            "input": {
                "case_description": text,
                "platform": None,
                "goods_or_service": None,
            },
            "ground_truth": make_ground_truth(),
        }
        append_record(OUT_B, record)
        passed += 1
        print(f"OK ({len(text)}字)")
        time.sleep(0.5)

    stats = client.get_statistics()
    print(f"\n[Source B] 完成: 通过{passed} / 失败{failed} / 跳过{skipped}")
    print(f"  Token使用: 输入{stats['total_input_tokens']} 输出{stats['total_output_tokens']}")


# ── Source C ──────────────────────────────────────────────────────────────────
SYSTEM_C = "你是一位中国市场监管领域的合规专家。"

USER_C_TEMPLATE = """请你构造一个"边界案例"——即表面上看起来可能涉嫌违规，但实际上有合理解释的价格行为。

边界类型: {boundary_type}
具体场景: {scenario}

要求:
1. 风格: 模拟市场监管部门现场检查的事实记录
2. 必须包含: 看似异常的价格要素（如"原价""折扣""价格差异"等），随后给出事实性解释
3. 解释应是事实性的（如"经查有真实交易记录"），而非法律判断
4. 长度: 150-400字
5. 禁止: 不引用法律条文
6. 禁止: 不使用"未违反""合规""不构成违法"等判定词

请输出事实描述:"""


def generate_source_c(limit: int = None):
    violations = load_violations()
    regions = extract_regions(violations)

    # 展开所有场景，两个模型交替使用
    all_tasks = []
    models = ["qwen", "minimax"]
    for type_key, type_info in SOURCE_C_TYPES.items():
        for idx, scenario in enumerate(type_info["scenarios"]):
            model = models[idx % 2]
            all_tasks.append((type_key, type_info["desc"], scenario, model))

    random.shuffle(all_tasks)
    if limit:
        all_tasks = all_tasks[:limit]

    existing = load_existing(OUT_C)
    existing_ids = {r["id"] for r in existing}
    start_idx = len(existing) + 1

    client = MaaSClient()
    passed = failed = skipped = 0

    print(f"[Source C] 目标: {len(all_tasks)} 条  已有: {len(existing)} 条")

    for i, (type_key, boundary_desc, scenario, model_key) in enumerate(all_tasks):
        comp_id = f"COMP_C_{start_idx + i:03d}"
        if comp_id in existing_ids:
            skipped += 1
            continue

        user_prompt = USER_C_TEMPLATE.format(boundary_type=boundary_desc, scenario=scenario)

        print(f"  [{i+1}/{len(all_tasks)}] {comp_id} [{type_key}] ({model_key}) ...", end=" ", flush=True)
        text = call_and_extract(client, SYSTEM_C, user_prompt, model_key=model_key)

        if text is None:
            print("API失败，跳过")
            failed += 1
            continue

        text = text.strip()
        ok, warnings = quality_check(text)
        if not ok:
            print(f"质检失败: {warnings}")
            failed += 1
            continue

        record = {
            "id": comp_id,
            "source_pdf": None,
            "region": random.choice(regions),
            "tier": 0,
            "source_type": "compliant_hard_negative",
            "input": {
                "case_description": text,
                "platform": None,
                "goods_or_service": None,
            },
            "ground_truth": make_ground_truth(),
        }
        append_record(OUT_C, record)
        passed += 1
        print(f"OK ({len(text)}字)")
        time.sleep(0.5)

    stats = client.get_statistics()
    print(f"\n[Source C] 完成: 通过{passed} / 失败{failed} / 跳过{skipped}")
    print(f"  Token使用: 输入{stats['total_input_tokens']} 输出{stats['total_output_tokens']}")


# ── Merge ─────────────────────────────────────────────────────────────────────
def merge():
    violations = load_violations()
    a = load_existing(OUT_A)
    b = load_existing(OUT_B)
    c = load_existing(OUT_C)

    compliant = a + b + c
    all_records = violations + compliant

    with open(OUT_V4, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 统计
    n_viol = sum(1 for r in all_records if r["ground_truth"]["is_violation"])
    n_comp = sum(1 for r in all_records if not r["ground_truth"]["is_violation"])
    source_types = {}
    for r in compliant:
        st = r.get("source_type", "unknown")
        source_types[st] = source_types.get(st, 0) + 1

    print(f"\n[Merge] 输出: {OUT_V4}")
    print(f"  总计: {len(all_records)} 条")
    print(f"  违规: {n_viol} 条 ({n_viol/len(all_records)*100:.1f}%)")
    print(f"  合规: {n_comp} 条 ({n_comp/len(all_records)*100:.1f}%)")
    print(f"  合规来源: {source_types}")


# ── 入口 ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="生成合规样本")
    parser.add_argument("--source", choices=["A", "B", "C"], help="生成哪一批")
    parser.add_argument("--limit", type=int, default=None, help="限制条数（用于Pilot测试）")
    parser.add_argument("--merge", action="store_true", help="合并所有来源到v4")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    args = parser.parse_args()

    random.seed(args.seed)

    if args.merge:
        merge()
    elif args.source == "A":
        generate_source_a(limit=args.limit)
    elif args.source == "B":
        generate_source_b(limit=args.limit)
    elif args.source == "C":
        generate_source_c(limit=args.limit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
