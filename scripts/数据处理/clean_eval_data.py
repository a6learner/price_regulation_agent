#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理eval数据集 - 移除user message中的答案泄露信息
移除"监管机关认定的违法类型为：XXX"这一行，因为这会泄露答案
"""

import json
import re
from pathlib import Path


def clean_user_message(content: str) -> str:
    """
    清理user message，移除"监管机关认定的违法类型为：XXX"这一行
    
    Args:
        content: 原始user message内容
        
    Returns:
        清理后的user message内容
    """
    # 匹配"监管机关认定的违法类型为：XXX"这一行（可能包含前后的换行）
    # 使用正则表达式匹配，包括可能的标点符号变化
    pattern = r'\n监管机关认定的违法类型为[：:]\s*[^\n]+。?\n'
    
    # 替换为空字符串
    cleaned = re.sub(pattern, '\n', content)
    
    # 如果还有残留（可能没有句号），再尝试一次
    pattern2 = r'\n监管机关认定的违法类型为[：:]\s*[^\n]+\n'
    cleaned = re.sub(pattern2, '\n', cleaned)
    
    # 清理可能出现的连续换行（最多保留两个换行）
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned.strip()


def process_eval_file(input_path: str, output_path: str = None):
    """
    处理eval数据文件，移除答案泄露信息
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径，如果为None则覆盖原文件
    """
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"错误：文件不存在 {input_path}")
        return
    
    if output_path is None:
        output_path = input_path
    else:
        output_path = Path(output_path)
    
    # 统计信息
    total_count = 0
    cleaned_count = 0
    cleaned_cases = []
    processed_cases = []
    
    print(f"正在处理文件: {input_path}")
    
    # 读取所有数据
    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                case = json.loads(line.strip())
                total_count += 1
                
                # 查找user message
                user_message = None
                user_idx = None
                for idx, msg in enumerate(case.get('messages', [])):
                    if msg.get('role') == 'user':
                        user_message = msg.get('content', '')
                        user_idx = idx
                        break
                
                if user_message is None:
                    print(f"警告：第{line_num}行没有找到user message")
                    processed_cases.append(case)
                    continue
                
                # 检查是否包含答案泄露信息
                if '监管机关认定的违法类型为' in user_message:
                    cleaned_content = clean_user_message(user_message)
                    
                    # 更新user message
                    case['messages'][user_idx]['content'] = cleaned_content
                    cleaned_count += 1
                    case_id = case.get('meta', {}).get('case_id', f'line_{line_num}')
                    cleaned_cases.append(case_id)
                    
                    print(f"  ✓ 已清理: {case_id}")
                
                processed_cases.append(case)
                    
            except json.JSONDecodeError as e:
                print(f"错误：第{line_num}行JSON解析失败: {e}")
                continue
            except Exception as e:
                print(f"错误：第{line_num}行处理失败: {e}")
                continue
    
    # 写入处理后的数据
    print(f"\n正在写入输出文件: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f_out:
        for case in processed_cases:
            f_out.write(json.dumps(case, ensure_ascii=False) + '\n')
    
    # 打印统计信息
    print(f"\n处理完成！")
    print(f"总数据量: {total_count}条")
    print(f"清理数量: {cleaned_count}条")
    print(f"输出文件: {output_path}")
    
    if cleaned_cases:
        print(f"\n已清理的案例ID (前20个):")
        for case_id in cleaned_cases[:20]:
            print(f"  - {case_id}")
        if len(cleaned_cases) > 20:
            print(f"  ... 还有{len(cleaned_cases) - 20}个案例")


def main():
    """主函数"""
    import sys
    
    # 默认处理eval_159.jsonl
    eval_file = Path(__file__).parent.parent.parent / "data" / "eval" / "eval_159.jsonl"
    
    # 检查是否有--auto参数
    auto_mode = '--auto' in sys.argv
    if auto_mode:
        sys.argv.remove('--auto')
    
    if len(sys.argv) > 1:
        eval_file = Path(sys.argv[1])
    
    # 输出文件路径（备份原文件）
    output_file = eval_file.parent / f"{eval_file.stem}_cleaned.jsonl"
    
    print("=" * 60)
    print("Eval数据集清理工具")
    print("=" * 60)
    print(f"输入文件: {eval_file}")
    print(f"输出文件: {output_file}")
    print("=" * 60)
    
    # 确认操作（除非是自动模式）
    if not auto_mode:
        try:
            response = input("\n是否继续？(y/n): ").strip().lower()
            if response != 'y':
                print("已取消操作")
                return
        except (EOFError, KeyboardInterrupt):
            print("\n已取消操作")
            return
    
    # 处理文件
    process_eval_file(str(eval_file), str(output_file))
    
    print("\n" + "=" * 60)
    print("清理完成！建议检查输出文件后，再替换原文件。")
    print("=" * 60)


if __name__ == "__main__":
    main()

