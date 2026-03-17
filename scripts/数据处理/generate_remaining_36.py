#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成剩余36条违规案例
"""
import json
import random

SYSTEM_PROMPT = "你是一名电商平台价格合规审查助手,熟悉《价格法》《明码标价和禁止价格欺诈规定》及相关配套规章。你需要根据给定的案件事实,做出法律分析并给出是否违规的结论和依据。"

# 商品库
PRODUCTS = {
    "服装": ["连衣裙", "羽绒服", "牛仔裤", "毛衣", "T恤", "风衣", "衬衫", "外套", "裤子", "裙子"],
    "数码": ["手机", "耳机", "充电宝", "数据线", "键盘", "鼠标", "音箱", "手环", "相机", "平板"],
    "食品": ["坚果", "巧克力", "茶叶", "咖啡", "零食", "饼干", "糖果", "果干", "蜂蜜", "麦片"],
    "美妆": ["口红", "粉底", "面膜", "精华", "护肤品", "香水", "眼影", "睫毛膏", "卸妆", "防晒"],
    "家居": ["床品", "毛巾", "收纳", "灯具", "餐具", "厨具", "抱枕", "地毯", "窗帘", "挂钟"],
    "母婴": ["奶粉", "纸尿裤", "玩具", "童装", "奶瓶", "推车", "座椅", "辅食", "爬行垫", "浴盆"],
    "图书": ["小说", "教材", "绘本", "工具书", "漫画", "字典", "杂志", "电子书", "音像", "文具"],
    "运动": ["运动鞋", "瑜伽垫", "哑铃", "跳绳", "运动服", "泳装", "球拍", "护具", "水杯", "背包"]
}

PLATFORMS = ["淘宝", "京东", "拼多多", "美团", "抖音"]

case_id = 65  # 从65开始

def gen_xujiazhekou():
    """虚假折扣案例生成器"""
    global case_id
    cases = []

    templates = [
        {
            "desc": lambda p, prod, daily, fake: f"某商家在{p}平台销售'{prod}'。商品页面显示'限时大促,5折优惠',标注'日常价{fake}元,活动价{daily}元'。经调查:该商品在过去3个月的实际销售价格一直为{daily-20}-{daily+20}元之间波动,并非{fake}元。活动期间以{daily}元销售{random.randint(80,150)}件。请分析该经营行为是否违规,并给出法律依据。",
            "analysis_key": lambda fake, daily: f"标注日常价{fake}元虚高,实际日常价{daily}元左右,折扣不实",
            "legal": ["《明码标价和禁止价格欺诈规定》第十九条", "《价格违法行为行政处罚规定》第七条"]
        },
        {
            "desc": lambda p, prod, daily, fake: f"某店铺在{p}销售'{prod}'。商品详情页标注'原价{fake}元,现价{daily}元,立减{fake-daily}元'。经核查:该商品从未以{fake}元销售,实际一直以{daily-10}-{daily+10}元价格出售。促销期间销售{random.randint(100,200)}件,每件{daily}元。请分析该行为是否违规。",
            "analysis_key": lambda fake, daily: f"从未以原价{fake}元销售,虚构立减金额",
            "legal": ["《明码标价和禁止价格欺诈规定》第十九条", "《中华人民共和国价格法》第十四条"]
        }
    ]

    for _ in range(12):
        cat = random.choice(list(PRODUCTS.keys()))
        prod = random.choice(PRODUCTS[cat])
        plat = random.choice(PLATFORMS)
        daily_price = random.choice([188, 228, 268, 298, 328, 358, 398])
        fake_price = daily_price * 2

        template = random.choice(templates)
        desc = template["desc"](plat, prod, daily_price, fake_price)
        key = template["analysis_key"](fake_price, daily_price)

        case = {
            "case_id": f"eval_{str(case_id).zfill(3)}",
            "input": {
                "system_prompt": SYSTEM_PROMPT,
                "case_description": desc
            },
            "expected_output": {
                "analysis": f"事实要点:\\n{desc.split('。')[0]}等核心事实\\n\\n合规分析:\\n{key},构成虚假折扣。\\n\\n结论:违规。该经营者的行为构成'虚假折扣'。\\n\\n法律依据:\\n" + "\\n".join([f"- {law}" for law in template["legal"]]),
                "structured": {
                    "facts": [key, f"销售{random.randint(80,200)}件"],
                    "compliance_analysis": "虚假折扣,误导消费者",
                    "conclusion": "违规",
                    "violation_type": "虚假折扣",
                    "legal_basis": template["legal"]
                }
            },
            "ground_truth": {
                "is_violation": True,
                "violation_type": "虚假折扣",
                "platform": plat,
                "scenario": random.choice(["限时折扣", "大促活动"]),
                "complexity": "simple"
            }
        }
        cases.append(case)
        case_id += 1

    return cases

def gen_jiagewd():
    """价格误导案例"""
    global case_id
    cases = []

    for _ in range(12):
        cat = random.choice(list(PRODUCTS.keys()))
        prod = random.choice(PRODUCTS[cat])
        plat = random.choice(PLATFORMS)
        show_price = random.choice([9.9, 19.9, 29.9, 39.9])
        real_price = show_price * 3

        desc = f"某商家在{plat}销售'{prod}'。首页宣传标注'限时{show_price}元包邮',但点击进入商品详情页后发现,商品实际售价为{real_price}元,仅在满足'拼团+领券+满减'三个条件同时满足时才能达到{show_price}元。由于条件苛刻,大部分消费者无法凑齐,实际成交价{real_price-10}-{real_price}元。该商品销售{random.randint(200,400)}件,平均成交价{real_price-5}元。请分析该经营行为是否违规,并给出法律依据。"

        case = {
            "case_id": f"eval_{str(case_id).zfill(3)}",
            "input": {
                "system_prompt": SYSTEM_PROMPT,
                "case_description": desc
            },
            "expected_output": {
                "analysis": f"事实要点:\\n展示价{show_price}元需满足苛刻条件,实际成交价{real_price-5}元\\n\\n合规分析:\\n展示价格与实际成交价差距大,优惠条件未明示,构成价格误导。\\n\\n结论:违规。该经营者的行为构成'价格误导'。\\n\\n法律依据:\\n- 《明码标价和禁止价格欺诈规定》第六条\\n- 《中华人民共和国价格法》第十四条",
                "structured": {
                    "facts": [f"展示{show_price}元但需苛刻条件", f"实际成交价{real_price-5}元"],
                    "compliance_analysis": "展示价与实际价差距大,条件未明示",
                    "conclusion": "违规",
                    "violation_type": "价格误导",
                    "legal_basis": [
                        "《明码标价和禁止价格欺诈规定》第六条",
                        "《中华人民共和国价格法》第十四条"
                    ]
                }
            },
            "ground_truth": {
                "is_violation": True,
                "violation_type": "价格误导",
                "platform": plat,
                "scenario": random.choice(["拼团优惠", "优惠券"]),
                "complexity": "medium"
            }
        }
        cases.append(case)
        case_id += 1

    return cases

def gen_yaosuqueshi():
    """要素缺失案例"""
    global case_id
    cases = []

    templates = [
        "某商家在{plat}销售'{prod}'。商品页面标注'限时特惠价{price}元',但未标明活动期限。经查:该商品自2025年3月起一直以此价格销售,实际并非'限时'。销售{qty}件。请分析是否违规。",
        "某店铺在{plat}销售'{prod}'。页面显示'满减优惠',但未标明满减条件和优惠金额。消费者购买后才发现需满399元减50元,部分消费者反映受到误导。请分析是否违规。",
        "某商家在{plat}销售'{prod}'。标注'限量抢购',但未标明限量数量。经查:该商品库存充足,已销售800件仍在继续销售。请分析是否违规。"
    ]

    for _ in range(8):
        cat = random.choice(list(PRODUCTS.keys()))
        prod = random.choice(PRODUCTS[cat])
        plat = random.choice(PLATFORMS)
        price = random.choice([99, 129, 159, 189, 219])
        qty = random.randint(100, 300)

        desc = random.choice(templates).format(plat=plat, prod=prod, price=price, qty=qty)

        case = {
            "case_id": f"eval_{str(case_id).zfill(3)}",
            "input": {
                "system_prompt": SYSTEM_PROMPT,
                "case_description": desc
            },
            "expected_output": {
                "analysis": f"事实要点:\\n促销信息未标明关键要素(期限/条件/数量)\\n\\n合规分析:\\n促销活动应明确标示关键要素,否则易误导消费者,构成要素缺失。\\n\\n结论:违规。该经营者的行为构成'要素缺失'。\\n\\n法律依据:\\n- 《明码标价和禁止价格欺诈规定》第六条\\n- 《明码标价和禁止价格欺诈规定》第八条",
                "structured": {
                    "facts": ["促销信息未标明关键要素", "消费者易受误导"],
                    "compliance_analysis": "缺失期限/条件/数量等关键要素",
                    "conclusion": "违规",
                    "violation_type": "要素缺失",
                    "legal_basis": [
                        "《明码标价和禁止价格欺诈规定》第六条",
                        "《明码标价和禁止价格欺诈规定》第八条"
                    ]
                }
            },
            "ground_truth": {
                "is_violation": True,
                "violation_type": "要素缺失",
                "platform": plat,
                "scenario": random.choice(["限时活动", "满减活动", "限量抢购"]),
                "complexity": "simple"
            }
        }
        cases.append(case)
        case_id += 1

    return cases

def gen_qita():
    """其他类型违规"""
    global case_id
    cases = []

    templates = [
        {
            "desc": "某商家在{plat}销售'{prod}'。商品标注'会员价{price1}元,非会员价{price2}元',但实际结算时所有用户均按{price2}元收费,会员并未享受优惠。销售{qty}件。请分析是否违规。",
            "type": "虚假会员价",
            "key": "标注会员优惠但实际未执行"
        },
        {
            "desc": "某店铺在{plat}销售'{prod}'。页面标注价格{price}元,但结算时自动添加{random.choice([5,8,10])}元'包装费',未事先明示。消费者投诉标价外加价。销售{qty}件。请分析是否违规。",
            "type": "标价外加价",
            "key": "结算时额外收取未明示费用"
        }
    ]

    for _ in range(4):
        cat = random.choice(list(PRODUCTS.keys()))
        prod = random.choice(PRODUCTS[cat])
        plat = random.choice(PLATFORMS)
        price1 = random.choice([188, 228, 268])
        price2 = price1 + 30
        qty = random.randint(80, 200)

        template = random.choice(templates)
        desc = template["desc"].format(plat=plat, prod=prod, price1=price1, price2=price2, price=price1, qty=qty)

        case = {
            "case_id": f"eval_{str(case_id).zfill(3)}",
            "input": {
                "system_prompt": SYSTEM_PROMPT,
                "case_description": desc
            },
            "expected_output": {
                "analysis": f"事实要点:\\n{template['key']}\\n\\n合规分析:\\n{template['key']},违反明码标价规定。\\n\\n结论:违规。该经营者的行为构成'{template['type']}'。\\n\\n法律依据:\\n- 《明码标价和禁止价格欺诈规定》第八条\\n- 《中华人民共和国价格法》第十三条",
                "structured": {
                    "facts": [template['key']],
                    "compliance_analysis": "违反明码标价规定",
                    "conclusion": "违规",
                    "violation_type": "其他",
                    "legal_basis": [
                        "《明码标价和禁止价格欺诈规定》第八条",
                        "《中华人民共和国价格法》第十三条"
                    ]
                }
            },
            "ground_truth": {
                "is_violation": True,
                "violation_type": "其他",
                "platform": plat,
                "scenario": random.choice(["会员优惠", "标价外收费"]),
                "complexity": "simple"
            }
        }
        cases.append(case)
        case_id += 1

    return cases

def main():
    """生成36条违规案例"""
    all_cases = []

    # 12个虚假折扣
    all_cases.extend(gen_xujiazhekou())

    # 12个价格误导
    all_cases.extend(gen_jiagewd())

    # 8个要素缺失
    all_cases.extend(gen_yaosuqueshi())

    # 4个其他类型
    all_cases.extend(gen_qita())

    # 追加到文件
    output_file = r"D:\pdd\project\毕设\实施\price_regulation_agent\data\eval\eval_batch2_80.jsonl"
    with open(output_file, 'a', encoding='utf-8') as f:
        for case in all_cases:
            f.write(json.dumps(case, ensure_ascii=False) + '\n')

    print(f"已追加36条违规案例到文件")
    print(f"文件: {output_file}")
    print(f"总计: 44 + 36 = 80条")

if __name__ == "__main__":
    main()
