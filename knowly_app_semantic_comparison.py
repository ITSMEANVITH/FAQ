import html

import io
import json

import os

import re

import tempfile

from datetime import datetime

from knowly_analytics_dashboard import render_analytics_dashboard

from knowly_feedback import (

    make_answer_key,

    render_answer_feedback,

    render_feedback_dashboard,

)

import streamlit as st

import streamlit.components.v1 as components

from document_pipeline import extract_document, split_into_chunks

from retrieval import search_chunks

from answer_generator import generate_answer

from summarizer import summarize_documents

from knowly_plus import save_workspace, load_workspace, compare_documents, extract_flashcards, graph_html, document_sentences

try:

    import ollama

except ImportError:

    ollama = None

st.set_page_config(page_title="Knowly | AI Knowledge Workspace", page_icon="✳️", layout="wide", initial_sidebar_state="expanded")

DEFAULTS = {

    "chunks": [], "messages": [], "document_names": [], "document_summary": "",

    "processing_errors": [], "pending_question": "", "bookmarks": [], "theme": "Violet glass",

    "quiz": "", "comparison": "", "plus_comparison": None, "show_summary_dashboard": False, "document_file_bytes": {},

}

for key, value in DEFAULTS.items():

    if key not in st.session_state:

        st.session_state[key] = value

# Restore the last local workspace once per Streamlit session.

if "workspace_restore_attempted" not in st.session_state:

    st.session_state.workspace_restore_attempted = True

    saved_workspace = load_workspace()

    if saved_workspace and not st.session_state.chunks:

        for key in ("chunks", "document_names", "messages", "bookmarks", "document_summary"):

            if key in saved_workspace:

                st.session_state[key] = saved_workspace[key]

THEMES = {

    "Violet glass": {"bg": "#080a12", "panel": "rgba(19,24,42,.88)", "line": "rgba(153,164,255,.20)", "accent": "#9670ff", "text": "#f6f7ff", "muted": "#9ba9c8"},

    "Midnight cyan": {"bg": "#061015", "panel": "rgba(11,30,39,.9)", "line": "rgba(83,221,231,.22)", "accent": "#42d9e8", "text": "#f2feff", "muted": "#9abfc8"},

    "Warm light": {"bg": "#f3f5fb", "panel": "rgba(255,255,255,.94)", "line": "rgba(88,103,150,.22)", "accent": "#7054db", "text": "#1b2140", "muted": "#5d6684"},

}

t = THEMES.get(st.session_state.theme, THEMES["Violet glass"])

st.markdown(f"""

<style>

@import url('https\\://fonts.googleapis.com/css2?family=DM+Sans:wght\\@400;500;600;700&family=Space+Grotesk:wght\\@400;500;600;700&display=swap');

:root{{--bg:{t['bg']};--panel:{t['panel']};--line:{t['line']};--accent:{t['accent']};--text:{t['text']};--muted:{t['muted']};}}

html,body,[class*="css"]{{font-family:'DM Sans',sans-serif}}

.stApp{{color:var(--text);background:radial-gradient(ellipse at 78% -8%,color-mix(in srgb,var(--accent) 20%,transparent),transparent 35%),linear-gradient(145deg,var(--bg),color-mix(in srgb,var(--bg) 82%,var(--accent)) 100%)}}

[data-testid="stHeader"]{{background:transparent}}

[data-testid="stSidebar"]{{background:linear-gradient(160deg,var(--panel),var(--bg));border-right:1px solid var(--line)}}

h1,h2,h3{{font-family:'Space Grotesk',sans-serif!important;color:var(--text)!important;letter-spacing:-.035em}}

p,li,label,.stMarkdown{{color:var(--text)}}

.brand{{display:flex;align-items:center;gap:13px;margin:5px 0 28px}}.brand-icon{{width:54px;height:54px;border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:29px;color:white;background:linear-gradient(135deg,#c2a7ff,#6846ee);box-shadow:0 10px 30px #7753ff45,inset 0 1px 0 #ffffff77}}.brand-name{{font:700 27px 'Space Grotesk';color:var(--text)}}.brand-subtitle{{font-size:10px;letter-spacing:2px;color:var(--muted);margin-top:5px}}

.eyebrow{{font-size:10px;letter-spacing:4px;font-weight:700;color:var(--accent);text-transform:uppercase;margin-bottom:16px}}.hero-title{{font:700 clamp(38px,4.3vw,65px)/1.06 'Space Grotesk';letter-spacing:-3px;color:var(--text);margin:0}}.gradient-text{{background:linear-gradient(90deg,var(--accent),#8b9bff,#67e8f9);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}}.hero-description{{color:var(--muted);font-size:16px;line-height:1.8;max-width:760px;margin-top:20px}}

.glass-card{{position:relative;overflow:hidden;min-height:120px;padding:21px;border:1px solid var(--line);border-radius:21px;background:linear-gradient(145deg,var(--panel),color-mix(in srgb,var(--bg) 82%,var(--accent)));box-shadow:0 13px 28px #0002,inset 0 1px 0 #ffffff0d;transition:transform .22s,border-color .22s,box-shadow .22s}}.glass-card:hover{{transform:translateY(-4px) perspective(700px) rotateX(1deg);border-color:var(--accent);box-shadow:0 20px 38px #0003,0 0 20px color-mix(in srgb,var(--accent) 17%,transparent)}}.card-top{{display:flex;justify-content:space-between;color:var(--muted);font-size:11px;letter-spacing:1px;text-transform:uppercase}}.card-value{{font:700 31px 'Space Grotesk';margin-top:12px;color:var(--text)}}.card-caption{{font-size:12px;color:var(--muted);margin-top:3px}}

.stButton>button{{border-radius:12px;border:1px solid var(--line);color:var(--text);background:linear-gradient(145deg,var(--panel),color-mix(in srgb,var(--bg) 82%,var(--accent)));font-weight:600;min-height:42px;transition:transform .18s,border-color .18s,box-shadow .18s}}.stButton>button:hover{{border-color:var(--accent);transform:translateY(-2px);box-shadow:0 8px 22px color-mix(in srgb,var(--accent) 20%,transparent)}}.stButton>button[kind="primary"]{{background:linear-gradient(110deg,var(--accent),#6953f4);border:0;color:white;box-shadow:0 8px 22px color-mix(in srgb,var(--accent) 28%,transparent)}}

[data-testid="stFileUploader"]{{padding:12px;border-radius:16px;border:1px dashed var(--line);background:color-mix(in srgb,var(--bg) 86%,var(--accent))}}[data-testid="stChatMessage"]{{border:1px solid var(--line);border-radius:18px;background:linear-gradient(145deg,var(--panel),color-mix(in srgb,var(--bg) 88%,var(--accent)));padding:13px 16px;margin-bottom:10px;box-shadow:0 9px 22px #0002}}[data-testid="stMainBlockContainer"]{{padding-bottom:7rem!important}}[data-testid="stChatInput"]{{background:var(--panel);padding:10px 12px;border:1px solid var(--line);border-radius:16px;box-shadow:0 12px 34px #0003;backdrop-filter:blur(18px)}}[data-testid="stChatInput"] textarea{{background:var(--bg);border:1px solid var(--line);border-radius:15px;color:var(--text)}}[data-testid="stExpander"]{{border:1px solid var(--line);border-radius:13px;background:color-mix(in srgb,var(--bg) 82%,var(--accent))}}[data-testid="stMetric"]{{padding:12px;border-radius:13px;background:var(--panel);border:1px solid var(--line)}}hr{{border-color:var(--line)!important}}.footer{{text-align:center;padding:22px 0 8px;font-size:11px;color:var(--muted)}}

@media(max-width:800px){{.hero-title{{letter-spacing:-1.5px}}.hero-description{{font-size:14px}}.glass-card{{min-height:105px;padding:16px}}}}@media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation-duration:.01ms!important;transition-duration:.01ms!important}}}}

</style>""", unsafe_allow_html=True)

