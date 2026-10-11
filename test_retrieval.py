
from document_pipeline import split_into_chunks
from retrieval import search_chunks

pages = [
    {
        "source": "test.txt",
        "page": 1,
        "text": (
            "The HR Manager is Priya Menon. "
            "She works at TechNova Solutions Pvt. Ltd. "
            "The office is located in Bengaluru. "
            "The monthly internship stipend is Rs. 15,000. "
            "The internship lasts three months. "
            "The internship role is Backend Developer. "
            "Interns receive structured mentorship. "
            "The offer is valid for seven days."
        )
    }
]

chunks = split_into_chunks(
    pages,
    chunk_size=100,
    overlap=15
)

print("Total chunks:", len(chunks))

questions = [
    "Who is the HR Manager?",
    "How much is the monthly stipend?",
    "How long is the internship?",
    "Where is the office located?",
    "What is the capital of Japan?"
]

for question in questions:
    print("\nQuestion:", question)

    results = search_chunks(question, chunks, top_k=2)

    if not results:
        print("No relevant chunks found.")
        continue

    for result in results:
        print("Similarity:", round(result["score"], 3))
        print("Chunk ID:", result["chunk_id"])
        print("Text:", result["text"])
