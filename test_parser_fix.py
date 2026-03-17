#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试response_parser修复：验证list类型violation_type的处理
"""

import sys
sys.path.insert(0, 'src')

from baseline.response_parser import ResponseParser

def test_list_violation_type():
    """测试list类型的violation_type处理"""
    parser = ResponseParser()

    # 测试1: violation_type是list
    print("=== 测试1: violation_type是list ===")
    prediction_list = {
        'is_violation': True,
        'violation_type': ['虚构原价', '虚假折扣'],  # list类型
        'confidence': 0.95,
        'reasoning': '测试推理',
        'legal_basis': '测试法律依据'
    }

    normalized = parser.normalize_prediction(prediction_list)
    print(f"输入: {prediction_list['violation_type']}")
    print(f"输出: {normalized['violation_type']}")
    print(f"类型: {type(normalized['violation_type'])}")
    assert isinstance(normalized['violation_type'], str), "应该转换为string"
    assert normalized['violation_type'] == '虚构原价', "应该取第一个元素"
    print("[通过]\n")

    # 测试2: violation_type是str
    print("=== 测试2: violation_type是str ===")
    prediction_str = {
        'is_violation': True,
        'violation_type': '价格误导',  # str类型
        'confidence': 0.95,
        'reasoning': '测试推理',
        'legal_basis': '测试法律依据'
    }

    normalized = parser.normalize_prediction(prediction_str)
    print(f"输入: {prediction_str['violation_type']}")
    print(f"输出: {normalized['violation_type']}")
    assert normalized['violation_type'] == '价格误导', "应该保持不变"
    print("[通过]\n")

    # 测试3: 比较时ground_truth也是list
    print("=== 测试3: ground_truth的violation_type是list ===")
    prediction = {'is_violation': True, 'violation_type': '虚构原价'}
    ground_truth = {'is_violation': True, 'violation_type': ['虚构原价']}

    comparison = parser.compare_prediction_with_truth(prediction, ground_truth)
    print(f"prediction: {prediction['violation_type']}")
    print(f"ground_truth: {ground_truth['violation_type']}")
    print(f"is_correct: {comparison['is_correct']}")
    print(f"type_correct: {comparison['type_correct']}")
    assert comparison['type_correct'] == True, "应该匹配成功"
    print("[通过]\n")

def test_quality_metrics():
    """测试新增的质量评估指标"""
    parser = ResponseParser()

    # 测试法律依据评估
    print("=== 测试4: 法律依据准确性评估 ===")
    prediction_with_legal = {
        'legal_basis': '《中华人民共和国价格法》第十四条规定，经营者不得利用虚假的或者使人误解的价格手段诱骗消费者。《禁止价格欺诈行为的规定》第七条...'
    }

    legal_eval = parser.evaluate_legal_basis_accuracy(prediction_with_legal)
    print(f"has_legal_basis: {legal_eval['has_legal_basis']}")
    print(f"laws_mentioned_count: {legal_eval['laws_mentioned_count']}")
    print(f"has_specific_article: {legal_eval['has_specific_article']}")
    print(f"legal_basis_score: {legal_eval['legal_basis_score']:.2f}")
    assert legal_eval['has_legal_basis'] == True
    assert legal_eval['laws_mentioned_count'] > 0
    assert legal_eval['has_specific_article'] == True
    print("[通过]\n")

    # 测试推理质量评估
    print("=== 测试5: 推理质量评估 ===")
    prediction_with_reasoning = {
        'reasoning': '经查实，该商品从未以原价销售。根据相关法规，这属于虚构原价行为。因此构成价格欺诈。'
    }

    reasoning_eval = parser.evaluate_reasoning_quality(prediction_with_reasoning)
    print(f"has_reasoning: {reasoning_eval['has_reasoning']}")
    print(f"has_facts: {reasoning_eval['has_facts']}")
    print(f"has_legal_analysis: {reasoning_eval['has_legal_analysis']}")
    print(f"has_logic_chain: {reasoning_eval['has_logic_chain']}")
    print(f"reasoning_score: {reasoning_eval['reasoning_score']:.2f}")
    assert reasoning_eval['has_reasoning'] == True
    assert reasoning_eval['has_facts'] == True
    assert reasoning_eval['has_legal_analysis'] == True
    assert reasoning_eval['has_logic_chain'] == True
    print("[通过]\n")

if __name__ == '__main__':
    print("开始测试response_parser修复...\n")
    try:
        test_list_violation_type()
        test_quality_metrics()
        print("=" * 50)
        print("所有测试通过! [成功]")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