def stat_card(label, value, caption, icon):

    st.markdown(f'<div class="glass-card"><div class="card-top"><span>{html.escape(str(label))}</span><span>{icon}</span></div><div class="card-value">{html.escape(str(value))}</div><div class="card-caption">{html.escape(str(caption))}</div></div>', unsafe_allow_html=True)

def unique_sources(sources):

    output, seen = [], set()

    for source in sources or []:

        key = (source.get("source"), source.get("page"))

        if key not in seen:

            seen.add(key)

            output.append(source)

    return output



def render_multi_document_intelligence():
    """Compare indexed documents and answer cross-document questions with evidence."""
    st.markdown("### 🧠 Multi-document Intelligence")
    st.caption(
        "Compare shared facts, differences, and gaps across uploaded documents. "
        "Results use the text currently indexed in Knowly."
    )

    names = st.session_state.get("document_names", [])
    chunks = st.session_state.get("chunks", [])
    if len(names) < 2:
        st.info("Upload and process at least two documents to use cross-document intelligence.")
        return

    selected_docs = st.multiselect(
        "Documents to compare",
        options=names,
        default=names[:min(4, len(names))],
        key="multi_intel_docs",
    )
    if len(selected_docs) < 2:
        st.warning("Select at least two documents.")
        return

    selected_chunks = [
        chunk for chunk in chunks
        if str(chunk.get("source", "")) in selected_docs and str(chunk.get("text", "")).strip()
    ]
    if not selected_chunks:
        st.warning("No indexed text found for the selected documents.")
        return

    with st.expander("📄 Selected document overview", expanded=False):
        for name in selected_docs:
            doc_chunks = [c for c in selected_chunks if str(c.get("source", "")) == name]
            word_count = sum(len(str(c.get("text", "")).split()) for c in doc_chunks)
            st.write(f"**{name}** — {len(doc_chunks)} chunks · {word_count:,} words")

    mode = st.radio(
        "Analysis type",
        ["Compare shared facts and differences", "Ask a cross-document question"],
        horizontal=True,
        key="multi_intel_mode",
    )

    if mode == "Compare shared facts and differences":
        if st.button("🔍 Compare selected documents", type="primary", key="run_multi_document_compare"):
            try:
                # Ask the local model to compare meaning, not just identical sentences.
                comparison_context = make_context(selected_chunks, limit=14000)
                comparison_prompt = (
                    "Compare the selected documents semantically. Identify: "
                    "(1) facts that are shared or mean essentially the same thing even if worded differently, "
                    "(2) facts unique to each document, and (3) possible conflicts or inconsistencies. "
                    "Use only the provided document context. For every finding, name the source document "
                    "and page when available. Never claim a fact is shared unless evidence from at least "
                    "two different documents supports it. If a document simply omits a topic, describe it "
                    "as 'not found in this document', not as a contradiction. Do not invent facts. "
                    "Use these headings: SEMANTICALLY SHARED FACTS, DOCUMENT-SPECIFIC FACTS, "
                    "POSSIBLE CONFLICTS / GAPS, LIMITATIONS. Keep the result concise and evidence-grounded."
                )
                semantic_result = ollama_generate(
                    comparison_prompt,
                    comparison_context,
                    "You are Knowly's careful document-comparison engine. Compare meanings conservatively. "
                    "Distinguish shared facts from similar topics and from missing information. Cite source labels "
                    "exactly as they appear in the supplied context."
                )
                # Preserve exact-match extraction as a deterministic companion view.
                grouped = {}
                for chunk in selected_chunks:
                    source = str(chunk.get("source", "Unknown"))
                    page = chunk.get("page")
                    chunk_text = str(chunk.get("text", "")).strip()
                    for sentence in re.split(r"(?<=[.!?])\s+|\n+", chunk_text):
                        sentence = sentence.strip()
                        if len(sentence) < 18:
                            continue
                        normalized = re.sub(r"\W+", " ", sentence.casefold()).strip()
                        if normalized:
                            grouped.setdefault(normalized, {"text": sentence, "sources": []})
                            ref = {"source": source, "page": page}
                            if ref not in grouped[normalized]["sources"]:
                                grouped[normalized]["sources"].append(ref)

                exact_shared = [
                    item for item in grouped.values()
                    if len({s["source"] for s in item["sources"]}) >= 2
                ]
                unique = [
                    item for item in grouped.values()
                    if len({s["source"] for s in item["sources"]}) == 1
                ]
                st.session_state["multi_intel_comparison"] = {
                    "semantic_result": semantic_result,
                    "shared": exact_shared[:30],
                    "unique": unique[:60],
                    "documents": selected_docs,
                }
            except Exception as error:
                st.session_state["multi_intel_error"] = str(error)

    else:
        cross_question = st.text_input(
            "Your question",
            placeholder="e.g. What details are shared, and what differs?",
            key="multi_intel_question",
        )
        if st.button(
            "💬 Answer using selected documents",
            type="primary",
            key="run_multi_document_question",
            disabled=not cross_question.strip(),
        ):
            try:
                # Prefer retrieved evidence restricted to selected documents.
                search_results = search_chunks(cross_question, selected_chunks)
                if not search_results:
                    search_results = selected_chunks[:8]
                answer_obj = generate_answer(cross_question, search_results)
                if isinstance(answer_obj, dict):
                    answer_text = str(answer_obj.get("answer", "No answer returned."))
                    sources = answer_obj.get("sources", [])
                else:
                    answer_text, sources = str(answer_obj), []
                st.session_state["multi_intel_answer"] = {
                    "question": cross_question,
                    "answer": answer_text,
                    "sources": sources,
                    "selected_documents": selected_docs,
                    "evidence": search_results,
                }
            except Exception as error:
                st.session_state["multi_intel_error"] = str(error)

    if st.session_state.get("multi_intel_error"):
        st.error("Cross-document question failed: " + str(st.session_state.pop("multi_intel_error")))

    comparison = st.session_state.get("multi_intel_comparison")
    if comparison and comparison.get("documents") == selected_docs:
        st.markdown("#### 🧠 Semantic comparison")
        st.markdown(
            comparison.get("semantic_result", "Semantic comparison was not generated.")
        )
        st.caption(
            "The local AI compares meaning across documents. Treat possible conflicts as review candidates "
            "and verify them against the source passages."
        )

        st.markdown("#### 🔗 Exact sentence matches")
        if comparison["shared"]:
            for item in comparison["shared"]:
                st.markdown(f"- {html.escape(item['text'])}")
                st.caption("Found in: " + ", ".join(
                    f"{ref['source']}" + (f" · page {ref['page']}" if ref.get("page") is not None else "")
                    for ref in item["sources"]
                ))
        else:
            st.info("No identical or normalized sentences were found. Semantic similarities, if any, are summarized above.")

        st.markdown("#### 🧩 Document-specific facts")
        if comparison["unique"]:
            for item in comparison["unique"]:
                ref = item["sources"][0]
                with st.expander(f"{ref['source']}" + (f" · page {ref['page']}" if ref.get("page") is not None else "") + f" — {item['text'][:95]}"):
                    st.write(item["text"])
        else:
            st.info("No document-specific sentences were extracted.")

        st.caption(
            "This exact-match list only finds identical/normalized sentences. The semantic comparison above uses the local AI "
            "to identify differently worded facts; verify each finding against the cited source text."
        )

    answer = st.session_state.get("multi_intel_answer")
    if answer and answer.get("selected_documents") == selected_docs:
        st.markdown("#### 💬 Cross-document answer")
        st.markdown(answer["answer"])
        if answer.get("sources"):
            st.markdown("**Sources returned by the answer engine**")
            for source in answer["sources"]:
                label = str(source.get("source", "Unknown source"))
                if source.get("page") is not None:
                    label += f" · page {source['page']}"
                st.write("📄 " + label)
        with st.expander("🔎 Evidence used", expanded=False):
            for i, chunk in enumerate(answer.get("evidence", []), start=1):
                title = f"{i}. {chunk.get('source', 'Unknown source')}"
                if chunk.get("page") is not None:
                    title += f" · page {chunk['page']}"
                with st.expander(title, expanded=False):
                    st.write(chunk.get("text", ""))


