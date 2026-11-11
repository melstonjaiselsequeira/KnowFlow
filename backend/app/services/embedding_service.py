from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

model = SentenceTransformer(MODEL_NAME)


def generate_embedding(text: str) -> list:
    """
    Convert text into a 384-dimensional embedding vector.
    """

    if not text or not text.strip():
        raise ValueError("Cannot generate embedding for empty text")

    vector = model.encode(
        text,
        normalize_embeddings=True
    )

    return vector.tolist()


def generate_embeddings(texts: list) -> list:
    """
    Generate embeddings for multiple text chunks.
    """

    if not texts:
        return []

    vectors = model.encode(
        texts,
        normalize_embeddings=True
    )

    return [vector.tolist() for vector in vectors]
