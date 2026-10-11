
import ollama
import numpy as np

from functools import lru_cache
from sklearn.metrics.pairwise import cosine_similarity


# ---------------- CONFIGURATION ----------------

EMBEDDING_MODEL = "nomic-embed-text"
MIN_SIMILARITY = 0.45


# ---------------- EMBEDDINGS ----------------

@lru_cache(maxsize=4096)
def get_embedding(text):
    response = ollama.embed(
        model=EMBEDDING_MODEL,
        input=text
    )

    return tuple(response["embeddings"][0])


# ---------------- QUESTION DETECTION ----------------

def is_address_question(question):
    question = question.lower()

    keywords = [
        "address",
        "where is the office",
        "where is the company located",
        "office location",
        "company location"
    ]

    return any(keyword in question for keyword in keywords)


# ---------------- RETRIEVAL ----------------

def search_chunks(question, chunks, top_k=3):
    if not chunks or not question or not question.strip():
        return []

    question = question.strip()

    question_embedding = np.array(
        get_embedding(question)
    ).reshape(1, -1)

    chunk_embeddings = np.array([
        get_embedding(chunk["text"])
        for chunk in chunks
    ])

    scores = cosine_similarity(
        question_embedding,
        chunk_embeddings
    ).flatten()

    address_question = is_address_question(question)

    results = []

    for index, chunk in enumerate(chunks):
        text = chunk.get("text", "").strip()

        if not text:
            continue

        similarity = float(scores[index])
        text_lower = text.lower()

        # Recognize chunks containing an actual address.
        contains_address = (
            "outer ring road" in text_lower
            or "office address" in text_lower
            or "company address" in text_lower
        )

        # Use a separate ranking score.
        rank_score = similarity

        if address_question and contains_address:
            rank_score += 1.0

        # Keep normal relevance filtering for other chunks.
        if not address_question and similarity < MIN_SIMILARITY:
            continue

        # For address questions, retain the address chunk
        # even if its semantic score is below the threshold.
        if address_question and contains_address:
            pass
        elif similarity < MIN_SIMILARITY:
            continue

        result = chunk.copy()
        result["score"] = similarity
        result["_rank_score"] = rank_score

        results.append(result)

    results.sort(
        key=lambda item: item["_rank_score"],
        reverse=True
    )

    # Remove duplicate chunks.
    unique_results = []
    seen_texts = set()

    for result in results:
        normalized_text = " ".join(
            result["text"].lower().split()
        )

        if normalized_text in seen_texts:
            continue

        seen_texts.add(normalized_text)
        unique_results.append(result)

        if len(unique_results) >= top_k:
            break

    # Keep the internal ranking score out of the results.
    for result in unique_results:
        result.pop("_rank_score", None)

    return unique_results
