import logging
from typing import List
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Embedding model loaded successfully")
    return _model

def generate_embedding(text: str) -> List[float]:
    model = get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()

def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    logger.info("Generating embeddings for %d texts...", len(texts))
    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    logger.info("Embeddings generated successfully")
    return [emb.tolist() for emb in embeddings]
