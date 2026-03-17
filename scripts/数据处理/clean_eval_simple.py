#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单版本的清理脚本 - 直接处理eval_159.jsonl
"""

import json
import re
from pathlib import Path

def clean_user_message(content: str) -> str:
    """清理user message，移除答案泄露信息"""
    # 匹配"监管机关认定的违法类型为：XXX"这一行
    pattern = r'\n监管机关认定的违法类型为[：:]\s*[^\n]+。?\n'
    cleaned = re.sub(pattern, '\n', content)
    pattern2 = r'\n监管机关认定的违法类型为[：:]\s*[^\n]+\n'
    cleaned = re.sub(pattern2, '\n', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

# 文件路径
eval_file = Path(__file__).parent.parent.parent / "data" / "eval" / "eval_159.jsonl"
output_file = eval_file.parent / "eval_159_cleaned.jsonl"

print(f"处理文件: {eval_file}")

total_count = 0
cleaned_count = 0
cleaned_cases = []
processed_cases = []

# 读取并处理
with open(eval_file, 'r', encoding='utf-8') as f:
    for line_num, line in enumerate(f, 1):
        if not line.strip():
            continue
        try:
            case = json.loads(line.strip())
            total_count += 1
            
            # 查找user message
            for idx, msg in enumerate(case.get('messages', [])):
                if msg.get('role') == 'user':
                    user_content = msg.get('content', '')
                    if '监管机关认定的违法类型为' in user_content:
                        case['messages'][idx]['content'] = clean_user_message(user_content)
                        cleaned_count += 1
                        case_id = case.get('meta', {}).get('case_id', f'line_{line_num}')
                        cleaned_cases.append(case_id)
                        print(f"  ✓ 已清理: {case_id}")
                    break
            
            processed_cases.append(case)
        except Exception as e:
            print(f"错误：第{line_num}行处理失败: {e}")

# 写入输出文件
print(f"\n写入输出文件: {output_file}")
with open(output_file, 'w', encoding='utf-8') as f_out:
    for case in processed_cases:
        f_out.write(json.dumps(case, ensure_ascii=False) + '\n')

print(f"\n处理完成！")
print(f"总数据量: {total_count}条")
print(f"清理数量: {cleaned_count}条")
print(f"输出文件: {output_file}")

