
from pathlib import Path
import pymupdf

from document_pipeline import split_into_chunks
from retrieval import search_chunks

pdf_path = Path(
    r"C:\Users\gamer\Downloads\Exp06_Report.pdf"
)

pdf = pymupdf.open(pdf_path)

pages = []

for page_number, page in enumerate(pdf, start=1):
    text = page.get_text("text").strip()

    if text:
        pages.append({
            "source": pdf_path.name,
            "page": page_number,
            "text": text
        })

pdf.close()

chunks = split_into_chunks(pages)

print("\nADDRESS CHUNK CHECK:")

for chunk in chunks:
    if "outer ring road" in chunk["text"].lower():
        print("Found address in chunk:", chunk["chunk_id"])
        print("Address text:", chunk["text"])

questions = [
    "What is the office address?",
    "What is the monthly stipend?",
    "How long is the internship?"
]

for question in questions:
    print("\n" + "=" * 50)
    print("QUESTION:", question)

    results = search_chunks(question, chunks, top_k=3)

    if not results:
        print("No relevant chunks found.")
        continue

    for result in results:
        print("\nSimilarity:", round(result["score"], 3))
        print("Chunk ID:", result["chunk_id"])
        print("Text:", result["text"])
