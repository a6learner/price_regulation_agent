#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于现有评估案例生成变体

三种变体类型：
1. 参数变体：修改商品名、价格、平台等参数（不调用LLM，模板替换）
2. 场景变体：修改促销场景、商品品类（使用Qwen3-8B）
3. 复杂度变体：Simple→Medium, Medium→Complex（使用Qwen3-8B）

输入：data/eval/eval_159.jsonl
输出：data/eval/eval_variants_{type}.jsonl
"""

import json
import sys
import re
import random
from pathlib import Path
from typing import List, Dict, Any
from copy import deepcopy

# 添加src到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from baseline.maas_client import MaaSClient


# 商品品类库
PRODUCT_CATEGORIES = {
    "服装": ["连衣裙", "T恤", "牛仔裤", "羽绒服", "毛衣", "卫衣", "风衣", "外套", "短裤", "衬衫"],
    "数码": ["蓝牙耳机", "充电宝", "数据线", "手机壳", "智能手表", "平板电脑", "键盘", "鼠标", "音箱"],
    "食品": ["巧克力礼盒", "坚果礼包", "进口零食", "茶叶", "咖啡豆", "燕麦片", "蜂蜜", "果干"],
    "美妆": ["护肤套装", "口红", "面膜", "精华液", "粉底液", "卸妆水", "眼霜", "乳液"],
    "家居": ["床上四件套", "毛巾浴巾", "收纳箱", "抱枕", "台灯", "加湿器", "香薰", "窗帘"],
    "母婴": ["纸尿裤", "奶粉", "婴儿推车", "安全座椅", "玩具", "儿童餐具", "爬行垫"],
    "运动": ["运动鞋", "瑜伽垫", "跳绳", "哑铃", "运动水杯", "健身手套", "运动背包"],
    "图书": ["畅销小说", "考试教材", "少儿绘本", "工具书", "漫画", "杂志"]
}

# 平台列表
PLATFORMS = ["淘宝", "京东", "拼多多", "美团", "抖音", "快手", "唯品会", "小红书"]

# 场景类型
SCENARIOS = ["限时折扣", "满减活动", "会员专享", "新人特惠", "拼团优惠", "秒杀活动", "优惠券", "预售活动", "大促活动"]

# 价格范围
PRICE_RANGES = {
    "low": (99, 299),    # 低价商品
    "mid": (299, 999),   # 中价商品
    "high": (999, 2999)  # 高价商品
}


class VariantGenerator:
    """案例变体生成器"""

    def __init__(self, llm_client: MaaSClient = None):
        self.llm_client = llm_client
        self.case_id_counter = 300  # 从eval_300开始

    def generate_parameter_variant(self, original_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成参数变体（简单模板替换，不调用LLM）

        修改：商品名称、价格数值、平台名称
        保持：违规类型、违规逻辑、法律依据
        """
        variant = deepcopy(original_case)

        # 提取原始内容
        user_content = variant['messages'][1]['content']
        assistant_content = variant['messages'][2]['content']

        # 1. 替换平台
        old_platform = variant['meta'].get('platform', '淘宝')
        new_platform = random.choice([p for p in PLATFORMS if p != old_platform])
        user_content = user_content.replace(old_platform, new_platform)
        assistant_content = assistant_content.replace(old_platform, new_platform)
        variant['meta']['platform'] = new_platform

        # 2. 替换商品名称（提取现有商品名）
        product_match = re.search(r'[""\'](.*?)["\']', user_content)
        if product_match:
            old_product = product_match.group(1)
            # 从同品类选择新商品
            new_product = self._get_random_product(old_product)
            user_content = user_content.replace(old_product, new_product)
            assistant_content = assistant_content.replace(old_product, new_product)

        # 3. 替换价格（保持比例关系）
        prices = re.findall(r'(\d+)元', user_content)
        if prices:
            # 随机选择价格范围
            price_range = random.choice(list(PRICE_RANGES.values()))
            base_price = random.randint(*price_range)

            # 按比例替换所有价格
            old_prices = sorted([int(p) for p in prices], reverse=True)
            if old_prices:
                scale = base_price / old_prices[0]
                for old_price in old_prices:
                    new_price = int(old_price * scale)
                    user_content = user_content.replace(f'{old_price}元', f'{new_price}元', 1)
                    assistant_content = assistant_content.replace(f'{old_price}元', f'{new_price}元', 1)

        # 更新内容
        variant['messages'][1]['content'] = user_content
        variant['messages'][2]['content'] = assistant_content

        # 更新meta
        variant['meta']['case_id'] = f"eval_{str(self.case_id_counter).zfill(3)}"
        variant['meta']['source'] = f"parameter_variant_of_{original_case['meta']['case_id']}"
        self.case_id_counter += 1

        return variant

    def generate_scenario_variant(self, original_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成场景变体（使用LLM改写促销场景和商品品类）

        修改：促销场景、商品品类
        保持：违规类型和核心逻辑
        """
        if not self.llm_client:
            raise ValueError("场景变体需要LLM客户端")

        user_content = original_case['messages'][1]['content']
        violation_type = original_case['meta'].get('violation_type')
        old_scenario = original_case['meta'].get('scenario', '限时折扣')

        # 选择新场景和商品品类
        new_scenario = random.choice([s for s in SCENARIOS if s != old_scenario])
        new_category = random.choice(list(PRODUCT_CATEGORIES.keys()))
        new_product = random.choice(PRODUCT_CATEGORIES[new_category])
        new_platform = random.choice(PLATFORMS)

        # 使用LLM改写
        rewrite_prompt = f"""
请改写以下电商价格违规案例，要求：

1. **保持违规类型**：{violation_type}（核心违规逻辑不变）
2. **修改促销场景**：从原场景改为"{new_scenario}"
3. **修改商品品类**：改为"{new_category}"类商品，如"{new_product}"
4. **修改平台**：改为{new_platform}平台

# 原始案例（user字段）
{user_content}

# 改写要求
- 保持案例结构：监管部门查处 → 平台信息 → 案情概述 → 关键事实 → 分析请求
- 保持违规类型和核心逻辑（{violation_type}）
- 修改促销场景为"{new_scenario}"
- 修改商品为"{new_product}"
- 价格、数量等参数可以合理调整
- 保持案例的完整性和真实性

请直接输出改写后的案例描述（user字段内容），不要包含其他文字。
"""

        try:
            rewritten_user = self.llm_client.call_api(
                user_prompt=rewrite_prompt,
                system_prompt="你是一个专业的法律文书改写助手，擅长在保持核心逻辑的前提下调整案例细节。",
                max_tokens=1000,
                temperature=0.7
            )

            # 生成对应的分析回复
            analysis_prompt = rewritten_user

            analysis_response = self.llm_client.call_api(
                user_prompt=analysis_prompt,
                system_prompt=original_case['messages'][0]['content'],
                max_tokens=1200,
                temperature=0.5
            )

            # 构建变体案例
            variant = {
                "messages": [
                    original_case['messages'][0],  # system prompt不变
                    {"role": "user", "content": rewritten_user},
                    {"role": "assistant", "content": analysis_response}
                ],
                "meta": {
                    **original_case['meta'],
                    "case_id": f"eval_{str(self.case_id_counter).zfill(3)}",
                    "platform": new_platform,
                    "scenario": new_scenario,
                    "source": f"scenario_variant_of_{original_case['meta']['case_id']}"
                }
            }

            self.case_id_counter += 1
            return variant

        except Exception as e:
            print(f"[错误] 生成场景变体失败: {e}")
            return None

    def generate_complexity_variant(
        self,
        original_case: Dict[str, Any],
        target_complexity: str
    ) -> Dict[str, Any]:
        """
        生成复杂度变体

        Simple → Medium: 增加价格计算细节、多时间段对比
        Medium → Complex: 增加多商品、多活动组合
        """
        if not self.llm_client:
            raise ValueError("复杂度变体需要LLM客户端")

        user_content = original_case['messages'][1]['content']
        current_complexity = original_case['meta'].get('complexity', 'simple')

        if current_complexity == target_complexity:
            return None

        complexity_instructions = {
            "medium": """
增加以下复杂度（Simple → Medium）：
1. 添加价格计算细节（原价vs实际价的对比数据）
2. 添加多时间段的价格变动（如：活动前30天的价格记录）
3. 添加销售数据统计（销售量、销售额等）
4. 保持违规类型和核心逻辑不变
            """,
            "complex": """
增加以下复杂度（Medium → Complex）：
1. 添加多商品组合（2-3个相关商品）
2. 添加多活动组合（如：满减+优惠券叠加）
3. 添加复杂的价格计算逻辑（多层级折扣）
4. 添加跨平台价格对比
5. 保持主要违规类型，可以增加次要违规行为
            """
        }

        rewrite_prompt = f"""
请将以下电商价格违规案例的复杂度从"{current_complexity}"提升至"{target_complexity}"。

# 原始案例
{user_content}

# 复杂度提升要求
{complexity_instructions.get(target_complexity, '')}

# 改写要求
- 保持原有违规类型的核心逻辑
- 增加案例的复杂度和细节
- 保持案例的真实性和合理性
- 保持案例结构完整

请直接输出改写后的案例描述（user字段内容），不要包含其他文字。
"""

        try:
            rewritten_user = self.llm_client.call_api(
                user_prompt=rewrite_prompt,
                system_prompt="你是一个专业的法律文书改写助手，擅长在保持核心逻辑的前提下增加案例复杂度。",
                max_tokens=1500,
                temperature=0.7
            )

            # 生成对应的分析回复
            analysis_response = self.llm_client.call_api(
                user_prompt=rewritten_user,
                system_prompt=original_case['messages'][0]['content'],
                max_tokens=1500,
                temperature=0.5
            )

            # 构建变体案例
            variant = {
                "messages": [
                    original_case['messages'][0],
                    {"role": "user", "content": rewritten_user},
                    {"role": "assistant", "content": analysis_response}
                ],
                "meta": {
                    **original_case['meta'],
                    "case_id": f"eval_{str(self.case_id_counter).zfill(3)}",
                    "complexity": target_complexity,
                    "source": f"complexity_variant_of_{original_case['meta']['case_id']}"
                }
            }

            self.case_id_counter += 1
            return variant

        except Exception as e:
            print(f"[错误] 生成复杂度变体失败: {e}")
            return None

    def _get_random_product(self, old_product: str) -> str:
        """根据旧商品名推测品类，从同品类选择新商品"""
        for category, products in PRODUCT_CATEGORIES.items():
            if old_product in products:
                return random.choice([p for p in products if p != old_product])

        # 如果找不到匹配，随机选择
        category = random.choice(list(PRODUCT_CATEGORIES.keys()))
        return random.choice(PRODUCT_CATEGORIES[category])

    def generate_variants_batch(
        self,
        input_file: Path,
        output_file: Path,
        variant_type: str,
        variants_per_case: int = 1,
        filter_types: List[str] = None,
        filter_complexity: str = None,
        target_complexity: str = None,
        limit: int = None
    ) -> None:
        """
        批量生成变体

        Args:
            input_file: 输入文件（eval_159.jsonl）
            output_file: 输出文件
            variant_type: 变体类型（parameter/scenario/complexity）
            variants_per_case: 每个案例生成的变体数
            filter_types: 过滤违规类型（仅处理这些类型）
            filter_complexity: 过滤复杂度
            target_complexity: 目标复杂度（仅用于complexity类型）
            limit: 限制处理的案例数（用于测试）
        """
        print(f"[INFO] 开始生成变体案例...")
        print(f"[INFO] 变体类型: {variant_type}")
        print(f"[INFO] 输入文件: {input_file}")
        print(f"[INFO] 输出文件: {output_file}")

        # 读取原始案例
        original_cases = []
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    case = json.loads(line)
                    # 过滤
                    if filter_types and case['meta'].get('violation_type') not in filter_types:
                        continue
                    if filter_complexity and case['meta'].get('complexity') != filter_complexity:
                        continue
                    original_cases.append(case)

        if limit:
            original_cases = original_cases[:limit]

        print(f"[INFO] 筛选后待处理案例: {len(original_cases)}个")

        # 生成变体
        variants = []
        success_count = 0
        fail_count = 0

        for i, original_case in enumerate(original_cases, 1):
            case_id = original_case['meta']['case_id']
            violation_type = original_case['meta'].get('violation_type')

            print(f"\n[{i}/{len(original_cases)}] 处理: {case_id} ({violation_type})")

            for j in range(variants_per_case):
                try:
                    if variant_type == 'parameter':
                        variant = self.generate_parameter_variant(original_case)
                    elif variant_type == 'scenario':
                        variant = self.generate_scenario_variant(original_case)
                    elif variant_type == 'complexity':
                        variant = self.generate_complexity_variant(original_case, target_complexity)
                    else:
                        raise ValueError(f"未知变体类型: {variant_type}")

                    if variant:
                        variants.append(variant)
                        success_count += 1
                        print(f"  [{j+1}/{variants_per_case}] OK 生成成功: {variant['meta']['case_id']}")
                    else:
                        fail_count += 1
                        print(f"  [{j+1}/{variants_per_case}] FAIL 生成失败")

                except Exception as e:
                    fail_count += 1
                    print(f"  [{j+1}/{variants_per_case}] ERROR 异常: {e}")

        # 保存结果
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for variant in variants:
                f.write(json.dumps(variant, ensure_ascii=False) + '\n')

        # 统计报告
        print(f"\n{'='*60}")
        print(f"[完成] 变体生成完成")
        print(f"{'='*60}")
        print(f"处理案例数: {len(original_cases)}")
        print(f"生成变体数: {len(variants)}个")
        print(f"  - 成功: {success_count}")
        print(f"  - 失败: {fail_count}")
        print(f"成功率: {success_count/(success_count+fail_count)*100:.1f}%")
        print(f"输出文件: {output_file}")
        print(f"{'='*60}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='生成案例变体')
    parser.add_argument('--input', type=str,
                       default='data/eval/eval_159.jsonl',
                       help='输入文件路径')
    parser.add_argument('--output', type=str,
                       required=True,
                       help='输出文件路径')
    parser.add_argument('--variant-type', type=str,
                       required=True,
                       choices=['parameter', 'scenario', 'complexity'],
                       help='变体类型')
    parser.add_argument('--variants-per-case', type=int, default=1,
                       help='每个案例生成的变体数（默认1）')
    parser.add_argument('--filter-types', type=str, default=None,
                       help='过滤违规类型（逗号分隔，如：要素缺失,虚假折扣）')
    parser.add_argument('--filter-complexity', type=str, default=None,
                       choices=['simple', 'medium', 'complex'],
                       help='过滤复杂度')
    parser.add_argument('--target-complexity', type=str, default='medium',
                       choices=['medium', 'complex'],
                       help='目标复杂度（仅用于complexity类型）')
    parser.add_argument('--limit', type=int, default=None,
                       help='限制处理的案例数（用于测试）')
    parser.add_argument('--model', type=str, default='qwen-8b',
                       help='使用的LLM模型（默认qwen-8b）')

    args = parser.parse_args()

    # 初始化LLM客户端（仅parameter类型不需要）
    llm_client = None
    if args.variant_type in ['scenario', 'complexity']:
        config_file = Path(__file__).parent.parent / 'configs' / 'model_config.yaml'
        llm_client = MaaSClient(config_file=str(config_file), model_key=args.model)

    # 创建生成器
    generator = VariantGenerator(llm_client)

    # 解析过滤类型
    filter_types = args.filter_types.split(',') if args.filter_types else None

    # 执行生成
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = Path(__file__).parent.parent / input_path

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).parent.parent / output_path

    generator.generate_variants_batch(
        input_file=input_path,
        output_file=output_path,
        variant_type=args.variant_type,
        variants_per_case=args.variants_per_case,
        filter_types=filter_types,
        filter_complexity=args.filter_complexity,
        target_complexity=args.target_complexity,
        limit=args.limit
    )


if __name__ == '__main__':
    main()
