
from document_pipeline import extract_document, split_into_chunks
from retrieval import search_chunks

file_path = input("Enter the full path of your PDF: ").strip().strip('"')

class LocalPDF:
    def __init__(self, path):
        self.name = path.split("\\")[-1]
        with open(path, "rb") as file:
            self.content = file.read()

    def getvalue(self):
        return self.content


uploaded_file = LocalPDF(file_path)

pages = extract_document(uploaded_file)
chunks = split_into_chunks(pages)

question = "Who is the HR Manager?"
results = search_chunks(question, chunks, top_k=3)

print("\nRetrieved chunks:")

for result in results:
    print("\nSimilarity:", round(result["score"], 3))
    print("Source:", result["source"])
    print("Page:", result["page"])
    print("Text:", result["text"])
