from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

# 최신 방식으로 Chroma 클라이언트 초기화
client = PersistentClient(path="./chroma_storage")
collection = client.get_or_create_collection(name="mentor_history")

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_text(text: str) -> list[float]:
    return model.encode([text])[0].tolist()

def upsert_vector(id: str, text: str, metadata: dict):
    embedding = embed_text(text)
    collection.add(
        ids=[id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[metadata]
    )

def query_vector(query: str, top_k: int = 5):
    vector = embed_text(query)
    return collection.query(
        query_embeddings=[vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )