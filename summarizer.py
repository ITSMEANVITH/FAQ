
from ai_client import chat


def summarize_text(text):
    if not text or not text.strip():
        return "No readable text was found to summarize."

    messages = [
        {
            "role": "system",
            "content": (
                "You are a document summarization assistant. "
                "Summarize only the information in the supplied text. "
                "Preserve important names, dates, amounts, and facts. "
                "Do not invent information. "
                "Use a clear heading and concise bullet points. "
                "If information is missing, do not guess."
            ),
        },
        {
            "role": "user",
            "content": (
                "Summarize the following document text:\n\n"
                + text
            ),
        },
    ]

    try:
        return chat(messages, temperature=0.2)
    except Exception as exc:
        print(f"Summary generation failed: {exc}")
        return (
            "Summary generation is currently unavailable. "
            "Please check your cloud AI configuration and try again."
        )


def summarize_documents(chunks):
    if not chunks:
        return "Please upload and process documents first."

    text_parts = []

    for chunk in chunks:
        source = chunk.get("source", "Unknown document")
        page = chunk.get("page")
        chunk_text = str(chunk.get("text", ""))

        label = source

        if page is not None:
            label += f", page {page}"

        text_parts.append(
            f"Source: {label}\n{chunk_text}"
        )

    combined_text = "\n\n".join(text_parts)

    return summarize_text(combined_text)
