"""
Baseline系统MVP测试脚本
在5个评估案例上测试系统是否正常工作
"""

import sys
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.baseline import BaselineEvaluator


def main():
    """主函数"""
    print("="*60)
    print("Baseline系统MVP测试")
    print("="*60)

    # 初始化评估器
    evaluator = BaselineEvaluator(config_path="configs/model_config.yaml")

    # 加载5个评估案例
    eval_path = "data/eval/eval_159.jsonl"
    print(f"\n加载评估数据: {eval_path}")
    eval_cases = evaluator.load_eval_data(eval_path, limit=5)

    if not eval_cases:
        print("错误: 无法加载评估数据")
        return

    # 测试第一个模型 (Qwen)
    print("\n" + "="*60)
    print("测试模型: Qwen3.5-397B-A17B")
    print("="*60)

    try:
        qwen_results = evaluator.evaluate_batch(
            eval_cases,
            model_key='qwen',
            save_progress=False
        )

        # 计算指标
        qwen_metrics = evaluator.calculate_metrics(qwen_results)
        evaluator.print_metrics(qwen_metrics, "Qwen3.5-397B-A17B")

        # 保存结果
        evaluator.save_results(qwen_results, 'qwen_test')

    except Exception as e:
        print(f"\nQwen模型测试失败: {e}")
        import traceback
        traceback.print_exc()

    # 询问是否测试第二个模型
    print("\n是否测试MiniMax-M2.5模型？(y/n): ", end='')
    choice = input().strip().lower()

    if choice == 'y':
        print("\n" + "="*60)
        print("测试模型: MiniMax-M2.5")
        print("="*60)

        try:
            minimax_results = evaluator.evaluate_batch(
                eval_cases,
                model_key='minimax',
                save_progress=False
            )

            # 计算指标
            minimax_metrics = evaluator.calculate_metrics(minimax_results)
            evaluator.print_metrics(minimax_metrics, "MiniMax-M2.5")

            # 保存结果
            evaluator.save_results(minimax_results, 'minimax_test')

        except Exception as e:
            print(f"\nMiniMax模型测试失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("MVP测试完成！")
    print("="*60)
    print("\n下一步:")
    print("1. 检查results/baseline/目录下的结果文件")
    print("2. 如果测试成功，运行完整评估: python scripts/run_baseline_eval.py")
    print("="*60)


if __name__ == "__main__":
    main()