def highlight_text_html(text, query):
    """Escape source text and highlight matching search terms for safe HTML display."""
    safe_text = html.escape(str(text or ""))
    terms = [term for term in re.findall(r"\w+", query or "") if len(term) > 1]
    for term in sorted(set(terms), key=len, reverse=True)[:8]:
        pattern = re.compile(re.escape(html.escape(term)), re.IGNORECASE)
        safe_text = pattern.sub(lambda match: f"<mark style='background:#ffe082;color:#222;border-radius:3px;padding:0 2px'>{match.group(0)}</mark>", safe_text)
    return safe_text


def render_document_reader():
    """Render an in-app text search reader and PDF page preview for current-session uploads."""
    st.markdown("### 📖 Document Reader")
    st.caption("Search extracted document text, inspect matching passages, and preview PDF pages. Uploaded-file previews are available while the files remain in this session.")

    names = st.session_state.get("document_names", [])
    chunks = st.session_state.get("chunks", [])
    if not names or not chunks:
        st.info("Upload and process a document first to use the Document Reader.")
        return

    selected_name = st.selectbox("Choose a document", names, key="reader_selected_document")
    search_query = st.text_input(
        "Search inside this document",
        placeholder="e.g. stipend, training schedule, company name…",
        key="reader_search_query",
    )

    doc_chunks = [chunk for chunk in chunks if str(chunk.get("source", "")) == selected_name]
    if search_query.strip():
        terms = [term.casefold() for term in re.findall(r"\w+", search_query) if len(term) > 1]
        matching = [
            chunk for chunk in doc_chunks
            if all(term in str(chunk.get("text", "")).casefold() for term in terms)
        ] if terms else []
        st.markdown(f"**{len(matching)} matching passage(s)**")
        if matching:
            for idx, chunk in enumerate(matching[:20], start=1):
                page = chunk.get("page")
                title = f"Match {idx}" + (f" · page {page}" if page is not None else "")
                with st.expander(title, expanded=(idx == 1)):
                    st.markdown(
                        highlight_text_html(chunk.get("text", ""), search_query),
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No passages matched every search term. Try fewer or shorter keywords.")
    else:
        st.markdown("**Extracted text**")
        for idx, chunk in enumerate(doc_chunks[:20], start=1):
            page = chunk.get("page")
            with st.expander(f"Passage {idx}" + (f" · page {page}" if page is not None else ""), expanded=(idx == 1)):
                st.write(chunk.get("text", ""))

    if selected_name.lower().endswith(".pdf"):
        raw_pdf = st.session_state.get("document_file_bytes", {}).get(selected_name)
        if raw_pdf:
            st.divider()
            st.markdown("#### 🗎 PDF page preview")
            try:
                import fitz
                with fitz.open(stream=raw_pdf, filetype="pdf") as pdf:
                    if len(pdf) == 0:
                        st.info("This PDF has no pages to preview.")
                    else:
                        page_num = st.number_input(
                            "PDF page number", min_value=1, max_value=len(pdf), value=1,
                            step=1, key="reader_pdf_page",
                        )
                        page = pdf.load_page(int(page_num) - 1)
                        pix = page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
                        st.image(pix.tobytes("png"), caption=f"{selected_name} · page {int(page_num)}", use_container_width=True)
            except ImportError:
                st.info("PDF preview needs PyMuPDF. Install it with: pip install pymupdf")
            except Exception as error:
                st.warning(f"Could not render this PDF page: {error}")
        else:
            st.caption("PDF page preview is unavailable after a workspace restore because original file bytes are not stored in the workspace database. Re-upload and process this PDF to enable page previews.")


def render_sources(sources, diagnostics=None, key_prefix="source"):
    """Show source references with clickable controls to inspect matching passages."""
    if not sources:
        return

    diagnostics = diagnostics or []
    clean_sources = unique_sources(sources)

    with st.expander("📚 View sources · click a citation to inspect evidence", expanded=False):
        for index, source in enumerate(clean_sources, start=1):
            name = str(source.get("source", "Unknown document"))
            page = source.get("page")
            label = f"[{index}] {name}" + (f" · page {page}" if page is not None else "")
            st.markdown(f"**{index}. {html.escape(name)}**" + (f" · page {html.escape(str(page))}" if page is not None else ""))

            matches = []
            for item in diagnostics:
                same_name = str(item.get("source", "")) == name
                same_page = page is None or item.get("page") is None or str(item.get("page")) == str(page)
                if same_name and same_page and str(item.get("text", "")).strip():
                    matches.append(item)

            if matches:
                button_key = f"{key_prefix}_inspect_{index}_{re.sub(r'[^a-zA-Z0-9]', '', name)[:12]}"
                if st.button(f"🔎 Inspect citation [{index}]", key=button_key):
                    st.session_state[f"{button_key}_open"] = not st.session_state.get(f"{button_key}_open", False)

                if st.session_state.get(f"{button_key}_open", False):
                    for passage_index, passage in enumerate(matches[:3], start=1):
                        if passage.get("page") is not None:
                            st.caption(f"Passage {passage_index} · page {passage['page']}")
                        st.info(str(passage.get("text", "")).strip())
            else:
                st.caption("No matching passage text was saved for this source reference.")

def render_diagnostics(diagnostics, key_prefix):

    if not diagnostics:

        return

    with st.expander("🔎 Retrieval diagnostics · inspect evidence", expanded=False):

        st.caption("Higher similarity scores indicate closer semantic matches.")

        for index, item in enumerate(diagnostics, start=1):

            title = f"Chunk {index} · {float(item.get('score', 0.0)):.3f} · {item.get('source', 'Unknown document')}"

            with st.expander(title, expanded=False):

                if item.get("page") is not None:

                    st.caption(f"Page {item['page']}")

                st.write(item.get("text", "Retrieved text unavailable."))

def process_uploaded_files(uploaded_files):

    all_chunks, document_names, failed_files = [], [], []
    uploaded_bytes = {}

    progress = st.progress(0, text="Preparing your knowledge base...")

    for index, uploaded_file in enumerate(uploaded_files):

        try:

            raw_bytes = uploaded_file.getvalue()
            pages = extract_document(uploaded_file)

            chunks = split_into_chunks(pages)

            if chunks:

                all_chunks.extend(chunks)

                document_names.append(uploaded_file.name)
                uploaded_bytes[uploaded_file.name] = raw_bytes

            else:

                failed_files.append(f"{uploaded_file.name}: No readable text found.")

        except Exception as error:

            failed_files.append(f"{uploaded_file.name}: {error}")

        progress.progress((index + 1) / len(uploaded_files), text=f"Processing {uploaded_file.name}...")

    progress.empty()

    if all_chunks:

        st.session_state.chunks = all_chunks

        st.session_state.document_names = document_names
        st.session_state.document_file_bytes = uploaded_bytes

        st.session_state.messages = []

        st.session_state.document_summary = ""

        st.session_state.quiz = ""

        st.session_state.comparison = ""

        st.session_state.processing_errors = failed_files

        st.success(f"Indexed {len(document_names)} document(s) into {len(all_chunks)} text chunks.")

    else:

        st.session_state.chunks, st.session_state.document_names, st.session_state.messages = [], [], []
        st.session_state.document_file_bytes = {}

        st.session_state.document_summary, st.session_state.processing_errors = "", failed_files

        st.error("No readable document text was found.")

    for failure in failed_files:

        st.warning(failure)

def clear_workspace():

    """Clear current indexed content, chat history, and persisted workspace."""

    reset_values = {

        "chunks": [],

        "messages": [],

        "document_names": [],

        "document_file_bytes": {},

        "document_summary": "",

        "processing_errors": [],

        "pending_question": "",

        "quiz": "",

        "comparison": "",

        "plus_comparison": None,

        "show_summary_dashboard": False,

        "bookmarks": [],

    }

    for key, value in reset_values.items():

        st.session_state[key] = value

    for state_key in list(st.session_state.keys()):

        if str(state_key).startswith("speak_text_"):

            del st.session_state[state_key]

    try:

        save_workspace([], [], [], [], "")

    except Exception as error:

        st.sidebar.warning(f"Session cleared, but saved-state cleanup failed: {error}")

def export_text():

    lines = ["KNOWLY CHAT EXPORT", f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}", "=" * 48, ""]

    for item in st.session_state.messages:

        lines.append(f"{item['role'].upper()}\n{item['content']}\n")

        sources = item.get("sources", [])

        if sources:

            lines.append("Sources: " + "; ".join(str(s.get("source", "Unknown")) + (f" page {s['page']}" if s.get("page") else "") for s in sources))

            lines.append("")

    return "\n".join(lines)

def ollama_generate(prompt, context, system=None):

    if ollama is None:

        raise RuntimeError("The ollama Python package is not installed.")

    response = ollama.chat(model="llama3.2:3b", messages=[

        {"role": "system", "content": system or "Use only the supplied document context. Never invent facts. Be concise."},

        {"role": "user", "content": f"DOCUMENT CONTEXT:\n{context}\n\nTASK:\n{prompt}"},

    ], options={"temperature": 0.2})

    return response["message"]["content"].strip()

def make_context(chunks, limit=12000):

    parts, total = [], 0

    for chunk in chunks:

        text = chunk.get("text", "")

        label = f"[{chunk.get('source', 'Unknown')}" + (f", page {chunk['page']}" if chunk.get("page") is not None else "") + "]"

        piece = f"{label}\n{text}"

        if total + len(piece) > limit:

            piece = piece[:max(0, limit - total)]

        if piece:

            parts.append(piece)

            total += len(piece)

        if total >= limit:

            break

    return "\n\n---\n\n".join(parts)

def suggest_questions(chunks):

    text = "\n".join(c.get("text", "") for c in chunks)

    suggestions = ["What are the key facts in these documents?", "What important dates are mentioned?", "What names and roles are listed?", "What amounts or fees are mentioned?"]

    patterns = [

        (r"training schedule[^****\n****.]*", "What is the training schedule?"),

        (r"technical support email[^****\n****.]*", "What is the technical support email?"),

        (r"monthly stipend[^****\n****.]*", "What is the monthly stipend?"),

        (r"leave policy[^****\n****.]*", "What is the leave policy?"),

        (r"equipment policy[^****\n****.]*", "What is the equipment policy?"),

    ]

    lower = text.lower()

    for pattern, question in patterns:

        if re.search(pattern, lower, re.IGNORECASE) and question not in suggestions:

            suggestions.append(question)

    return suggestions[:8]



def assess_evidence_quality(question, answer_text, diagnostics, sources):
    """Heuristic evidence support assessment; never a calibrated confidence probability."""
    q = (question or "").casefold()
    answer = (answer_text or "").strip()
    answer_lower = answer.casefold()

    abstention_markers = (
        "could not find relevant information",
        "do not mention",
        "does not mention",
        "don't mention",
        "doesn't mention",
        "do not provide information",
        "does not provide information",
        "don't provide information",
        "doesn't provide information",
        "not mentioned in the documents",
        "not stated in the documents",
        "documents do not identify",
        "documents don't identify",
        "insufficient information",
        "i cannot determine",
        "i can't determine",
        "i cannot find",
        "i can't find",
        "not available in the provided",
        "something went wrong",
        "could not summarize",
    )

    # When the answer explicitly says the documents don't contain the requested fact,
    # don't label it "strong evidence" just because multiple passages were retrieved.
    explicit_abstention = any(marker in answer_lower for marker in abstention_markers)
    usable = [
        item for item in (diagnostics or [])
        if str(item.get("text", "")).strip()
    ]
    source_refs = [
        item for item in (sources or [])
        if item.get("source") or item.get("name")
    ]

    if explicit_abstention:
        return {
            "level": "Insufficient evidence",
            "detail": "Knowly's answer says the documents do not provide the requested fact. The retrieved passages may provide context, but they do not establish that missing fact.",
            "icon": "🛑",
            "score": None,
            "supported": False,
        }

    if not usable and not source_refs:
        return {
            "level": "Limited evidence",
            "detail": "No saved retrieval passages or source references are available to inspect for this answer.",
            "icon": "⚠️",
            "score": None,
            "supported": False,
        }

    scores = []
    for item in usable:
        try:
            scores.append(float(item.get("score", 0)))
        except (TypeError, ValueError):
            pass

    best = max(scores) if scores else None
    # Conservative label: retrieval quantity alone is not sufficient to call evidence strong.
    # "Strong" here means there are multiple inspectable passages and source references,
    # and the answer is not an explicit abstention. It still does not verify entailment.
    if len(usable) >= 2 and source_refs:
        level, icon = "Some evidence", "🟡"
        detail = f"{len(usable)} retrieved passage(s) and source reference(s) are available, but automatic checks do not prove that every claim is supported."
    else:
        level, icon = "Limited evidence", "⚠️"
        detail = "Some evidence may be available, but there is not enough inspectable support to assign a stronger label."

    if best is not None:
        detail += f" Best retrieval similarity: {best:.3f} (a retrieval signal, not a probability of correctness)."

    return {
        "level": level,
        "detail": detail,
        "icon": icon,
        "score": best,
        "supported": False,
    }

def render_evidence_quality(quality, key):
    """Show evidence support with clear limits; never label it as answer accuracy."""
    if not quality:
        return
    level = quality.get("level", "Limited evidence")
    detail = quality.get("detail", "Evidence details are unavailable.")
    with st.expander(f"{quality.get('icon', '🔎')} Evidence quality · {level}", expanded=False):
        st.write(detail)
        st.caption(
            "This is a heuristic based on retrieved passages and source references. "
            "It does not verify factual correctness or represent a probability."
        )

def generate_follow_up_questions(question, answer_text, evidence_chunks):
    """Create three document-grounded follow-up questions, with a safe fallback."""
    fallback = []
    try:
        fallback = [
            q for q in suggest_questions(evidence_chunks)
            if q.strip().lower() != question.strip().lower()
        ][:3]
    except Exception:
        fallback = []

    if not evidence_chunks or not answer_text or "something went wrong" in answer_text.lower():
        return fallback

    try:
        context = make_context(evidence_chunks, limit=6500)
        prompt = (
            "Suggest exactly 3 useful follow-up questions a user could ask next. "
            "Use only the supplied document evidence and the answer below. "
            "Questions must be distinct, specific, short, and answerable from the evidence. "
            "Do not answer the questions. Do not repeat the original question. "
            "Return only a numbered list with one question per line.\n\n"
            f"Original question: {question}\n\n"
            f"Answer already given: {answer_text[:2500]}"
        )
        raw = ollama_generate(
            prompt,
            context,
            "You generate concise follow-up questions for a private document Q&A assistant. "
            "Never invent details. Return only questions grounded in the provided evidence."
        )
        candidates = []
        for line in raw.splitlines():
            line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip().strip('"“”')
            if not line or "?" not in line:
                continue
            # If a line contains commentary, keep its first question only.
            line = line[:line.find("?") + 1].strip()
            if line and line.casefold() != question.strip().casefold():
                if line.casefold() not in {x.casefold() for x in candidates}:
                    candidates.append(line)
            if len(candidates) == 3:
                break
        return candidates or fallback
    except Exception:
        return fallback

def build_pdf(text):

    try:

        from reportlab.lib.pagesizes import letter

        from reportlab.lib.styles import getSampleStyleSheet

        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        from reportlab.lib import colors

        from xml.sax.saxutils import escape

    except ImportError:

        return None

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=48, leftMargin=48, topMargin=48, bottomMargin=48)

    styles = getSampleStyleSheet()

    story = []

    for paragraph in text.split("\n"):

        if paragraph.strip():

            story.append(Paragraph(escape(paragraph), styles["BodyText"]))

            story.append(Spacer(1, 7))

        else:

            story.append(Spacer(1, 5))

    doc.build(story)

    return buffer.getvalue()

