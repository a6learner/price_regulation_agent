#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估数据集生成脚本 - 批量生成剩余80条评估数据
"""
import json
import random

# 系统提示词
SYSTEM_PROMPT = "你是一名电商平台价格合规审查助手,熟悉《价格法》《明码标价和禁止价格欺诈规定》及相关配套规章。你需要根据给定的案件事实,做出法律分析并给出是否违规的结论和依据。"

# 商品类目库
PRODUCT_CATEGORIES = {
    "服装": ["连衣裙", "T恤", "牛仔裤", "羽绒服", "毛衣", "卫衣", "风衣"],
    "数码": ["蓝牙耳机", "充电宝", "数据线", "手机壳", "智能手表", "平板电脑", "键盘"],
    "食品": ["巧克力礼盒", "坚果礼包", "进口零食", "茶叶", "咖啡豆", "燕麦片", "蜂蜜"],
    "美妆": ["护肤套装", "口红", "面膜", "精华液", "粉底液", "卸妆水", "眼霜"],
    "家居": ["床上四件套", "毛巾浴巾", "收纳箱", "抱枕", "台灯", "加湿器", "香薰"],
    "母婴": ["纸尿裤", "奶粉", "婴儿推车", "安全座椅", "玩具", "儿童餐具", "爬行垫"],
    "运动": ["运动鞋", "瑜伽垫", "跳绳", "哑铃", "运动水杯", "健身手套", "运动背包"],
    "图书": ["畅销小说", "考试教材", "少儿绘本", "工具书", "漫画", "杂志", "电子书卡"]
}

# 平台列表
PLATFORMS = ["淘宝", "京东", "拼多多", "美团", "抖音", "快手", "唯品会", "小红书"]

# 场景类型
SCENARIOS = ["限时折扣", "满减活动", "会员专享", "新人特惠", "拼团优惠", "秒杀活动", "优惠券", "预售活动"]

# 案例ID计数器
case_id_counter = 21  # 从21开始

def generate_violation_case_xugouyuanjia(platform, product):
    """生成虚构原价违规案例"""
    global case_id_counter
    case_id = f"eval_{str(case_id_counter).zfill(3)}"
    case_id_counter += 1

    original_price = random.choice([599, 699, 799, 899, 999, 1299, 1599])
    actual_price = random.randint(int(original_price * 0.3), int(original_price * 0.4))
    quantity = random.randint(50, 300)
    revenue = actual_price * quantity

    case_description = f"某商家在{platform}平台销售'{product}'。商品详情页标注'原价{original_price}元,特惠价{actual_price}元'。经调查核实:该商品自上架以来从未以{original_price}元的价格成交过,也无法提供近期以{original_price}元销售的交易凭证。该商品在促销活动期间共销售{quantity}件,每件售价{actual_price}元,销售额{revenue}元。请分析该经营行为是否违规,并给出法律依据。"

    analysis = f"事实要点:\\n- 商品为'{product}',在{platform}平台销售\\n- 商品详情页标注'原价{original_price}元,特惠价{actual_price}元'\\n- 该商品自上架以来从未以{original_price}元成交\\n- 无法提供近期以{original_price}元销售的交易凭证\\n- 促销期间销售{quantity}件,每件{actual_price}元,销售额{revenue}元\\n\\n合规分析:\\n- 经营者采用'原价/划线价'进行价格比较时,被比较价格应当真实、准确,并有可核验的交易记录或形成机制支撑。\\n- 若从未以划线价成交,或无法提供近期成交凭证,则该比较价格缺乏依据,容易使消费者对优惠幅度产生误解。\\n- 本案中,商品从未以{original_price}元成交,标注的'原价'属于虚构价格,诱导消费者认为获得了大幅优惠。\\n\\n结论:违规。该经营者的价格展示行为构成'虚构原价'。\\n\\n法律依据:\\n- 《明码标价和禁止价格欺诈规定》第十七条:经营者不得采用无依据或者无从比较的价格,作为折价、减价的计算基准或者被比较价格。\\n- 《中华人民共和国价格法》第十四条:经营者不得利用虚假的或者使人误解的价格手段,诱骗消费者或者其他经营者与其进行交易。\\n\\n整改建议:\\n- 立即下架或更正虚假的'原价'标注,确保展示价与实际交易情况一致。\\n- 若要使用'原价'进行价格对比,必须保留真实的历史成交记录和凭证。"

    return {
        "case_id": case_id,
        "input": {
            "system_prompt": SYSTEM_PROMPT,
            "case_description": case_description
        },
        "expected_output": {
            "analysis": analysis,
            "structured": {
                "facts": [
                    f"标注原价{original_price}元,实际从未以此价格成交",
                    "无法提供交易凭证",
                    f"促销期间以{actual_price}元销售{quantity}件"
                ],
                "compliance_analysis": "原价应有真实交易记录支撑,虚构原价诱导消费者",
                "conclusion": "违规",
                "violation_type": "虚构原价",
                "legal_basis": [
                    "《明码标价和禁止价格欺诈规定》第十七条",
                    "《中华人民共和国价格法》第十四条"
                ]
            }
        },
        "ground_truth": {
            "is_violation": True,
            "violation_type": "虚构原价",
            "platform": platform,
            "scenario": random.choice(["限时折扣", "特惠活动"]),
            "complexity": "simple"
        }
    }

def generate_compliant_case(platform, product):
    """生成不违规案例"""
    global case_id_counter
    case_id = f"eval_{str(case_id_counter).zfill(3)}"
    case_id_counter += 1

    daily_price = random.choice([358, 368, 378, 398, 428, 458, 488])
    promo_price = int(daily_price * 0.7)
    quantity = random.randint(100, 500)

    case_description = f"某专营店在{platform}平台销售'{product}'。商品页面标注:日常价{daily_price}元,促销活动期间(2025年6月1日-6月18日)特惠价{promo_price}元,活动结束后恢复日常价。经查:该商品在活动前30天的销售价格为{daily_price-20}-{daily_price+10}元之间,平均约{daily_price}元。活动期间确实以{promo_price}元价格销售,共销售{quantity}件。活动结束后(6月19日),商品价格恢复为{daily_price}元继续销售。商品页面清晰标注了活动时间、活动价格、日常价格,促销信息完整。消费者实际支付价格与活动标注一致。请分析该经营行为是否违规。"

    analysis = f"事实要点:\\n- 商品为'{product}',在{platform}平台销售\\n- 标注日常价{daily_price}元,活动价{promo_price}元(6月1-18日)\\n- 活动前30天价格{daily_price-20}-{daily_price+10}元,平均约{daily_price}元\\n- 活动期间以{promo_price}元销售{quantity}件\\n- 活动结束后恢复{daily_price}元销售\\n- 促销信息完整,实际支付价格与标注一致\\n\\n合规分析:\\n- 促销活动应当基于真实的价格变动,标注的'日常价'应有真实交易记录支撑。\\n- 本案中,标注的日常价{daily_price}元符合实际销售情况(活动前平均约{daily_price}元),活动价{promo_price}元真实执行,活动结束后按承诺恢复日常价,促销信息完整、真实。\\n- 该经营行为符合明码标价和诚实守信原则。\\n\\n结论:不违规。该经营者的促销活动价格展示和实际执行符合价格法律法规的要求。\\n\\n法律依据:\\n- 符合《明码标价和禁止价格欺诈规定》第六条关于明码标价的要求。\\n- 符合《中华人民共和国价格法》第十三条关于价格标示真实准确的要求。\\n\\n合规建议:\\n- 继续保持促销信息的完整性和真实性。\\n- 保留促销前后的价格记录和交易凭证,以备核查。"

    return {
        "case_id": case_id,
        "input": {
            "system_prompt": SYSTEM_PROMPT,
            "case_description": case_description
        },
        "expected_output": {
            "analysis": analysis,
            "structured": {
                "facts": [
                    f"日常价{daily_price}元有真实交易记录支撑",
                    f"活动价{promo_price}元真实执行",
                    "活动结束后按承诺恢复原价"
                ],
                "compliance_analysis": "促销活动基于真实价格变动,信息完整准确",
                "conclusion": "不违规",
                "violation_type": "不违规",
                "legal_basis": [
                    "《明码标价和禁止价格欺诈规定》第六条",
                    "《中华人民共和国价格法》第十三条"
                ]
            }
        },
        "ground_truth": {
            "is_violation": False,
            "violation_type": "不违规",
            "platform": platform,
            "scenario": random.choice(["限时折扣", "大促活动"]),
            "complexity": "simple"
        }
    }

def main():
    """主函数:生成80条评估数据"""
    output_file = r"D:\pdd\project\毕设\实施\price_regulation_agent\data\eval\eval_batch2_80.jsonl"

    cases = []

    # 生成12个虚构原价案例
    for i in range(12):
        category = random.choice(list(PRODUCT_CATEGORIES.keys()))
        product = random.choice(PRODUCT_CATEGORIES[category])
        platform = random.choice(PLATFORMS[:5])  # 主流平台
        case = generate_violation_case_xugouyuanjia(platform, product)
        cases.append(case)

    # 生成32个不违规案例
    for i in range(32):
        category = random.choice(list(PRODUCT_CATEGORIES.keys()))
        product = random.choice(PRODUCT_CATEGORIES[category])
        platform = random.choice(PLATFORMS[:5])
        case = generate_compliant_case(platform, product)
        cases.append(case)

    # 先写入这44条
    with open(output_file, 'w', encoding='utf-8') as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + '\n')

    print(f"已生成44条数据 (12个虚构原价违规 + 32个不违规)")
    print(f"文件保存至: {output_file}")
    print(f"\n剩余36条违规案例需要手动补充:")
    print("   - 虚假折扣: 12条")
    print("   - 价格误导: 12条")
    print("   - 要素缺失: 8条")
    print("   - 其他类型: 4条")

if __name__ == "__main__":
    main()
