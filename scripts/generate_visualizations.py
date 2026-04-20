"""生成可视化图表脚本

功能:
1. 读取三方法对比的可视化数据
2. 生成雷达图（综合能力对比）
3. 生成柱状图（成本-效果分析）
4. 生成热力图（不同复杂度案例表现）

运行:
    # 从默认路径读取数据并生成图表
    python scripts/generate_visualizations.py

    # 指定输入数据路径
    python scripts/generate_visualizations.py --data results/comparison/visualization_data.json

    # 指定输出目录
    python scripts/generate_visualizations.py --output-dir results/comparison/figures
"""

import sys
import json
import argparse
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

# 检查matplotlib是否可用
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("[警告] matplotlib未安装，无法生成图表。请运行: pip install matplotlib")

# 检查seaborn是否可用
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
    print("[提示] seaborn未安装，将使用基础绘图。可选安装: pip install seaborn")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="生成可视化图表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--data',
        type=str,
        default='results/comparison/visualization_data.json',
        help='可视化数据文件路径'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='results/comparison/figures',
        help='图表输出目录'
    )

    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='图表DPI（默认300）'
    )

    return parser.parse_args()


def load_visualization_data(data_path: str):
    """加载可视化数据"""
    data_path = Path(data_path)
    if not data_path.exists():
        print(f"[错误] 数据文件不存在: {data_path}")
        return None

    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_radar_chart(data: dict, output_path: str, dpi: int = 300):
    """生成雷达图 - 综合能力对比"""
    if not HAS_MATPLOTLIB:
        print("[跳过] 雷达图生成（matplotlib未安装）")
        return

    radar_data = data['radar_chart_data']
    metrics = radar_data['metrics']
    baseline_values = radar_data['Baseline']
    rag_values = radar_data['RAG']
    agent_values = radar_data['Agent']

    # 计算角度
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    baseline_values += baseline_values[:1]
    rag_values += rag_values[:1]
    agent_values += agent_values[:1]
    angles += angles[:1]

    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(projection='polar'))

    # 绘制三条线
    ax.plot(angles, baseline_values, 'o-', linewidth=2, label='Baseline', color='#3498db')
    ax.fill(angles, baseline_values, alpha=0.15, color='#3498db')

    ax.plot(angles, rag_values, 's-', linewidth=2, label='RAG', color='#2ecc71')
    ax.fill(angles, rag_values, alpha=0.15, color='#2ecc71')

    ax.plot(angles, agent_values, '^-', linewidth=2, label='Agent', color='#e74c3c')
    ax.fill(angles, agent_values, alpha=0.15, color='#e74c3c')

    # 设置标签
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics, size=11)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], size=9)
    ax.grid(True, linestyle='--', alpha=0.5)

    # 标题和图例
    plt.title('三方法综合能力对比（雷达图）', size=14, pad=20, weight='bold')
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)

    # 保存
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    print(f"✓ 雷达图已生成: {output_path}")


def generate_cost_effectiveness_chart(data: dict, output_path: str, dpi: int = 300):
    """生成成本-效果分析图（柱状图）"""
    if not HAS_MATPLOTLIB:
        print("[跳过] 成本-效果图生成（matplotlib未安装）")
        return

    cost_data = data['cost_effectiveness_data']
    methods = cost_data['methods']
    token_cost = cost_data['token_cost']
    quality_score = cost_data['quality_score']

    # 归一化Token消耗（以Baseline为基准）
    baseline_tokens = token_cost[0]
    normalized_cost = [tc / baseline_tokens for tc in token_cost]

    # 创建图表
    fig, ax1 = plt.subplots(figsize=(10, 6))

    x = np.arange(len(methods))
    width = 0.35

    # 柱状图1: Token消耗（相对值）
    bars1 = ax1.bar(x - width/2, normalized_cost, width, label='Token消耗（相对）', color='#3498db', alpha=0.7)
    ax1.set_ylabel('Token消耗（相对Baseline）', fontsize=11, weight='bold')
    ax1.set_ylim(0, max(normalized_cost) * 1.2)

    # 第二个Y轴: 质量评分
    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width/2, quality_score, width, label='综合质量评分', color='#e74c3c', alpha=0.7)
    ax2.set_ylabel('综合质量评分', fontsize=11, weight='bold')
    ax2.set_ylim(0, 1.0)

    # 设置X轴
    ax1.set_xlabel('方法', fontsize=11, weight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(methods, fontsize=11)

    # 添加数值标签
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}x',
                ha='center', va='bottom', fontsize=9)

    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.3f}',
                ha='center', va='bottom', fontsize=9)

    # 标题和图例
    plt.title('成本-效果分析对比', fontsize=14, pad=20, weight='bold')
    fig.legend(loc='upper center', bbox_to_anchor=(0.5, 0.95), ncol=2, fontsize=10)

    # 保存
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    print(f"✓ 成本-效果图已生成: {output_path}")