def speak_button(text, key):

    # JSON encoding safely passes punctuation, apostrophes, and newlines into JavaScript.
    speech_text = json.dumps(str(text)[:5000], ensure_ascii=False)

    components.html(f"""
    <div style="font-family:Arial,sans-serif;color:#f6f7ff">
      <button id="knowly-speak-{key}" style="
        cursor:pointer;border:1px solid #8067db;border-radius:10px;
        padding:9px 13px;background:#171a2a;color:#eee;font-size:14px">
        🔊 Read answer aloud
      </button>
      <span id="knowly-speech-status-{key}" style="margin-left:8px;font-size:12px;color:#b8bde0"></span>
    </div>
    <script>
      (() => {{
        const button = document.getElementById("knowly-speak-{key}");
        const status = document.getElementById("knowly-speech-status-{key}");
        const text = {speech_text};

        if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {{
          button.disabled = true;
          status.textContent = "Text-to-speech is not supported by this browser.";
          return;
        }}

        button.addEventListener("click", () => {{
          try {{
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1;
            utterance.pitch = 1;
            utterance.onstart = () => {{ status.textContent = "Speaking…"; }};
            utterance.onend = () => {{ status.textContent = "Finished"; }};
            utterance.onerror = (event) => {{
              status.textContent = "Speech failed: " + (event.error || "browser error");
            }};
            window.speechSynthesis.speak(utterance);
            status.textContent = "Starting…";
          }} catch (error) {{
            status.textContent = "Could not start speech.";
          }}
        }});
      }})();
    </script>
    """, height=58)

