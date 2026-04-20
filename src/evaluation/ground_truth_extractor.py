"""
Ground Truth提取器

从评估数据集中提取正确答案（ground truth），用于计算评估指标:
- 法律依据 (legal_basis)
- 违规判断 (is_violation)
- 违规类型 (violation_type)
"""

import json
import re
from typing import Dict, Any, List


class GroundTruthExtractor:
    """从评估数据中提取Ground Truth"""

    def __init__(self, eval_data_path: str = None, gt_map: dict = None):
        self.eval_data_path = eval_data_path or "data/eval/eval_159.jsonl"
        self.ground_truths = {}  # case_id -> ground_truth mapping
        if gt_map:
            # 直接使用v4的ground truth map（跳过旧格式解析）
            self.ground_truths = gt_map

    def load_eval_data(self) -> List[Dict[str, Any]]:
        """
        加载评估数据集

        Returns:
            评估数据列表
        """
        eval_data = []
        with open(self.eval_data_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        case = json.loads(line)
                        eval_data.append(case)
                    except json.JSONDecodeError as e:
                        print(f"[Warning] Failed to parse line: {e}")
                        continue
        return eval_data

    def extract_laws_from_text(self, text: str) -> List[str]:
        """
        从文本中提取法律引用

        使用正则表达式提取《法律名》和条款号

        Args:
            text: 待提取的文本

        Returns:
            法律引用列表，如 ["《价格法》第14条", "《禁止价格欺诈规定》第7条"]
        """
        laws = []

        # 模式1: 《法律名》第X条
        pattern1 = r'《([^》]+)》第([一二三四五六七八九十\d]+)条'
        matches1 = re.findall(pattern1, text)
        for law_name, article_num in matches1:
            laws.append(f"《{law_name}》第{article_num}条")

        # 模式2: 《法律名》（无条款号）
        pattern2 = r'《([^》]+)》'
        matches2 = re.findall(pattern2, text)
        for law_name in matches2:
            # 如果没有条款号，只记录法律名
            full_law = f"《{law_name}》"
            # 避免重复
            if not any(full_law in law for law in laws):
                laws.append(full_law)

        # 去重
        laws = list(dict.fromkeys(laws))

        return laws

    def extract_ground_truth(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        从单个评估案例中提取Ground Truth

        Args:
            case: 评估案例（包含messages和meta）

        Returns:
            Ground Truth字典
        """
        # 从messages中提取assistant的回复（ground truth）
        messages = case.get("messages", [])
        assistant_message = None

        for msg in messages:
            if msg.get("role") == "assistant":
                assistant_message = msg.get("content", "")
                break

        # 从meta中提取基础信息
        meta = case.get("meta", {})
        case_id = meta.get("case_id", "unknown")

        # 提取法律依据
        ground_truth_laws = []
        if assistant_message:
            ground_truth_laws = self.extract_laws_from_text(assistant_message)

        # 提取违规判断
        is_violation = meta.get("is_violation", None)

        # 提取违规类型
        violation_type = meta.get("violation_type", None)

        # 提取复杂度
        complexity = meta.get("complexity", "medium")

        # 提取平台
        platform = meta.get("platform", "unknown")

        return {
            "case_id": case_id,
            "is_violation": is_violation,
            "violation_type": violation_type,
            "ground_truth_laws": ground_truth_laws,
            "complexity": complexity,
            "platform": platform,
            "assistant_response": assistant_message
        }

    def build_ground_truth_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        构建完整的Ground Truth字典

        Returns:
            {case_id: ground_truth_data} 映射
        """
        eval_data = self.load_eval_data()

        for case in eval_data:
            gt = self.extract_ground_truth(case)
            case_id = gt["case_id"]
            self.ground_truths[case_id] = gt

        print(f"[Info] Extracted ground truth for {len(self.ground_truths)} cases")

        # 统计法律引用情况
        total_laws = sum(len(gt["ground_truth_laws"]) for gt in self.ground_truths.values())
        cases_with_laws = sum(1 for gt in self.ground_truths.values() if gt["ground_truth_laws"])

        print(f"[Info] Total law citations: {total_laws}")
        print(f"[Info] Cases with law citations: {cases_with_laws}/{len(self.ground_truths)} ({cases_with_laws/len(self.ground_truths)*100:.1f}%)")

        return self.ground_truths

    def get_ground_truth(self, case_id: str) -> Dict[str, Any]:
        """
        获取指定case_id的Ground Truth

        Args:
            case_id: 案例ID

        Returns:
            Ground Truth数据，如果不存在返回None
        """
        if not self.ground_truths:
            self.build_ground_truth_dict()

        gt = self.ground_truths.get(case_id, None)
        if gt is None:
            return None

        # 兼容v4格式：将 qualifying_article_keys 映射为 ground_truth_laws
        if 'qualifying_article_keys' in gt:
            return {
                'ground_truth_laws': gt['qualifying_article_keys'],
                'is_violation': gt['is_violation'],
                'violation_type': gt.get('violation_type'),
            }
        return gt

    def save_ground_truth(self, output_path: str = "data/eval/ground_truths.json"):
        """
        保存Ground Truth到文件

        Args:
            output_path: 输出文件路径
        """
        if not self.ground_truths:
            self.build_ground_truth_dict()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.ground_truths, f, ensure_ascii=False, indent=2)

        print(f"[Info] Saved ground truth to {output_path}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取Ground Truth的统计信息

        Returns:
            统计信息字典
        """
        if not self.ground_truths:
            self.build_ground_truth_dict()

        total_cases = len(self.ground_truths)
        violation_cases = sum(1 for gt in self.ground_truths.values() if gt["is_violation"])
        compliance_cases = total_cases - violation_cases

        # 违规类型分布
        violation_types = {}
        for gt in self.ground_truths.values():
            vt = gt.get("violation_type", "unknown")
            violation_types[vt] = violation_types.get(vt, 0) + 1

        # 复杂度分布
        complexity_dist = {}
        for gt in self.ground_truths.values():
            comp = gt.get("complexity", "medium")
            complexity_dist[comp] = complexity_dist.get(comp, 0) + 1

        # 平台分布
        platform_dist = {}
        for gt in self.ground_truths.values():
            plat = gt.get("platform", "unknown")
            platform_dist[plat] = platform_dist.get(plat, 0) + 1

        # 法律引用统计
        law_citations = {}
        for gt in self.ground_truths.values():
            for law in gt["ground_truth_laws"]:
                # 提取法律名称（不含条款号）
                law_name_match = re.search(r'《([^》]+)》', law)
                if law_name_match:
                    law_name = law_name_match.group(1)
                    law_citations[law_name] = law_citations.get(law_name, 0) + 1

        return {
            "total_cases": total_cases,
            "violation_cases": violation_cases,
            "compliance_cases": compliance_cases,
            "violation_types": violation_types,
            "complexity_distribution": complexity_dist,
            "platform_distribution": platform_dist,
            "law_citations": law_citations
        }

    def print_statistics(self):
        """打印统计信息"""
        stats = self.get_statistics()

        print("\n=== Ground Truth 统计信息 ===")
        print(f"总案例数: {stats['total_cases']}")
        print(f"违规案例: {stats['violation_cases']} ({stats['violation_cases']/stats['total_cases']*100:.1f}%)")
        print(f"合规案例: {stats['compliance_cases']} ({stats['compliance_cases']/stats['total_cases']*100:.1f}%)")

        print("\n违规类型分布:")
        for vt, count in sorted(stats['violation_types'].items(), key=lambda x: -x[1]):
            print(f"  {vt}: {count}")

        print("\n复杂度分布:")
        for comp, count in sorted(stats['complexity_distribution'].items(), key=lambda x: -x[1]):
            print(f"  {comp}: {count}")

        print("\n平台分布:")
        for plat, count in sorted(stats['platform_distribution'].items(), key=lambda x: -x[1])[:10]:
            print(f"  {plat}: {count}")

        print("\n高频法律引用 (Top 10):")
        for law, count in sorted(stats['law_citations'].items(), key=lambda x: -x[1])[:10]:
            print(f"  《{law}》: {count}次")


if __name__ == "__main__":
    # 测试提取器
    import os

    # 切换到项目根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(current_dir, "..", "..")
    os.chdir(project_root)

    print("当前工作目录:", os.getcwd())

    # 创建提取器
    extractor = GroundTruthExtractor()

    # 构建Ground Truth字典
    ground_truths = extractor.build_ground_truth_dict()

    # 打印统计信息
    extractor.print_statistics()

    # 测试单个案例提取
    print("\n=== 测试案例: eval_001 ===")
    gt_001 = extractor.get_ground_truth("eval_001")
    if gt_001:
        print(f"案例ID: {gt_001['case_id']}")
        print(f"是否违规: {gt_001['is_violation']}")
        print(f"违规类型: {gt_001['violation_type']}")
        print(f"法律依据: {gt_001['ground_truth_laws']}")
        print(f"复杂度: {gt_001['complexity']}")
    else:
        print("未找到案例 eval_001")

    # 保存Ground Truth到文件
    extractor.save_ground_truth()
