import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.data_processor import LawDocumentExtractor


def main():
    extractor = LawDocumentExtractor()

    laws_chunks = extractor.process_all_laws("data/laws")

    output_path = "data/rag/laws_chunks.jsonl"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for chunk in laws_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

    print(f"\n提取了 {len(laws_chunks)} 条法律切片")
    print(f"保存到: {output_path}")


if __name__ == '__main__':
    main()
