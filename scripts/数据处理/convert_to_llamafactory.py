#!/usr/bin/env python3
"""
将LlamaFactory不兼容的格式转换为正确的OpenAI格式
- 移除meta字段，保存到单独文件
- 只保留messages字段
"""
import json
import sys

def convert_to_llamafactory_format(input_file, output_file, meta_file):
    """转换JSONL文件格式"""
    converted_count = 0
    error_count = 0

    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out, \
         open(meta_file, 'w', encoding='utf-8') as f_meta:

        for line_num, line in enumerate(f_in, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)

                # 只保留messages字段
                if 'messages' in data:
                    new_data = {'messages': data['messages']}
                    f_out.write(json.dumps(new_data, ensure_ascii=False) + '\n')
                    converted_count += 1

                    # 保存meta数据
                    if 'meta' in data:
                        f_meta.write(json.dumps(data['meta'], ensure_ascii=False) + '\n')
                    else:
                        f_meta.write(json.dumps({}, ensure_ascii=False) + '\n')
                else:
                    print(f"警告: 第{line_num}行缺少messages字段")
                    error_count += 1

            except json.JSONDecodeError as e:
                print(f"错误: 第{line_num}行JSON解析失败: {e}")
                error_count += 1

    print(f"\n转换完成!")
    print(f"成功转换: {converted_count} 条")
    print(f"失败: {error_count} 条")
    print(f"LlamaFactory格式: {output_file}")
    print(f"Meta数据: {meta_file}")

if __name__ == '__main__':
    # 默认转换133case.jsonl
    input_file = 'data/training/133case.jsonl'
    output_file = 'data/training/133case_llamafactory.jsonl'
    meta_file = 'data/training/133case_meta.jsonl'

    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    if len(sys.argv) >= 4:
        meta_file = sys.argv[3]

    convert_to_llamafactory_format(input_file, output_file, meta_file)
