#!/usr/bin/env python3
"""
将 OpenAI 格式的数据集转换为 ShareGPT 格式

OpenAI 格式:
{
  "messages": [
    {"role": "system",    "content": "..."},
    {"role": "user",      "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}

ShareGPT 格式:
{
  "conversations": [
    {"from": "human", "value": "..."},
    {"from": "gpt",   "value": "..."}
  ],
  "system": "..."   # 可选，来自 system 消息
}
"""

import json
import argparse
import sys
from pathlib import Path

# OpenAI role -> ShareGPT from 映射
ROLE_MAP = {
    "user":      "human",
    "assistant": "gpt",
    "function":  "function_call",   # function calling 场景
    "tool":      "observation",     # tool result 场景
}


def convert_record(record: dict) -> dict | None:
    """将单条 OpenAI 格式记录转换为 ShareGPT 格式，失败返回 None。"""
    messages = record.get("messages")
    if not messages or not isinstance(messages, list):
        return None

    system_content = None
    conversations = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            system_content = content          # system 单独存放
        elif role in ROLE_MAP:
            conversations.append({
                "from":  ROLE_MAP[role],
                "value": content,
            })
        else:
            # 未知 role，跳过并警告
            print(f"[警告] 未知 role '{role}'，已跳过该消息", file=sys.stderr)

    if not conversations:
        return None

    result: dict = {"conversations": conversations}
    if system_content is not None:
        result["system"] = system_content

    return result


def convert_file(input_path: str, output_path: str) -> None:
    input_path  = Path(input_path)
    output_path = Path(output_path)

    total   = 0
    success = 0
    skipped = 0

    with input_path.open("r", encoding="utf-8") as fin, \
         output_path.open("w", encoding="utf-8") as fout:

        for line_no, line in enumerate(fin, 1):
            line = line.strip()
            if not line:
                continue
            total += 1

            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[错误] 第 {line_no} 行 JSON 解析失败: {e}", file=sys.stderr)
                skipped += 1
                continue

            converted = convert_record(record)
            if converted is None:
                print(f"[警告] 第 {line_no} 行转换失败，已跳过", file=sys.stderr)
                skipped += 1
                continue

            fout.write(json.dumps(converted, ensure_ascii=False) + "\n")
            success += 1

    print(f"\n✅ 转换完成！")
    print(f"   输入文件 : {input_path}")
    print(f"   输出文件 : {output_path}")
    print(f"   总条数   : {total}")
    print(f"   成功转换 : {success}")
    print(f"   跳过条数 : {skipped}")


def main():
    parser = argparse.ArgumentParser(
        description="将 OpenAI 格式 JSONL 数据集转换为 ShareGPT 格式"
    )
    parser.add_argument(
        "input",
        help="输入文件路径（OpenAI 格式 .jsonl）"
    )
    parser.add_argument(
        "output",
        nargs="?",
        help="输出文件路径（ShareGPT 格式 .jsonl），默认在输入文件名后加 _sharegpt"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[错误] 输入文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        output_path = input_path.with_name(
            input_path.stem + "_sharegpt" + input_path.suffix
        )

    convert_file(str(input_path), str(output_path))


if __name__ == "__main__":
    main()