# SIDEBAR

with st.sidebar:

    st.markdown('<div class="brand"><div class="brand-icon">✳</div><div><div class="brand-name">knowly</div><div class="brand-subtitle">AI KNOWLEDGE WORKSPACE</div></div></div>', unsafe_allow_html=True)

    st.markdown("### Your knowledge base")

    st.caption("Upload files to build a searchable, private knowledge base.")

    st.session_state.theme = st.selectbox("🎨 Workspace theme", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme))

    uploaded_files = st.file_uploader("Add documents", type=["pdf", "docx", "txt"], accept_multiple_files=True, help="Upload PDF, DOCX or TXT files.")

    if uploaded_files:

        st.caption(f"{len(uploaded_files)} file(s) selected · {sum(f.size for f in uploaded_files)/(1024*1024):.2f} MB total")

    if st.button("✦ Process documents", type="primary", use_container_width=True, disabled=not uploaded_files):

        process_uploaded_files(uploaded_files)

    if st.button("🧹 Clear workspace & old answers", use_container_width=True):

        clear_workspace()

        st.rerun()

    st.divider()

    render_analytics_dashboard()

    st.divider()

    st.markdown("### Workspace status")

    if st.session_state.chunks:

        st.success("Knowledge base ready")

        st.metric("Documents indexed", len(st.session_state.document_names))

        st.metric("Text chunks", len(st.session_state.chunks))

        with st.expander("📄 Indexed documents"):

            for name in st.session_state.document_names:

                st.write(f"• {name}")

        if st.session_state.processing_errors:

            with st.expander("⚠️ Files not processed"):

                for error in st.session_state.processing_errors:

                    st.warning(error)

        st.divider()

        st.markdown("### Document summary")

        if st.button("✨ Summarize all documents", use_container_width=True):

            with st.spinner("Summarizing your knowledge base..."):

                try:

                    st.session_state.document_summary = summarize_documents(st.session_state.chunks)

                    st.session_state.show_summary_dashboard = True

                except Exception as error:

                    st.error(f"Summary failed: {error}")

        if st.session_state.document_summary:

            with st.expander("📝 Read summary", expanded=True):

                st.markdown(st.session_state.document_summary)

        if st.button("🧠 Generate document quiz", use_container_width=True):

            with st.spinner("Building a quiz from your documents..."):

                try:

                    st.session_state.quiz = ollama_generate("Create 8 quiz questions based only on this context. Mix multiple-choice and short-answer questions. Put the answer key at the end and cite source filenames where possible.", make_context(st.session_state.chunks), "You create accurate study quizzes from documents. Do not add facts not present in context.")

                except Exception as error:

                    st.error(f"Quiz generation failed: {error}")

        if st.session_state.quiz:

            with st.expander("🧠 Your document quiz", expanded=True):

                st.markdown(st.session_state.quiz)

        if len(st.session_state.document_names) >= 2:

            st.divider()

            st.markdown("### Compare documents")

            left_doc = st.selectbox("First document", st.session_state.document_names, key="compare_left")

            right_options = [name for name in st.session_state.document_names if name != left_doc]

            right_doc = st.selectbox("Second document", right_options, key="compare_right")

            if st.button("⚖️ Compare selected files", use_container_width=True):

                left_chunks = [c for c in st.session_state.chunks if c.get("source") == left_doc]

                right_chunks = [c for c in st.session_state.chunks if c.get("source") == right_doc]

                context = f"DOCUMENT A: {left_doc}\n{make_context(left_chunks, 6000)}\n\nDOCUMENT B: {right_doc}\n{make_context(right_chunks, 6000)}"

                with st.spinner("Comparing document content..."):

                    try:

                        st.session_state.comparison = ollama_generate("Compare these two documents. Provide: shared topics, facts unique to A, facts unique to B, and any contradictions. If the documents are unrelated, say so. Use clear headings.", context, "You compare documents carefully. Do not assume a fact absent from a document. Distinguish explicit evidence from uncertainty.")

                    except Exception as error:

                        st.session_state.comparison = f"Comparison failed: {error}"

        if st.session_state.comparison:

            with st.expander("⚖️ Document comparison", expanded=True):

                st.markdown(st.session_state.comparison)

    else:

        st.info("Your workspace is waiting for its first documents.")

    st.divider()

    st.markdown("### Saved answers")

    st.caption(f"{len(st.session_state.bookmarks)} bookmarked answer(s)")

    if st.session_state.bookmarks:

        for i, item in enumerate(st.session_state.bookmarks):

            with st.expander(f"🔖 {item['question'][:42]}"):

                st.write(item["answer"])

                if st.button("Remove bookmark", key=f"remove_bookmark_{i}"):

                    st.session_state.bookmarks.pop(i)

                    st.rerun()

    st.markdown('<div class="footer">✳ Knowly · Local AI workspace<br>Your documents stay on your machine.</div>', unsafe_allow_html=True)

