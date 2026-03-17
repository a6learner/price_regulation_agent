from sentence_transformers import SentenceTransformer


class EmbedderModel:
    def __init__(self, model_name="BAAI/bge-small-zh-v1.5"):
        self.model = SentenceTransformer(model_name)
        print(f"Embedding模型加载成功: {model_name}")

    def encode(self, texts):
        return self.model.encode(texts, convert_to_numpy=True).tolist()
