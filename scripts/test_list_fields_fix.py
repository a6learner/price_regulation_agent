"""
测试所有字段的list类型处理
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.baseline.response_parser import ResponseParser

def test_list_fields():
    """测试所有可能为list的字段"""

    parser = ResponseParser()

    # 测试用例1: violation_type为list
    test_case_1 = {
        'is_violation': True,
        'violation_type': ['虚构原价', '虚假折扣'],
        'confidence': 0.95,
        'reasoning': '这是推理过程',
        'legal_basis': '价格法第十四条'
    }

    # 测试用例2: reasoning为list
    test_case_2 = {
        'is_violation': True,
        'violation_type': '价格误导',
        'confidence': 0.9,
        'reasoning': ['经查明', '商家标注的原价不真实', '构成价格欺诈'],
        'legal_basis': '价格法第十四条'
    }

    # 测试用例3: legal_basis为list
    test_case_3 = {
        'is_violation': True,
        'violation_type': '虚构原价',
        'confidence': 0.92,
        'reasoning': '这是推理过程',
        'legal_basis': ['价格法第十四条', '禁止价格欺诈行为的规定']
    }

    # 测试用例4: 所有字段都是list
    test_case_4 = {
        'is_violation': True,
        'violation_type': ['虚假折扣'],
        'confidence': 0.88,
        'reasoning': ['查实商家', '存在虚假折扣行为'],
        'legal_basis': ['价格法', '明码标价规定']
    }

    # 测试用例5: 正常字符串（不应受影响）
    test_case_5 = {
        'is_violation': False,
        'violation_type': '无违规',
        'confidence': 0.85,
        'reasoning': '商家标价规范',
        'legal_basis': '符合明码标价要求'
    }

    test_cases = [
        ('violation_type为list', test_case_1),
        ('reasoning为list', test_case_2),
        ('legal_basis为list', test_case_3),
        ('所有字段都是list', test_case_4),
        ('正常字符串', test_case_5)
    ]

    print("=" * 70)
    print("测试list类型字段处理")
    print("=" * 70)

    all_passed = True

    for test_name, test_case in test_cases:
        print(f"\n[测试] {test_name}")
        print(f"  输入: {test_case}")

        try:
            normalized = parser.normalize_prediction(test_case)
            print(f"  [通过] 标准化成功")
            print(f"  输出: {normalized}")

            # 验证所有字段都是正确的类型
            assert isinstance(normalized['violation_type'], str), "violation_type应该是字符串"
            assert isinstance(normalized['reasoning'], str), "reasoning应该是字符串"
            assert isinstance(normalized['legal_basis'], str), "legal_basis应该是字符串"

            # 测试质量评估方法（之前报错的地方）
            legal_eval = parser.evaluate_legal_basis_accuracy(normalized)
            reasoning_eval = parser.evaluate_reasoning_quality(normalized)

            print(f"  [通过] 法律依据评估: {legal_eval['legal_basis_score']:.2f}")
            print(f"  [通过] 推理质量评估: {reasoning_eval['reasoning_score']:.2f}")

        except Exception as e:
            print(f"  [失败] {e}")
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("[成功] 所有测试通过！")
    else:
        print("[失败] 部分测试失败")
    print("=" * 70)

    return all_passed

if __name__ == '__main__':
    success = test_list_fields()
    sys.exit(0 if success else 1)
