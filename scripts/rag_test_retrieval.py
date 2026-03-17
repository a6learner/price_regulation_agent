import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.retriever import HybridRetriever


def main():
    retriever = HybridRetriever()

    test_queries = [
        "某酒店在携程划线价3000元，实际预订价198元",
        "直播间声称原价798元，实际从未以此价格销售",
        "商品标注限时9.9元，但需拼团+领券+首单"
    ]

    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"【查询】{query}")
        results = retriever.retrieve(query, laws_k=3, cases_k=5)

        print(f"\n相关法律 (Top-3):")
        for i, law in enumerate(results['laws'], 1):
            print(f"{i}. {law['metadata']['law_name']} {law['metadata'].get('article', '')}")
            print(f"   相似度: {1-law['distance']:.3f}")
            print(f"   内容: {law['content'][:100]}...")

        print(f"\n相似案例 (Top-5):")
        for i, case in enumerate(results['cases'], 1):
            print(f"{i}. {case['metadata'].get('violation_type', '未知')}")
            print(f"   相似度: {1-case['distance']:.3f}")
            print(f"   内容: {case['content'][:80]}...")


if __name__ == '__main__':
    main()
