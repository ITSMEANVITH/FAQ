
from document_pipeline import extract_document, split_into_chunks


class TestFile:
    def __init__(self, name, content):
        self.name = name
        self.content = content

    def getvalue(self):
        return self.content


sample_text = """
College Attendance Policy

Students must maintain 75 percent attendance.
Students should contact the academic office for clarification.
"""

uploaded_file = TestFile(
    "attendance.txt",
    sample_text.encode("utf-8")
)

pages = extract_document(uploaded_file)
chunks = split_into_chunks(pages)

print("Extracted text:")
print(pages)

print("\nGenerated chunks:")
for chunk in chunks:
    print(chunk)
