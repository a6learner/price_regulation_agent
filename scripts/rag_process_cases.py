import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.data_processor import CaseDataProcessor


def main():
    processor = CaseDataProcessor()
    cases_chunks = processor.load_and_process("data/sft/processed/extracted_cases.jsonl")

    output_path = "data/rag/cases_chunks.jsonl"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for chunk in cases_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

    print(f"处理了 {len(cases_chunks)} 个案例")
    print(f"保存到: {output_path}")


if __name__ == '__main__':
    main()
