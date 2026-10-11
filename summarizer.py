
import ollama


MODEL = "llama3.2:3b"


def summarize_text(text):
    if not text or not text.strip():
        return "No readable text was found to summarize."

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a document summarization assistant. "
                    "Summarize only the information in the supplied text. "
                    "Preserve important names, dates, amounts, and facts. "
                    "Do not invent information. "
                    "Use a clear heading and concise bullet points. "
                    "If information is missing, do not guess."
                )
            },
            {
                "role": "user",
                "content": (
                    "Summarize the following document text:\n\n"
                    + text
                )
            }
        ],
        options={"temperature": 0.2}
    )

    return response["message"]["content"]


def summarize_documents(chunks):
    if not chunks:
        return "Please upload and process documents first."

    text_parts = []

    for chunk in chunks:
        source = chunk.get("source", "Unknown document")
        page = chunk.get("page")

        label = source

        if page is not None:
            label += f", page {page}"

        text_parts.append(
            f"Source: {label}\n{chunk['text']}"
        )

    combined_text = "\n\n".join(text_parts)

    return summarize_text(combined_text)