# HERO

st.markdown('<div class="eyebrow">YOUR PERSONAL KNOWLEDGE ENGINE</div><div class="hero-title">Your documents.<br><span class="gradient-text">Your answers.</span></div><div class="hero-description">Turn scattered files into searchable knowledge. Ask questions in plain language and explore answers grounded in your own files.</div><div class="privacy-pill">● Private, local AI processing</div>', unsafe_allow_html=True)

st.write("")

col1, col2, col3, col4 = st.columns(4)

with col1: stat_card("Documents", len(st.session_state.document_names), "Files indexed", "▤")

with col2: stat_card("Text chunks", len(st.session_state.chunks), "Searchable evidence", "⠿")

with col3: stat_card("Saved answers", len(st.session_state.bookmarks), "Your bookmarks", "🔖")

with col4: stat_card("AI engine", "Ollama", "Local model processing", "✳")

# FEATURES PANEL

if st.session_state.chunks:

    with st.expander("📊 Document insights dashboard", expanded=st.session_state.show_summary_dashboard):

        if not st.session_state.document_summary:

            st.info("Use 'Summarize all documents' in the sidebar to generate your overview.")

        else:

            st.markdown(st.session_state.document_summary)

        file_cols = st.columns(min(3, max(1, len(st.session_state.document_names))))

        for i, name in enumerate(st.session_state.document_names):

            with file_cols[i % len(file_cols)]:

                count = sum(1 for c in st.session_state.chunks if c.get("source") == name)

                st.metric(name, f"{count} chunks", "indexed")

# KNOWLY PLUS · additional workspace tools

