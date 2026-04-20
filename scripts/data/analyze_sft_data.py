#!/usr/bin/env python3
"""分析微调数据集的特征"""
import json
from collections import Counter

def analyze_training_data(file_path, num_samples=10):
    """分析训练数据集的关键特征"""
    with open(file_path, 'r', encoding='utf-8') as f:
        samples = [json.loads(line) for line in f]

    print(f"总样本数: {len(samples)}")
    print(f"\n=== 前{num_samples}条样本分析 ===\n")

    response_lengths = []
    legal_basis_keywords = Counter()
    reasoning_keywords = Counter()

    key_laws = ['价格法', '禁止价格欺诈', '明码标价', '价格违法行为']
    reason_keywords = ['经查', '查实', '根据', '违反', '构成', '因此', '所以']

    for i, sample in enumerate(samples[:num_samples], 1):
        response = sample['conversations'][1]['value']
        response_lengths.append(len(response))

        # 检查法律依据部分
        if '主要依据：' in response:
            legal_part = response.split('主要依据：')[1].split('\n')[0]
            print(f"Sample {i} 法律依据长度: {len(legal_part)}")
            print(f"  内容: {legal_part[:100]}...")

            for law in key_laws:
                if law in legal_part:
                    legal_basis_keywords[law] += 1

        # 检查推理部分
        if '合规分析：' in response:
            analysis_part = response.split('合规分析：')[1].split('\n\n')[0]
            print(f"  合规分析长度: {len(analysis_part)}")

            for kw in reason_keywords:
                if kw in analysis_part:
                    reasoning_keywords[kw] += 1

        print()

    print(f"\n=== 整体统计 ===")
    print(f"平均响应长度: {sum(response_lengths) / len(response_lengths):.1f} 字符")
    print(f"最短响应: {min(response_lengths)} 字符")
    print(f"最长响应: {max(response_lengths)} 字符")

    print(f"\n=== 关键词统计（前{num_samples}条）===")
    print(f"法律关键词: {dict(legal_basis_keywords)}")
    print(f"推理关键词: {dict(reasoning_keywords)}")

if __name__ == "__main__":
    analyze_training_data(
        "D:/pdd/project/graduation_project/implement/price_regulation_agent/data/sft/training/train_sharegpt.jsonl",
        num_samples=10
    )
