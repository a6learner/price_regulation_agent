import chromadb


class VectorDatabase:
    def __init__(self, persist_dir="data/rag/chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.laws_collection = None
        self.cases_collection = None

    def create_collections(self):
        self.laws_collection = self.client.get_or_create_collection(
            name="price_regulation_laws",
            metadata={"description": "法律法规条文库"}
        )
        self.cases_collection = self.client.get_or_create_collection(
            name="price_regulation_cases",
            metadata={"description": "处罚案例库"}
        )

    def add_documents(self, collection_name, ids, documents, embeddings, metadatas):
        collection = getattr(self, f"{collection_name}_collection")
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
