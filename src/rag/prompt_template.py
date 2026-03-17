from src.baseline.prompt_template import PromptTemplate


class RAGPromptTemplate(PromptTemplate):
    RAG_SYSTEM_PROMPT = """你是一名电商平台价格合规分析专家，熟悉《价格法》、《禁止价格欺诈行为规定》等相关法律法规和典型案例。你的任务是根据给定的案例事实，从价格合规的角度分析经营行为是否违规，并提供专业的法律依据和结论。

**重要参考资料**：
你可以参考以下法律条文和相似案例进行分析：

【相关法律条文】
{laws_context}

【相似处罚案例】
{cases_context}

请结合以上资料进行分析，严格按照以下JSON格式输出你的分析结果：

```json
{{
  "is_violation": true/false,
  "violation_type": "违规类型",
  "confidence": 0.0-1.0,
  "reasoning": "详细的分析依据和法律推理过程",
  "legal_basis": "相关法律条文或案例"
}}
```

**注意事项**：
1. 优先引用提供的【相关法律条文】中的具体条款
2. 可以参考【相似处罚案例】中的判罚逻辑
3. reasoning必须结合检索到的资料进行分析
4. legal_basis需要引用具体的法律条款名称和条款号

请确保输出是有效的JSON格式，不要包含任何其他文本。"""

    @classmethod
    def build_rag_prompt(cls, query, laws, cases):
        laws_context = cls._format_laws_context(laws)
        cases_context = cls._format_cases_context(cases)

        system_prompt = cls.RAG_SYSTEM_PROMPT.format(
            laws_context=laws_context,
            cases_context=cases_context
        )

        user_prompt = cls.build_user_prompt(query)

        return {
            'system_prompt': system_prompt,
            'user_prompt': user_prompt
        }

    @classmethod
    def _format_laws_context(cls, laws):
        if not laws:
            return "暂无相关法律条文"

        formatted = []
        for i, law in enumerate(laws, 1):
            meta = law['metadata']
            content = law['content'][:200] + ('...' if len(law['content']) > 200 else '')
            formatted.append(
                f"{i}. 《{meta['law_name']}》{meta.get('article', '')}\n"
                f"   {content}"
            )
        return '\n\n'.join(formatted)

    @classmethod
    def _format_cases_context(cls, cases):
        if not cases:
            return "暂无相似案例"

        formatted = []
        for i, case in enumerate(cases, 1):
            meta = case['metadata']
            content = case['content'][:150] + ('...' if len(case['content']) > 150 else '')
            formatted.append(
                f"【案例{i}】{meta.get('violation_type', '未知')}\n"
                f"{content}"
            )
        return '\n\n'.join(formatted)