if st.session_state.chunks:

    st.divider()

    st.markdown("## ✨ Knowly Plus")

    st.caption("Explore connected facts, inspect evidence, study your documents, and compare files.")

    plus_tabs = st.tabs([

    "🕸️ Knowledge graph",

    "🔬 Evidence",

    "⚖️ Compare",

    "🧠 Study mode",

    "💾 Workspace & exports",

    "⭐ Feedback analytics",

    "📖 Document Reader",

    "🧠 Multi-document AI",

])

    with plus_tabs[0]:

        st.markdown("### Explore your knowledge graph")

        st.caption("Nodes are candidate entities extracted from the text. Edges mean the entities appeared in the same text chunk; they do not prove a real-world relationship.")

        graph_doc, graph_nodes, graph_edges = graph_html(st.session_state.chunks)

        g1, g2 = st.columns(2)

        g1.metric("Entities", graph_nodes)

        g2.metric("Co-occurrence links", graph_edges)

        components.html(graph_doc, height=570, scrolling=False)

    with plus_tabs[1]:

        st.markdown("### Evidence inspector")

        st.caption("Review indexed passages and source locations. Similarity scores are retrieval signals, not calibrated probabilities of correctness.")

        if not st.session_state.messages:

            st.info("Ask a question below; each answer will include retrieved evidence when available.")

        for msg_index, item in enumerate(reversed(st.session_state.messages)):

            if item.get("role") != "assistant":

                continue

            with st.expander(f"Answer: {item.get('question', 'Saved response')[:100]}", expanded=False):

                st.markdown(item.get("content", ""))

                render_sources(item.get("sources", []), item.get("diagnostics", []), f"evidence_{msg_index}")

                diagnostics = item.get("diagnostics", [])

                if diagnostics:

                    for j, d in enumerate(diagnostics, 1):

                        with st.expander(f"Evidence {j} · similarity {float(d.get('score', 0)):.3f} · {d.get('source', 'Unknown')}"):

                            if d.get("page") is not None:

                                st.caption(f"Page {d['page']}")

                            st.write(d.get("text", "No passage text recorded."))

                else:

                    st.caption("No retrieval diagnostics were saved for this answer.")

    with plus_tabs[2]:

        st.markdown("### Evidence-first document comparison")

        if len(st.session_state.document_names) < 2:

            st.info("Upload and process at least two documents to compare them.")

        else:

            cmp_a = st.selectbox("Document A", st.session_state.document_names, key="plus_compare_a")

            cmp_b_options = [n for n in st.session_state.document_names if n != cmp_a]

            cmp_b = st.selectbox("Document B", cmp_b_options, key="plus_compare_b")

            if st.button("Compare facts", key="plus_compare_button", type="primary"):

                st.session_state.plus_comparison = compare_documents(st.session_state.chunks, cmp_a, cmp_b)

            comparison = st.session_state.get("plus_comparison")

            if comparison and comparison.get("a") == cmp_a and comparison.get("b") == cmp_b:

                st.info(comparison["note"])

                ca, cb = st.columns(2)

                with ca:

                    st.markdown(f"#### Unique to {cmp_a}")

                    for fact in comparison["only_a"]: st.markdown(f"- {fact}")

                    if not comparison["only_a"]: st.caption("No unique exact sentences found.")

                with cb:

                    st.markdown(f"#### Unique to {cmp_b}")

                    for fact in comparison["only_b"]: st.markdown(f"- {fact}")

                    if not comparison["only_b"]: st.caption("No unique exact sentences found.")

                st.markdown("#### Exact shared sentences")

                for fact in comparison["shared"]: st.markdown(f"- {fact}")

                if not comparison["shared"]: st.caption("No exact shared sentences found. Similar meaning may still exist with different wording.")

                st.markdown("#### Possible differences to review")

                if comparison["review"]:

                    for item in comparison["review"]:

                        st.warning(f"{item['field'].title()} may differ. A: {'; '.join(item['a'])} | B: {'; '.join(item['b'])}")

                else:

                    st.caption("No obvious field-level differences were detected by the simple rule-based checks.")

                comparison_text = f"DOCUMENT COMPARISON\nA: {cmp_a}\nB: {cmp_b}\n\nSHARED EXACT SENTENCES\n" + "\n".join(comparison["shared"]) + "\n\nUNIQUE TO A\n" + "\n".join(comparison["only_a"]) + "\n\nUNIQUE TO B\n" + "\n".join(comparison["only_b"])

                st.download_button("Download comparison as TXT", comparison_text, file_name="knowly_comparison.txt", mime="text/plain", key="download_plus_comparison")

    with plus_tabs[3]:

        st.markdown("### Study mode")

        st.caption("Cards and questions are built from text actually present in your documents. Check the cited source before relying on an answer.")

        cards = extract_flashcards(st.session_state.chunks, limit=30)

        if not cards:

            st.info("No suitable study facts were extracted. Try a text-based PDF, DOCX, or TXT file.")

        else:

            st.metric("Study cards available", len(cards))

            card_index = st.selectbox("Choose a flashcard", list(range(len(cards))), format_func=lambda i: f"Card {i+1}: {cards[i]['question']}", key="study_card_index")

            selected_card = cards[card_index]

            st.markdown(f"**Question**\n\n{selected_card['question']}")

            with st.expander("Reveal answer"):

                st.success(selected_card['answer'])

                source_label = str(selected_card.get("source", "Unknown"))

                if selected_card.get("page") is not None: source_label += f" · page {selected_card['page']}"

                st.caption("Source: " + source_label)

            st.divider()

            st.markdown("#### Quick check")

            if len(cards) >= 2:

                quiz_index = st.selectbox("Question", list(range(len(cards))), format_func=lambda i: cards[i]['question'], key="study_quiz_index")

                qcard = cards[quiz_index]

                # Candidate choices are other document-backed answers. Similar text may occur, so user sees the source-backed target.

                distractors = [c["answer"] for i, c in enumerate(cards) if i != quiz_index and c["answer"].strip().lower() != qcard["answer"].strip().lower()]

                options = list(dict.fromkeys([qcard["answer"]] + distractors[:3]))

                options = sorted(options, key=lambda x: (len(x), x.lower()))

                chosen = st.radio("Select the answer supported by the document", options, key="study_answer_choice")

                if st.button("Check answer", key="study_check_answer"):

                    if chosen.strip().lower() == qcard["answer"].strip().lower():

                        st.success("Correct — this matches the extracted document text.")

                    else:

                        st.error("Not quite. The source-backed answer is shown below.")

                    st.write("**Source-backed answer:** " + qcard["answer"])

                    st.caption("Source: " + str(qcard.get("source", "Unknown")) + (f" · page {qcard['page']}" if qcard.get("page") is not None else ""))

            else:

                st.info("Add more document facts to enable multiple-choice practice.")

            study_export = "KNOWLY STUDY CARDS\n\n" + "\n\n".join(f"Q: {c['question']}\nA: {c['answer']}\nSource: {c.get('source','Unknown')}" for c in cards)

            st.download_button("Export flashcards as TXT", study_export, file_name="knowly_flashcards.txt", mime="text/plain", key="export_flashcards")

    with plus_tabs[4]:

        st.markdown("### Persistent workspace")

        st.write("Knowly automatically saves your indexed text, chat, bookmarks, and summary in a local SQLite database on this computer.")

        if st.button("Save workspace now", type="primary", key="save_workspace_now"):

            try:

                save_workspace(st.session_state.chunks, st.session_state.document_names, st.session_state.messages, st.session_state.bookmarks, st.session_state.document_summary)

                st.success("Workspace saved locally.")

            except Exception as error:

                st.error(f"Could not save workspace: {error}")

        st.caption("Local database: knowly_workspace.sqlite3 next to app.py. Keep this file private because it contains your document text and chat history.")

        export_bundle = export_text()

        st.download_button("Export chat (TXT)", export_bundle, file_name="knowly_chat.txt", mime="text/plain", key="plus_export_chat_txt")

        pdf_bundle = build_pdf(export_bundle)

        if pdf_bundle:

            st.download_button("Export chat (PDF)", pdf_bundle, file_name="knowly_chat.pdf", mime="application/pdf", key="plus_export_chat_pdf")

        if st.session_state.document_summary:

            st.download_button("Export summary (TXT)", st.session_state.document_summary, file_name="knowly_summary.txt", mime="text/plain", key="plus_export_summary_txt")

        if st.session_state.get("quiz"):

            st.download_button("Export existing quiz (TXT)", st.session_state.quiz, file_name="knowly_quiz.txt", mime="text/plain", key="plus_export_quiz")

    with plus_tabs[5]:
        st.markdown("### ⭐ Answer quality tracker")
        st.caption(
            "Review ratings and identify answers that may need improvement."
        )
        render_feedback_dashboard()

    with plus_tabs[6]:
        render_document_reader()

    with plus_tabs[7]:
        render_multi_document_intelligence()


# EMPTY STATE / CHAT

if not st.session_state.chunks:

    st.divider()

    st.markdown("## Make your files work for you")

    st.write("1. Upload PDF, DOCX or TXT files.  2. Process documents.  3. Ask questions and inspect evidence.")

    st.info("No documents are currently indexed, so Knowly will not generate document-based answers. If old content was restored earlier, use **Clear workspace & old answers** in the sidebar.")

