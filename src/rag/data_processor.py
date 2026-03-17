import json
import re
from pathlib import Path
from docx import Document


class LawDocumentExtractor:
    def extract_from_docx(self, file_path):
        doc = Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return paragraphs

    def chunk_by_article(self, paragraphs, law_name, law_level, global_counter):
        chunks = []
        current_article = None
        current_content = []

        # 识别条款号的正则（第X条）
        article_pattern = re.compile(r'第[一二三四五六七八九十百\d]+条')

        for para in paragraphs:
            match = article_pattern.match(para)
            if match:
                # 保存前一个条款
                if current_article and current_content:
                    global_counter[0] += 1
                    chunks.append({
                        'chunk_id': f"law_{global_counter[0]:04d}",
                        'law_name': law_name,
                        'law_level': law_level,
                        'article': current_article,
                        'content': ' '.join(current_content)
                    })

                # 开始新条款
                current_article = match.group()
                current_content = [para]
            else:
                # 累积当前条款内容
                if current_content:
                    current_content.append(para)

        # 保存最后一个条款
        if current_article and current_content:
            global_counter[0] += 1
            chunks.append({
                'chunk_id': f"law_{global_counter[0]:04d}",
                'law_name': law_name,
                'law_level': law_level,
                'article': current_article,
                'content': ' '.join(current_content)
            })

        return chunks

    def process_all_laws(self, laws_dir):
        laws_dir = Path(laws_dir)
        all_chunks = []
        global_counter = [0]  # 全局计数器

        # 处理中央法规
        central_dir = laws_dir / "中央"
        if central_dir.exists():
            for file_path in central_dir.glob("*.docx"):
                law_name = file_path.stem.split('_')[0]
                paragraphs = self.extract_from_docx(file_path)
                chunks = self.chunk_by_article(paragraphs, law_name, "中央", global_counter)
                all_chunks.extend(chunks)
                print(f"已处理: {law_name} ({len(chunks)}条)")

        # 处理浙江法规
        zj_dir = laws_dir / "浙江"
        if zj_dir.exists():
            for file_path in zj_dir.glob("*.docx"):
                law_name = file_path.stem.split('_')[0]
                paragraphs = self.extract_from_docx(file_path)
                chunks = self.chunk_by_article(paragraphs, law_name, "浙江", global_counter)
                all_chunks.extend(chunks)
                print(f"已处理: {law_name} ({len(chunks)}条)")

        # 处理平台规则
        platform_dir = laws_dir / "平台规则"
        if platform_dir.exists():
            for file_path in platform_dir.glob("*.docx"):
                law_name = file_path.stem
                paragraphs = self.extract_from_docx(file_path)
                chunks = self.chunk_by_article(paragraphs, law_name, "平台规则", global_counter)
                all_chunks.extend(chunks)
                print(f"已处理: {law_name} ({len(chunks)}条)")

        return all_chunks


class CaseDataProcessor:
    def load_and_process(self, cases_path):
        cases_chunks = []
        chunk_counter = 0

        with open(cases_path, 'r', encoding='utf-8') as f:
            for line in f:
                case = json.loads(line.strip())
                chunk_counter += 1

                # 提取核心内容
                violation_desc = case.get('violation_description', '')
                law_refs = ' '.join(case.get('law_references', []))
                content = f"{violation_desc} {law_refs}".strip()

                cases_chunks.append({
                    'chunk_id': f"case_{chunk_counter:03d}",
                    'case_id': case.get('case_id', ''),
                    'violation_type': case.get('violation_type', ''),
                    'platform': case.get('platform', ''),
                    'penalty_amount': case.get('penalty_amount', 0),
                    'content': content
                })

        return cases_chunks
