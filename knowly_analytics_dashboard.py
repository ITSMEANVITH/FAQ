"""Knowly Analytics Dashboard — lightweight, local-only Streamlit dashboard."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import os

import streamlit as st


def render_analytics_dashboard():
    """Render analytics from the existing Knowly session state; no database migration."""
    chunks = st.session_state.get("chunks", []) or []
    documents = st.session_state.get("document_names", []) or []
    messages = st.session_state.get("messages", []) or []
    bookmarks = st.session_state.get("bookmarks", []) or []

    user_messages = [m for m in messages if str(m.get("role", "")).lower() == "user"]
    assistant_messages = [m for m in messages if str(m.get("role", "")).lower() == "assistant"]
    answered = [m for m in assistant_messages if m.get("content")]
    chunk_counts = Counter(str(c.get("source", "Unknown document")) for c in chunks)
    ext_counts = Counter(Path(str(name)).suffix.lower().lstrip(".") or "unknown" for name in documents)
    total_chars = sum(len(str(c.get("text", ""))) for c in chunks)
    total_words = sum(len(str(c.get("text", "")).split()) for c in chunks)

    st.markdown("## 📊 Knowly Analytics")
    st.caption("A live snapshot of this workspace. All figures are calculated locally from the current Knowly session.")

    a, b, c, d = st.columns(4)
    a.metric("Documents indexed", len(documents))
    b.metric("Searchable chunks", len(chunks))
    c.metric("Questions asked", len(user_messages))
    d.metric("Saved answers", len(bookmarks))

    st.divider()
    left, right = st.columns([1.15, 1])

    with left:
        st.markdown("### 📚 Knowledge base")
        m1, m2 = st.columns(2)
        m1.metric("Extracted words", f"{total_words:,}")
        m2.metric("Extracted characters", f"{total_chars:,}")
        if documents:
            st.markdown("**Documents by type**")
            import pandas as pd
            type_df = pd.DataFrame(
                [{"File type": f".{kind}" if kind != "unknown" else "Unknown", "Files": count}
                 for kind, count in sorted(ext_counts.items())]
            )
            st.bar_chart(type_df.set_index("File type"))
            st.markdown("**Indexed files**")
            for name in documents:
                st.write(f"📄 **{name}** — {chunk_counts.get(str(name), 0)} chunks")
        else:
            st.info("Upload and process a document to populate knowledge-base analytics.")

    with right:
        st.markdown("### 💬 Usage overview")
        st.progress(min(len(user_messages) / max(len(user_messages), 10), 1.0),
                    text=f"{len(user_messages)} user question(s) in the current chat history")
        st.write(f"**Assistant responses:** {len(answered)}")
        st.write(f"**Bookmarked answers:** {len(bookmarks)}")
        st.write(f"**Average chunks per document:** "
                 f"{(len(chunks) / len(documents)):.1f}" if documents else "**Average chunks per document:** —")
        if user_messages:
            st.markdown("**Recent questions**")
            for item in reversed(user_messages[-5:]):
                question = str(item.get("content", "")).strip()
                if question:
                    st.write("• " + (question[:180] + ("…" if len(question) > 180 else "")))
        else:
            st.caption("Questions will appear here after you chat with your documents.")

    st.divider()
    st.markdown("### 🧠 Local AI status")
    s1, s2, s3 = st.columns(3)
    s1.metric("Answer engine", "Ollama", help="Knowly's configured local model runtime.")
    s2.metric("Workspace storage", "SQLite", help="Knowly saves its workspace locally.")
    db_path = Path(__file__).with_name("knowly_workspace.sqlite3")
    s3.metric("Workspace database", "Found" if db_path.exists() else "Not created yet")
    try:
        import ollama
        models = ollama.list()
        model_items = models.get("models", []) if isinstance(models, dict) else getattr(models, "models", [])
        model_names = []
        for model in model_items:
            if isinstance(model, dict):
                model_names.append(model.get("name") or model.get("model") or "Unknown model")
            else:
                model_names.append(getattr(model, "model", None) or getattr(model, "name", None) or str(model))
        st.success("Ollama is reachable.")
        if model_names:
            st.write("**Installed models:** " + ", ".join(f"`{name}`" for name in model_names))
        else:
            st.info("Ollama is reachable, but no installed models were returned.")
    except Exception as exc:
        st.warning(f"Ollama status could not be checked: {exc}")
    st.caption("Privacy note: this dashboard does not send analytics to an external service. Usage counts reflect the messages currently available in Knowly's workspace, not a lifetime audit log.")