else:

    st.divider()

    top_a, top_b, top_c = st.columns([3, 1, 1])

    with top_a:

        st.markdown("## ✦ Ask your documents")

        st.caption("Answers grounded in retrieved document evidence.")

    with top_b:

        if st.button("🗑 Clear chat", use_container_width=True):

            st.session_state.messages = []

            st.session_state.pending_question = ""

            st.rerun()

    with top_c:

        if st.button("🔖 Bookmarks", use_container_width=True):

            st.session_state.pending_question = "__SHOW_BOOKMARKS__"

            st.rerun()

    with st.expander("⬇️ Export conversation", expanded=False):

        export_data = export_text()

        st.download_button("Download chat as TXT", export_data, file_name="knowly_chat.txt", mime="text/plain", use_container_width=True)

        pdf_data = build_pdf(export_data)

        if pdf_data:

            st.download_button("Download chat as PDF", pdf_data, file_name="knowly_chat.pdf", mime="application/pdf", use_container_width=True)

        else:

            st.caption("PDF export needs reportlab. Install it with: pip install reportlab")

        if st.session_state.document_summary:

            st.download_button("Download document summary", st.session_state.document_summary, file_name="knowly_summary.md", mime="text/markdown", use_container_width=True)

    if st.session_state.pending_question == "__SHOW_BOOKMARKS__":

        st.session_state.pending_question = ""

        st.info("Your saved answers are listed in the sidebar under Saved answers.")

    st.caption("TRY ASKING · SMART SUGGESTIONS FROM YOUR DOCUMENTS")

    suggestions = suggest_questions(st.session_state.chunks)

    suggestion_cols = st.columns(4)

    for i, suggestion in enumerate(suggestions[:8]):

        with suggestion_cols[i % 4]:

            if st.button(suggestion, key=f"smart_suggestion_{i}", use_container_width=True):

                st.session_state.pending_question = suggestion

                st.rerun()

    with st.expander("🎙️ Ask by voice", expanded=False):

        st.caption("Record a question, then transcribe it locally with faster-whisper. The first use downloads the selected speech model.")

        voice_recording = st.audio_input("Record your question")

        if voice_recording and st.button("Transcribe recording", key="transcribe_voice"):

            try:

                from faster_whisper import WhisperModel

                audio_path = None

                try:

                    with st.spinner("Transcribing audio locally..."):

                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:

                            audio_file.write(voice_recording.getvalue())

                            audio_path = audio_file.name

                        # Beam search and voice activity detection help reduce

                        # filler words and hallucinations during pauses.

                        model = WhisperModel("base", device="cpu", compute_type="int8")

                        segments, _ = model.transcribe(

                            audio_path,

                            beam_size=5,

                            vad_filter=True,

                            condition_on_previous_text=False,

                            no_speech_threshold=0.6,

                            log_prob_threshold=-1.0,

                            compression_ratio_threshold=2.4,

                        )

                        transcript_parts = [

                            segment.text.strip()

                            for segment in segments

                            if segment.text and segment.text.strip()

                        ]

                        transcript = " ".join(transcript_parts).strip()

                    # Remove a few common speech fillers at the beginning/end,

                    # without rewriting the actual question.

                    transcript = re.sub(

                        r"^(?:(?:um+|uh+|erm+|hmm+|okay|ok|well|so)[,!.]?\s+)+",

                        "", transcript, flags=re.IGNORECASE

                    ).strip()

                    transcript = re.sub(r"\s+", " ", transcript)

                    if transcript:

                        st.session_state.pending_question = transcript

                        st.success(f"Recognized: {transcript}")

                        st.rerun()

                    else:

                        st.warning("No clear speech was recognized. Try recording a short question clearly, with less background noise.")

                finally:

                    if audio_path and os.path.exists(audio_path):

                        try:

                            os.remove(audio_path)

                        except OSError:

                            pass

            except ImportError:

                st.error("Voice transcription needs faster-whisper. Install it in your active .venv with: pip install faster-whisper")

            except Exception as error:

                st.error(f"Voice transcription failed: {error}")

    for index, message in enumerate(st.session_state.messages):

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

            if message["role"] == "assistant":

                quality = assess_evidence_quality(
                    message.get("question", ""),
                    message.get("content", ""),
                    message.get("diagnostics", []),
                    message.get("sources", []),
                )
                render_evidence_quality(
                    quality,
                    f"quality_{index}",
                )

                followups = message.get("follow_up_questions", [])
                if followups:
                    st.markdown("**↗ Ask a follow-up**")
                    followup_cols = st.columns(min(3, len(followups)))
                    for followup_index, followup in enumerate(followups[:3]):
                        with followup_cols[followup_index]:
                            if st.button(
                                followup,
                                key=f"followup_{index}_{followup_index}",
                                use_container_width=True,
                            ):
                                st.session_state.pending_question = followup
                                st.rerun()

                render_sources(message.get("sources", []), message.get("diagnostics", []), f"history_{index}")

                render_diagnostics(message.get("diagnostics", []), f"history_{index}")

                feedback_question = message.get("question", "")
                feedback_answer = message.get("content", "")
                feedback_key = make_answer_key(
                    feedback_question,
                    feedback_answer,
                )
                render_answer_feedback(
                    feedback_question,
                    feedback_answer,
                    feedback_key,
                )

                action_cols = st.columns([1, 4])
                with action_cols[0]:
                    if st.button("🔖 Save", key=f"bookmark_{index}"):
                        pair = {
                            "question": message.get("question", "Saved answer"),
                            "answer": message["content"],
                            "sources": message.get("sources", []),
                        }
                        if not any(b["answer"] == pair["answer"] for b in st.session_state.bookmarks):
                            st.session_state.bookmarks.append(pair)
                        st.toast("Answer saved to bookmarks")

                # One direct browser speech button; no extra click/rerun is needed.
                speak_button(message.get("content", ""), f"answer_{index}")

    typed_question = st.chat_input("Ask anything about your uploaded documents...")

    question = typed_question

    if not question and st.session_state.pending_question:

        question = st.session_state.pending_question

        st.session_state.pending_question = ""

    if question:

        if not st.session_state.chunks:

            st.warning("Your knowledge base is empty. Upload and process at least one document before asking questions.")

            st.session_state.pending_question = ""

            st.stop()

        st.session_state.messages.append({"role": "user", "content": question})

        lower = question.lower().strip()
        results = []

        if lower in {"summarize my documents", "summarize all documents", "summarize documents"}:

            with st.spinner("Summarizing your documents..."):

                try:

                    answer = {"answer": summarize_documents(st.session_state.chunks), "sources": [{"reference": f"[{i}]", "source": n, "page": None} for i, n in enumerate(st.session_state.document_names, 1)]}

                    diagnostics = []

                except Exception as error:

                    answer, diagnostics = {"answer": f"Could not summarize documents: {error}", "sources": []}, []

        elif lower in {"what are the key facts?", "show stipend details"}:

            with st.spinner("Finding key facts..."):

                try:

                    results = search_chunks(question, st.session_state.chunks, top_k=6)

                    diagnostics = [{"score": float(r.get("score", 0)), "source": r.get("source", "Unknown"), "page": r.get("page"), "text": r.get("text", "")} for r in results]

                    answer = generate_answer(question, results) if results else {"answer": "I could not find relevant information in the uploaded documents.", "sources": []}

                except Exception as error:

                    answer, diagnostics = {"answer": f"Something went wrong: {error}", "sources": []}, []

        elif len(question.split()) < 2:

            answer, diagnostics = {"answer": "Please ask a more specific question, such as 'What is the training schedule?'", "sources": []}, []

        else:

            with st.spinner("Searching evidence and generating your answer..."):

                try:

                    results = search_chunks(question, st.session_state.chunks, top_k=6)

                    diagnostics = [{"score": float(r.get("score", 0)), "source": r.get("source", "Unknown"), "page": r.get("page"), "text": r.get("text", "")} for r in results]

                    answer = generate_answer(question, results) if results else {"answer": "I could not find relevant information in the uploaded documents to answer this.", "sources": []}

                except Exception as error:

                    answer, diagnostics = {"answer": f"Something went wrong: {error}", "sources": []}, []

        # Generate optional next questions from the evidence used for this answer.
        evidence_for_followups = results if results else st.session_state.chunks
        follow_up_questions = generate_follow_up_questions(
            question,
            answer.get("answer", ""),
            evidence_for_followups,
        )
        evidence_quality = assess_evidence_quality(
            question,
            answer.get("answer", ""),
            diagnostics,
            answer.get("sources", []),
        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer["answer"],
            "question": question,
            "sources": answer.get("sources", []),
            "diagnostics": diagnostics,
            "follow_up_questions": follow_up_questions,
            "evidence_quality": evidence_quality,
        })

        st.rerun()

# Persist state on every normal rerun so the workspace survives browser refreshes/app restarts.

try:

    save_workspace(st.session_state.chunks, st.session_state.document_names, st.session_state.messages, st.session_state.bookmarks, st.session_state.document_summary)

except Exception as persistence_error:

    st.sidebar.caption(f"Workspace autosave unavailable: {persistence_error}")

st.markdown('<div class="footer">KNOWLY · YOUR FILES, YOUR KNOWLEDGE · BUILT WITH LOCAL AI</div>', unsafe_allow_html=True)
