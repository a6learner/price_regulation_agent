"""为 Web 前端提供「检索到的法规条文」全文（来自 Grader 输出）"""


def serialize_graded_laws_for_ui(graded_laws: list | None, max_chars: int = 50000) -> list[dict]:
    """将 graded_laws 转为前端可展示的列表，含 label + content 全文。"""
    out: list[dict] = []
    for law in graded_laws or []:
        meta = law.get("metadata") or {}
        title = (meta.get("law_name") or "").strip()
        article = (meta.get("article") or "").strip()
        cid = meta.get("chunk_id") or law.get("chunk_id")
        if title and article:
            label = f"《{title}》{article}"
        elif title:
            label = f"《{title}》"
        elif article:
            label = article
        else:
            label = str(cid or "法规条文")

        content = law.get("content") or ""
        if len(content) > max_chars:
            content = content[:max_chars] + "\n…（正文过长已截断）"

        out.append(
            {
                "chunk_id": cid,
                "label": label,
                "law_name": title,
                "article": article,
                "content": content,
                "score": law.get("final_score"),
            }
        )
    return out