def generate_complexity_heatmap(data: dict, output_path: str, dpi: int = 300):
    """生成复杂度热力图（如果有复杂度数据）"""
    if not HAS_MATPLOTLIB:
        print("[跳过] 复杂度热力图生成（matplotlib未安装）")
        return

    # 模拟复杂度数据（实际应该从评估结果中提取）
    # TODO: 从实际结果中按complexity分组计算质量评分
    metric_breakdown = data['metric_breakdown']

    # 提取关键指标
    methods = ['Baseline', 'RAG', 'Agent']
    metrics_to_show = [
        'evidence_chain',
        'legal_citation',
        'explainability',
        'remediation',
        'structured_output'
    ]
    metric_labels = [
        '证据链',
        '法律引用',
        '可解释性',
        '整改建议',
        '结构化输出'
    ]

    # 构建热力图数据
    heatmap_data = []
    for metric in metrics_to_show:
        row = [
            metric_breakdown['Baseline'][metric],
            metric_breakdown['RAG'][metric],
            metric_breakdown['Agent'][metric]
        ]
        heatmap_data.append(row)

    heatmap_data = np.array(heatmap_data)

    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 7))

    if HAS_SEABORN:
        sns.heatmap(heatmap_data, annot=True, fmt='.3f', cmap='RdYlGn',
                   xticklabels=methods, yticklabels=metric_labels,
                   cbar_kws={'label': '评分 (0-1)'}, vmin=0, vmax=1.0,
                   linewidths=0.5, ax=ax)
    else:
        im = ax.imshow(heatmap_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1.0)
        ax.set_xticks(np.arange(len(methods)))
        ax.set_yticks(np.arange(len(metric_labels)))
        ax.set_xticklabels(methods)
        ax.set_yticklabels(metric_labels)

        # 添加数值标注
        for i in range(len(metric_labels)):
            for j in range(len(methods)):
                text = ax.text(j, i, f'{heatmap_data[i, j]:.3f}',
                             ha="center", va="center", color="black", fontsize=10)

        # 添加颜色条
        plt.colorbar(im, ax=ax, label='评分 (0-1)')

    # 标题
    plt.title('三方法高级指标热力图', fontsize=14, pad=20, weight='bold')
    plt.xlabel('方法', fontsize=11, weight='bold')
    plt.ylabel('评估指标', fontsize=11, weight='bold')

    # 保存
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    print(f"✓ 高级指标热力图已生成: {output_path}")


def generate_metric_comparison_bar_chart(data: dict, output_path: str, dpi: int = 300):
    """生成高级指标对比柱状图"""
    if not HAS_MATPLOTLIB:
        print("[跳过] 指标对比图生成（matplotlib未安装）")
        return

    metric_breakdown = data['metric_breakdown']

    metrics = ['evidence_chain', 'legal_citation', 'remediation', 'explainability', 'structured_output']
    metric_labels = ['证据链\n完整性', '法律引用\n准确性', '整改建议\n可操作性', '可解释性', '结构化\n输出质量']

    baseline_values = [metric_breakdown['Baseline'][m] for m in metrics]
    rag_values = [metric_breakdown['RAG'][m] for m in metrics]
    agent_values = [metric_breakdown['Agent'][m] for m in metrics]

    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(metrics))
    width = 0.25

    # 三组柱状图
    bars1 = ax.bar(x - width, baseline_values, width, label='Baseline', color='#3498db', alpha=0.8)
    bars2 = ax.bar(x, rag_values, width, label='RAG', color='#2ecc71', alpha=0.8)
    bars3 = ax.bar(x + width, agent_values, width, label='Agent', color='#e74c3c', alpha=0.8)

    # 设置坐标轴
    ax.set_ylabel('评分', fontsize=11, weight='bold')
    ax.set_xlabel('评估指标', fontsize=11, weight='bold')
    ax.set_title('高级指标对比（柱状图）', fontsize=14, pad=20, weight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, fontsize=10)
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=11)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    # 添加数值标签
    def add_value_labels(bars):
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.3f}',
                       ha='center', va='bottom', fontsize=8)

    add_value_labels(bars1)
    add_value_labels(bars2)
    add_value_labels(bars3)

    # 保存
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    print(f"✓ 指标对比柱状图已生成: {output_path}")


def main():
    args = parse_args()

    if not HAS_MATPLOTLIB:
        print("\n[错误] matplotlib未安装，无法生成图表")
        print("请运行: pip install matplotlib seaborn")
        return

    print("="*80)
    print("生成可视化图表")
    print("="*80)

    # 加载数据
    print("\n[1/5] 加载可视化数据...")
    data = load_visualization_data(args.data)

    if not data:
        print("\n[错误] 无法加载数据，请先运行:")
        print("  python scripts/run_comprehensive_comparison.py")
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成各类图表
    print("\n[2/5] 生成雷达图...")
    generate_radar_chart(data, output_dir / 'radar_chart.png', args.dpi)

    print("\n[3/5] 生成成本-效果图...")
    generate_cost_effectiveness_chart(data, output_dir / 'cost_effectiveness.png', args.dpi)

    print("\n[4/5] 生成高级指标热力图...")
    generate_complexity_heatmap(data, output_dir / 'advanced_metrics_heatmap.png', args.dpi)

    print("\n[5/5] 生成指标对比柱状图...")
    generate_metric_comparison_bar_chart(data, output_dir / 'metric_comparison_bar.png', args.dpi)

    print("\n" + "="*80)
    print("图表生成完成！")
    print("="*80)

    print(f"\n生成的图表:")
    print(f"  - {output_dir / 'radar_chart.png'}")
    print(f"  - {output_dir / 'cost_effectiveness.png'}")
    print(f"  - {output_dir / 'advanced_metrics_heatmap.png'}")
    print(f"  - {output_dir / 'metric_comparison_bar.png'}")

    print("\n下一步:")
    print("  1. 查看图表: 在文件管理器中打开 results/comparison/figures/")
    print("  2. 生成案例展示: python scripts/generate_case_showcase.py")
    print("  3. 整理论文材料: 将图表和报告整合到论文中")


if __name__ == "__main__":
    main()
