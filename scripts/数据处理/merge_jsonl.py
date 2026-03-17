#!/usr/bin/env python3
"""
合并多个LlamaFactory格式的JSONL文件
"""
import json
import glob

def merge_jsonl_files(input_files, output_file):
    """合并多个JSONL文件"""
    total_count = 0

    with open(output_file, 'w', encoding='utf-8') as f_out:
        for input_file in input_files:
            try:
                with open(input_file, 'r', encoding='utf-8') as f_in:
                    for line in f_in:
                        line = line.strip()
                        if line:
                            # 验证JSON格式
                            data = json.loads(line)
                            if 'messages' in data:
                                f_out.write(line + '\n')
                                total_count += 1
            except FileNotFoundError:
                print(f"文件不存在: {input_file}")
            except json.JSONDecodeError as e:
                print(f"JSON解析错误 {input_file}: {e}")

    print(f"合并完成! 总共 {total_count} 条数据")
    return total_count

if __name__ == '__main__':
    input_files = [
        'data/training/133case_llamafactory.jsonl',
        'data/training/synthetic_compliant_samples_llamafactory.jsonl',
        'data/training/synthetic_compliant_samples_2_llamafactory.jsonl'
    ]
    output_file = 'data/training/train_llamafactory.jsonl'

    merge_jsonl_files(input_files, output_file)
