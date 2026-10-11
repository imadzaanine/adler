from sentence_transformers import SentenceTransformer

EMBED_MODEL = "BAAI/bge-small-en-v1.5"   # 384 dimensions
_model = SentenceTransformer(EMBED_MODEL)

def embed(text: str) -> list[float]:
    return _model.encode(text, normalize_embeddings=True).tolist()