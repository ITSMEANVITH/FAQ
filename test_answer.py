
from document_pipeline import split_into_chunks
from retrieval import search_chunks
from answer_generator import generate_answer

pages = [
    {
        "source": "test.txt",
        "page": 1,
        "text": (
            "The HR Manager is Priya Menon. "
            "The monthly internship stipend is Rs. 15,000. "
            "The internship lasts three months. "
            "The office is located in Bengaluru."
        )
    }
]

chunks = split_into_chunks(pages)

questions = [
    "Who is the HR Manager?",
    "How much is the monthly stipend?",
    "How long is the internship?",
    "Where is the office located?",
    "What is the CEO's name?"
]

for question in questions:
    print("\nQuestion:", question)

    results = search_chunks(question, chunks, top_k=3)
    answer = generate_answer(question, results)

    print("Answer:", answer["answer"])
    print("Sources:", answer["sources"])
