"""诊断 CrossEncoder Reranker 问题"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("Step 1: 导入 CrossEncoder...")
from sentence_transformers import CrossEncoder
print("[OK] 导入成功")

print("\nStep 2: 初始化 CrossEncoder...")
try:
    reranker = CrossEncoder('BAAI/bge-reranker-v2-m3')
    print("[OK] 初始化成功")
except Exception as e:
    print(f"[ERROR] 初始化失败: {e}")
    sys.exit(1)

print("\nStep 3: 准备测试数据...")
test_pairs = [
    ["商品标注原价899元，实际从未销售", "《禁止价格欺诈行为规定》第八条"],
    ["虚假折扣促销", "《价格法》第十四条"]
]
print(f"[OK] 测试对: {len(test_pairs)} pairs")

print("\nStep 4: 测试 predict() - 单个pair...")
try:
    print("  调用: reranker.predict([test_pairs[0]])")
    score = reranker.predict([test_pairs[0]])
    print(f"[OK] 单个pair成功: score={score}")
except Exception as e:
    print(f"[ERROR] 单个pair失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 5: 测试 predict() - 多个pairs...")
try:
    print("  调用: reranker.predict(test_pairs)")
    scores = reranker.predict(test_pairs)
    print(f"[OK] 多个pairs成功: scores={scores}")
except Exception as e:
    print(f"[ERROR] 多个pairs失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 6: 测试 predict() - 带参数...")
try:
    print("  调用: reranker.predict(test_pairs, batch_size=1)")
    scores = reranker.predict(test_pairs, batch_size=1)
    print(f"[OK] 带batch_size=1成功: scores={scores}")
except Exception as e:
    print(f"[ERROR] 带batch_size=1失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 7: 测试 predict() - 带更多参数...")
try:
    print("  调用: reranker.predict(test_pairs, batch_size=1, show_progress_bar=False)")
    scores = reranker.predict(test_pairs, batch_size=1, show_progress_bar=False)
    print(f"[OK] 带更多参数成功: scores={scores}")
except Exception as e:
    print(f"[ERROR] 带更多参数失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("[SUCCESS] 所有测试通过！Reranker工作正常。")
print("="*60)
