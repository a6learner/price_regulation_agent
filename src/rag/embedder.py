from sentence_transformers import SentenceTransformer

from .local_model_paths import resolve_st_model

_EMBED_HUB = "BAAI/bge-small-zh-v1.5"


class EmbedderModel:
    def __init__(self, model_name=None):
        resolved = model_name or resolve_st_model(
            "PRICE_REG_EMBEDDING_MODEL", _EMBED_HUB, "bge-small-zh-v1.5"
        )
        self.model = SentenceTransformer(resolved)
        print(f"Embedding模型加载成功: {resolved}")

    def encode(self, texts):
        return self.model.encode(texts, convert_to_numpy=True).tolist()
